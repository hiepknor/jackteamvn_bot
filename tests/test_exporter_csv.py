import asyncio
import csv

import pytest

from database.connection import db
from database.models import init_database
from database.repositories import product_repo
from services.exporter import CsvExportValidationError, exporter


def test_export_csv_uses_listing_schema(tmp_path, monkeypatch):
    async def scenario():
        original_db_path = db.db_path
        try:
            db.db_path = str(tmp_path / "main.db")
            monkeypatch.setattr(exporter, "cleanup_old_files", lambda: None)
            monkeypatch.setattr("services.exporter.settings.EXPORT_DIR", str(tmp_path / "exports"))
            monkeypatch.setattr("services.exporter.settings.EXPORT_IMAGE_BASE_URL", "https://example.com")

            await db.connect()
            await init_database()

            product_text = "PP 7118/1450G new 2026//1,450,000 HKD"
            product_id = await product_repo.create(product_text, user_id=1)
            assert await product_repo.update_thumbnail(
                product_id,
                "storage/thumbnails/product_1.jpg",
                user_id=1,
            )

            path = await exporter.export_to_csv()

            with path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert reader.fieldnames == ["intent", "title", "captionText", "imageUrl", "mediaAssetId", "tags"]
            assert rows[0]["intent"] == ""
            assert rows[0]["title"] == "PP 7118/1450G"
            assert rows[0]["captionText"] == product_text
            assert rows[0]["imageUrl"].startswith("https://example.com/storage/thumbnails/product_1.jpg?v=")
            assert rows[0]["mediaAssetId"] == ""
            assert rows[0]["tags"] == "pp,hk"
        finally:
            await db.close()
            db.db_path = original_db_path

    asyncio.run(scenario())


def test_export_csv_requires_image_or_media_asset(tmp_path, monkeypatch):
    async def scenario():
        original_db_path = db.db_path
        try:
            db.db_path = str(tmp_path / "main.db")
            export_dir = tmp_path / "exports"
            monkeypatch.setattr(exporter, "cleanup_old_files", lambda: None)
            monkeypatch.setattr("services.exporter.settings.EXPORT_DIR", str(export_dir))

            await db.connect()
            await init_database()

            product_id = await product_repo.create("RL 116515LN mete 2022//605,000 HKD", user_id=1)

            with pytest.raises(CsvExportValidationError) as exc_info:
                await exporter.export_to_csv()

            assert f"#{product_id}" in str(exc_info.value)
            assert "imageUrl hoặc mediaAssetId" in str(exc_info.value)
            assert list(export_dir.glob("*.csv")) == []
        finally:
            await db.close()
            db.db_path = original_db_path

    asyncio.run(scenario())
