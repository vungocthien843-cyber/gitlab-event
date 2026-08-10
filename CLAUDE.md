

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Two codebases in one repo

| Path     | What it is                                                                                          |
| -------- | --------------------------------------------------------------------------------------------------- |
| `app/` | **The real project.** IDP Catalog Graph API â€” the only code that has been written for P-030. |
| `src/` | Untouched AI20K starter-template boilerplate (LangGraph chat agent). Not part of the product yet.   |

They are wired separately: `Dockerfile` / `docker-compose.yml` run `src.main:app`; `vercer.json` (filename typo of `vercel.json`, so Vercel does not actually pick it up) points at `src/main.py`; `Makefile` has `run` for `app` and `run-agent-template` for `src`. `tests/conftest.py` imports `src.main`, so the template must stay importable even though the product tests (`tests/test_catalog_api.py`) only touch `app/`.

`docs/BRIEF.md`, `docs/PRD.md`, `docs/UI_FLOW.md` describe the **eventual** product: an agent that reviews a design `spec.yaml` across security / availability / scalability / cost, with LangGraph + Postgres+pgvector + HITL approval. `app/` currently implements only the first stage of that â€” ingesting and validating `catalog-info.yaml` and turning it into a graph JSON. Don't assume anything in those docs exists in code.

## Commands

The venv is `.venv` (Python 3.14 locally; Docker builds on python:3.11-slim, ruff targets py311). `make` is **not** installed on this machine â€” run the underlying commands directly.

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --port 8000   # run API, Swagger at /docs
.\.venv\Scripts\python.exe -m pytest tests/ -q                            # full suite (96 tests, ~40s â€” hits Postgres)
.\.venv\Scripts\python.exe -m pytest tests/test_catalog_api.py -q         # product tests only
.\.venv\Scripts\python.exe -m pytest "tests/test_catalog_api.py::TestLayer2Security" -q         # one class
.\.venv\Scripts\python.exe -m pytest "tests/test_catalog_api.py::TestDelete::test_goi_y_khi_go_tat" -q  # one test
.\.venv\Scripts\python.exe -m ruff check app/ src/ tests/
.\.venv\Scripts\python.exe -m ruff format app/ src/ tests/
```

`make typecheck` is declared but mypy is not in `requirements.txt` or the venv â€” it will fail until installed.

`catalog_to_graph.py` also runs standalone as a CLI (independent of the API), useful for eyeballing a YAML file:

```powershell
.\.venv\Scripts\python.exe -m app.services.catalog_to_graph data/happyCase/02-normal-order-service.catalog.yaml --no-timestamp
```

Exit code 1 means the file has errors. `--no-timestamp` drops `generatedAt` so output is byte-deterministic.

Docker: `docker compose up --build` (needs `.env`; the container healthchecks `/health`).

`DATABASE_URL` (Postgres, in `.env`) is **required** â€” there is no filesystem or in-memory fallback. `app/core/config.py` calls `load_dotenv()`, so a local uvicorn run picks `.env` up on its own. The `input_json` table is created automatically at startup; to create it without booting the API:

```powershell
.\.venv\Scripts\python.exe -c "from app.core.db import init_db; init_db()"
```

## Architecture of `app/`

Request flow, one direction, no layer reaching back:

```
POST /catalogs
  api/catalogs.py      thin controller â€” extract from HTTP, call service, set status code
  services/ingest.py   the ONLY layer that knows step order:
                         validate â†’ cross-file conflict check â†’ save to DB â†’ cache â†’ build response
  services/validation.py   5-layer fail-fast pipeline (below)
  services/catalog_to_graph.py  YAML â†’ nodes/edges/diagnostics (also a standalone CLI)
  services/catalog_merge.py     merge N ParsedFile â†’ one graph doc; finds cross-file problems
  services/catalog_repository.py  the ONLY layer that touches SQLAlchemy
  services/store.py    in-memory cache of the input_json table
