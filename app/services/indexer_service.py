from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.clients.database.article_embedding_database_client import (
    get_article_embedding_index_reads,
    upsert_embedding_manifest_failed,
    upsert_embedding_manifest_indexed,
)
from app.clients.database.worker_task_database_client import (
    ClaimedEmbeddingTask,
    RUNTIME_COUNTER_PAYLOAD_REBUILD_FAILURES,
    increment_worker_runtime_counter,
    mark_embedding_task_completed,
    mark_embedding_task_failed,
    refresh_worker_job_status,
)
from app.clients.networking.embedding_service_networking_client import EmbeddingServiceNetworkingClient
from app.clients.qdrant.qdrant_embedding_client import QdrantEmbeddingClient
from app.domain.config import BGE_M3_MODEL_NAME
from app.schemas.indexer_schema import (
    EmbeddingServiceRequestSchema,
)


class EmbeddingIndexingError(RuntimeError):
    """Raised when an embedding queue item cannot be indexed."""


def index_claimed_embedding_task(
    content_db: Session,
    workers_db: Session,
    *,
    task: ClaimedEmbeddingTask,
    embedding_client: EmbeddingServiceNetworkingClient | None = None,
    qdrant_client: QdrantEmbeddingClient | None = None,
) -> int:
    article_ids = _resolve_article_ids(task)
    articles_by_id = get_article_embedding_index_reads(content_db, article_ids=article_ids)
    if not article_ids or len(articles_by_id) != len(article_ids):
        increment_worker_runtime_counter(
            workers_db,
            counter_name=RUNTIME_COUNTER_PAYLOAD_REBUILD_FAILURES,
        )
        _finalize_indexing_task(
            workers_db,
            task=task,
            item_success=0,
            item_error=task.item_total,
            failed=True,
            error_message="stale_reference: unable to rebuild embedding payload from article refs",
        )
        return 0

    try:
        embedding_client = embedding_client or EmbeddingServiceNetworkingClient()
        qdrant_client = qdrant_client or QdrantEmbeddingClient()
        ordered_articles = [articles_by_id[article_id] for article_id in article_ids if article_id in articles_by_id]
        response = embedding_client.embed_documents(
            EmbeddingServiceRequestSchema(
                input=[_build_document_text(article.title, article.summary) for article in ordered_articles],
                dense=True,
                sparse=True,
                colbert=False,
            )
        )
        if len(response.data) != len(ordered_articles):
            raise EmbeddingIndexingError(
                f"Unexpected embedding item count: expected {len(ordered_articles)}, got {len(response.data)}"
            )

        items_by_index = {item.index: item for item in response.data}
        indexed_count = 0
        error_count = 0
        indexed_at = datetime.now(UTC)
        for expected_index, article in enumerate(ordered_articles):
            embedding = items_by_index.get(expected_index)
            if embedding is None or embedding.embedding is None or embedding.sparse_embedding is None:
                upsert_embedding_manifest_failed(
                    content_db,
                    article_id=article.article_id,
                    model_name=BGE_M3_MODEL_NAME,
                    error_message="bge-m3_inference response missing expected dense or sparse vectors",
                )
                error_count += 1
                continue
            try:
                qdrant_client.upsert_article_embedding(
                    article=article,
                    dense=embedding.embedding,
                    sparse=embedding.sparse_embedding,
                )
                upsert_embedding_manifest_indexed(
                    content_db,
                    article_id=article.article_id,
                    model_name=BGE_M3_MODEL_NAME,
                    indexed_at=indexed_at,
                )
                indexed_count += 1
            except Exception as exception:
                upsert_embedding_manifest_failed(
                    content_db,
                    article_id=article.article_id,
                    model_name=BGE_M3_MODEL_NAME,
                    error_message=str(exception),
                )
                error_count += 1
        content_db.commit()
        _finalize_indexing_task(
            workers_db,
            task=task,
            item_success=indexed_count,
            item_error=error_count,
            failed=False,
        )
        return indexed_count
    except Exception:
        content_db.rollback()
        _mark_batch_failed(
            content_db,
            workers_db,
            task=task,
            article_ids=article_ids,
        )
        raise


def _resolve_article_ids(task: ClaimedEmbeddingTask) -> list[int]:
    return [int(value) for value in task.ref_ids if int(value) > 0]


def _build_document_text(title: str, summary: str | None) -> str:
    return "\n\n".join(part.strip() for part in (title, summary or "") if part and part.strip())


def _finalize_indexing_task(
    workers_db: Session,
    *,
    task: ClaimedEmbeddingTask,
    item_success: int,
    item_error: int,
    failed: bool,
    error_message: str | None = None,
) -> None:
    if failed:
        mark_embedding_task_failed(
            workers_db,
            task_id=task.task_id,
            execution_id=task.execution_id,
            item_error=item_error,
            error_message=error_message or "embedding batch failed",
        )
    else:
        mark_embedding_task_completed(
            workers_db,
            task_id=task.task_id,
            execution_id=task.execution_id,
            item_success=item_success,
            item_error=item_error,
        )
    refresh_worker_job_status(workers_db, job_id=task.job_id)
    workers_db.commit()


def _mark_batch_failed(
    content_db: Session,
    workers_db: Session,
    *,
    task: ClaimedEmbeddingTask,
    article_ids: list[int],
) -> None:
    for article_id in article_ids:
        upsert_embedding_manifest_failed(
            content_db,
            article_id=article_id,
            model_name=BGE_M3_MODEL_NAME,
            error_message="embedding batch failed before indexing completed",
        )
    content_db.commit()
    _finalize_indexing_task(
        workers_db,
        task=task,
        item_success=0,
        item_error=max(len(article_ids), task.item_total),
        failed=True,
        error_message="embedding batch failed before indexing completed",
    )
