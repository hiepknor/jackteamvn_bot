import asyncio
import sqlite3
from io import BytesIO

import pytest
from PIL import Image

from database.connection import db
from database.models import init_database
from database.repositories import product_repo
from services.thumbnail import thumbnail_service


def _sample_image() -> bytes:
    image = Image.new("RGB", (640, 480), color=(200, 40, 40))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_delete_product_removes_thumbnail_file(tmp_path):
    async def scenario():
        original_db_path = db.db_path
        try:
            db.db_path = str(tmp_path / "main.db")
            await db.connect()
            await init_database()

            product_id = await product_repo.create("RL 126528LN", user_id=1)
            thumbnail_path = thumbnail_service.save_jpeg_thumbnail(product_id, _sample_image())
            assert await product_repo.update_thumbnail(product_id, thumbnail_path, user_id=1)

            path = thumbnail_service.resolve_path(thumbnail_path)
            assert path is not None
            assert path.exists()

            deleted, product = await product_repo.delete(product_id, user_id=1)
            assert deleted
            assert product is not None
            assert not path.exists()
        finally:
            await db.close()
            db.db_path = original_db_path
            thumbnail_service.delete_thumbnail("storage/thumbnails/product_1.jpg")

    asyncio.run(scenario())


def test_failed_delete_keeps_thumbnail_file(tmp_path):
    async def scenario():
        original_db_path = db.db_path
        try:
            db.db_path = str(tmp_path / "main.db")
            await db.connect()
            await init_database()

            product_id = await product_repo.create("RL 126528LN", user_id=1)
            thumbnail_path = thumbnail_service.save_jpeg_thumbnail(product_id, _sample_image())
            assert await product_repo.update_thumbnail(product_id, thumbnail_path, user_id=1)

            path = thumbnail_service.resolve_path(thumbnail_path)
            assert path is not None
            assert path.exists()

            async with db.get_cursor() as cursor:
                await cursor.execute("DROP TABLE audit_log")

            with pytest.raises(sqlite3.OperationalError):
                await product_repo.delete(product_id, user_id=1)

            assert path.exists()
            product = await product_repo.get_by_id(product_id)
            assert product is not None
        finally:
            await db.close()
            db.db_path = original_db_path
            thumbnail_service.delete_thumbnail("storage/thumbnails/product_1.jpg")

    asyncio.run(scenario())
