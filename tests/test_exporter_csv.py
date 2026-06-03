import asyncio
import csv

import pytest

from database.connection import db
from database.models import init_database
from database.repositories import product_repo
from services.exporter import CsvExportValidationError, exporter


def test_export_csv_tags_from_product_text():
    assert exporter._tags_from_text("RL 116515LN mete 2022//605,000 HKD") == "rolex,hk"
    assert exporter._tags_from_text("AP 15500 blue ready in hk") == "ap,hk"
    assert exporter._tags_from_text("Hublot 507.JX.0800.RT.TAK21 full set 2022//120,000 USDT") == "hublot,usdt"
    assert exporter._tags_from_text("RM 07-01RG snow like new 2020//229k USD") == "rm,usd"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hublot 682.SX.9800.LR.0999//12/2024//260.000 HKD", "Hublot 682.SX.9800.LR.0999"),
        ("Hublot 507.JX.0800.RT.TAK21 full set 2022//120.000 USDT", "Hublot 507.JX.0800.RT.TAK21"),
        (
            "Hublot MP-17 MECA-10 ARSHAM SPLASH titanium sapphire new 2025//55k USDT",
            "Hublot MP-17 MECA-10 ARSHAM SPLASH titanium sapphire",
        ),
        ("A.lange&sohne 182.886 new full set 12/2024//390.000 HKD", "A.lange&sohne 182.886"),
        (
            "Zenith Defy 03.A780.400-3/56.M3642 Limited Edition//10/2025//11,000 USDT",
            "Zenith Defy 03.A780.400-3/56.M3642 Limited Edition",
        ),
        ("RL 116515LN mete 2022//605.000 HKD", "RL 116515LN mete"),
        ("RL 278288RBR used 2020 340k HKD only watch", "RL 278288RBR"),
        ("AP 26240OR black full good full set 2023//105k USDT", "AP 26240OR black"),
        ("AP 67651ST white 2019//40k USDT", "AP 67651ST white"),
        ("AP 26540or/2016/899.000 HKD", "AP 26540or"),
        ("RM07-01 black ceramic black lips 2023//225k USDT", "RM07-01 black ceramic black lips"),
        ("AP 15450SR full set 2021 - 310,000 HKD", "AP 15450SR"),
        ("RM 07-01RG snow like new 2020//229k USDT", "RM 07-01RG snow"),
        ("PP 7118/1A grey like new 2022 - 560,000 HKD", "PP 7118/1A grey"),
    ],
)
def test_export_csv_title_uses_product_name_only(text, expected):
    assert exporter._title_from_text(text, "Item 1") == expected


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
