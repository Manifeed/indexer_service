from __future__ import annotations

from datetime import UTC, datetime

from app.clients.database.worker_task_database_client import ClaimedEmbeddingTask
from app.schemas.indexer_schema import (
    ArticleEmbeddingIndexRead,
    ArticleNerMentionRead,
    ArticleThemeRead,
    EmbeddingServiceItemRead,
    EmbeddingServiceResponseRead,
    NerServiceBatchItemRead,
    NerServiceBatchResponseRead,
    SparseEmbeddingRead,
    ThemeServiceResponseRead,
)
from app.services import indexer_service as module_under_test


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeThemeClient:
    def classify_article(self, payload):
        assert payload.language == "fr"
        return ThemeServiceResponseRead(
            themes=[ArticleThemeRead(theme="politics", confidence=0.8)]
        )


class FakeNerClient:
    def __init__(self) -> None:
        self.received_themes: list[list[str]] = []

    def extract_article_entities_batch(self, payload):
        self.received_themes = [list(item.themes) for item in payload.items]
        return NerServiceBatchResponseRead(
            data=[
                NerServiceBatchItemRead(
                    index=index,
                    article_id=item.article_id,
                    entities=[
                        ArticleNerMentionRead(
                            label="PERSON",
                            text="Ada",
                            score=0.9,
                            start_offset=0,
                            end_offset=3,
                        )
                    ],
                )
                for index, item in enumerate(payload.items)
            ]
        )


class FakeEmbeddingClient:
    def embed_documents(self, payload):
        assert payload.input == ["Titre\n\nResume"]
        return EmbeddingServiceResponseRead(
            data=[
                EmbeddingServiceItemRead(
                    index=0,
                    embedding=[0.1, 0.2],
                    sparse_embedding=SparseEmbeddingRead(indices=[1], values=[0.5]),
                )
            ]
        )


class FakeQdrantClient:
    def __init__(self) -> None:
        self.article_language: str | None = None
        self.article_themes: list[str] = []

    def upsert_article_embedding(self, *, article, dense, sparse) -> None:
        self.article_language = article.language
        self.article_themes = [theme.theme for theme in article.themes]
        assert dense == [0.1, 0.2]
        assert sparse.indices == [1]


def test_index_claimed_embedding_task_runs_pipeline_before_qdrant(monkeypatch) -> None:
    article = ArticleEmbeddingIndexRead(
        article_id=42,
        article_key="key",
        url="https://example.com/a",
        title="Titre",
        summary="Resume",
        company_id=1,
        company="Company",
        country="fr",
        language="fr ",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    content_db = FakeDb()
    workers_db = FakeDb()
    ner_client = FakeNerClient()
    qdrant_client = FakeQdrantClient()
    updates: dict[str, object] = {}

    monkeypatch.setattr(
        module_under_test,
        "get_article_embedding_index_reads",
        lambda db, *, article_ids: {42: article},
    )
    monkeypatch.setattr(
        module_under_test,
        "replace_article_themes",
        lambda db, *, article_id, themes: updates.setdefault("themes", themes),
    )
    monkeypatch.setattr(
        module_under_test,
        "replace_article_ner_mentions",
        lambda db, *, article_id, mentions: updates.setdefault("mentions", mentions),
    )
    monkeypatch.setattr(
        module_under_test,
        "upsert_embedding_manifest_indexed",
        lambda db, *, article_id, model_name, indexed_at: updates.setdefault("indexed", article_id),
    )
    monkeypatch.setattr(
        module_under_test,
        "_finalize_indexing_task",
        lambda workers_db, **kwargs: updates.setdefault("finalized", kwargs),
    )

    indexed_count = module_under_test.index_claimed_embedding_task(
        content_db,  # type: ignore[arg-type]
        workers_db,  # type: ignore[arg-type]
        task=ClaimedEmbeddingTask(
            task_id=1,
            execution_id=2,
            job_id="job",
            ref_ids=[42],
            item_total=1,
        ),
        theme_client=FakeThemeClient(),  # type: ignore[arg-type]
        ner_client=ner_client,  # type: ignore[arg-type]
        embedding_client=FakeEmbeddingClient(),  # type: ignore[arg-type]
        qdrant_client=qdrant_client,  # type: ignore[arg-type]
    )

    assert indexed_count == 1
    assert [theme.theme for theme in updates["themes"]] == ["politics"]  # type: ignore[index]
    assert ner_client.received_themes == [["politics"]]
    assert qdrant_client.article_language == "fr"
    assert qdrant_client.article_themes == ["politics"]
    assert updates["indexed"] == 42
    assert content_db.commits == 3


def test_index_claimed_embedding_task_preserves_three_letter_language_codes(monkeypatch) -> None:
    article = ArticleEmbeddingIndexRead(
        article_id=7,
        article_key="key-7",
        url="https://example.com/7",
        title="Titre",
        summary="Resume",
        company_id=1,
        company="Company",
        country="ma",
        language="arz",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    content_db = FakeDb()
    workers_db = FakeDb()
    qdrant_client = FakeQdrantClient()
    seen_languages: dict[str, object] = {}

    class ThreeLetterThemeClient:
        def classify_article(self, payload):
            seen_languages["theme"] = payload.language
            return ThemeServiceResponseRead(
                themes=[ArticleThemeRead(theme="politics", confidence=0.8)]
            )

    class ThreeLetterNerClient:
        def extract_article_entities_batch(self, payload):
            seen_languages["ner"] = [item.language for item in payload.items]
            return NerServiceBatchResponseRead(
                data=[
                    NerServiceBatchItemRead(
                        index=index,
                        article_id=item.article_id,
                        entities=[],
                    )
                    for index, item in enumerate(payload.items)
                ]
            )

    monkeypatch.setattr(
        module_under_test,
        "get_article_embedding_index_reads",
        lambda db, *, article_ids: {7: article},
    )
    monkeypatch.setattr(module_under_test, "replace_article_themes", lambda db, *, article_id, themes: None)
    monkeypatch.setattr(module_under_test, "replace_article_ner_mentions", lambda db, *, article_id, mentions: None)
    monkeypatch.setattr(module_under_test, "upsert_embedding_manifest_indexed", lambda *args, **kwargs: None)
    monkeypatch.setattr(module_under_test, "_finalize_indexing_task", lambda *args, **kwargs: None)

    indexed_count = module_under_test.index_claimed_embedding_task(
        content_db,  # type: ignore[arg-type]
        workers_db,  # type: ignore[arg-type]
        task=ClaimedEmbeddingTask(
            task_id=1,
            execution_id=2,
            job_id="job",
            ref_ids=[7],
            item_total=1,
        ),
        theme_client=ThreeLetterThemeClient(),  # type: ignore[arg-type]
        ner_client=ThreeLetterNerClient(),  # type: ignore[arg-type]
        embedding_client=FakeEmbeddingClient(),  # type: ignore[arg-type]
        qdrant_client=qdrant_client,  # type: ignore[arg-type]
    )

    assert indexed_count == 1
    assert seen_languages == {
        "theme": "arz",
        "ner": ["arz"],
    }
    assert qdrant_client.article_language == "arz"
