from __future__ import annotations

from datetime import UTC, datetime

import httpx

from shared_backend.clients.qdrant_client import build_qdrant_collection_config
from app.domain.config import (
    resolve_dense_dimensions,
    resolve_qdrant_api_key,
    resolve_qdrant_collection_name,
    resolve_qdrant_url,
)
from app.schemas.indexer_schema import ArticleEmbeddingIndexRead, SparseEmbeddingRead


_ENSURED_COLLECTIONS: set[str] = set()


def _published_at_to_unix_seconds(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        normalized = value.replace(tzinfo=UTC)
    else:
        normalized = value.astimezone(UTC)
    return int(normalized.timestamp())


class QdrantEmbeddingClientError(RuntimeError):
    """Raised when Qdrant cannot index article embeddings."""


class QdrantEmbeddingClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.base_url = resolve_qdrant_url()
        self.collection_name = resolve_qdrant_collection_name()
        self.api_key = resolve_qdrant_api_key()
        self._http_client = http_client

    def upsert_article_embedding(
        self,
        *,
        article: ArticleEmbeddingIndexRead,
        dense: list[float],
        sparse: SparseEmbeddingRead,
    ) -> None:
        self._ensure_collection()
        payload = {
            "article_id": article.article_id,
            "article_key": article.article_key,
            "url": article.url,
            "title": article.title,
            "summary": article.summary,
            "company_id": article.company_id,
            "company": article.company,
            "country": article.country or "xx",
            "language": article.language or "xx",
            "published_at": _published_at_to_unix_seconds(article.published_at),
            "feeds": [feed.model_dump(mode="json") for feed in article.feeds],
            "authors": [author.model_dump(mode="json") for author in article.authors],
            "img_url": article.img_url,
        }
        response = self._request(
            method="PUT",
            path=f"/collections/{self.collection_name}/points?wait=true",
            json={
                "points": [
                    {
                        "id": article.article_id,
                        "vector": {
                            "dense": dense,
                            "sparse": sparse.model_dump(mode="json"),
                        },
                        "payload": payload,
                    }
                ]
            },
        )
        self._require_success(response, "Unable to upsert article embedding")

    def check_ready(self) -> None:
        response = self._request(method="GET", path="/collections")
        self._require_success(response, "Unable to read Qdrant collections")

    def _ensure_collection(self) -> None:
        if self.collection_name in _ENSURED_COLLECTIONS:
            return
        response = self._request(method="GET", path=f"/collections/{self.collection_name}")
        if response.status_code == 404:
            create_response = self._request(
                method="PUT",
                path=f"/collections/{self.collection_name}",
                json=build_qdrant_collection_config(resolve_dense_dimensions()),
            )
            self._require_success(create_response, "Unable to create Qdrant collection")
            self._ensure_payload_indexes()
            _ENSURED_COLLECTIONS.add(self.collection_name)
            return

        self._require_success(response, "Unable to read Qdrant collection")
        self._ensure_payload_indexes()
        _ENSURED_COLLECTIONS.add(self.collection_name)

    def _ensure_payload_indexes(self) -> None:
        for field_name, field_schema in (
            ("country", "keyword"),
            ("language", "keyword"),
            ("published_at", "integer"),
            ("company_id", "integer"),
        ):
            response = self._request(
                method="PUT",
                path=f"/collections/{self.collection_name}/index",
                json={
                    "field_name": field_name,
                    "field_schema": field_schema,
                },
            )
            self._require_success(response, f"Unable to create Qdrant payload index for {field_name}")

    def _request(
        self,
        *,
        method: str,
        path: str,
        json: dict | None = None,
    ) -> httpx.Response:
        headers = {"Content-Type": "application/json"}
        if self.api_key is not None:
            headers["api-key"] = self.api_key
        if self._http_client is not None:
            return self._http_client.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json,
                headers=headers,
            )
        with httpx.Client(timeout=60.0) as client:
            return client.request(method=method, url=f"{self.base_url}{path}", json=json, headers=headers)

    def _require_success(self, response: httpx.Response, message: str) -> None:
        if response.status_code >= 400:
            raise QdrantEmbeddingClientError(f"{message}: HTTP {response.status_code} - {response.text}")
        payload = response.json()
        if payload.get("status") not in (None, "ok"):
            raise QdrantEmbeddingClientError(f"{message}: unexpected Qdrant payload {payload}")
