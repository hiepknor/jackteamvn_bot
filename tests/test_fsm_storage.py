import asyncio

from aiogram.fsm.storage.memory import MemoryStorage

from utils import fsm_storage


def test_memory_backend_does_not_try_redis(monkeypatch):
    monkeypatch.setattr(fsm_storage.settings, "FSM_BACKEND", "memory")
    monkeypatch.setattr(fsm_storage.settings, "REDIS_URL", "redis://redis:6379/0")

    class _FailRedis:
        @staticmethod
        def from_url(_url):
            raise AssertionError("Redis must not be touched when FSM_BACKEND=memory")

    monkeypatch.setattr(fsm_storage, "Redis", _FailRedis)

    storage, backend = asyncio.run(fsm_storage.create_fsm_storage())

    assert backend == "memory"
    assert isinstance(storage, MemoryStorage)
