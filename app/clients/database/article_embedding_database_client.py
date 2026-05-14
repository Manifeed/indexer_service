from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.indexer_schema import (
    ArticleEmbeddingIndexRead,
    AuthorIndexPayloadRead,
    FeedIndexPayloadRead,
)


def get_article_embedding_index_reads(
    db: Session,
    *,
    article_ids: list[int],
) -> dict[int, ArticleEmbeddingIndexRead]:
    if not article_ids:
        return {}
    rows = (
        db.execute(
            text(
                """
                SELECT
                    article.article_id,
                    article.article_key,
                    COALESCE(NULLIF(article.canonical_url, ''), 'article://' || article.article_key) AS url,
                    COALESCE(NULLIF(article.title, ''), article.article_key) AS title,
                    article.summary,
                    article.image_url,
                    article.company_id,
                    company.name AS company,
                    COALESCE(NULLIF(article.country, ''), 'xx') AS country,
                    article.published_at,
                    COALESCE(
                        (
                            SELECT json_agg(
                                json_build_object(
                                    'id', feed.id,
                                    'section', feed.section
                                )
                                ORDER BY feed.id
                            )
                            FROM article_feed_links AS link
                            JOIN rss_feeds AS feed ON feed.id = link.feed_id
                            WHERE link.article_id = article.article_id
                        ),
                        '[]'::json
                    ) AS feeds,
                    COALESCE(
                        (
                            SELECT json_agg(
                                json_build_object(
                                    'id', author.id,
                                    'name', COALESCE(author.display_name, '')
                                )
                                ORDER BY article_author.position
                            )
                            FROM article_authors AS article_author
                            JOIN authors AS author ON author.id = article_author.author_id
                            WHERE article_author.article_id = article.article_id
                        ),
                        '[]'::json
                    ) AS authors
                FROM articles AS article
                LEFT JOIN rss_company AS company ON company.id = article.company_id
                WHERE article.article_id = ANY(:article_ids)
                """
            ),
            {"article_ids": article_ids},
        )
        .mappings()
        .all()
    )
    return {int(row["article_id"]): _row_to_index_read(row) for row in rows}


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


def _row_to_index_read(row: Any) -> ArticleEmbeddingIndexRead:
    feeds_raw = row["feeds"] or []
    authors_raw = row["authors"] or []
    return ArticleEmbeddingIndexRead(
        article_id=int(row["article_id"]),
        article_key=str(row["article_key"]),
        url=str(row["url"]),
        title=str(row["title"]),
        summary=(str(row["summary"]) if row["summary"] is not None else None),
        company_id=(int(row["company_id"]) if row["company_id"] is not None else None),
        company=(str(row["company"]) if row["company"] is not None else None),
        country=(str(row["country"]) if row["country"] is not None else "xx"),
        published_at=row["published_at"],
        feeds=[
            FeedIndexPayloadRead.model_validate(feed)
            for feed in feeds_raw
            if isinstance(feed, dict)
        ],
        authors=[
            AuthorIndexPayloadRead.model_validate(author_row)
            for author_row in authors_raw
            if isinstance(author_row, dict)
        ],
        img_url=(str(row["image_url"]) if row["image_url"] is not None else None),
    )
