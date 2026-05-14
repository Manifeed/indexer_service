# Indexer Service Docs Index

This folder contains split documentation for `indexer_service`.

## Documentation Map

- [01-overview.md](./01-overview.md): purpose, scope, dependencies, and
  responsibilities
- [02-architecture.md](./02-architecture.md): internal modules and indexing
  execution flow
- [03-api-and-runtime.md](./03-api-and-runtime.md): exposed endpoints, queue
  behavior, and task lifecycle
- [04-configuration.md](./04-configuration.md): environment variable reference
- [05-development-and-tests.md](./05-development-and-tests.md): local setup,
  Docker workflow, and test commands
- [06-operations.md](./06-operations.md): readiness, observability, and common
  operational failure modes
- [07-repository-bootstrap.md](./07-repository-bootstrap.md): repository setup
  and first-push workflow

## Source of Truth

When implementation changes, update these files in the same pull request so the
repository stays self-explanatory after being cloned independently.
