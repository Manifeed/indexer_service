from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from app.clients.networking.redis_queue_client import RedisQueueClient
from app.clients.database.worker_task_database_client import (
    RUNTIME_COUNTER_EMBEDDING_TASKS_REQUEUED,
    RUNTIME_COUNTER_STALE_REDIS_TASK_IDS_DROPPED,
    claim_embedding_task,
    increment_worker_runtime_counter,
    list_requeueable_embedding_task_ids,
)
from app.database import get_db_session, get_workers_db_session
from app.schemas.indexer_schema import EmbeddingQueueMessageRead
from app.domain.config import (
    resolve_embed_task_lease_seconds,
    resolve_embedding_claim_owner,
    resolve_redis_reconcile_interval_seconds,
)
from app.services.indexer_service import index_claimed_embedding_task

logger = logging.getLogger(__name__)


class EmbeddingQueueConsumer:
    def __init__(self, redis_client_factory: Callable[[], RedisQueueClient] = RedisQueueClient) -> None:
        self._redis_client_factory = redis_client_factory
        self._stopped = asyncio.Event()
        self._lease_seconds = resolve_embed_task_lease_seconds()
        self._claim_owner = resolve_embedding_claim_owner()
        self._reconcile_interval_seconds = resolve_redis_reconcile_interval_seconds()
        self._last_reconcile_at = 0.0

    async def run_forever(self) -> None:
        redis_client = self._redis_client_factory()
        while not self._stopped.is_set():
            try:
                payload = await asyncio.to_thread(redis_client.pop_message, timeout_seconds=5)
                if payload is None:
                    await asyncio.to_thread(self._requeue_pending_messages, redis_client)
                    continue
                message = EmbeddingQueueMessageRead.model_validate(payload)
                content_session_generator = get_db_session()
                workers_session_generator = get_workers_db_session()
                content_db = next(content_session_generator)
                workers_db = next(workers_session_generator)
                try:
                    claimed_task = await asyncio.to_thread(
                        claim_embedding_task,
                        workers_db,
                        task_id=message.task_id,
                        lease_seconds=self._lease_seconds,
                        claim_owner=self._claim_owner,
                    )
                    if claimed_task is None:
                        await asyncio.to_thread(self._record_stale_drop, workers_db)
                        continue
                    await asyncio.to_thread(
                        index_claimed_embedding_task,
                        content_db,
                        workers_db,
                        task=claimed_task,
                    )
                finally:
                    content_session_generator.close()
                    workers_session_generator.close()
            except Exception:
                logger.exception("Embedding queue consumer failed to process a message")

    def stop(self) -> None:
        self._stopped.set()

    def _requeue_pending_messages(self, redis_client: RedisQueueClient) -> int:
        now = time.monotonic()
        if now - self._last_reconcile_at < self._reconcile_interval_seconds:
            return 0
        self._last_reconcile_at = now
        workers_session_generator = get_workers_db_session()
        workers_db = next(workers_session_generator)
        try:
            task_ids = list_requeueable_embedding_task_ids(workers_db)
            if not task_ids:
                return 0
            queued_count = redis_client.enqueue_task_ids(task_ids)
            increment_worker_runtime_counter(
                workers_db,
                counter_name=RUNTIME_COUNTER_EMBEDDING_TASKS_REQUEUED,
                amount=len(task_ids),
            )
            workers_db.commit()
            return queued_count
        finally:
            workers_session_generator.close()

    def _record_stale_drop(self, workers_db) -> None:
        increment_worker_runtime_counter(
            workers_db,
            counter_name=RUNTIME_COUNTER_STALE_REDIS_TASK_IDS_DROPPED,
        )
        workers_db.commit()
