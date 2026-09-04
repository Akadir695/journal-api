async def check_rate_limit(redis, key: str, limit: int, window: int) -> tuple[bool, int]:
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window)
    allowed = count <= limit
    remaining = max(0, limit - count)
    return allowed, remaining
