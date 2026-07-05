import time
import redis
import os
from redis.exceptions import RedisError

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=2)

BUCKET_CAPACITY = 5      # max tokens
REFILL_RATE = 1           # tokens added per second

# Lua script for atomic rate limit check (prevents race conditions)
RATE_LIMIT_SCRIPT = r.register_script("""
local key = KEYS[1]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill_rate = tonumber(ARGV[3])

local data = redis.call('HGETALL', key)
local tokens, last_refill

if #data == 0 then
    tokens = capacity
    last_refill = now
else
    tokens = tonumber(data[2])
    last_refill = tonumber(data[4])
end

local elapsed = now - last_refill
tokens = math.min(capacity, tokens + elapsed * refill_rate)

if tokens < 1 then
    redis.call('HSET', key, 'tokens', tokens, 'last_refill', now)
    return 0
end

tokens = tokens - 1
redis.call('HSET', key, 'tokens', tokens, 'last_refill', now)
return 1
""")


def is_allowed(client_id: str) -> bool:
    """Token bucket rate limiter backed by Redis.

    Each client gets a bucket with BUCKET_CAPACITY tokens.
    Tokens refill at REFILL_RATE per second.
    Returns True if the request is allowed, False if rate limited.

    Storing state in Redis (not in-memory) means this works correctly
    even with multiple API replicas behind a load balancer.
    Uses a Lua script to atomically check and update to prevent race conditions.
    
    On Redis connection error, denies the request (fail closed) to prevent
    abuse if the rate limiter is unavailable.
    """
    key = f"bucket:{client_id}"
    now = time.time()
    try:
        result = RATE_LIMIT_SCRIPT(keys=[key], args=[now, BUCKET_CAPACITY, REFILL_RATE])
        return result == 1
    except RedisError as e:
        # Fail closed: if Redis is down, reject the request to prevent abuse
        print(f"Redis error in rate limiter: {e}")
        return False
