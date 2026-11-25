"""Daily UTC spending persisted in Redis."""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = settings.price_input_per_1k
PRICE_OUTPUT_PER_1K = settings.price_output_per_1k


def _budget_key() -> str:
    return "agent:cost:" + datetime.now(timezone.utc).strftime("%Y-%m-%d")


def check_budget() -> None:
    if float(r.get(_budget_key()) or 0) >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exhausted")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000
    key = _budget_key()
    with r.pipeline(transaction=True) as pipeline:
        pipeline.incrbyfloat(key, cost)
        pipeline.expire(key, 172800)
        pipeline.execute()
    return cost
