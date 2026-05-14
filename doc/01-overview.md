# Indexer Service Overview

## Purpose

`indexer_service` is the internal worker-facing embedding indexing service for
Manifeed. It bridges three data planes:

- worker task orchestration data stored in the workers database
- article content data stored in the content database
- vector search data stored in Qdrant

Its main job is to transform queued article embedding tasks into searchable
vector records.

## What It Does

For each claimed embedding task, the service:

1. Reads a message from Redis containing a task ID.
2. Claims the corresponding task in the workers database.
3. Rebuilds the list of target articles from the content database.
4. Calls `bge-m3_inference` to generate dense and sparse embeddings.
5. Writes the embedding payload into Qdrant.
6. Marks embedding manifest rows and worker task execution status as completed
   or failed.

## What It Does Not Do

- It does not expose public or browser-facing APIs.
- It does not create embeddings itself.
- It does not own the worker scheduling domain.
- It does not own source/article authoring data.

## External Dependencies

- PostgreSQL content database
- PostgreSQL workers database
- Redis
- `bge-m3_inference`
- Qdrant

All of them are validated by `GET /internal/ready`.

## Main Runtime Characteristics

- FastAPI process with a background async consumer
- Blocking integrations are delegated to threads with `asyncio.to_thread`
- Queue reconciliation re-enqueues stale pending worker tasks on an interval
- Qdrant collection creation is lazy and happens on the first successful upsert

## Repository Scope

This repository contains only the indexer service source code, tests, Docker
image definition, and operational documentation needed for standalone
maintenance and deployment.
