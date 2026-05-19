# Development And Tests

## Local Setup

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Run In API Mode

This starts the FastAPI process and the consumer by default:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

To run only the HTTP endpoints without the queue consumer:

```bash
export EMBEDDING_INDEXER_CONSUMER_ENABLED=false
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Run Tests

```bash
pytest -q
```

Current automated tests cover:

- configuration parsing and safe defaults
- content and workers database bootstrap fallbacks
- Redis queue payload validation and minimal `task_id` enqueue format
- consumer retry behavior and invalid-payload logging
- article embedding payload adaptation from `shared_backend`

Suggested future integration coverage:

- worker task claim and finalization flow against PostgreSQL
- Qdrant collection bootstrap behavior
- embedding service response mismatch handling in `indexer_service`

## Python Runtime

The service targets Python 3.13 in Docker. Local development can use any
compatible Python 3.13 interpreter.

## Docker Workflow

Build:

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

## Suggested Validation Checklist

- `GET /internal/health` returns `ok`
- `GET /internal/ready` returns `ready`
- Redis contains or accepts messages for the configured queue
- a queued task can be claimed and completed
- article embeddings appear in the configured Qdrant collection
