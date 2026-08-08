

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Two codebases in one repo

| Path     | What it is                                                                                          |
| -------- | --------------------------------------------------------------------------------------------------- |
| `app/` | **The real project.** IDP Catalog Graph API — the only code that has been written for P-030. |
| `src/` | Untouched AI20K starter-template boilerplate (LangGraph chat agent). Not part of the product yet.   |

They are wired separately: `Dockerfile` / `docker-compose.yml` run `app.main:app`; `vercer.json` (filename typo of `vercel.json`, so Vercel does not actually pick it up) points at `src/main.py`; `Makefile` has `run` for `app` and `run-agent-template` for `src`. `tests/conftest.py` imports `src.main`, so the template must stay importable even though the product tests (`tests/test_catalog_api.py`) only touch `app/`.

`docs/BRIEF.md`, `docs/PRD.md`, `docs/UI_FLOW.md` describe the **eventual** product: an agent that reviews a design `spec.yaml` across security / availability / scalability / cost, with LangGraph + Postgres+pgvector + HITL approval. `app/` currently implements only the first stage of that — ingesting and validating `catalog-info.yaml` and turning it into a graph JSON. Don't assume anything in those docs exists in code.

## Commands

The venv is `.venv` (Python 3.14 locally; Docker builds on python:3.11-slim, ruff targets py311). `make` is **not** installed on this machine — run the underlying commands directly.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000   # run API, Swagger at /docs
.\.venv\Scripts\python.exe -m pytest tests/ -q                            # full suite (91 tests, ~1s)
.\.venv\Scripts\python.exe -m pytest tests/test_catalog_api.py -q         # product tests only
.\.venv\Scripts\python.exe -m pytest "tests/test_catalog_api.py::TestLayer2Security" -q         # one class
.\.venv\Scripts\python.exe -m pytest "tests/test_catalog_api.py::TestDelete::test_goi_y_khi_go_tat" -q  # one test
.\.venv\Scripts\python.exe -m ruff check app/ src/ tests/
.\.venv\Scripts\python.exe -m ruff format app/ src/ tests/
```

`make typecheck` is declared but mypy is not in `requirements.txt` or the venv — it will fail until installed.

`catalog_to_graph.py` also runs standalone as a CLI (independent of the API), useful for eyeballing a YAML file:

```powershell
.\.venv\Scripts\python.exe -m app.services.catalog_to_graph data/happyCase/02-normal-order-service.catalog.yaml --no-timestamp
```

Exit code 1 means the file has errors. `--no-timestamp` drops `generatedAt` so output is byte-deterministic.

Docker: `docker compose up --build` (needs `.env`; the container healthchecks `/health`).

## Architecture of `app/`

Request flow, one direction, no layer reaching back:

```
POST /catalogs
  api/catalogs.py      thin controller — extract from HTTP, call service, set status code
  services/ingest.py   the ONLY layer that knows step order:
                         validate → cross-file conflict check → write JSON → index → build response
  services/validation.py   5-layer fail-fast pipeline (below)
  services/catalog_to_graph.py  YAML → nodes/edges/diagnostics (also a standalone CLI)
  services/catalog_merge.py     merge N ParsedFile → one graph doc; finds cross-file problems
  services/store.py    in-memory index of successfully ingested catalogs
