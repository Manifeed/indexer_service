# API And Runtime Behavior

## HTTP Endpoints

### `GET /internal/health`

Returns a lightweight liveness payload:

```json
{
  "service": "embedding-indexer-service",
  "status": "ok"
}
```

Use this for container or process liveness checks.

### `GET /internal/ready`

Validates runtime dependencies in this order:

1. content database
2. workers database
3. Redis
4. embedding service
5. Qdrant

Returns:

```json
{
  "service": "embedding-indexer-service",
  "status": "ready"
}
```

Use this for readiness gates before routing traffic or declaring the worker
healthy in orchestration.

## Background Consumer Behavior

The consumer starts automatically during app lifespan unless
`EMBEDDING_INDEXER_CONSUMER_ENABLED` disables it.

Runtime characteristics:

- Redis polling uses `BLPOP`
- empty polls trigger stale-task reconciliation
- queue processing errors are logged and do not crash the process
- blocking database and network steps are executed in worker threads

## Reconciliation Behavior

When no queue item is available, the service periodically checks the workers
database for requeueable embedding tasks and pushes their task IDs back into the
Redis queue.

This protects the system against:

- lost queue messages
- worker restarts during task execution
- expired task leases that need to be replayed

## Qdrant Initialization

The service does not require the target collection to exist before startup.
During the first write, it creates the configured collection if missing and
ensures payload indexes for:

- `country`
- `published_at`
- `company_id`

## Failure Semantics

- Stale task references become failed worker tasks.
- Missing embedding items from the embedding service are recorded per article.
- Unhandled batch failures mark all impacted articles as failed before the
  worker task is finalized.
