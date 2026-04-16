from database.connection import db
from utils.logger import logger
import shutil
from datetime import datetime
from config import settings


async def init_database() -> None:
    """Initialize database schema for Jack Stock Bot"""
    async with db.get_cursor() as cursor:
        # Products table
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_text TEXT NOT NULL,
                normalizer_version TEXT NOT NULL DEFAULT 'v2',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await cursor.execute("PRAGMA table_info(products)")
        product_columns = {row["name"] for row in await cursor.fetchall()}

        if "normalized_text" not in product_columns:
            await cursor.execute("ALTER TABLE products ADD COLUMN normalized_text TEXT")
            logger.info("Added products.normalized_text column")

        if "normalizer_version" not in product_columns:
            await cursor.execute("ALTER TABLE products ADD COLUMN normalizer_version TEXT DEFAULT 'v2'")
            logger.info("Added products.normalizer_version column")

        if "raw_text" in product_columns:
            await cursor.execute("""
                UPDATE products
                SET normalized_text = TRIM(raw_text)
                WHERE normalized_text IS NULL OR normalized_text = ''
            """)

        await cursor.execute("""
            UPDATE products
            SET normalized_text = ''
            WHERE normalized_text IS NULL
        """)
        await cursor.execute("""
            UPDATE products
            SET normalizer_version = 'v2'
            WHERE normalizer_version IS NULL OR normalizer_version = ''
        """)
        
        # Audit log table
        await cursor.execute("""
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
        """)
        
        # Indexes for better performance
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_normalized_text ON products(normalized_text)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id)")
        
        logger.info("Jack Stock Bot database initialized with indexes")


async def backup_database() -> str:
    """Create database backup"""
    if not settings.DB_BACKUP_ENABLED:
        return ""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = settings.db_path.parent / f"jackteamvn_backup_{timestamp}.db"
    shutil.copy2(settings.db_path, backup_path)
    logger.info(f"Database backed up to: {backup_path}")
    return str(backup_path)
