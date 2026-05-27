import asyncio
import csv

from database.connection import db
from database.models import init_database
from database.repositories import product_repo
from services.exporter import exporter


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

            product_id = await product_repo.create("PP 7118/1450G new 2026", user_id=1)
            assert await product_repo.update_thumbnail(
                product_id,
                "storage/thumbnails/product_1.jpg",
                user_id=1,
            )

            path = await exporter.export_to_csv()

            with path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert reader.fieldnames == ["title", "captionText", "imageUrl"]
            assert rows[0]["title"] == "Item 1"
            assert rows[0]["captionText"] == "Looking for PP 7118/1450G new 2026"
            assert rows[0]["imageUrl"].startswith("https://example.com/storage/thumbnails/product_1.jpg?v=")
        finally:
            await db.close()
            db.db_path = original_db_path

    asyncio.run(scenario())
