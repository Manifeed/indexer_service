from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.networking.embedding_service_networking_client import EmbeddingServiceNetworkingClient
from app.clients.networking.redis_queue_client import RedisQueueClient
from app.clients.qdrant.qdrant_embedding_client import QdrantEmbeddingClient
from app.database import check_database_ready, check_workers_database_ready
from app.domain.config import should_start_consumer
from app.routers.health_router import health_router
from app.schemas.indexer_schema import InternalServiceHealthRead
from app.services.consumer_service import EmbeddingQueueConsumer


@asynccontextmanager
async def _app_lifespan(_: FastAPI):
    consumer = EmbeddingQueueConsumer()
    task: asyncio.Task[None] | None = None
    if should_start_consumer():
        task = asyncio.create_task(consumer.run_forever())
    try:
        yield
    finally:
        consumer.stop()
        if task is not None:
            task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="Manifeed Embedding Indexer Service", lifespan=_app_lifespan)
    app.include_router(health_router)

    @app.get("/internal/ready", response_model=InternalServiceHealthRead)
    def read_internal_ready() -> InternalServiceHealthRead:
        check_database_ready()
        check_workers_database_ready()
        RedisQueueClient().check_ready()
        EmbeddingServiceNetworkingClient().check_ready()
        QdrantEmbeddingClient().check_ready()
        return InternalServiceHealthRead(service="embedding-indexer-service", status="ready")

    return app


app = create_app()
