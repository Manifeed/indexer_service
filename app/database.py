from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from shared_backend.database import (
    check_database_ready as shared_check_database_ready,
    configure_database_access,
    get_db_session as shared_get_db_session,
)


_CONTENT_DATABASE = configure_database_access(
    write_env="CONTENT_WRITE_DATABASE_URL",
    read_env="CONTENT_READ_DATABASE_URL",
    write_fallback_env_names=("CONTENT_READ_DATABASE_URL",),
    read_fallback_env_names=("CONTENT_WRITE_DATABASE_URL",),
)
_WORKERS_DATABASE = configure_database_access(
    write_env="WORKERS_WRITE_DATABASE_URL",
    read_env="WORKERS_READ_DATABASE_URL",
    write_fallback_env_names=("WORKERS_READ_DATABASE_URL",),
    read_fallback_env_names=("WORKERS_WRITE_DATABASE_URL",),
)

content_engine = _CONTENT_DATABASE.write_engine
ContentSessionLocal: sessionmaker[Session] = _CONTENT_DATABASE.write_session_factory
workers_engine = _WORKERS_DATABASE.write_engine
WorkersSessionLocal: sessionmaker[Session] = _WORKERS_DATABASE.write_session_factory

# Backward-compatible alias for existing content DB call sites.
SessionLocal = ContentSessionLocal


def get_db_session() -> Generator[Session, None, None]:
    yield from shared_get_db_session(ContentSessionLocal)


def get_workers_db_session() -> Generator[Session, None, None]:
    yield from shared_get_db_session(WorkersSessionLocal)


def check_database_ready() -> None:
    _check_ready(content_engine)


def check_workers_database_ready() -> None:
    _check_ready(workers_engine)


def _check_ready(engine: Engine) -> None:
    shared_check_database_ready(engine)
