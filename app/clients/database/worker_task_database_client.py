from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


RUNTIME_COUNTER_STALE_REDIS_TASK_IDS_DROPPED = "stale_redis_task_ids_dropped"
RUNTIME_COUNTER_EMBEDDING_TASKS_REQUEUED = "embedding_tasks_requeued"
RUNTIME_COUNTER_PAYLOAD_REBUILD_FAILURES = "payload_rebuild_failures"
_KNOWN_RUNTIME_COUNTERS = (
    RUNTIME_COUNTER_STALE_REDIS_TASK_IDS_DROPPED,
    RUNTIME_COUNTER_EMBEDDING_TASKS_REQUEUED,
    RUNTIME_COUNTER_PAYLOAD_REBUILD_FAILURES,
)


@dataclass(frozen=True)
class ClaimedEmbeddingTask:
    task_id: int
    execution_id: int
    job_id: str
    ref_ids: list[int]
    item_total: int


@dataclass(frozen=True)
class WorkerJobProgressSnapshot:
    task_total: int
    task_processed: int
    item_success: int
    item_error: int
    processing_count: int
    pending_count: int
    cancelled_count: int


def claim_embedding_task(
    db: Session,
    *,
    task_id: int,
    lease_seconds: int,
    claim_owner: str,
) -> ClaimedEmbeddingTask | None:
    row = (
        db.execute(
            text(
                """
                WITH candidate AS (
                    SELECT task.task_id
                    FROM worker_tasks AS task
                    JOIN worker_jobs AS job
                        ON job.job_id = task.job_id
                    WHERE task.task_id = :task_id
                        AND task.task_type = 'embed.source'
                        AND job.status IN ('queued', 'processing')
                        AND (
                            task.status = 'pending'
                            OR (
                                task.status = 'processing'
                                AND task.claim_expires_at IS NOT NULL
                                AND task.claim_expires_at < now()
                            )
                        )
                    FOR UPDATE SKIP LOCKED
                ),
                claimed AS (
                    UPDATE worker_tasks AS task
                    SET
                        status = 'processing',
                        claimed_at = now(),
                        claim_expires_at = now() + (:lease_seconds * interval '1 second'),
                        completed_at = NULL,
                        attempt_count = task.attempt_count + 1,
                        execution_id = nextval('worker_task_execution_id_seq'),
                        last_error = NULL,
                        claim_owner = :claim_owner
                    FROM candidate
                    WHERE task.task_id = candidate.task_id
                    RETURNING
                        task.task_id,
                        task.execution_id,
                        task.job_id,
                        task.ref_ids,
                        task.item_total
                )
                SELECT
                    task_id,
                    execution_id,
                    job_id,
                    ref_ids,
                    item_total
                FROM claimed
                """
            ),
            {
                "task_id": int(task_id),
                "lease_seconds": max(30, int(lease_seconds)),
                "claim_owner": claim_owner[:255],
            },
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    return ClaimedEmbeddingTask(
        task_id=int(row["task_id"]),
        execution_id=int(row["execution_id"]),
        job_id=str(row["job_id"]),
        ref_ids=_coerce_ref_ids(row["ref_ids"]),
        item_total=int(row["item_total"] or 0),
    )


def mark_embedding_task_completed(
    db: Session,
    *,
    task_id: int,
    execution_id: int,
    item_success: int,
    item_error: int,
) -> None:
    db.execute(
        text(
            """
            UPDATE worker_tasks
            SET
                status = 'completed',
                claimed_at = NULL,
                claim_expires_at = NULL,
                completed_at = now(),
                item_success = :item_success,
                item_error = :item_error,
                last_error = NULL,
                claim_owner = NULL
            WHERE task_id = :task_id
                AND execution_id = :execution_id
                AND task_type = 'embed.source'
                AND status = 'processing'
            """
        ),
        {
            "task_id": task_id,
            "execution_id": execution_id,
            "item_success": max(0, int(item_success)),
            "item_error": max(0, int(item_error)),
        },
    )


def mark_embedding_task_failed(
    db: Session,
    *,
    task_id: int,
    execution_id: int,
    item_error: int,
    error_message: str,
) -> None:
    db.execute(
        text(
            """
            UPDATE worker_tasks
            SET
                status = 'failed',
                claimed_at = NULL,
                claim_expires_at = NULL,
                completed_at = now(),
                item_success = 0,
                item_error = :item_error,
                last_error = :last_error,
                claim_owner = NULL
            WHERE task_id = :task_id
                AND execution_id = :execution_id
                AND task_type = 'embed.source'
                AND status = 'processing'
            """
        ),
        {
            "task_id": task_id,
            "execution_id": execution_id,
            "item_error": max(0, int(item_error)),
            "last_error": error_message[:2000],
        },
    )


def refresh_worker_job_status(
    db: Session,
    *,
    job_id: str,
) -> None:
    snapshot = get_worker_job_progress_snapshot(db, job_id=job_id)
    if snapshot is None:
        return
    status = _resolve_worker_job_status(snapshot)
    db.execute(
        text(
            """
            UPDATE worker_jobs
            SET
                status = CAST(:status AS VARCHAR(64)),
                task_total = :task_total,
                task_processed = :task_processed,
                item_success = :item_success,
                item_error = :item_error,
                started_at = CASE
                    WHEN CAST(:status AS VARCHAR(64)) IN ('processing', 'paused', 'cancelled', 'completed', 'completed_with_errors', 'failed')
                        THEN COALESCE(started_at, now())
                    ELSE started_at
                END,
                finished_at = CASE
                    WHEN CAST(:status AS VARCHAR(64)) IN ('cancelled', 'completed', 'completed_with_errors', 'failed')
                        THEN COALESCE(finished_at, now())
                    ELSE NULL
                END,
                finalized_at = CASE
                    WHEN CAST(:status AS VARCHAR(64)) IN ('cancelled', 'completed', 'completed_with_errors', 'failed')
                        THEN COALESCE(finalized_at, now())
                    ELSE NULL
                END
            WHERE job_id = :job_id
            """
        ),
        {
            "job_id": job_id,
            "status": status,
            "task_total": snapshot.task_total,
            "task_processed": snapshot.task_processed,
            "item_success": snapshot.item_success,
            "item_error": snapshot.item_error,
        },
    )


def get_worker_job_progress_snapshot(
    db: Session,
    *,
    job_id: str,
) -> WorkerJobProgressSnapshot | None:
    row = (
        db.execute(
            text(
                """
                SELECT
                    COUNT(task.task_id) AS task_total,
                    COUNT(task.task_id) FILTER (WHERE task.status IN ('completed', 'failed', 'cancelled')) AS task_processed,
                    COALESCE(SUM(task.item_success), 0) AS item_success,
                    COALESCE(SUM(task.item_error), 0) AS item_error,
                    COUNT(task.task_id) FILTER (WHERE task.status = 'processing') AS processing_count,
                    COUNT(task.task_id) FILTER (WHERE task.status = 'pending') AS pending_count,
                    COUNT(task.task_id) FILTER (WHERE task.status = 'cancelled') AS cancelled_count
                FROM worker_tasks AS task
                WHERE task.job_id = :job_id
                """
            ),
            {"job_id": job_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    return WorkerJobProgressSnapshot(
        task_total=int(row["task_total"] or 0),
        task_processed=int(row["task_processed"] or 0),
        item_success=int(row["item_success"] or 0),
        item_error=int(row["item_error"] or 0),
        processing_count=int(row["processing_count"] or 0),
        pending_count=int(row["pending_count"] or 0),
        cancelled_count=int(row["cancelled_count"] or 0),
    )


def list_requeueable_embedding_task_ids(
    db: Session,
    *,
    limit: int = 512,
) -> list[int]:
    rows = (
        db.execute(
            text(
                """
                SELECT task.task_id
                FROM worker_tasks AS task
                JOIN worker_jobs AS job
                    ON job.job_id = task.job_id
                WHERE task.task_type = 'embed.source'
                    AND job.status IN ('queued', 'processing')
                    AND (
                        task.status = 'pending'
                        OR (
                            task.status = 'processing'
                            AND task.claim_expires_at IS NOT NULL
                            AND task.claim_expires_at < now()
                        )
                    )
                ORDER BY task.requested_at ASC, task.task_id ASC
                LIMIT :limit
                """
            ),
            {"limit": max(1, int(limit))},
        )
        .all()
    )
    return [int(row[0]) for row in rows]


def increment_worker_runtime_counter(
    db: Session,
    *,
    counter_name: str,
    amount: int = 1,
) -> None:
    normalized_amount = int(amount)
    if counter_name not in _KNOWN_RUNTIME_COUNTERS or normalized_amount <= 0:
        return
    db.execute(
        text(
            """
            INSERT INTO worker_runtime_counters (
                counter_name,
                counter_value,
                updated_at
            ) VALUES (
                :counter_name,
                :counter_value,
                now()
            )
            ON CONFLICT (counter_name) DO UPDATE SET
                counter_value = worker_runtime_counters.counter_value + EXCLUDED.counter_value,
                updated_at = now()
            """
        ),
        {
            "counter_name": counter_name,
            "counter_value": normalized_amount,
        },
    )


def _resolve_worker_job_status(snapshot: WorkerJobProgressSnapshot) -> str:
    if snapshot.task_total == 0:
        return "completed"
    if snapshot.processing_count > 0 or (
        snapshot.task_processed > 0 and snapshot.pending_count > 0
    ):
        return "processing"
    if snapshot.pending_count == snapshot.task_total or snapshot.pending_count > 0:
        return "queued"
    if snapshot.cancelled_count > 0:
        return "cancelled"
    if snapshot.item_error > 0:
        return "completed_with_errors"
    return "completed"

def _coerce_ref_ids(raw_ref_ids: object) -> list[int]:
    if not isinstance(raw_ref_ids, list):
        return []
    normalized: list[int] = []
    for value in raw_ref_ids:
        if value is None:
            continue
        normalized_value = int(value)
        if normalized_value > 0:
            normalized.append(normalized_value)
    return normalized
