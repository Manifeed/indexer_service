from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.indexer_schema import (
	ArticleEmbeddingIndexRead,
	EmbeddingQueueMessageRead,
	NerServiceRequestSchema,
)


def test_embedding_queue_message_read_accepts_task_id_only() -> None:
	message = EmbeddingQueueMessageRead.model_validate({"task_id": 42})

	assert message.task_id == 42


def test_embedding_queue_message_read_rejects_missing_task_id() -> None:
	with pytest.raises(ValidationError):
		EmbeddingQueueMessageRead.model_validate({})


def test_embedding_queue_message_read_rejects_invalid_task_id() -> None:
	with pytest.raises(ValidationError):
		EmbeddingQueueMessageRead.model_validate({"task_id": 0})


def test_pipeline_schemas_strip_sql_padding_from_country_and_language_codes() -> None:
	article = ArticleEmbeddingIndexRead(
		article_id=1,
		article_key="article-key",
		url="article://article-key",
		title="Titre",
		summary=None,
		company_id=None,
		company=None,
		country=" FR ",
		language="fr ",
	)

	assert article.country == "fr"
	assert article.language == "fr"


def test_ner_service_request_schema_accepts_minimal_fields() -> None:
	ner_request = NerServiceRequestSchema(
		article_id=1,
		title="Titre",
		summary=None,
	)

	assert ner_request.article_id == 1
	assert ner_request.title == "Titre"
