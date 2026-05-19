from __future__ import annotations

import importlib


def test_database_module_accepts_read_url_fallbacks(monkeypatch) -> None:
    monkeypatch.delenv("CONTENT_WRITE_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "CONTENT_READ_DATABASE_URL",
        "postgresql://user:pass@localhost:5432/content",
    )
    monkeypatch.delenv("WORKERS_WRITE_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "WORKERS_READ_DATABASE_URL",
        "postgresql://user:pass@localhost:5432/workers",
    )

    import app.database as database_module

    database_module = importlib.reload(database_module)

    assert database_module.content_engine is not None
    assert database_module.workers_engine is not None
    assert database_module.ContentSessionLocal is not None
    assert database_module.WorkersSessionLocal is not None
