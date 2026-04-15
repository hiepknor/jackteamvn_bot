import csv
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from database.repositories import product_repo
from config import settings
from utils.logger import logger


class Exporter:
    """Exporter for Jack Stock Bot"""
    
    @staticmethod
    def cleanup_old_files() -> None:
        """Xóa file export cũ, giữ lại N file gần nhất"""
        if not settings.export_dir.exists():
            return
        
        pattern = "products_*"
        files = sorted(settings.export_dir.glob(pattern), key=os.path.getmtime)
        
        for old_file in files[:-settings.EXPORT_KEEP_COUNT]:
            try:
                old_file.unlink()
                logger.info(f"Deleted old export file: {old_file}")
            except Exception as e:
                logger.error(f"Failed to delete {old_file}: {e}")
    
    @staticmethod
    async def export_to_txt() -> Path:
        """Export products to TXT file"""
        rows = await product_repo.get_all(limit=settings.MAX_EXPORT_ROWS)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = settings.export_dir / f"products_{timestamp}.txt"
        
        with path.open("w", encoding="utf-8") as f:
            for row in reversed(rows):
                f.write(f"{row['raw_text']}\n")
        
        logger.info(f"Exported {len(rows)} products to TXT: {path}")
        Exporter.cleanup_old_files()
        return path
    
    @staticmethod
    async def export_to_csv() -> Path:
        """Export products to CSV file"""
        rows = await product_repo.get_all(limit=settings.MAX_EXPORT_ROWS)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = settings.export_dir / f"products_{timestamp}.csv"
        
        fieldnames = [
            "id", "raw_text", "brand", "model", "dial_desc", "condition",
            "date_info", "price_text", "currency", "note", "created_at", "updated_at"
        ]
        
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in reversed(rows):
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        
        logger.info(f"Exported {len(rows)} products to CSV: {path}")
        Exporter.cleanup_old_files()
        return path


# ✅ QUAN TRỌNG: Tạo instance
exporter = Exporter()
