from __future__ import annotations

from fastapi import APIRouter

from app.schemas.indexer_schema import InternalServiceHealthRead


health_router = APIRouter(prefix="/internal", tags=["health"])


@health_router.get("/health", response_model=InternalServiceHealthRead)
def read_internal_health() -> InternalServiceHealthRead:
    return InternalServiceHealthRead(service="embedding-indexer-service", status="ok")
