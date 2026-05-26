from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from config import settings
from utils.logger import logger

MAX_THUMBNAIL_SIDE = 512
JPEG_QUALITY = 85
THUMBNAIL_DIR_NAME = "thumbnails"


class ThumbnailService:
    """Persist product thumbnails as normalized local JPEG files."""

    @property
    def thumbnail_dir(self) -> Path:
        path = settings.storage_dir / THUMBNAIL_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    def relative_path_for(self, product_id: int) -> str:
        path = self.thumbnail_dir / f"product_{product_id}.jpg"
        return path.relative_to(settings.base_dir).as_posix()

    def resolve_path(self, relative_path: str | None) -> Path | None:
        if not relative_path:
            return None
        path = Path(relative_path)
        if path.is_absolute():
            return path
        return settings.base_dir / path

    def save_jpeg_thumbnail(self, product_id: int, image_bytes: bytes) -> str:
        relative_path = self.relative_path_for(product_id)
        output_path = self.resolve_path(relative_path)
        if output_path is None:
            raise ValueError("Cannot resolve thumbnail path")

        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            image.thumbnail((MAX_THUMBNAIL_SIDE, MAX_THUMBNAIL_SIDE), Image.Resampling.LANCZOS)
            image.save(output_path, format="JPEG", quality=JPEG_QUALITY, optimize=True)

        logger.info("Thumbnail saved | product_id=%s path=%s", product_id, relative_path)
        return relative_path

    def delete_thumbnail(self, relative_path: str | None) -> bool:
        path = self.resolve_path(relative_path)
        if not path or not path.exists():
            return False

        try:
            path.unlink()
            logger.info("Thumbnail deleted: %s", path)
            return True
        except OSError as exc:
            logger.warning("Failed deleting thumbnail %s: %s", path, exc)
            return False


thumbnail_service = ThumbnailService()
