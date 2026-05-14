# Operations Notes

## Health Model

- Liveness is provided by `GET /internal/health`
- Readiness is provided by `GET /internal/ready`

The Docker image healthcheck uses the liveness endpoint.

## Logging

The consumer logs exceptions when queue processing fails, then keeps running.
There is currently no structured logging layer or custom metrics exporter in
this repository.

## Common Failure Modes

### Missing embedding service API key

If `EMBEDDING_SERVICE_API_KEY` is unset, the embedding client raises a runtime
error before outbound requests can succeed.

### Missing database URLs

If the content or workers database URLs are missing, readiness checks fail and
queue processing cannot load sessions.

### Redis connectivity issues

Redis failures prevent queue reads and requeue operations. The process stays up
but logs repeated processing errors.

### Qdrant schema mismatch

If `SOURCE_EMBEDDING_DIMENSIONS` does not match the dense vector shape returned
by the embedding service, Qdrant writes can fail.

### Stale task references

If a queued task points to missing article references, the service records a
payload rebuild failure and finalizes the worker task as failed.

## Deployment Checklist

- all required environment variables are present
- the embedding service URL and bearer token are valid
- Redis is reachable from the service network
- both PostgreSQL databases are reachable
- Qdrant is reachable and has sufficient storage
- readiness succeeds before enabling workload

## Recovery Guidance

- If queue items are lost, keep the service running long enough for
  reconciliation to requeue eligible tasks.
- If the embedding service was temporarily unavailable, inspect failed tasks and
  replay them through the normal worker/task workflow.
- If Qdrant was recreated, verify collection settings before replaying backlog.
