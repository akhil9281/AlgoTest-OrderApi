"""
Redis client utilities for connecting to Redis.

Provides helper functions to create Redis connections
with consistent configuration across services.
"""

import redis.asyncio as redis
import os
from typing import Optional


def get_redis_url() -> str:
    """
    Get Redis URL from environment variable.
    Falls back to localhost if not set.
    """
    return os.getenv("REDIS_URL", "redis://localhost:6379")


async def create_redis_client() -> redis.Redis:
    """
    Create an async Redis client instance.
    
    Returns:
        redis.Redis: Async Redis client
    """
    redis_url = get_redis_url()
    client = await redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    return client


async def create_redis_pool() -> redis.ConnectionPool:
    """
    Create a Redis connection pool for reuse.
    
    Returns:
        redis.ConnectionPool: Redis connection pool
    """
    redis_url = get_redis_url()
    pool = redis.ConnectionPool.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=10
    )
    return pool


class RedisClientManager:
    """
    Manages Redis client lifecycle for services.
    Ensures proper connection pooling and cleanup.
    """
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """Initialize Redis connection pool and client"""
        self.pool = await create_redis_pool()
        self.client = redis.Redis(connection_pool=self.pool)
    
    async def disconnect(self):
        """Close Redis connections"""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
    
    def get_client(self) -> redis.Redis:
        """Get the Redis client instance"""
        if not self.client:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self.client
