#!/usr/bin/env python
"""Railway database bootstrap for PostgreSQL."""
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text

from app.config import settings
from app.db.session import engine
from app.models import Base


def main() -> None:
    print(f"Connecting to database: {settings.DATABASE_URL}")
    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))

    Base.metadata.create_all(bind=engine)
    print("Railway PostgreSQL schema is ready.")


if __name__ == "__main__":
    main()
