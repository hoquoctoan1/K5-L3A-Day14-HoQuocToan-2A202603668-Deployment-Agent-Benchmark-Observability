"""Atomic sliding window shared across workers and replicas."""
import hashlib
import uuid
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

# Server time avoids clock skew; Lua makes pruning/counting/inserting atomic.
WINDOW_SCRIPT = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) + tonumber(clock[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - 60)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    return 0
end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('EXPIRE', KEYS[1], 60)
return 1
"""


def check_rate_limit(key: str) -> None:
    redis_key = "agent:rate:" + hashlib.sha256(key.encode()).hexdigest()
    allowed = r.eval(WINDOW_SCRIPT, 1, redis_key,
                     settings.rate_limit_per_minute, uuid.uuid4().hex)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded",
                            headers={"Retry-After": "60"})
