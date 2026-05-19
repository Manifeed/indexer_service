# Manifeed Indexer Service

`indexer_service` is the internal embedding indexing worker for Manifeed.

It consumes embedding task messages from Redis, rebuilds article payloads from
the content database, requests dense and sparse embeddings from
`bge-m3_inference`, and upserts the final vectors into Qdrant.

This service is not browser-facing. It is meant to run inside the backend
platform alongside Redis, PostgreSQL-backed Manifeed services, the embedding
service, and Qdrant.

## Responsibilities

- Consume embedding task IDs from a Redis queue
- Claim and reconcile worker tasks from the workers database
- Rebuild article payloads from the content database
- Request embeddings from `bge-m3_inference`
- Upsert dense and sparse vectors into Qdrant
- Mark embedding manifests and worker task status as completed or failed
- Expose internal health and readiness endpoints

## Service Endpoints

- `GET /internal/health`: process-level liveness check
- `GET /internal/ready`: dependency readiness check for both databases, Redis,
  `bge-m3_inference`, and Qdrant

## Architecture Overview

- [app/main.py](./app/main.py): FastAPI bootstrap and background consumer
  lifecycle
- [app/services/consumer_service.py](./app/services/consumer_service.py):
  Redis-driven queue consumer and requeue reconciliation loop
- [app/services/indexer_service.py](./app/services/indexer_service.py):
  embedding orchestration and final task status updates
- [app/clients/networking](./app/clients/networking): Redis and embedding
  service clients
- [app/clients/qdrant](./app/clients/qdrant): Qdrant collection and point
  upsert client
- [app/clients/database](./app/clients/database): task and article data access
- [app/domain/config.py](./app/domain/config.py): runtime configuration
  resolution
- [app/database.py](./app/database.py): SQLAlchemy engines and readiness checks

## Quick Start

### 1. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 2. Export a minimal local environment

```bash
export CONTENT_WRITE_DATABASE_URL='postgresql://manifeed:manifeed@localhost:5432/manifeed_content'
export WORKERS_WRITE_DATABASE_URL='postgresql://manifeed:manifeed@localhost:5432/manifeed_workers'
export REDIS_URL='redis://localhost:6379/0'
export EMBEDDING_SERVICE_URL='http://127.0.0.1:8000'
export EMBEDDING_SERVICE_API_KEY='replace-with-local-service-key'
export QDRANT_URL='http://127.0.0.1:6333'
```

Optional overrides:

```bash
export EMBEDDING_REDIS_QUEUE='embedding:source_embedding'
export QDRANT_COLLECTION_NAME='article_embeddings'
export EMBEDDING_INDEXER_CONSUMER_ENABLED='true'
```

### 3. Run the service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The background consumer starts automatically unless
`EMBEDDING_INDEXER_CONSUMER_ENABLED=false`.

## Runtime Dependencies

- PostgreSQL content database
- PostgreSQL workers database
- Redis queue storage
- `bge-m3_inference` HTTP service
- Qdrant vector database

## Configuration

Core settings used by the service:

- `CONTENT_WRITE_DATABASE_URL` or `CONTENT_READ_DATABASE_URL`
- `WORKERS_WRITE_DATABASE_URL` or `WORKERS_READ_DATABASE_URL`
- `REDIS_URL`
- `EMBEDDING_REDIS_QUEUE`
- `EMBEDDING_SERVICE_URL`
- `EMBEDDING_SERVICE_API_KEY`
- `EMBEDDING_SERVICE_TIMEOUT_SECONDS`
- `QDRANT_URL`
- `QDRANT_COLLECTION_NAME`
- `QDRANT_API_KEY`
- `SOURCE_EMBEDDING_DIMENSIONS`
- `EMBEDDING_INDEXER_CONSUMER_ENABLED`
- `EMBED_TASK_LEASE_SECONDS`
- `EMBEDDING_REDIS_RECONCILE_INTERVAL_SECONDS`
- `EMBEDDING_INDEXER_CLAIM_OWNER`

See [doc/04-configuration.md](./doc/04-configuration.md) for the detailed
reference.

## Tests

Run the test suite with:

```bash
pytest -q
```

Automated coverage currently includes:

- configuration and environment parsing
- database bootstrap fallbacks
- Redis queue payload validation and enqueue format
- consumer retry and invalid-payload logging behavior
- article embedding payload adaptation from `shared_backend`

## Docker

Build from the repository root:

```bash
docker build -t manifeed-indexer-service .
```

Run:

```bash
docker run --rm -p 8000:8000 \
  -e CONTENT_WRITE_DATABASE_URL='postgresql://user:pass@content-db:5432/content' \
  -e WORKERS_WRITE_DATABASE_URL='postgresql://user:pass@workers-db:5432/workers' \
  -e REDIS_URL='redis://redis:6379/0' \
  -e EMBEDDING_SERVICE_URL='http://bge-m3_inference:8000' \
  -e EMBEDDING_SERVICE_API_KEY='replace-with-strong-secret' \
  -e QDRANT_URL='http://qdrant:6333' \
  manifeed-indexer-service
```

The container runs `uvicorn` directly and exposes port `8000`.

## Detailed Documentation

Detailed documentation lives in [doc/README.md](./doc/README.md).
