from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from config import settings
from database.connection import db
from utils.logger import logger


async def init_database() -> None:
    """Initialize database schema for Jack Stock Bot"""
    async with db.get_cursor() as cursor:
        # Products table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_text TEXT NOT NULL,
                normalizer_version TEXT NOT NULL DEFAULT 'v2',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        await cursor.execute("PRAGMA table_info(products)")
        product_columns = {row["name"] for row in await cursor.fetchall()}

        if "normalized_text" not in product_columns:
            await cursor.execute("ALTER TABLE products ADD COLUMN normalized_text TEXT")
            logger.info("Added products.normalized_text column")

        if "normalizer_version" not in product_columns:
            await cursor.execute(
                "ALTER TABLE products ADD COLUMN normalizer_version TEXT DEFAULT 'v2'"
            )
            logger.info("Added products.normalizer_version column")

        if "raw_text" in product_columns:
            await cursor.execute(
                """
                UPDATE products
                SET normalized_text = TRIM(raw_text)
                WHERE normalized_text IS NULL OR normalized_text = ''
            """
            )

        await cursor.execute(
            """
            UPDATE products
            SET normalized_text = ''
            WHERE normalized_text IS NULL
        """
        )
        await cursor.execute(
            """
            UPDATE products
            SET normalizer_version = 'v2'
            WHERE normalizer_version IS NULL OR normalizer_version = ''
        """
        )

        # Audit log table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Indexes for better performance
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at)")
        await cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_products_normalized_text ON products(normalized_text)"
        )
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id)")

        logger.info("Jack Stock Bot database initialized with indexes")


def _backup_dir() -> Path:
    path = settings.storage_dir / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cleanup_old_backups() -> None:
    cutoff = datetime.now() - timedelta(days=settings.BACKUP_RETENTION_DAYS)
    for path in _backup_dir().glob("jackteamvn_backup_*.db"):
        try:
            modified_at = datetime.fromtimestamp(path.stat().st_mtime)
            if modified_at < cutoff:
                path.unlink()
                logger.info("Deleted old backup: %s", path)
        except Exception as exc:
            logger.warning("Failed deleting old backup %s: %s", path, exc)


async def backup_database() -> str:
    """Create database backup."""
    if not settings.DB_BACKUP_ENABLED:
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = _backup_dir() / f"jackteamvn_backup_{timestamp}.db"
    shutil.copy2(settings.db_path, backup_path)
    _cleanup_old_backups()
    logger.info("Database backup created: %s", backup_path)
    return str(backup_path)


def _is_sqlite_db_valid(path: Path) -> bool:
    """Best-effort validation for SQLite file."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        conn = sqlite3.connect(str(path))
        try:
            cursor = conn.execute("PRAGMA quick_check")
            result = cursor.fetchone()
            return bool(result and str(result[0]).lower() == "ok")
        finally:
            conn.close()
    except Exception:
        return False


def _get_product_count(path: Path) -> int | None:
    """Read products count from a SQLite file; None if unreadable."""
    if not _is_sqlite_db_valid(path):
        return None
    try:
        conn = sqlite3.connect(str(path))
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='products'"
            )
            if cursor.fetchone() is None:
                return 0
            row = conn.execute("SELECT COUNT(*) FROM products").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()
    except Exception:
        return None


def _find_backup_candidates() -> list[Path]:
    # Prefer the new deterministic backup directory, then legacy location.
    candidates: list[Path] = list(_backup_dir().glob("jackteamvn_backup_*.db"))
    candidates.extend(settings.db_path.parent.glob("jackteamvn_backup_*.db"))
    unique = {str(path.resolve()): path for path in candidates}
    return sorted(unique.values(), key=lambda p: p.stat().st_mtime, reverse=True)


def restore_latest_backup_if_needed() -> str:
    """
    Restore latest backup when DB is missing or invalid.
    Returns status: "valid", "restored", "new", "failed".
    """
    db_path = settings.db_path
    backups = _find_backup_candidates()
    valid_backups = [b for b in backups if _is_sqlite_db_valid(b)]
    current_count = _get_product_count(db_path)

    # DB is usable; only restore when DB looks empty but backup has real data.
    if current_count is not None:
        if current_count > 0:
            return "valid"

        richer_backup = next((b for b in valid_backups if (_get_product_count(b) or 0) > 0), None)
        if not richer_backup:
            return "valid"

        try:
            broken_path = (
                db_path.parent / f"{db_path.stem}.empty_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            db_path.rename(broken_path)
            shutil.copy2(richer_backup, db_path)
            logger.info(
                "Database was empty; restored from latest non-empty backup: %s",
                richer_backup,
            )
            return "restored"
        except Exception as exc:
            logger.error("Failed to restore from non-empty backup: %s", exc, exc_info=exc)
            return "failed"

    valid_backup = valid_backups[0] if valid_backups else None
    if not valid_backup:
        if db_path.exists():
            try:
                broken_path = (
                    db_path.parent
                    / f"{db_path.stem}.corrupt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                )
                db_path.rename(broken_path)
                logger.warning("Current DB seems invalid, moved to: %s", broken_path)
            except Exception as exc:
                logger.error("Failed to move invalid DB file: %s", exc, exc_info=exc)
                return "failed"
        logger.warning("No valid backup found. Bot will initialize a new database.")
        return "new"

    try:
        if db_path.exists():
            broken_path = (
                db_path.parent / f"{db_path.stem}.corrupt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            db_path.rename(broken_path)
            logger.warning("Current DB seems invalid, moved to: %s", broken_path)

        shutil.copy2(valid_backup, db_path)
        logger.info("Database restored from latest backup: %s", valid_backup)
        return "restored"
    except Exception as exc:
        logger.error("Failed to restore database from backup: %s", exc, exc_info=exc)
        return "failed"
