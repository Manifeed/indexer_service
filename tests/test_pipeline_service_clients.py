from __future__ import annotations

import httpx

from app.clients.networking.ner_service_networking_client import NerServiceNetworkingClient
from app.clients.networking.theme_service_networking_client import ThemeServiceNetworkingClient
from app.schemas.indexer_schema import NerServiceBatchRequestSchema, NerServiceRequestSchema, ThemeServiceRequestSchema


class FakeHttpClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def request(self, *, method: str, url: str, json=None, headers=None):
        self.requests.append({"method": method, "url": url, "json": json, "headers": headers})
        if url.endswith("/v1/themes"):
            return httpx.Response(200, json={"themes": [{"theme": "politics", "confidence": 0.8}]})
        if url.endswith("/v1/entities/batch"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "index": 0,
                            "article_id": 1,
                            "entities": [{"label": "PERSON", "text": "Ada", "score": 0.9}],
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"service": "service", "status": "ready"})


def test_theme_service_client_posts_theme_payload(monkeypatch) -> None:
    monkeypatch.setenv("THEME_SERVICE_URL", "http://theme-service:8000")
    monkeypatch.setenv("THEME_SERVICE_API_KEY", "secret")
    http_client = FakeHttpClient()
    client = ThemeServiceNetworkingClient(http_client=http_client)  # type: ignore[arg-type]

    response = client.classify_article(
        ThemeServiceRequestSchema(article_id=1, title="Election", summary=None, language="en")
    )

    assert response.themes[0].theme == "politics"
    assert http_client.requests[0]["url"] == "http://theme-service:8000/v1/themes"
    assert http_client.requests[0]["headers"] == {"Authorization": "Bearer secret"}


def test_ner_service_client_posts_batch_payload(monkeypatch) -> None:
    monkeypatch.setenv("NER_SERVICE_URL", "http://ner-service:8000")
    http_client = FakeHttpClient()
    client = NerServiceNetworkingClient(http_client=http_client)  # type: ignore[arg-type]

    response = client.extract_article_entities_batch(
        NerServiceBatchRequestSchema(
            items=[
                NerServiceRequestSchema(
                    article_id=1,
                    title="Ada works at OpenAI",
                    summary=None,
                    language="en",
                    themes=["technology"],
                )
            ]
        )
    )

    assert response.data[0].entities[0].label == "PERSON"
    assert http_client.requests[0]["url"] == "http://ner-service:8000/v1/entities/batch"
    assert http_client.requests[0]["json"]["items"][0]["themes"] == ["technology"]  # type: ignore[index]
