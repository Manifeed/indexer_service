# Indexer Service Architecture

## Entry Point

[app/main.py](../app/main.py) creates the FastAPI application and wires the
background consumer lifecycle through the application lifespan.

When the process starts:

1. the FastAPI app is created
2. the health router is mounted
3. the queue consumer is started unless disabled by configuration

## Internal Modules

- [app/main.py](../app/main.py): application bootstrap and readiness endpoint
- [app/database.py](../app/database.py): content/workers database engine
  creation and readiness checks
- [app/domain/config.py](../app/domain/config.py): environment variable parsing
  and safe defaults
- [app/routers/health_router.py](../app/routers/health_router.py): liveness
  endpoint
- [app/services/consumer_service.py](../app/services/consumer_service.py):
  queue polling, task claiming, reconciliation, and exception logging
- [app/services/indexer_service.py](../app/services/indexer_service.py):
  embedding request orchestration and final state transitions
- [app/clients/networking/redis_queue_client.py](../app/clients/networking/redis_queue_client.py):
  Redis queue access
- [app/clients/networking/embedding_service_networking_client.py](../app/clients/networking/embedding_service_networking_client.py):
  HTTP client for `bge-m3_inference`
- [app/clients/qdrant/qdrant_embedding_client.py](../app/clients/qdrant/qdrant_embedding_client.py):
  Qdrant writes, collection bootstrap, and payload index creation
- [app/clients/database](../app/clients/database): SQL data access for worker
  tasks and article embedding materialization

## End-to-End Flow

### 1. Queue polling

`EmbeddingQueueConsumer.run_forever()` blocks on Redis `BLPOP` with a short
timeout.

### 2. Task claim

The Redis message payload is validated as `{"task_id": <int>}` and the matching
embedding task is claimed in the workers database with a lease owner and lease
duration.

### 3. Payload rebuild

The service derives article IDs from the claimed task and reloads the full
article indexing payload from the content database.

### 4. Embedding generation

The ordered article texts are sent to `bge-m3_inference` through
`POST /v1/embeddings`.

### 5. Vector indexing

Each article embedding is upserted into Qdrant with:

- a dense vector named `dense`
- a sparse vector named `sparse`
- article metadata stored as payload

### 6. Finalization

Embedding manifest rows are updated, worker runtime counters are incremented
when needed, and the worker task is marked completed or failed.

## Data Safety Notes

- Missing or stale article references are treated as rebuild failures.
- A batch-wide failure marks all affected manifest rows as failed.
- Qdrant collection creation is idempotent at process level through an in-memory
  ensured-collections set.
