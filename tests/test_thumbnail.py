import asyncio
from io import BytesIO

from PIL import Image

from services.thumbnail import MAX_THUMBNAIL_SIDE, thumbnail_service


def _sample_png(width: int = 1200, height: int = 800) -> bytes:
    image = Image.new("RGB", (width, height), color=(20, 120, 220))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_thumbnail_service_saves_resized_jpeg():
    relative_path = thumbnail_service.save_jpeg_thumbnail(999999, _sample_png())
    path = thumbnail_service.resolve_path(relative_path)

    try:
        assert relative_path == "storage/thumbnails/product_999999.jpg"
        assert path is not None
        assert path.exists()

        with Image.open(path) as image:
            assert image.format == "JPEG"
            assert max(image.size) <= MAX_THUMBNAIL_SIDE
    finally:
        thumbnail_service.delete_thumbnail(relative_path)


def test_thumbnail_delete_missing_file_is_noop():
    assert not thumbnail_service.delete_thumbnail("storage/thumbnails/does-not-exist.jpg")
