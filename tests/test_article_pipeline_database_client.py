from __future__ import annotations

from app.clients.database.article_embedding_database_client import (
    replace_article_ner_mentions,
    replace_article_themes,
)
from app.schemas.indexer_schema import ArticleNerMentionRead, ArticleThemeRead


class FakeDb:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))


def test_replace_article_themes_deletes_then_upserts_themes() -> None:
    db = FakeDb()

    replace_article_themes(
        db,  # type: ignore[arg-type]
        article_id=7,
        themes=[ArticleThemeRead(theme="economy", confidence=0.8)],
    )

    assert "DELETE FROM article_theme" in db.calls[0][0]
    assert db.calls[1][1] == [{"article_id": 7, "theme": "economy", "confidence": 0.8}]


def test_replace_article_ner_mentions_deletes_then_inserts_mentions() -> None:
    db = FakeDb()

    replace_article_ner_mentions(
        db,  # type: ignore[arg-type]
        article_id=7,
        mentions=[
            ArticleNerMentionRead(
                label="PERSON",
                text="Ada",
                score=0.9,
                start_offset=0,
                end_offset=3,
            )
        ],
    )

    assert "DELETE FROM article_ner_mention" in db.calls[0][0]
    assert db.calls[1][1] == [
        {
            "article_id": 7,
            "label": "PERSON",
            "text": "Ada",
            "score": 0.9,
            "start_offset": 0,
            "end_offset": 3,
        }
    ]
