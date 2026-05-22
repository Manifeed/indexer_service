from __future__ import annotations

import httpx

from app.clients.qdrant.qdrant_embedding_client import QdrantEmbeddingClient
from app.schemas.indexer_schema import ArticleEmbeddingIndexRead, SparseEmbeddingRead


class FakeHttpClient:
	def __init__(self) -> None:
		self.requests: list[dict[str, object]] = []

	def request(self, *, method: str, url: str, json=None, headers=None):
		self.requests.append({"method": method, "url": url, "json": json, "headers": headers})
		if method == "GET":
			return httpx.Response(200, json={"status": "ok", "result": {"config": {"params": {"vectors": {"dense": {"size": 2}}}}}})
		return httpx.Response(200, json={"status": "ok"})


def test_upsert_article_embedding_includes_language(monkeypatch) -> None:
	monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
	monkeypatch.setenv("QDRANT_COLLECTION_NAME", "test_articles")
	monkeypatch.setenv("SOURCE_EMBEDDING_DIMENSIONS", "2")
	http_client = FakeHttpClient()
	client = QdrantEmbeddingClient(http_client=http_client)  # type: ignore[arg-type]

	client.upsert_article_embedding(
		article=ArticleEmbeddingIndexRead(
			article_id=1,
			article_key="key",
			url="https://example.com",
			title="Title",
			country="fr",
			language="fr",
		),
		dense=[0.1, 0.2],
		sparse=SparseEmbeddingRead(indices=[1], values=[0.5]),
	)

	upsert_request = http_client.requests[-1]
	point = upsert_request["json"]["points"][0]  # type: ignore[index]
	assert point["payload"]["language"] == "fr"
	assert "themes" not in point["payload"]
