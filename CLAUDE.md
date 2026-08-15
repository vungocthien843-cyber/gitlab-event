# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository actually is

This started from the generic "AI20K Agent Template" (FastAPI + LangGraph scaffold), but the
LangGraph agent under `src/agents/` is **unused leftover scaffold** — it has been removed from the
git working tree and is not part of the running system. Don't build on it or assume it's wired up.

The real system is an **IDP Catalog Graph API**: it ingests `catalog-info.yaml` files (uploaded
manually or pushed automatically via a GitHub webhook), runs them through a 5-layer validation
pipeline, converts valid files into a dependency graph (nodes + edges), persists that graph to
Postgres, and broadcasts real-time progress events (via Pusher) for a dashboard to consume.

For a detailed breakdown (in Vietnamese) of every module and the full request-flow diagram, see
[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) — read it before making non-trivial changes; it is
more accurate than `README.md`, which still describes the original generic template.

## Commands

```bash
# Run the API (reload enabled)
make run
# equivalent to: uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run the full test suite
make test
# equivalent to: pytest tests/ -v

# Run a single test file / test
pytest tests/test_catalog_api.py -v
pytest tests/test_catalog_api.py::test_name -v

# Lint / format / typecheck
ruff check src/ tests/
ruff format src/ tests/
mypy src/

# Docker (local full stack)
docker-compose up --build
```

Note: `make lint`/`make format`/`make typecheck` in the [Makefile](Makefile) still reference a
stale `app/` directory that no longer exists — run the `ruff`/`mypy` commands above directly
against `src/` instead, or fix the Makefile paths first.

There is no `pyproject.toml`/`pytest.ini`; pytest and ruff run with their default discovery plus
[ruff.toml](ruff.toml) (line-length 120, `py311` target).

## Environment / config

- Config is centralized in [src/core/config.py](src/core/config.py): module-level constants for
  every safety threshold (upload size, YAML bomb limits, filename rules, etc.) plus a
  `pydantic-settings` `Settings` class for app/LLM/DB/webhook/Pusher values. If you need to
  add or change a limit, it belongs in this one file, not scattered in validation code.
- `.env` is loaded from the project root regardless of the process's cwd (`BASE_DIR` is derived
  from this file's own path) — safe to run `uvicorn` from any directory.
- `DATABASE_URL` has no default; a missing value fails fast at first DB access
  (`STORAGE_FAILURE`, HTTP 500) rather than silently writing somewhere unexpected.
- Tests use a **separate Postgres schema**, not a different database. `TEST_DB_SCHEMA`
  (default `ai20k_db_test`) must differ from the production schema — see the guard in
  [tests/test_catalog_api.py](tests/test_catalog_api.py) and
  [tests/test_webhook_events.py](tests/test_webhook_events.py), which call
  `core.db.configure(DATABASE_URL, schema)` to point at it. Tests run against real Postgres
  (JSONB / BIGSERIAL semantics matter), not sqlite or a mock.

## Architecture

Layered, one-way dependency flow — each layer only knows about the one below it:

```
src/api/          HTTP only. No business logic, no DB, no validation.
src/services/     Business logic — "what order do the steps happen in."
src/repositories/ The ONLY layer that touches SQLAlchemy directly.
src/core/         Shared infra: config, errors, db, logging, cache, broadcaster.
src/models/       Data shapes: schemas.py (API contract), tables.py (Postgres ORM), events.py (SSE/Pusher payloads).
```

- **`src/api/routes.py`** is the single place HTTP routes are defined, mounted at `/api/v1` from
  [src/main.py](src/main.py) with an internal `prefix="/catalogs"` — so real paths are
  `/api/v1/catalogs/...`. Routes only parse the request and call a service function; if you're
  adding business logic, it does not belong here.
- **`src/services/ingest.py`** is the orchestrator for loading one catalog: validate → check
  cross-file conflicts → persist to DB → update in-memory cache → build response. It's called by
  both the manual upload route and the GitHub webhook path — this is the one place to hook in a
  new step.
- **`src/services/validation.py`** is a fail-fast 5-layer pipeline (see `Stage` enum in
  [src/core/errors.py](src/core/errors.py)): L1 basic input → L2 security (YAML bombs, unsafe
  tags, binary files spoofing as YAML) → L3 YAML syntax/encoding → L4 schema → L5 business rules
  (valid refs, no dependency cycles).
- **`src/services/catalog_to_graph.py`** is where a single YAML file becomes nodes/edges — this
  is where all schema rules (slugs, refs, owners, topology) live.
- **`src/services/catalog_merge.py`** merges multiple parsed files into one graph and detects
  cross-file conflicts (ownership disputes, orphaned edges, cross-file dependency cycles).
- **`src/services/github_events.py`** handles the GitHub webhook: verifies the HMAC-SHA256
  signature against the raw request body (before any parsing), extracts the push payload, fetches
  changed file contents via the GitHub API, hashes them (SHA-256) for the audit log, then calls
  into `ingest`/`delete_catalog`. The webhook endpoint always returns HTTP 200 (even when a YAML
  file fails validation) so GitHub doesn't retry a delivery that will just fail the same way again.
- **`src/repositories/`** is the only place importing SQLAlchemy directly — swapping databases
  means changing only these two files.
- **`src/core/store.py`** is an in-memory RAM cache of the `input_json` table, used to speed up
  GET/list and to check for conflicts between files without hitting Postgres each time.
- **`src/core/broadcaster.py`** pushes real-time events over Pusher (chosen over holding an SSE
  connection open, since the target deploy environment — Vercel — is serverless).

### Error model

All errors flow through the exception hierarchy in [src/core/errors.py](src/core/errors.py),
caught centrally in [src/main.py](src/main.py)'s exception handlers — don't catch-and-format
errors ad hoc inside routes or services. The hierarchy is organized by **how the error should be
handled**, not by technical cause:

- `ValidationError` (422) — bad input; user fixes the file and re-uploads. No stack trace logged.
- `SecurityError` (400) — input looks like an attack (spoofed file, YAML bomb, path traversal).
  Client message is intentionally vague; specifics go only to the log.
- `CriticalError` (500) — system can't guarantee a safe state to continue (DB unreachable, missing
  config, unexpected exception). Always logs a stack trace. This is the default for anything
  ambiguous ("unknown error = fail safely").
- `HumanReviewRequiredError` (409) — input is readable but the system isn't authorized to decide
  automatically (e.g. two files both claiming ownership of the same node).

Every endpoint returns the same response shape (`ApiResponse` in
[src/models/schemas.py](src/models/schemas.py)): `status`, `severity`, `code`, `message`,
`can_continue`, `next_action`, `stage`, `request_id`, `issues[]`, `details{}`. When adding a new
error case, add an `ErrorCode` entry rather than inventing an ad hoc message the frontend would
have to parse — the frontend switches on `code`, never on `message` text.

## AI usage logging

This repo has hooks (installed via `bash scripts/setup_hooks.sh`) that auto-log AI tool prompts
(Claude Code, Cursor, Codex, Gemini CLI, Copilot, Antigravity) to `.ai-log/session.jsonl` and
submit them to a grading server on `git push`. This is a grading requirement for the AI20K
program, not application behavior — don't remove or bypass it.
