"""Production agent with shared protections and structured logging."""
import json
import logging
import math
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname, "event": record.getMessage(),
            **getattr(record, "fields", {}),
        }, ensure_ascii=False)


logger = logging.getLogger("production_agent")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers = [handler]
logger.setLevel(logging.INFO)
logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"fields": {"environment": settings.environment}})
    yield
    # Uvicorn handles SIGTERM and drains requests before lifespan cleanup.
    r.close()
    logger.info("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.middleware("http")
async def log_request(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    logger.info("request", extra={"fields": {
        "method": request.method, "path": request.url.path,
        "status": response.status_code,
        "ms": round((time.perf_counter() - start) * 1000, 3),
    }})
    return response


@app.exception_handler(redis.RedisError)
async def redis_error(request: Request, exc: redis.RedisError):
    logger.warning("redis_unavailable")
    return JSONResponse(status_code=503, content={"detail": "State service unavailable"})


@app.get("/health")
def health():
    return {"status": "healthy", "environment": settings.environment}


@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"status": "ready"}


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    check_budget()
    try:
        answer = llm_ask(body.question)
    except Exception:
        logger.error("llm_error")
        raise HTTPException(status_code=502, detail="Model service unavailable") from None
    # Mock LLM supplies no provider usage: clearly mark a four-character estimate.
    input_tokens = max(1, math.ceil(len(body.question) / 4))
    output_tokens = max(1, math.ceil(len(answer) / 4))
    cost = record_cost(input_tokens, output_tokens)
    return {"question": body.question, "answer": answer,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "cost_usd": cost, "token_usage_estimated": True}
