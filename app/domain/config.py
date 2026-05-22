from __future__ import annotations

import os
import socket

from shared_backend.domain.source_embedding_config import (
    resolve_qdrant_api_key,
    resolve_qdrant_collection_name,
    resolve_qdrant_url,
    resolve_source_embedding_dimensions,
)

DEFAULT_EMBEDDING_SERVICE_URL = "http://127.0.0.1:8000"
DEFAULT_NER_SERVICE_URL = "http://127.0.0.1:8002"
DEFAULT_EMBEDDING_REDIS_QUEUE = "embedding:source_embedding"
DEFAULT_DENSE_DIMENSIONS = 1024
DEFAULT_EMBEDDING_SERVICE_TIMEOUT_SECONDS = 300.0
DEFAULT_PIPELINE_SERVICE_TIMEOUT_SECONDS = 120.0
DEFAULT_EMBED_TASK_LEASE_SECONDS = 900
DEFAULT_REDIS_RECONCILE_INTERVAL_SECONDS = 30


def resolve_embedding_service_url() -> str:
    return _env_url("EMBEDDING_SERVICE_URL", DEFAULT_EMBEDDING_SERVICE_URL)


def resolve_ner_service_url() -> str:
    return _env_url("NER_SERVICE_URL", DEFAULT_NER_SERVICE_URL)


def resolve_embedding_service_timeout_seconds() -> float:
    raw_value = os.getenv("EMBEDDING_SERVICE_TIMEOUT_SECONDS", "").strip()
    if not raw_value:
        return DEFAULT_EMBEDDING_SERVICE_TIMEOUT_SECONDS
    try:
        parsed = float(raw_value)
    except ValueError:
        return DEFAULT_EMBEDDING_SERVICE_TIMEOUT_SECONDS
    if parsed <= 0:
        return DEFAULT_EMBEDDING_SERVICE_TIMEOUT_SECONDS
    return parsed


def resolve_pipeline_service_timeout_seconds() -> float:
    raw_value = os.getenv("PIPELINE_SERVICE_TIMEOUT_SECONDS", "").strip()
    if not raw_value:
        return DEFAULT_PIPELINE_SERVICE_TIMEOUT_SECONDS
    try:
        parsed = float(raw_value)
    except ValueError:
        return DEFAULT_PIPELINE_SERVICE_TIMEOUT_SECONDS
    if parsed <= 0:
        return DEFAULT_PIPELINE_SERVICE_TIMEOUT_SECONDS
    return parsed


def resolve_embedding_service_api_key() -> str:
    value = os.getenv("EMBEDDING_SERVICE_API_KEY", "").strip()
    if value:
        return value
    raise RuntimeError("EMBEDDING_SERVICE_API_KEY is required")


def resolve_ner_service_api_key() -> str | None:
    value = os.getenv("NER_SERVICE_API_KEY", "").strip()
    return value or None


def resolve_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://redis:6379/0").strip() or "redis://redis:6379/0"


def resolve_embedding_queue_name() -> str:
    return os.getenv("EMBEDDING_REDIS_QUEUE", DEFAULT_EMBEDDING_REDIS_QUEUE).strip() or DEFAULT_EMBEDDING_REDIS_QUEUE


def resolve_dense_dimensions() -> int:
    parsed = resolve_source_embedding_dimensions()
    if parsed is not None:
        return parsed
    return DEFAULT_DENSE_DIMENSIONS


def should_start_consumer() -> bool:
    return os.getenv("EMBEDDING_INDEXER_CONSUMER_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }


def resolve_embed_task_lease_seconds() -> int:
    raw_value = os.getenv("EMBED_TASK_LEASE_SECONDS", "").strip()
    if raw_value:
        try:
            parsed = int(raw_value)
        except ValueError:
            parsed = DEFAULT_EMBED_TASK_LEASE_SECONDS
        if parsed >= 30:
            return parsed
    return DEFAULT_EMBED_TASK_LEASE_SECONDS


def resolve_redis_reconcile_interval_seconds() -> int:
    raw_value = os.getenv("EMBEDDING_REDIS_RECONCILE_INTERVAL_SECONDS", "").strip()
    if raw_value:
        try:
            parsed = int(raw_value)
        except ValueError:
            parsed = DEFAULT_REDIS_RECONCILE_INTERVAL_SECONDS
        if parsed > 0:
            return parsed
    return DEFAULT_REDIS_RECONCILE_INTERVAL_SECONDS


def resolve_embedding_claim_owner() -> str:
    value = os.getenv("EMBEDDING_INDEXER_CLAIM_OWNER", "").strip()
    if value:
        return value[:255]
    return f"embedding-indexer@{socket.gethostname()}"[:255]


def _env_url(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return (value or default).rstrip("/")
