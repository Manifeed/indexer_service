from __future__ import annotations

import asyncio
import importlib
import logging
import sys
import types


def _load_consumer_module(monkeypatch):
    database_module = types.ModuleType("app.database")
    database_module.get_db_session = lambda: iter(())
    database_module.get_workers_db_session = lambda: iter(())

    worker_task_module = types.ModuleType("app.clients.database.worker_task_database_client")
    worker_task_module.RUNTIME_COUNTER_EMBEDDING_TASKS_REQUEUED = "embedding_tasks_requeued"
    worker_task_module.RUNTIME_COUNTER_STALE_REDIS_TASK_IDS_DROPPED = "stale_redis_task_ids_dropped"
    worker_task_module.claim_embedding_task = lambda *args, **kwargs: None
    worker_task_module.increment_worker_runtime_counter = lambda *args, **kwargs: None
    worker_task_module.list_requeueable_embedding_task_ids = lambda *args, **kwargs: []

    schemas_module = types.ModuleType("app.schemas.indexer_schema")

    class EmbeddingQueueMessageRead:
        @classmethod
        def model_validate(cls, payload):
            return payload

    schemas_module.EmbeddingQueueMessageRead = EmbeddingQueueMessageRead

    indexer_module = types.ModuleType("app.services.indexer_service")
    indexer_module.index_claimed_embedding_task = lambda *args, **kwargs: None

    monkeypatch.setitem(sys.modules, "app.database", database_module)
    monkeypatch.setitem(
        sys.modules,
        "app.clients.database.worker_task_database_client",
        worker_task_module,
    )
    monkeypatch.setitem(sys.modules, "app.schemas.indexer_schema", schemas_module)
    monkeypatch.setitem(sys.modules, "app.services.indexer_service", indexer_module)

    import app.services.consumer_service as consumer_module

    return importlib.reload(consumer_module)


def test_run_forever_recreates_redis_client_after_connection_error(monkeypatch, caplog) -> None:
    consumer_module = _load_consumer_module(monkeypatch)
    unavailable_error = consumer_module.RedisQueueUnavailableError("Redis unavailable")
    created_clients: list[object] = []
    sleep_calls: list[float] = []

    class FakeRedisClient:
        def __init__(self, responses) -> None:
            self._responses = list(responses)

        def pop_message(self, *, timeout_seconds: int = 5):
            assert timeout_seconds == 5
            response = self._responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    async def fake_to_thread(function, /, *args, **kwargs):
        return function(*args, **kwargs)

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    clients = [
        FakeRedisClient([unavailable_error]),
        FakeRedisClient([None]),
    ]

    def fake_redis_client_factory():
        client = clients[len(created_clients)]
        created_clients.append(client)
        return client

    consumer = consumer_module.EmbeddingQueueConsumer(
        redis_client_factory=fake_redis_client_factory,
        redis_retry_delay_seconds=0.25,
    )

    def fake_requeue_pending_messages(_redis_client) -> int:
        consumer.stop()
        return 0

    monkeypatch.setattr(consumer_module.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(consumer_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(consumer, "_requeue_pending_messages", fake_requeue_pending_messages)

    with caplog.at_level(logging.WARNING):
        asyncio.run(consumer.run_forever())

    assert len(created_clients) == 2
    assert sleep_calls == [0.25]
    assert "cannot reach Redis" in caplog.text


def test_run_forever_logs_invalid_payload_errors_without_retry_sleep(monkeypatch, caplog) -> None:
    consumer_module = _load_consumer_module(monkeypatch)
    sleep_calls: list[float] = []

    class FakeRedisClient:
        def __init__(self) -> None:
            self._calls = 0

        def pop_message(self, *, timeout_seconds: int = 5):
            assert timeout_seconds == 5
            self._calls += 1
            if self._calls == 1:
                raise consumer_module.RedisQueueClientError("Invalid queue payload")
            return None

    async def fake_to_thread(function, /, *args, **kwargs):
        return function(*args, **kwargs)

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    consumer = consumer_module.EmbeddingQueueConsumer(
        redis_client_factory=FakeRedisClient,
        redis_retry_delay_seconds=0.25,
    )

    def fake_requeue_pending_messages(_redis_client) -> int:
        consumer.stop()
        return 0

    monkeypatch.setattr(consumer_module.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(consumer_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(consumer, "_requeue_pending_messages", fake_requeue_pending_messages)

    with caplog.at_level(logging.ERROR):
        asyncio.run(consumer.run_forever())

    assert sleep_calls == []
    assert "invalid Redis queue payload" in caplog.text
