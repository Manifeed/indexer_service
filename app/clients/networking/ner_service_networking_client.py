from __future__ import annotations

import httpx

from app.domain.config import (
    resolve_ner_service_api_key,
    resolve_ner_service_url,
    resolve_pipeline_service_timeout_seconds,
)
from app.schemas.indexer_schema import NerServiceRequestSchema, NerServiceResponseRead


class NerServiceClientError(RuntimeError):
    """Raised when ner_service cannot parse article entities."""


class NerServiceNetworkingClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.base_url = resolve_ner_service_url()
        self.api_key = resolve_ner_service_api_key()
        self.timeout_seconds = resolve_pipeline_service_timeout_seconds()
        self._http_client = http_client

    def extract_article_entities(self, payload: NerServiceRequestSchema) -> NerServiceResponseRead:
        response = self._request(
            method="POST",
            path="/v1/entities",
            json=payload.model_dump(mode="json"),
        )
        if response.status_code >= 400:
            raise NerServiceClientError(f"ner_service returned HTTP {response.status_code}: {response.text}")
        return NerServiceResponseRead.model_validate(response.json())

    def check_ready(self) -> None:
        response = self._request(method="GET", path="/internal/ready")
        if response.status_code >= 400:
            raise NerServiceClientError(f"ner_service readiness returned HTTP {response.status_code}: {response.text}")

    def _request(self, *, method: str, path: str, json: dict | None = None) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.request(method=method, url=f"{self.base_url}{path}", json=json, headers=self._headers())
        with httpx.Client(timeout=self.timeout_seconds) as client:
            return client.request(method=method, url=f"{self.base_url}{path}", json=json, headers=self._headers())

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key is not None:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
