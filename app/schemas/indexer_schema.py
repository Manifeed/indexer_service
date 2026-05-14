from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SourceEmbeddingPayloadRead(BaseModel):
    id: int = Field(ge=1)
    title: str = Field(min_length=1)
    summary: str | None = None
    url: str | None = None


class EmbeddingQueueMessageRead(BaseModel):
    task_id: int = Field(ge=1)
    job_id: str | None = Field(default=None, min_length=1)
    requested_at: datetime | None = None
    embedding_model_name: str = "BAAI/bge-m3"
    sources: list[SourceEmbeddingPayloadRead] = Field(default_factory=list)
    article_ids: list[int] = Field(default_factory=list)


class SparseEmbeddingRead(BaseModel):
    indices: list[int] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)


class EmbeddingServiceInputRead(BaseModel):
    id: str
    text: str


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
    country: str = "xx"
    published_at: datetime | None = None
    feeds: list[FeedIndexPayloadRead] = Field(default_factory=list)
    authors: list[AuthorIndexPayloadRead] = Field(default_factory=list)
    img_url: str | None = None


class InternalServiceHealthRead(BaseModel):
    service: str
    status: str
