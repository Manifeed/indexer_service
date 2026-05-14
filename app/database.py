from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _content_database_url() -> str:
    database_url = os.getenv("CONTENT_WRITE_DATABASE_URL", "").strip() or os.getenv(
        "CONTENT_READ_DATABASE_URL",
        "",
    ).strip()
    return _normalize_database_url(database_url)


def _workers_database_url() -> str:
    database_url = os.getenv("WORKERS_WRITE_DATABASE_URL", "").strip() or os.getenv(
        "WORKERS_READ_DATABASE_URL",
        "",
    ).strip()
    return _normalize_database_url(database_url)


content_engine = (
    create_engine(_content_database_url(), pool_pre_ping=True)
    if _content_database_url()
    else None
)
ContentSessionLocal = (
    sessionmaker(autocommit=False, autoflush=False, bind=content_engine)
    if content_engine is not None
    else None
)
workers_engine = (
    create_engine(_workers_database_url(), pool_pre_ping=True)
    if _workers_database_url()
    else None
)
WorkersSessionLocal = (
    sessionmaker(autocommit=False, autoflush=False, bind=workers_engine)
    if workers_engine is not None
    else None
)

# Backward-compatible alias for existing content DB call sites.
SessionLocal = ContentSessionLocal


def get_db_session() -> Generator[Session, None, None]:
    if ContentSessionLocal is None:
        raise RuntimeError("CONTENT_WRITE_DATABASE_URL is not configured")
    db = ContentSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_workers_db_session() -> Generator[Session, None, None]:
    if WorkersSessionLocal is None:
        raise RuntimeError("WORKERS_WRITE_DATABASE_URL is not configured")
    db = WorkersSessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_ready() -> None:
    if content_engine is None:
        raise RuntimeError("CONTENT_WRITE_DATABASE_URL is not configured")
    with content_engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def check_workers_database_ready() -> None:
    if workers_engine is None:
        raise RuntimeError("WORKERS_WRITE_DATABASE_URL is not configured")
    with workers_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
