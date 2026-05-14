from __future__ import annotations

from datetime import UTC, datetime

from app.clients.database import article_embedding_database_client as module_under_test
from shared_backend.clients.article_embedding_database_client import (
    ArticleEmbeddingIndexRead as SharedArticleEmbeddingIndexRead,
)


def test_get_article_embedding_index_reads_adapts_shared_rows(monkeypatch) -> None:
    published_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    def fake_shared_get_article_embedding_index_reads(db, *, article_ids: list[int]):
        assert db == "db-session"
        assert article_ids == [42]
        return {
            42: SharedArticleEmbeddingIndexRead(
                article_id=42,
                article_key="article-key",
                url="article://article-key",
                title="Article title",
                summary="Article summary",
                company_id=9,
                company="Acme",
                country="fr",
                published_at=published_at,
                feeds=[{"id": 7, "section": "tech"}],
                authors=[{"id": 11, "name": "Ada"}],
                img_url="https://example.com/image.png",
            )
        }

    monkeypatch.setattr(
        module_under_test,
        "shared_get_article_embedding_index_reads",
        fake_shared_get_article_embedding_index_reads,
    )

    result = module_under_test.get_article_embedding_index_reads(
        "db-session",
        article_ids=[42],
    )

    article = result[42]
    assert article.article_id == 42
    assert article.article_key == "article-key"
    assert article.url == "article://article-key"
    assert article.title == "Article title"
    assert article.summary == "Article summary"
    assert article.company_id == 9
    assert article.company == "Acme"
    assert article.country == "fr"
    assert article.published_at == published_at
    assert len(article.feeds) == 1
    assert article.feeds[0].id == 7
    assert article.feeds[0].section == "tech"
    assert len(article.authors) == 1
    assert article.authors[0].id == 11
    assert article.authors[0].name == "Ada"
    assert article.img_url == "https://example.com/image.png"
