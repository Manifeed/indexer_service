from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _normalize_alpha_code(value: object, *, default: str = "xx") -> str:
    if value is None:
        return default
    normalized = str(value).strip().casefold()
    return normalized or default


class EmbeddingQueueMessageRead(BaseModel):
    task_id: int = Field(ge=1)


class SparseEmbeddingRead(BaseModel):
    indices: list[int] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)


class EmbeddingServiceRequestSchema(BaseModel):
    model: str = "bge-m3"
    input: list[str] = Field(min_length=1, max_length=256)
    dense: bool = True
    sparse: bool = True
    colbert: bool = False


class EmbeddingServiceItemRead(BaseModel):
    index: int
    embedding: list[float] | None = None
    sparse_embedding: SparseEmbeddingRead | None = None
    colbert_embedding: list[list[float]] | None = None


class EmbeddingServiceResponseRead(BaseModel):
    data: list[EmbeddingServiceItemRead]


ArticleTheme = Literal[
    "economy",
    "sports",
    "society",
    "news",
    "politics",
    "technology",
    "science",
    "culture",
    "health",
    "environment",
    "world",
    "justice",
    "education",
    "business",
    "finance",
    "other",
]


class ArticleThemeRead(BaseModel):
    theme: ArticleTheme
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ThemeServiceRequestSchema(BaseModel):
    article_id: int = Field(ge=1)
    title: str
    summary: str | None = None
    language: str = Field(default="xx", min_length=2, max_length=3)

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, value: object) -> str:
        return _normalize_alpha_code(value)


class ThemeServiceResponseRead(BaseModel):
    themes: list[ArticleThemeRead] = Field(default_factory=list)


class NerServiceRequestSchema(BaseModel):
    article_id: int = Field(ge=1)
    title: str
    summary: str | None = None
    language: str = Field(default="xx", min_length=2, max_length=3)
    themes: list[ArticleTheme] = Field(default_factory=list)

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, value: object) -> str:
        return _normalize_alpha_code(value)


class NerServiceBatchRequestSchema(BaseModel):
    items: list[NerServiceRequestSchema] = Field(min_length=1, max_length=256)


class ArticleNerMentionRead(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1)
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)


class NerServiceResponseRead(BaseModel):
    entities: list[ArticleNerMentionRead] = Field(default_factory=list)


class NerServiceBatchItemRead(BaseModel):
    index: int = Field(ge=0)
    article_id: int = Field(ge=1)
    entities: list[ArticleNerMentionRead] = Field(default_factory=list)


class NerServiceBatchResponseRead(BaseModel):
    data: list[NerServiceBatchItemRead] = Field(default_factory=list)


class FeedIndexPayloadRead(BaseModel):
    id: int = Field(ge=1)
    section: str | None = None


class AuthorIndexPayloadRead(BaseModel):
    id: int = Field(ge=1)
    name: str


class ArticleEmbeddingIndexRead(BaseModel):
    article_id: int
    article_key: str
    url: str
    title: str
    summary: str | None = None
    company_id: int | None = None
    company: str | None = None
    country: str = Field(default="xx", min_length=2, max_length=2)
    language: str = Field(default="xx", min_length=2, max_length=3)
    themes: list[ArticleThemeRead] = Field(default_factory=list)
    published_at: datetime | None = None
    feeds: list[FeedIndexPayloadRead] = Field(default_factory=list)
    authors: list[AuthorIndexPayloadRead] = Field(default_factory=list)
    img_url: str | None = None

    @field_validator("country", mode="before")
    @classmethod
    def normalize_country(cls, value: object) -> str:
        return _normalize_alpha_code(value)

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, value: object) -> str:
        return _normalize_alpha_code(value)
