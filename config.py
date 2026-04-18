from __future__ import annotations

import re
from pathlib import Path
from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Jack Stock Bot configuration."""

    # Bot
    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    BOT_NAME: str = Field("JackStockBot", description="Bot Name")

    # Access control
    ADMIN_IDS: str = Field("", description="Comma/space-separated admin Telegram IDs")
    PRIVATE_BOT_MODE: bool = Field(True, description="Allow bot access only for admins")

    # Database
    DB_NAME: str = Field("data/jackteamvn.db", description="SQLite DB path")
    DB_BACKUP_ENABLED: bool = Field(True, description="Enable DB backup")
    BACKUP_RETENTION_DAYS: int = Field(7, description="Remove backups older than N days")

    # FSM
    FSM_BACKEND: str = Field("memory", description="FSM backend: memory|redis")
    REDIS_URL: str = Field("redis://redis:6379/0", description="Redis URL for FSM storage")

    # Runtime
    HEALTHCHECK_ENABLED: bool = Field(True, description="Enable runtime healthcheck")

    # Paths
    EXPORT_DIR: str = Field("exports", description="Export directory")
    STORAGE_DIR: str = Field("storage", description="Storage directory")
    EXPORT_KEEP_COUNT: int = Field(10, description="Keep N recent export files")
    MAX_EXPORT_ROWS: int = Field(10000, description="Max rows per export")

    # Logging
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    LOG_FILE: str = Field("logs/jackteamvn_bot.log", description="Log file path")

    # Misc
    RATE_LIMIT_PER_MINUTE: int = Field(60, description="Rate limit per minute")

    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator("BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, value: str) -> str:
        token = (value or "").strip()
        if not token:
            raise ValueError("BOT_TOKEN is required and cannot be empty")
        return token

    @field_validator("FSM_BACKEND")
    @classmethod
    def validate_fsm_backend(cls, value: str) -> str:
        backend = (value or "memory").strip().lower()
        if backend not in {"memory", "redis"}:
            raise ValueError("FSM_BACKEND must be one of: memory, redis")
        return backend

    @field_validator("BACKUP_RETENTION_DAYS")
    @classmethod
    def validate_retention_days(cls, value: int) -> int:
        if value < 1:
            raise ValueError("BACKUP_RETENTION_DAYS must be >= 1")
        return value

    @model_validator(mode="after")
    def validate_private_mode(self) -> "Settings":
        if self.PRIVATE_BOT_MODE and not self.admin_id_list:
            raise ValueError("PRIVATE_BOT_MODE=true requires non-empty ADMIN_IDS")
        if self.invalid_admin_id_tokens:
            invalid = ", ".join(self.invalid_admin_id_tokens)
            raise ValueError(f"ADMIN_IDS contains invalid values: {invalid}")
        return self

    @property
    def admin_id_tokens(self) -> List[str]:
        """ADMIN_IDS tokens split by comma/space/semicolon."""
        tokens = re.split(r"[,;\s]+", self.ADMIN_IDS or "")
        return [token.strip() for token in tokens if token.strip()]

    @property
    def invalid_admin_id_tokens(self) -> List[str]:
        """Return invalid ADMIN_IDS tokens (non-numeric)."""
        return [token for token in self.admin_id_tokens if not token.isdigit()]

    @property
    def admin_id_list(self) -> List[int]:
        """Return unique admin IDs from ADMIN_IDS."""
        ids: List[int] = []
        for token in self.admin_id_tokens:
            if token.isdigit():
                value = int(token)
                if value not in ids:
                    ids.append(value)
        return ids

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent

    def _resolve_path(self, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.base_dir / path
        return path

    def _ensure_dir(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        path = self._resolve_path(self.DB_NAME)
        self._ensure_dir(path.parent)
        return path

    @property
    def logs_dir(self) -> Path:
        log_path = self._resolve_path(self.LOG_FILE)
        return self._ensure_dir(log_path.parent)

    @property
    def exports_dir(self) -> Path:
        return self._ensure_dir(self._resolve_path(self.EXPORT_DIR))

    @property
    def storage_dir(self) -> Path:
        return self._ensure_dir(self._resolve_path(self.STORAGE_DIR))

    @property
    def log_path(self) -> Path:
        return self.logs_dir / Path(self.LOG_FILE).name

    @property
    def export_dir(self) -> Path:
        """Backward-compatible alias."""
        return self.exports_dir

    @property
    def storage_path(self) -> Path:
        """Backward-compatible alias."""
        return self.storage_dir

    def ensure_directories(self) -> None:
        """Create core runtime directories if missing."""
        _ = self.db_path
        _ = self.logs_dir
        _ = self.exports_dir
        _ = self.storage_dir


settings = Settings()
