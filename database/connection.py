import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from config import settings
from utils.logger import logger


class DatabaseConnection:
    """Async SQLite Database Connection for Jack Stock Bot"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None
    
    async def connect(self) -> None:
        """Establish database connection"""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        logger.info(f"Database connected: {self.db_path}")
    
    async def close(self) -> None:
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            logger.info("Database connection closed")
    
    @property
    def connection(self) -> aiosqlite.Connection:
        if not self._connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection
    
    @asynccontextmanager
    async def get_cursor(self) -> AsyncGenerator[aiosqlite.Cursor, None]:
        """Get cursor with auto-commit"""
        async with self.connection.cursor() as cursor:
            try:
                yield cursor
                await self.connection.commit()
            except Exception:
                await self.connection.rollback()
                raise


db = DatabaseConnection(str(settings.db_path))
