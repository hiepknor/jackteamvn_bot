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
                raw_text TEXT NOT NULL,
                brand TEXT,
                model TEXT,
                dial_desc TEXT,
                condition TEXT,
                date_info TEXT,
                price_text TEXT,
                currency TEXT,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
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
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_model ON products(model)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at)")
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
