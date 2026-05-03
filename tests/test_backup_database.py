import asyncio
import sqlite3
from pathlib import Path

from database import models


def test_backup_database_uses_sqlite_backup_api(tmp_path, monkeypatch):
    db_path = tmp_path / "main.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(models.settings, "DB_BACKUP_ENABLED", True)
    monkeypatch.setattr(models.settings, "DB_NAME", str(db_path))

    def _fake_backup_dir() -> Path:
        return backup_dir

    monkeypatch.setattr(models, "_backup_dir", _fake_backup_dir)

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, normalized_text TEXT)")
        conn.execute("INSERT INTO products (normalized_text) VALUES ('RL 126528LN')")
        conn.commit()

    backup_file = asyncio.run(models.backup_database())

    assert backup_file
    backup_path = Path(backup_file)
    assert backup_path.exists()

    with sqlite3.connect(str(backup_path)) as conn:
        row = conn.execute("SELECT COUNT(*) FROM products").fetchone()

    assert row is not None
    assert row[0] == 1
