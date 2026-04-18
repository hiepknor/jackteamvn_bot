from __future__ import annotations

import asyncio
from typing import Tuple

from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from config import settings
from utils.logger import logger


async def create_fsm_storage() -> Tuple[BaseStorage, str]:
    """Create FSM storage from settings with safe fallback."""
    preferred = settings.FSM_BACKEND.lower()
    should_try_redis = preferred == "redis" or bool((settings.REDIS_URL or "").strip())

    if should_try_redis:
        try:
            redis = Redis.from_url(settings.REDIS_URL)
            await asyncio.wait_for(redis.ping(), timeout=2)
            logger.info("FSM backend initialized: redis")
            return RedisStorage(redis=redis), "redis"
        except Exception as exc:
            logger.warning("Redis FSM unavailable, fallback to memory storage: %s", exc)

    logger.info("FSM backend initialized: memory")
    return MemoryStorage(), "memory"