```

### The response contract

Every endpoint, every outcome (success, warning, validation error, security refusal, 500, 404, wrong HTTP method) returns the same `ApiResponse` shape: `status` / `severity` / `code` / `message` / `can_continue` / `next_action` / `stage` / `request_id` / `issues` / `details`.

Rules that keep it that way â€” break any one and the contract silently drifts:

- **Never construct `ApiResponse(...)` directly in a service.** Use `schemas.success()`, `schemas.warning()`, or `schemas.from_error()`.
- **Never set `status` by hand.** It is derived from `severity` via `Status.of()`.
- **Don't wrap service calls in try/except in routes.** Every `AppError` already has a global handler in `app/main.py` that produces the contract. The one exception in `catalogs.py` is a `finally` to close the temp upload file â€” endpoint-specific cleanup, not error mapping.
- `ErrorCode` values are a **stable API**; the frontend switches on the code, not the message. Add codes, don't rename or remove them.
- User-facing `message` is Vietnamese prose meant to be rendered as-is. Docstrings and comments in `app/` are Vietnamese too â€” match that when editing.

### Error taxonomy (`app/core/errors.py`)

Exceptions are classified by **how they must be handled**, not by technical cause:

| Class                        | HTTP | Log                   | Meaning                                                                                          |
| ---------------------------- | ---- | --------------------- | ------------------------------------------------------------------------------------------------ |
| `ValidationError`          | 422  | WARNING, no traceback | User's input is wrong; they fix the file and retry                                               |
| `SecurityError`            | 400  | ERROR, no traceback   | Input looks hostile. Client`message` is deliberately vague; details go to `log_message` only |
| `HumanReviewRequiredError` | 409  | ERROR, no traceback   | System understood the input but has no authority to decide (ownership conflict)                  |
| `CriticalError`            | 500  | CRITICAL + traceback  | System can't guarantee a safe state.**The default for anything unclear.**                  |

Low-level builtins (`OSError`, `UnicodeDecodeError`, `yaml.YAMLError`) are caught at the layer that understands them and re-raised as one of these with `from exc`. The catch-all `Exception` handler in `main.py` turns anything unforeseen into `CriticalError` â€” an unknown error must never become a 200.

### The 5 validation layers (`app/services/validation.py`)

```
L1 basic input     filename safety, extension, empty, size cap (streamed, chunked)
L2 security        RAW BYTES, before parsing: magic bytes, NUL, forbidden tags, anchor/alias bomb, line/indent caps
L3 file integrity  UTF-8 (utf-8-sig) decode, YAML syntax, duplicate keys (StrictLoader)
L4 schema          required top-level sections, mapping types, post-parse depth
L5 data            business rules, refs, ownership, dependency cycles, invariants
```

Two things about this ordering that are deliberate and easy to break:

- **L2 runs on raw bytes before the parser touches them.** A YAML anchor/alias bomb detonates *during* parse and `yaml.SafeLoader` does not stop it (it's valid YAML) â€” checking afterwards means checking after the process is already dead. Never move content-safety checks after `load_yaml`.
- **L1â€“L4 fail fast; L5 collects everything.** A user fixing a YAML file needs all 12 business-rule errors in one response, not 12 upload round-trips. L5 accumulates into `Diagnostics` and raises once.

Every threshold (sizes, depths, line counts, magic-byte table, allowed extensions) lives in `app/core/config.py` â€” not inline in the validators.

Filename safety sits in L1 rather than L2 on purpose: reject `../../etc/passwd.yaml` as `UNSAFE_FILENAME` before the extension check, otherwise a path-traversal probe is reported as "wrong file type" and the signal is lost. Classification comes from the *exception class*, not the layer number.

### Graph model (`catalog_to_graph.py`)

- Node id is `{kind}:{namespace}/{name}`; kinds are `system | component | resource | api | topic`.
- `REF_KIND_MAP` is the central semantic table: a ref's `kind` decides both the target node kind and the edge relation (`providesApis` â†’ api/`provides`, `consumesFrom` â†’ topic/`subscribes`, â€¦).
- In JSON, `source` is always the declaring component ("X provides Y"). `RELATION_REVERSED` flips `provides` and `publishes` **only** when building the networkX graph, so `nx.ancestors()` answers "who dies if X dies".
- Ownership (`declared_by`): components own themselves; APIs are owned by whoever `provides` them; `system`/`resource`/`topic` are permanently unowned (`UNOWNABLE_KINDS`) and never warned about.
- `assert_invariants()` failing is a **bug in our generation code**, not bad input â€” it maps to `CriticalError`/`INCONSISTENT_STATE`, never to a validation message.
- Output ordering is deterministic: nodes by id, edges by (declaring file, topology line index).

### Persistence and state (`app/core/db.py`, `app/services/catalog_repository.py`)

Postgres is the source of truth. Table `ai20k_db.input_json` has exactly two columns: `id BIGSERIAL PK` and `content JSONB` â€” the same graph document that used to be written to `output_json/*.json`. That directory is gone.

- **The table is created by ORM, never by hand.** `app/models/tables.py` describes it; `init_db()` runs `CreateSchema(if_not_exists)` + `create_all`, then *verifies via `inspect()`* that `input_json` really landed in the expected schema before logging success â€” `create_all` is silent when a table already exists, so on its own it proves nothing. No Alembic yet.
- Every connection gets `SET search_path` from an engine-level `connect` listener. The Neon URL already carries `options=-csearch_path%3D...`, but a pasted URL missing it would silently put the table in `public` â€” data still writes, nobody notices until they look for it.
- **The lookup key is inside the JSON.** `id` is a serial, so rows are found by `content->'scope'->'sources'->0->>'file'` â€” the original upload filename, which `merge_documents` already writes into the document. No extra column, and nothing foreign is injected into `content`.
- Re-uploading a file **UPDATEs its row** rather than inserting. The table models "the catalogs that exist", not an upload log; if it appended, `GET /catalogs` would have to guess which row is current.
- `store` is now a **cache** of that table, warmed by `store.load_from_db()` in the `lifespan` handler, so a restart no longer empties the listing. Writes go to the DB first and the cache second â€” a DB failure must not leave the cache claiming a file was ingested. Multiple uvicorn workers still each hold their own cache, so one worker's upload isn't visible to another until restart.
- `delete` removes the DB row first, then the cache entry â€” a failed delete leaves a consistent, retryable state instead of an orphan row that reappears on the next restart.
- `size_bytes` is **not** recoverable after a restart (it's a property of the uploaded YAML, not of the JSON), so `CatalogSummary.size_bytes` is nullable and reads `null` for restored rows. `uploaded_at` survives via the document's own `generatedAt`.
- `catalog_repository` is the only module importing SQLAlchemy. It wraps every `SQLAlchemyError` into `CriticalError`/`STORAGE_FAILURE`, and its `log_message` deliberately carries only the exception *class name* â€” psycopg2 connection errors can embed the full DSN, password included.

### Logging (`app/core/logging.py`)

Each request gets a `request_id` (ContextVar) that appears in every log line, in the response body, and in the `X-Request-ID` header â€” client-supplied values are honored. Log metadata only: sanitized filename, size, 12-hex sha256 fingerprint, error code, stage. Never log file contents, emails, tokens, or keys.

## Test data

`data/happyCase/` holds valid catalogs; `data/testCase/` holds deliberately broken ones. `data/testCase/README-testset.md` documents the exact error codes and counts each fixture should produce, plus a list of known parser blind spots (email format, unknown `protocol`, typo'd field names) â€” check it before "fixing" something that looks like a gap. It references `run-testset.py`, which does not exist in this repo.

Note `data/` is gitignored despite being present locally. `output_json/` is no longer written to â€” if the directory is still on disk it is leftover and safe to delete.

## Test conventions

`tests/test_catalog_api.py` is organized by validation layer, with `TestContract` asserting properties that must hold for *every* response (status matches severity, `request_id` always present, errors never set `can_continue=True`). When adding an endpoint, add it to `TestContract.ALL_REQUESTS` â€” that's what catches contract drift in endpoints nobody wrote targeted tests for.

**Tests hit a real Postgres** â€” there is no SQLite fallback, because the table uses JSONB/BIGSERIAL and the row lookup uses a Postgres JSON operator; a different engine would test a system that doesn't exist. The session-scoped `test_database` fixture points the engine at schema `ai20k_db_test` (`TEST_DB_SCHEMA`) on the same server, and drops it `CASCADE` at the end; it refuses to run if that name equals the production schema. The autouse `isolate` fixture `TRUNCATE`s the table and clears `store` between tests. Consequence: the suite needs network and takes ~40s.

`TestClient` is built with `raise_server_exceptions=False` so the 500 path is actually exercised instead of re-raising into pytest. It is *not* used as a context manager, so the `lifespan` handler never runs in tests â€” the fixtures own DB setup instead.

Use the `stored(filename)` / `row_count()` helpers to assert on what's actually in the table rather than reaching into `store`.

Test names are Vietnamese-transliterated (`test_ten_file_nguy_hiem_bi_tu_choi`) â€” follow that pattern.

