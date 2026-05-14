# Configuration Reference

## Core Connectivity

- `CONTENT_WRITE_DATABASE_URL`
  Primary content database connection string.
- `CONTENT_READ_DATABASE_URL`
  Fallback content database URL when the write URL is not provided.
- `WORKERS_WRITE_DATABASE_URL`
  Primary workers database connection string.
- `WORKERS_READ_DATABASE_URL`
  Fallback workers database URL when the write URL is not provided.
- `REDIS_URL`
  Redis connection string. Default: `redis://redis:6379/0`
- `EMBEDDING_REDIS_QUEUE`
  Redis list name used for embedding task messages.
  Default: `embedding:source_embedding`

## Embedding Service

- `EMBEDDING_SERVICE_URL`
  Base URL for `bge-m3_inference`.
  Default: `http://127.0.0.1:8000`
- `EMBEDDING_SERVICE_API_KEY`
  Required bearer token used for embedding service requests.
- `EMBEDDING_SERVICE_TIMEOUT_SECONDS`
  HTTP timeout for embedding requests.
  Default: `300`

## Qdrant

- `QDRANT_URL`
  Base URL for Qdrant.
  Default: `http://qdrant:6333`
- `QDRANT_COLLECTION_NAME`
  Target collection name for article embeddings.
  Default: `article_embeddings`
- `QDRANT_API_KEY`
  Optional API key header for secured Qdrant deployments.
- `SOURCE_EMBEDDING_DIMENSIONS`
  Dense vector size used when auto-creating the collection.
  Default: `1024`

## Consumer Control

- `EMBEDDING_INDEXER_CONSUMER_ENABLED`
  Enables or disables the background consumer.
  Default: `true`
- `EMBED_TASK_LEASE_SECONDS`
  Lease duration used when claiming a worker task.
  Default: `900`
  Minimum effective accepted value: `30`
- `EMBEDDING_REDIS_RECONCILE_INTERVAL_SECONDS`
  Interval between stale-task requeue scans when Redis is idle.
  Default: `30`
- `EMBEDDING_INDEXER_CLAIM_OWNER`
  Explicit task claim owner string stored in worker task execution rows.
  Default: `embedding-indexer@<hostname>`

## Static Model Metadata

- embedding model name written to manifests: `BAAI/bge-m3`
- embedding request model field: `bge-m3`

## Minimal Local Example

```bash
export CONTENT_WRITE_DATABASE_URL='postgresql://manifeed:manifeed@localhost:5432/manifeed_content'
export WORKERS_WRITE_DATABASE_URL='postgresql://manifeed:manifeed@localhost:5432/manifeed_workers'
export REDIS_URL='redis://localhost:6379/0'
export EMBEDDING_SERVICE_URL='http://127.0.0.1:8000'
export EMBEDDING_SERVICE_API_KEY='local-dev-key'
export QDRANT_URL='http://127.0.0.1:6333'
```
