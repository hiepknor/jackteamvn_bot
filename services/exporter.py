import csv
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urljoin

from config import settings
from database.repositories import product_repo
from utils.logger import logger


class Exporter:
    """Exporter for Jack Stock Bot"""

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

        fieldnames = ["title", "captionText", "imageUrl"]

        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for index, row in enumerate(reversed(rows), 1):
                writer.writerow(
                    {
                        "title": f"Item {index}",
                        "captionText": row.get("normalized_text", ""),
                        "imageUrl": Exporter._image_url(
                            row.get("thumbnail_path"),
                            row.get("thumbnail_updated_at") or row.get("updated_at") or row.get("id"),
                        ),
                    }
                )

        logger.info("Exported %s products to CSV: %s", len(rows), path)
        Exporter.cleanup_old_files()
        return path


exporter = Exporter()
