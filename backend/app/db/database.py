"""SQLAlchemy connection foundation for PostgreSQL.

This module intentionally defines no application models, tables, or migrations.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

DATABASE_URL = os.getenv("DATABASE_URL")

engine: Engine | None = (
    create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
)

SessionLocal = (
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
    if engine is not None
    else None
)


def is_database_connected() -> bool:
    """Return whether PostgreSQL is reachable with the configured connection."""
    if engine is None:
        return False

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
