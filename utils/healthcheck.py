from __future__ import annotations

import sqlite3
import sys

from config import settings


def run_healthcheck() -> int:
    if not settings.HEALTHCHECK_ENABLED:
        return 0

    db_path = settings.db_path

    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print(f"healthcheck: cannot create db directory: {exc}", file=sys.stderr)
        return 1

    try:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("PRAGMA quick_check")
        finally:
            conn.close()
    except Exception as exc:
        print(f"healthcheck: sqlite unavailable: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(run_healthcheck())
