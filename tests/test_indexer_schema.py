from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.indexer_schema import EmbeddingQueueMessageRead


def test_embedding_queue_message_read_accepts_task_id_only() -> None:
    message = EmbeddingQueueMessageRead.model_validate({"task_id": 42})

    assert message.task_id == 42


def test_embedding_queue_message_read_rejects_missing_task_id() -> None:
    with pytest.raises(ValidationError):
        EmbeddingQueueMessageRead.model_validate({})


def test_embedding_queue_message_read_rejects_invalid_task_id() -> None:
    with pytest.raises(ValidationError):
        EmbeddingQueueMessageRead.model_validate({"task_id": 0})
