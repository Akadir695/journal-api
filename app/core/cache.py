async def cache_get(redis, key: str) -> str | None:
    return await redis.get(key)


async def cache_set(redis, key: str, value: str, ttl: int) -> None:
    await redis.set(key, value, ex=ttl)


async def cache_delete(redis, *keys: str) -> None:
    if keys:
        await redis.delete(*keys)


async def cache_delete_user_stats(redis, user_id: int) -> None:
    async for key in redis.scan_iter(match=f"stats:*user:{user_id}"):
        await redis.delete(key)
