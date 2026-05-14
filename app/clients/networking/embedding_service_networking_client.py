from __future__ import annotations

import httpx

from app.domain.config import (
    resolve_embedding_service_api_key,
    resolve_embedding_service_timeout_seconds,
    resolve_embedding_service_url,
)
from app.schemas.indexer_schema import (
    EmbeddingServiceRequestSchema,
    EmbeddingServiceResponseRead,
)


class EmbeddingServiceClientError(RuntimeError):
    """Raised when bge-m3_inference cannot produce document embeddings."""


class EmbeddingServiceNetworkingClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.base_url = resolve_embedding_service_url()
        self.api_key = resolve_embedding_service_api_key()
        self.timeout_seconds = resolve_embedding_service_timeout_seconds()
        self._http_client = http_client

    def embed_documents(
        self,
        payload: EmbeddingServiceRequestSchema,
    ) -> EmbeddingServiceResponseRead:
        response = self._request(
            method="POST",
            path="/v1/embeddings",
            json=payload.model_dump(mode="json"),
        )
        if response.status_code >= 400:
            raise EmbeddingServiceClientError(
                f"bge-m3_inference returned HTTP {response.status_code}: {response.text}"
            )
        return EmbeddingServiceResponseRead.model_validate(response.json())

    def check_ready(self) -> None:
        response = self._request(method="GET", path="/internal/ready")
        if response.status_code >= 400:
            raise EmbeddingServiceClientError(
                f"bge-m3_inference readiness returned HTTP {response.status_code}: {response.text}"
            )

    def _request(
        self,
        *,
        method: str,
        path: str,
        json: dict | None = None,
    ) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json,
                headers=self._headers(),
            )
        with httpx.Client(timeout=self.timeout_seconds) as client:
            return client.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json,
                headers=self._headers(),
            )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}
