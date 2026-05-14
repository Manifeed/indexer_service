# Repository Bootstrap

## Purpose

This document captures the expected bootstrap workflow for the standalone
`indexer_service` Git repository.

Remote target:

```text
git@github.com:Manifeed/indexer_service.git
```

## Recommended First Push Workflow

From the repository root:

```bash
git init -b main
git remote add origin git@github.com:Manifeed/indexer_service.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

## What Should Exist Before The Push

- a Python-oriented `.gitignore`
- a root `README.md`
- split documentation in `doc/`
- source code, tests, Dockerfile, and license

## Pre-Push Checks

Run:

```bash
pytest -q
git status
git remote -v
```

Expected result:

- tests pass
- working tree is clean
- `origin` points to `git@github.com:Manifeed/indexer_service.git`

## Branching Note

This bootstrap assumes `main` is the default branch for the new repository.
