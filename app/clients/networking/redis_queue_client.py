from __future__ import annotations

import json
from typing import Any

import redis

from app.domain.config import resolve_embedding_queue_name, resolve_redis_url


class RedisQueueClientError(RuntimeError):
    """Raised when the Redis embedding queue is not available."""


class RedisQueueClient:
    def __init__(self) -> None:
        self.queue_name = resolve_embedding_queue_name()
        self._client = redis.Redis.from_url(resolve_redis_url(), decode_responses=True)

    def pop_message(self, *, timeout_seconds: int = 5) -> dict[str, Any] | None:
        try:
            item = self._client.blpop(self.queue_name, timeout=timeout_seconds)
        except redis.RedisError as exception:
            raise RedisQueueClientError("Unable to pop embedding queue message") from exception
        if item is None:
            return None
        _, raw_payload = item
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exception:
            raise RedisQueueClientError("Embedding queue message is not valid JSON") from exception
        if not isinstance(payload, dict):
            raise RedisQueueClientError("Embedding queue message must be a JSON object")
        return payload

    def enqueue_messages(self, payloads: list[dict[str, Any]]) -> int:
        if not payloads:
            return 0
        try:
            encoded_payloads = [
                json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
                for payload in payloads
            ]
            return int(self._client.rpush(self.queue_name, *encoded_payloads))
        except redis.RedisError as exception:
            raise RedisQueueClientError("Unable to enqueue embedding queue messages") from exception

    def enqueue_task_ids(self, task_ids: list[int]) -> int:
        normalized_task_ids = [int(task_id) for task_id in task_ids if int(task_id) > 0]
        if not normalized_task_ids:
            return 0
        return self.enqueue_messages([{"task_id": task_id} for task_id in normalized_task_ids])

    def check_ready(self) -> None:
        try:
            self._client.ping()
        except redis.RedisError as exception:
            raise RedisQueueClientError("Redis is not ready") from exception
