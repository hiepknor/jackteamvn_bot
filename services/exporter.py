import csv
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urljoin

from config import settings
from database.repositories import product_repo
from services.listing_parser import listing_parser
from utils.logger import logger


class CsvExportValidationError(ValueError):
    """Raised when product rows cannot satisfy the CSV import requirements."""


class Exporter:
    """Exporter for Jack Stock Bot"""

    @staticmethod
    def _title_from_text(text: str | None, fallback: str) -> str:
        return listing_parser.title_from_text(text, fallback)

    @staticmethod
    def _tags_from_text(text: str | None) -> str:
        return listing_parser.tags_from_text(text)

    @staticmethod
    def _media_asset_id(row: dict) -> str:
        return str(row.get("mediaAssetId") or row.get("media_asset_id") or "").strip()

    @staticmethod
    def _format_missing_media_error(missing_rows: list[dict]) -> str:
        total = len(missing_rows)
        preview_rows = missing_rows[:10]
        details = []
        for row in preview_rows:
            product_id = row.get("id", "N/A")
            title = Exporter._title_from_text(row.get("normalized_text"), f"Item #{product_id}")
            details.append(f"#{product_id} {title}")

        suffix = ""
        if total > len(preview_rows):
            suffix = f"; và {total - len(preview_rows)} sản phẩm khác"

        return (
            "CSV export yêu cầu mỗi sản phẩm có imageUrl hoặc mediaAssetId. "
            f"Có {total} sản phẩm thiếu thumbnail/mediaAssetId: {', '.join(details)}{suffix}"
        )

    @staticmethod
    def _image_url(thumbnail_path: str | None, version: object = None) -> str:
        path = (thumbnail_path or "").strip()
        if not path:
            return ""
        if path.startswith(("http://", "https://")):
            url = path
        else:
            base_url = settings.EXPORT_IMAGE_BASE_URL.strip()
            if not base_url:
                url = path
            else:
                url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))

        if not version:
            return url

        separator = "&" if "?" in url else "?"
        return f"{url}{separator}v={quote(str(version), safe='')}"

    @staticmethod
    def cleanup_old_files() -> None:
        """Xóa file export cũ, giữ lại N file gần nhất"""
        if not settings.export_dir.exists():
            return

        pattern = "products_*"
        files = sorted(settings.export_dir.glob(pattern), key=lambda path: path.stat().st_mtime)

        for old_file in files[:-settings.EXPORT_KEEP_COUNT]:
            try:
                old_file.unlink()
                logger.info("Deleted old export file: %s", old_file)
            except Exception as exc:
                logger.error("Failed to delete export file %s: %s", old_file, exc)

    @staticmethod
    async def export_to_txt() -> Path:
        """Export products to TXT file"""
        rows = await product_repo.get_all(limit=settings.MAX_EXPORT_ROWS)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = settings.export_dir / f"products_{timestamp}.txt"

        with path.open("w", encoding="utf-8") as f:
            for row in reversed(rows):
                f.write(f"{row['normalized_text']}\n")

        logger.info("Exported %s products to TXT: %s", len(rows), path)
        Exporter.cleanup_old_files()
        return path

    @staticmethod
    async def export_to_csv() -> Path:
        """Export products to CSV file"""
        rows = await product_repo.get_all(limit=settings.MAX_EXPORT_ROWS)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = settings.export_dir / f"products_{timestamp}.csv"

        fieldnames = ["intent", "title", "captionText", "imageUrl", "mediaAssetId", "tags"]
        csv_rows = []
        missing_media_rows = []

        for index, row in enumerate(reversed(rows), 1):
            caption_text = row.get("normalized_text", "")
            image_url = Exporter._image_url(
                row.get("thumbnail_path"),
                row.get("thumbnail_updated_at") or row.get("updated_at") or row.get("id"),
            )
            media_asset_id = Exporter._media_asset_id(row)
            if not image_url and not media_asset_id:
                missing_media_rows.append(row)

            csv_rows.append(
                {
                    "intent": "",
                    "title": Exporter._title_from_text(caption_text, f"Item {index}"),
                    "captionText": caption_text,
                    "imageUrl": image_url,
                    "mediaAssetId": media_asset_id,
                    "tags": Exporter._tags_from_text(caption_text),
                }
            )

        if missing_media_rows:
            raise CsvExportValidationError(Exporter._format_missing_media_error(missing_media_rows))

        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

        logger.info("Exported %s products to CSV: %s", len(rows), path)
        Exporter.cleanup_old_files()
        return path


exporter = Exporter()
