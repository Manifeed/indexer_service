from __future__ import annotations

from app.domain.config import (
    resolve_embed_task_lease_seconds,
    resolve_embedding_claim_owner,
    resolve_embedding_service_api_key,
    resolve_embedding_service_timeout_seconds,
    resolve_embedding_service_url,
    resolve_dense_dimensions,
    resolve_ner_service_url,
    resolve_pipeline_service_timeout_seconds,
    resolve_redis_reconcile_interval_seconds,
    resolve_theme_service_url,
)


def test_resolve_embedding_service_url_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_SERVICE_URL", "http://192.168.4.67:8000")

    assert resolve_embedding_service_url() == "http://192.168.4.67:8000"


def test_resolve_embedding_service_url_uses_safe_default(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_SERVICE_URL", raising=False)

    assert resolve_embedding_service_url() == "http://127.0.0.1:8000"


def test_resolve_theme_and_ner_service_urls_read_environment(monkeypatch) -> None:
    monkeypatch.setenv("THEME_SERVICE_URL", "http://theme:8000")
    monkeypatch.setenv("NER_SERVICE_URL", "http://ner:8000")

    assert resolve_theme_service_url() == "http://theme:8000"
    assert resolve_ner_service_url() == "http://ner:8000"


def test_resolve_embedding_service_timeout_seconds_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_SERVICE_TIMEOUT_SECONDS", "123")

    assert resolve_embedding_service_timeout_seconds() == 123.0


def test_resolve_pipeline_service_timeout_seconds_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("PIPELINE_SERVICE_TIMEOUT_SECONDS", "45")

    assert resolve_pipeline_service_timeout_seconds() == 45.0


def test_resolve_embedding_service_api_key_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_SERVICE_API_KEY", "service-key")

    assert resolve_embedding_service_api_key() == "service-key"


def test_resolve_embedding_service_api_key_requires_environment(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_SERVICE_API_KEY", raising=False)

    try:
        resolve_embedding_service_api_key()
    except RuntimeError as exception:
        assert str(exception) == "EMBEDDING_SERVICE_API_KEY is required"
    else:
        raise AssertionError("Expected RuntimeError when EMBEDDING_SERVICE_API_KEY is missing")


def test_resolve_embed_task_lease_seconds_uses_safe_default(monkeypatch) -> None:
    monkeypatch.delenv("EMBED_TASK_LEASE_SECONDS", raising=False)

    assert resolve_embed_task_lease_seconds() == 900


def test_resolve_redis_reconcile_interval_seconds_prefers_positive_values(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_REDIS_RECONCILE_INTERVAL_SECONDS", "12")

    assert resolve_redis_reconcile_interval_seconds() == 12


def test_resolve_embedding_claim_owner_accepts_override(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_INDEXER_CLAIM_OWNER", "indexer-1")

    assert resolve_embedding_claim_owner() == "indexer-1"


def test_resolve_dense_dimensions_uses_shared_environment_value(monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_EMBEDDING_DIMENSIONS", "2048")

    assert resolve_dense_dimensions() == 2048


def test_resolve_dense_dimensions_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_EMBEDDING_DIMENSIONS", "invalid")

    assert resolve_dense_dimensions() == 1024
