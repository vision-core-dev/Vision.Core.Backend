import os
import redis.asyncio as redis

async def connect_redis():
    client = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True
    )
    await client.set("test_key", "Redis connected!")
    print("Redis connected")
    return client

async def disconnect_redis(client: redis.Redis):
    if client:
        await client.close()
        print("Redis disconnected")
