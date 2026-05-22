from __future__ import annotations

import httpx

from app.clients.networking.ner_service_networking_client import NerServiceNetworkingClient
from app.schemas.indexer_schema import NerServiceBatchRequestSchema, NerServiceRequestSchema


class FakeHttpClient:
	def __init__(self) -> None:
		self.requests: list[dict[str, object]] = []

	def request(self, *, method: str, url: str, json=None, headers=None):
		self.requests.append({"method": method, "url": url, "json": json, "headers": headers})
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
				)
			]
		)
	)

	assert response.data[0].entities[0].label == "PERSON"
	assert http_client.requests[0]["url"] == "http://ner-service:8000/v1/entities/batch"
	assert http_client.requests[0]["json"]["items"][0] == {  # type: ignore[index]
		"article_id": 1,
		"title": "Ada works at OpenAI",
		"summary": None,
	}
