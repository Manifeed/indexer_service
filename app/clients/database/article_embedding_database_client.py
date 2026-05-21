from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from shared_backend.clients.article_embedding_database_client import (
    get_article_embedding_index_reads as shared_get_article_embedding_index_reads,
)

from app.schemas.indexer_schema import (
    ArticleNerMentionRead,
    ArticleThemeRead,
    ArticleEmbeddingIndexRead,
)


def get_article_embedding_index_reads(
    db: Session,
    *,
    article_ids: list[int],
) -> dict[int, ArticleEmbeddingIndexRead]:
    return {
        article_id: ArticleEmbeddingIndexRead.model_validate(shared_row.__dict__)
        for article_id, shared_row in shared_get_article_embedding_index_reads(
            db,
            article_ids=article_ids,
        ).items()
    }


def upsert_embedding_manifest_indexed(
    db: Session,
    *,
    article_id: int,
    model_name: str,
    indexed_at: datetime,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO embedding_manifest (
                article_id,
                model_name,
                status,
                indexed_at,
                updated_at
            ) VALUES (
                :article_id,
                :model_name,
                'indexed',
                :indexed_at,
                now()
            )
            ON CONFLICT (article_id) DO UPDATE SET
                model_name = EXCLUDED.model_name,
                status = EXCLUDED.status,
                indexed_at = EXCLUDED.indexed_at,
                updated_at = now()
            """
        ),
        {
            "article_id": article_id,
            "model_name": model_name,
            "indexed_at": indexed_at,
        },
    )


def upsert_embedding_manifest_failed(
    db: Session,
    *,
    article_id: int,
    model_name: str,
    error_message: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO embedding_manifest (
                article_id,
                model_name,
                status,
                failure_reason,
                updated_at
            ) VALUES (
                :article_id,
                :model_name,
                'failed',
                :failure_reason,
                now()
            )
            ON CONFLICT (article_id) DO UPDATE SET
                model_name = EXCLUDED.model_name,
                status = EXCLUDED.status,
                failure_reason = EXCLUDED.failure_reason,
                updated_at = now()
            """
        ),
        {
            "article_id": article_id,
            "model_name": model_name,
            "failure_reason": error_message[:1000],
        },
    )


def replace_article_themes(
    db: Session,
    *,
    article_id: int,
    themes: list[ArticleThemeRead],
) -> None:
    db.execute(
        text("DELETE FROM article_theme WHERE article_id = :article_id"),
        {"article_id": article_id},
    )
    if not themes:
        return
    db.execute(
        text(
            """
            INSERT INTO article_theme (
                article_id,
                theme,
                confidence
            ) VALUES (
                :article_id,
                :theme,
                :confidence
            )
            ON CONFLICT (article_id, theme) DO UPDATE SET
                confidence = EXCLUDED.confidence
            """
        ),
        [
            {
                "article_id": article_id,
                "theme": theme.theme,
                "confidence": theme.confidence,
            }
            for theme in themes
        ],
    )


def replace_article_ner_mentions(
    db: Session,
    *,
    article_id: int,
    mentions: list[ArticleNerMentionRead],
) -> None:
    db.execute(
        text("DELETE FROM article_ner_mention WHERE article_id = :article_id"),
        {"article_id": article_id},
    )
    if not mentions:
        return
    db.execute(
        text(
            """
            INSERT INTO article_ner_mention (
                article_id,
                label,
                text,
                score,
                start_offset,
                end_offset
            ) VALUES (
                :article_id,
                :label,
                :text,
                :score,
                :start_offset,
                :end_offset
            )
            """
        ),
        [
            {
                "article_id": article_id,
                "label": mention.label,
                "text": mention.text,
                "score": mention.score,
                "start_offset": mention.start_offset,
                "end_offset": mention.end_offset,
            }
            for mention in mentions
        ],
    )