```

### The response contract

Every endpoint, every outcome (success, warning, validation error, security refusal, 500, 404, wrong HTTP method) returns the same `ApiResponse` shape: `status` / `severity` / `code` / `message` / `can_continue` / `next_action` / `stage` / `request_id` / `issues` / `details`.

Rules that keep it that way — break any one and the contract silently drifts:

- **Never construct `ApiResponse(...)` directly in a service.** Use `schemas.success()`, `schemas.warning()`, or `schemas.from_error()`.
- **Never set `status` by hand.** It is derived from `severity` via `Status.of()`.
- **Don't wrap service calls in try/except in routes.** Every `AppError` already has a global handler in `app/main.py` that produces the contract. The one exception in `catalogs.py` is a `finally` to close the temp upload file — endpoint-specific cleanup, not error mapping.
- `ErrorCode` values are a **stable API**; the frontend switches on the code, not the message. Add codes, don't rename or remove them.
- User-facing `message` is Vietnamese prose meant to be rendered as-is. Docstrings and comments in `app/` are Vietnamese too — match that when editing.

### Error taxonomy (`app/core/errors.py`)

Exceptions are classified by **how they must be handled**, not by technical cause:

| Class                        | HTTP | Log                   | Meaning                                                                                          |
| ---------------------------- | ---- | --------------------- | ------------------------------------------------------------------------------------------------ |
| `ValidationError`          | 422  | WARNING, no traceback | User's input is wrong; they fix the file and retry                                               |
| `SecurityError`            | 400  | ERROR, no traceback   | Input looks hostile. Client`message` is deliberately vague; details go to `log_message` only |
| `HumanReviewRequiredError` | 409  | ERROR, no traceback   | System understood the input but has no authority to decide (ownership conflict)                  |
| `CriticalError`            | 500  | CRITICAL + traceback  | System can't guarantee a safe state.**The default for anything unclear.**                  |

Low-level builtins (`OSError`, `UnicodeDecodeError`, `yaml.YAMLError`) are caught at the layer that understands them and re-raised as one of these with `from exc`. The catch-all `Exception` handler in `main.py` turns anything unforeseen into `CriticalError` — an unknown error must never become a 200.

### The 5 validation layers (`app/services/validation.py`)

```
L1 basic input     filename safety, extension, empty, size cap (streamed, chunked)
L2 security        RAW BYTES, before parsing: magic bytes, NUL, forbidden tags, anchor/alias bomb, line/indent caps
L3 file integrity  UTF-8 (utf-8-sig) decode, YAML syntax, duplicate keys (StrictLoader)
L4 schema          required top-level sections, mapping types, post-parse depth
L5 data            business rules, refs, ownership, dependency cycles, invariants
```

Two things about this ordering that are deliberate and easy to break:

- **L2 runs on raw bytes before the parser touches them.** A YAML anchor/alias bomb detonates *during* parse and `yaml.SafeLoader` does not stop it (it's valid YAML) — checking afterwards means checking after the process is already dead. Never move content-safety checks after `load_yaml`.
- **L1–L4 fail fast; L5 collects everything.** A user fixing a YAML file needs all 12 business-rule errors in one response, not 12 upload round-trips. L5 accumulates into `Diagnostics` and raises once.

Every threshold (sizes, depths, line counts, magic-byte table, allowed extensions) lives in `app/core/config.py` — not inline in the validators.

Filename safety sits in L1 rather than L2 on purpose: reject `../../etc/passwd.yaml` as `UNSAFE_FILENAME` before the extension check, otherwise a path-traversal probe is reported as "wrong file type" and the signal is lost. Classification comes from the *exception class*, not the layer number.

### Graph model (`catalog_to_graph.py`)

- Node id is `{kind}:{namespace}/{name}`; kinds are `system | component | resource | api | topic`.
- `REF_KIND_MAP` is the central semantic table: a ref's `kind` decides both the target node kind and the edge relation (`providesApis` → api/`provides`, `consumesFrom` → topic/`subscribes`, …).
- In JSON, `source` is always the declaring component ("X provides Y"). `RELATION_REVERSED` flips `provides` and `publishes` **only** when building the networkX graph, so `nx.ancestors()` answers "who dies if X dies".
- Ownership (`declared_by`): components own themselves; APIs are owned by whoever `provides` them; `system`/`resource`/`topic` are permanently unowned (`UNOWNABLE_KINDS`) and never warned about.
- `assert_invariants()` failing is a **bug in our generation code**, not bad input — it maps to `CriticalError`/`INCONSISTENT_STATE`, never to a validation message.
- Output ordering is deterministic: nodes by id, edges by (declaring file, topology line index).

### Persistence and state

- `store` is an in-memory, lock-guarded dict. It is only an **index** — the JSON files in `output_json/` are the source of truth. It does not survive a restart, and multiple uvicorn workers each get their own copy.
- JSON is written temp-file-then-`os.replace` (atomic), and only after the file passed *all* validation. A partially valid file never reaches disk.
- `delete` removes the JSON file first, then the index entry — so a failed unlink leaves a consistent, retryable state instead of an invisible orphan file.
- `_resolve_output_path()` re-asserts containment in `OUTPUT_DIR` even though L1 already vetted the filename; safety must not depend on the caller remembering to validate.

### Logging (`app/core/logging.py`)

Each request gets a `request_id` (ContextVar) that appears in every log line, in the response body, and in the `X-Request-ID` header — client-supplied values are honored. Log metadata only: sanitized filename, size, 12-hex sha256 fingerprint, error code, stage. Never log file contents, emails, tokens, or keys.

## Test data

`data/happyCase/` holds valid catalogs; `data/testCase/` holds deliberately broken ones. `data/testCase/README-testset.md` documents the exact error codes and counts each fixture should produce, plus a list of known parser blind spots (email format, unknown `protocol`, typo'd field names) — check it before "fixing" something that looks like a gap. It references `run-testset.py`, which does not exist in this repo.

Note `data/` and `output_json/` are gitignored despite being present locally.

## Test conventions

`tests/test_catalog_api.py` is organized by validation layer, with `TestContract` asserting properties that must hold for *every* response (status matches severity, `request_id` always present, errors never set `can_continue=True`). When adding an endpoint, add it to `TestContract.ALL_REQUESTS` — that's what catches contract drift in endpoints nobody wrote targeted tests for.

The autouse `isolate` fixture monkeypatches `ingest.OUTPUT_DIR` to a tmp dir and clears `store`; tests must never write to the real `output_json/`. `TestClient` is built with `raise_server_exceptions=False` so the 500 path is actually exercised instead of re-raising into pytest.

Test names are Vietnamese-transliterated (`test_ten_file_nguy_hiem_bi_tu_choi`) — follow that pattern.
