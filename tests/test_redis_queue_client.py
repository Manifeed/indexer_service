from __future__ import annotations

import json

import pytest

from app.clients.networking.redis_queue_client import (
    RedisQueueClient,
    RedisQueueClientError,
)


def test_enqueue_task_ids_serializes_minimal_payload(monkeypatch) -> None:
    pushed_payloads: list[str] = []

    class FakeRedis:
        def rpush(self, queue_name: str, *payloads: str) -> int:
            assert queue_name == "embedding:source_embedding"
            pushed_payloads.extend(payloads)
            return len(payloads)

    client = RedisQueueClient.__new__(RedisQueueClient)
    client.queue_name = "embedding:source_embedding"
    client._client = FakeRedis()

    queued_count = client.enqueue_task_ids([12, 0, -3, 34])

    assert queued_count == 2
    assert [json.loads(payload) for payload in pushed_payloads] == [
        {"task_id": 12},
        {"task_id": 34},
    ]


def test_pop_message_rejects_non_object_payload(monkeypatch) -> None:
    class FakeRedis:
        def blpop(self, queue_name: str, timeout: int = 5):
            return (queue_name, json.dumps(["not-an-object"]))

    client = RedisQueueClient.__new__(RedisQueueClient)
    client.queue_name = "embedding:source_embedding"
    client._client = FakeRedis()

    with pytest.raises(RedisQueueClientError, match="JSON object"):
        client.pop_message(timeout_seconds=1)
