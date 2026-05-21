from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.indexer_schema import (
    ArticleEmbeddingIndexRead,
    EmbeddingQueueMessageRead,
    NerServiceRequestSchema,
    ThemeServiceRequestSchema,
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


def test_pipeline_request_schemas_accept_three_letter_language_codes() -> None:
    theme_request = ThemeServiceRequestSchema(
        article_id=1,
        title="Titre",
        summary=None,
        language="arz",
    )
    ner_request = NerServiceRequestSchema(
        article_id=1,
        title="Titre",
        summary=None,
        language="arz",
        themes=[],
    )

    assert theme_request.language == "arz"
    assert ner_request.language == "arz"


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
    theme_request = ThemeServiceRequestSchema(
        article_id=1,
        title="Titre",
        summary=None,
        language=" fr ",
    )
    ner_request = NerServiceRequestSchema(
        article_id=1,
        title="Titre",
        summary=None,
        language=" fr ",
        themes=[],
    )

    assert article.country == "fr"
    assert article.language == "fr"
    assert theme_request.language == "fr"
    assert ner_request.language == "fr"


def test_pipeline_request_schemas_reject_four_letter_language_codes() -> None:
    with pytest.raises(ValidationError):
        ThemeServiceRequestSchema(article_id=1, title="Titre", summary=None, language="engl")

    with pytest.raises(ValidationError):
        NerServiceRequestSchema(article_id=1, title="Titre", summary=None, language="engl", themes=[])
