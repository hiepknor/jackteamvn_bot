from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Jack Stock Bot Configuration"""
    
    # Bot
    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    BOT_NAME: str = Field("JackStockBot", description="Bot Name")
    
    # Admin
    ADMIN_IDS: str = Field("", description="Comma-separated admin Telegram IDs")
    
    # Database
    DB_NAME: str = Field("jackteamvn.db", description="SQLite Database Name")
    DB_BACKUP_ENABLED: bool = Field(True, description="Enable DB Backup")
    
    # Export
    EXPORT_DIR: str = Field("exports", description="Export Directory")
    EXPORT_KEEP_COUNT: int = Field(10, description="Keep N recent export files")
    MAX_EXPORT_ROWS: int = Field(10000, description="Max rows per export")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", description="Logging Level")
    LOG_FILE: str = Field("logs/jackteamvn_bot.log", description="Log File Path")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(60, description="Rate limit per minute")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def admin_id_list(self) -> List[int]:
        """Convert ADMIN_IDS string to list of integers"""
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip().isdigit()]

    @property
    def admin_id_tokens(self) -> List[str]:
        """Raw ADMIN_IDS tokens without empty values."""
        return [x.strip() for x in self.ADMIN_IDS.split(",") if x.strip()]

    @property
    def invalid_admin_id_tokens(self) -> List[str]:
        """Return invalid ADMIN_IDS tokens (non-numeric)."""
        return [x for x in self.admin_id_tokens if not x.isdigit()]
    
    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent
    
    @property
    def db_path(self) -> Path:
        path = self.base_dir / self.DB_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def export_dir(self) -> Path:
        path = self.base_dir / self.EXPORT_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def log_path(self) -> Path:
        path = self.base_dir / self.LOG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def storage_path(self) -> Path:
        path = self.base_dir / "storage"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
