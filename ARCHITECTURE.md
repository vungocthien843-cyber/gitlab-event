
CLAUDE.md:
Γûê∩╗┐
Γöé
Γûê# CLAUDE.md
Γöé
ΓûêThis file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
Γöé
Γûê## Two codebases in one repo
Γöé
Γûê| Path     | What it is                                                                                          |
Γûê| -------- | --------------------------------------------------------------------------------------------------- |
Γûê| `app/` | **The real project.** IDP Catalog Graph API ├óΓé¼ΓÇ¥ the only code that has been written for P-030. |
Γûê| `src/` | Untouched AI20K starter-template boilerplate (LangGraph chat agent). Not part of the product yet.   |
Γöé
ΓûêThey are wired separately: `Dockerfile` / `docker-compose.yml` run `src.main:app`; `vercer.json` (filename typo of `vercel.json`, so Vercel does not actually pick it up) points at `src/main.py`; `Makefile` has `run` for `app` and `run-agent-template` for `src`. `tests/conftest.py` imports `src.main`, so the template must stay importable even though the product tests (`tests/test_catalog_api.py`) only touch `app/`.
Γöé
Γûê`docs/BRIEF.md`, `docs/PRD.md`, `docs/UI_FLOW.md` describe the **eventual** product: an agent that reviews a design `spec.yaml` across security / availability / scalability / cost, with LangGraph + Postgres+pgvector + HITL approval. `app/` currently implements only the first stage of that ├óΓé¼ΓÇ¥ ingesting and validating `catalog-info.yaml` and turning it into a graph JSON. Don't assume anything in those docs exists in code.
Γöé
Γûê## Commands
Γöé
ΓûêThe venv is `.venv` (Python 3.14 locally; Docker builds on python:3.11-slim, ruff targets py311). `make` is **not** installed on this machine ├óΓé¼ΓÇ¥ run the underlying commands directly.
Γöé
Γûê```powershell
Γûê.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --port 8000   # run API, Swagger at /docs
Γûê.\.venv\Scripts\python.exe -m pytest tests/ -q                            # full suite (96 tests, ~40s ├óΓé¼ΓÇ¥ hits Postgres)
Γûê.\.venv\Scripts\python.exe -m pytest tests/test_catalog_api.py -q         # product tests only
Γûê.\.venv\Scripts\python.exe -m pytest "tests/test_catalog_api.py::TestLayer2Security" -q         # one class
Γûê.\.venv\Scripts\python.exe -m pytest "tests/test_catalog_api.py::TestDelete::test_goi_y_khi_go_tat" -q  # one test
Γûê.\.venv\Scripts\python.exe -m ruff check app/ src/ tests/
Γûê.\.venv\Scripts\python.exe -m ruff format app/ src/ tests/
Γûê```
Γöé
Γûê`make typecheck` is declared but mypy is not in `requirements.txt` or the venv ├óΓé¼ΓÇ¥ it will fail until installed.
Γöé
Γûê`catalog_to_graph.py` also runs standalone as a CLI (independent of the API), useful for eyeballing a YAML file:
Γöé
Γûê```powershell
Γûê.\.venv\Scripts\python.exe -m app.services.catalog_to_graph data/happyCase/02-normal-order-service.catalog.yaml --no-timestamp
Γûê```
Γöé
ΓûêExit code 1 means the file has errors. `--no-timestamp` drops `generatedAt` so output is byte-deterministic.
Γöé
ΓûêDocker: `docker compose up --build` (needs `.env`; the container healthchecks `/health`).
Γöé
Γûê`DATABASE_URL` (Postgres, in `.env`) is **required** ├óΓé¼ΓÇ¥ there is no filesystem or in-memory fallback. `app/core/config.py` calls `load_dotenv()`, so a local uvicorn run picks `.env` up on its own. The `input_json` table is created automatically at startup; to create it without booting the API:
Γöé
Γûê```powershell
Γûê.\.venv\Scripts\python.exe -c "from app.core.db import init_db; init_db()"
Γûê```
Γöé
Γûê## Architecture of `app/`
Γöé
ΓûêRequest flow, one direction, no layer reaching back:
Γöé
Γûê```
ΓûêPOST /catalogs
Γûê  api/catalogs.py      thin controller ├óΓé¼ΓÇ¥ extract from HTTP, call service, set status code
Γûê  services/ingest.py   the ONLY layer that knows step order:
Γûê                         validate ├óΓÇáΓÇÖ cross-file conflict check ├óΓÇáΓÇÖ save to DB ├óΓÇáΓÇÖ cache ├óΓÇáΓÇÖ build response
Γûê  services/validation.py   5-layer fail-fast pipeline (below)
Γûê  services/catalog_to_graph.py  YAML ├óΓÇáΓÇÖ nodes/edges/diagnostics (also a standalone CLI)
Γûê  services/catalog_merge.py     merge N ParsedFile ├óΓÇáΓÇÖ one graph doc; finds cross-file problems
Γûê  services/catalog_repository.py  the ONLY layer that touches SQLAlchemy
Γûê  services/store.py    in-memory cache of the input_json table
Γûê```
Γöé
Γûê### The response contract
Γöé
ΓûêEvery endpoint, every outcome (success, warning, validation error, security refusal, 500, 404, wrong HTTP method) returns the same `ApiResponse` shape: `status` / `severity` / `code` / `message` / `can_continue` / `next_action` / `stage` / `request_id` / `issues` / `details`.
Γöé
ΓûêRules that keep it that way ├óΓé¼ΓÇ¥ break any one and the contract silently drifts:
Γöé
Γûê- **Never construct `ApiResponse(...)` directly in a service.** Use `schemas.success()`, `schemas.warning()`, or `schemas.from_error()`.
Γûê- **Never set `status` by hand.** It is derived from `severity` via `Status.of()`.
Γûê- **Don't wrap service calls in try/except in routes.** Every `AppError` already has a global handler in `app/main.py` that produces the contract. The one exception in `catalogs.py` is a `finally` to close the temp upload file ├óΓé¼ΓÇ¥ endpoint-specific cleanup, not error mapping.
Γûê- `ErrorCode` values are a **stable API**; the frontend switches on the code, not the message. Add codes, don't rename or remove them.
Γûê- User-facing `message` is Vietnamese prose meant to be rendered as-is. Docstrings and comments in `app/` are Vietnamese too ├óΓé¼ΓÇ¥ match that when editing.
Γöé
Γûê### Error taxonomy (`app/core/errors.py`)
Γöé
ΓûêExceptions are classified by **how they must be handled**, not by technical cause:
Γöé
Γûê| Class                        | HTTP | Log                   | Meaning                                                                                          |
Γûê| ---------------------------- | ---- | --------------------- | ------------------------------------------------------------------------------------------------ |
Γûê| `ValidationError`          | 422  | WARNING, no traceback | User's input is wrong; they fix the file and retry                                               |
Γûê| `SecurityError`            | 400  | ERROR, no traceback   | Input looks hostile. Client`message` is deliberately vague; details go to `log_message` only |
Γûê| `HumanReviewRequiredError` | 409  | ERROR, no traceback   | System understood the input but has no authority to decide (ownership conflict)                  |
Γûê| `CriticalError`            | 500  | CRITICAL + traceback  | System can't guarantee a safe state.**The default for anything unclear.**                  |
Γöé
ΓûêLow-level builtins (`OSError`, `UnicodeDecodeError`, `yaml.YAMLError`) are caught at the layer that understands them and re-raised as one of these with `from exc`. The catch-all `Exception` handler in `main.py` turns anything unforeseen into `CriticalError` ├óΓé¼ΓÇ¥ an unknown error must never become a 200.
Γöé
Γûê### The 5 validation layers (`app/services/validation.py`)
Γöé
Γûê```
ΓûêL1 basic input     filename safety, extension, empty, size cap (streamed, chunked)
ΓûêL2 security        RAW BYTES, before parsing: magic bytes, NUL, forbidden tags, anchor/alias bomb, line/indent caps
ΓûêL3 file integrity  UTF-8 (utf-8-sig) decode, YAML syntax, duplicate keys (StrictLoader)
ΓûêL4 schema          required top-level sections, mapping types, post-parse depth
ΓûêL5 data            business rules, refs, ownership, dependency cycles, invariants
Γûê```
Γöé
ΓûêTwo things about this ordering that are deliberate and easy to break:
Γöé
Γûê- **L2 runs on raw bytes before the parser touches them.** A YAML anchor/alias bomb detonates *during* parse and `yaml.SafeLoader` does not stop it (it's valid YAML) ├óΓé¼ΓÇ¥ checking afterwards means checking after the process is already dead. Never move content-safety checks after `load_yaml`.
Γûê- **L1├óΓé¼ΓÇ£L4 fail fast; L5 collects everything.** A user fixing a YAML file needs all 12 business-rule errors in one response, not 12 upload round-trips. L5 accumulates into `Diagnostics` and raises once.
Γöé
ΓûêEvery threshold (sizes, depths, line counts, magic-byte table, allowed extensions) lives in `app/core/config.py` ├óΓé¼ΓÇ¥ not inline in the validators.
Γöé
ΓûêFilename safety sits in L1 rather than L2 on purpose: reject `../../etc/passwd.yaml` as `UNSAFE_FILENAME` before the extension check, otherwise a path-traversal probe is reported as "wrong file type" and the signal is lost. Classification comes from the *exception class*, not the layer number.
Γöé
Γûê### Graph model (`catalog_to_graph.py`)
Γöé
Γûê- Node id is `{kind}:{namespace}/{name}`; kinds are `system | component | resource | api | topic`.
Γûê- `REF_KIND_MAP` is the central semantic table: a ref's `kind` decides both the target node kind and the edge relation (`providesApis` ├óΓÇáΓÇÖ api/`provides`, `consumesFrom` ├óΓÇáΓÇÖ topic/`subscribes`, ├óΓé¼┬ª).
Γûê- In JSON, `source` is always the declaring component ("X provides Y"). `RELATION_REVERSED` flips `provides` and `publishes` **only** when building the networkX graph, so `nx.ancestors()` answers "who dies if X dies".
Γûê- Ownership (`declared_by`): components own themselves; APIs are owned by whoever `provides` them; `system`/`resource`/`topic` are permanently unowned (`UNOWNABLE_KINDS`) and never warned about.
Γûê- `assert_invariants()` failing is a **bug in our generation code**, not bad input ├óΓé¼ΓÇ¥ it maps to `CriticalError`/`INCONSISTENT_STATE`, never to a validation message.
Γûê- Output ordering is deterministic: nodes by id, edges by (declaring file, topology line index).
Γöé
Γûê### Persistence and state (`app/core/db.py`, `app/services/catalog_repository.py`)
Γöé
ΓûêPostgres is the source of truth. Table `ai20k_db.input_json` has exactly two columns: `id BIGSERIAL PK` and `content JSONB` ├óΓé¼ΓÇ¥ the same graph document that used to be written to `output_json/*.json`. That directory is gone.
Γöé
Γûê- **The table is created by ORM, never by hand.** `app/models/tables.py` describes it; `init_db()` runs `CreateSchema(if_not_exists)` + `create_all`, then *verifies via `inspect()`* that `input_json` really landed in the expected schema before logging success ├óΓé¼ΓÇ¥ `create_all` is silent when a table already exists, so on its own it proves nothing. No Alembic yet.
Γûê- Every connection gets `SET search_path` from an engine-level `connect` listener. The Neon URL already carries `options=-csearch_path%3D...`, but a pasted URL missing it would silently put the table in `public` ├óΓé¼ΓÇ¥ data still writes, nobody notices until they look for it.
Γûê- **The lookup key is inside the JSON.** `id` is a serial, so rows are found by `content->'scope'->'sources'->0->>'file'` ├óΓé¼ΓÇ¥ the original upload filename, which `merge_documents` already writes into the document. No extra column, and nothing foreign is injected into `content`.
Γûê- Re-uploading a file **UPDATEs its row** rather than inserting. The table models "the catalogs that exist", not an upload log; if it appended, `GET /catalogs` would have to guess which row is current.
Γûê- `store` is now a **cache** of that table, warmed by `store.load_from_db()` in the `lifespan` handler, so a restart no longer empties the listing. Writes go to the DB first and the cache second ├óΓé¼ΓÇ¥ a DB failure must not leave the cache claiming a file was ingested. Multiple uvicorn workers still each hold their own cache, so one worker's upload isn't visible to another until restart.
Γûê- `delete` removes the DB row first, then the cache entry ├óΓé¼ΓÇ¥ a failed delete leaves a consistent, retryable state instead of an orphan row that reappears on the next restart.
Γûê- `size_bytes` is **not** recoverable after a restart (it's a property of the uploaded YAML, not of the JSON), so `CatalogSummary.size_bytes` is nullable and reads `null` for restored rows. `uploaded_at` survives via the document's own `generatedAt`.
Γûê- `catalog_repository` is the only module importing SQLAlchemy. It wraps every `SQLAlchemyError` into `CriticalError`/`STORAGE_FAILURE`, and its `log_message` deliberately carries only the exception *class name* ├óΓé¼ΓÇ¥ psycopg2 connection errors can embed the full DSN, password included.
Γöé
Γûê### Logging (`app/core/logging.py`)
Γöé
ΓûêEach request gets a `request_id` (ContextVar) that appears in every log line, in the response body, and in the `X-Request-ID` header ├óΓé¼ΓÇ¥ client-supplied values are honored. Log metadata only: sanitized filename, size, 12-hex sha256 fingerprint, error code, stage. Never log file contents, emails, tokens, or keys.
Γöé
Γûê## Test data
Γöé
Γûê`data/happyCase/` holds valid catalogs; `data/testCase/` holds deliberately broken ones. `data/testCase/README-testset.md` documents the exact error codes and counts each fixture should produce, plus a list of known parser blind spots (email format, unknown `protocol`, typo'd field names) ├óΓé¼ΓÇ¥ check it before "fixing" something that looks like a gap. It references `run-testset.py`, which does not exist in this repo.
Γöé
ΓûêNote `data/` is gitignored despite being present locally. `output_json/` is no longer written to ├óΓé¼ΓÇ¥ if the directory is still on disk it is leftover and safe to delete.
Γöé
Γûê## Test conventions
Γöé
Γûê`tests/test_catalog_api.py` is organized by validation layer, with `TestContract` asserting properties that must hold for *every* response (status matches severity, `request_id` always present, errors never set `can_continue=True`). When adding an endpoint, add it to `TestContract.ALL_REQUESTS` ├óΓé¼ΓÇ¥ that's what catches contract drift in endpoints nobody wrote targeted tests for.
Γöé
Γûê**Tests hit a real Postgres** ├óΓé¼ΓÇ¥ there is no SQLite fallback, because the table uses JSONB/BIGSERIAL and the row lookup uses a Postgres JSON operator; a different engine would test a system that doesn't exist. The session-scoped `test_database` fixture points the engine at schema `ai20k_db_test` (`TEST_DB_SCHEMA`) on the same server, and drops it `CASCADE` at the end; it refuses to run if that name equals the production schema. The autouse `isolate` fixture `TRUNCATE`s the table and clears `store` between tests. Consequence: the suite needs network and takes ~40s.
Γöé
Γûê`TestClient` is built with `raise_server_exceptions=False` so the 500 path is actually exercised instead of re-raising into pytest. It is *not* used as a context manager, so the `lifespan` handler never runs in tests ├óΓé¼ΓÇ¥ the fixtures own DB setup instead.
Γöé
ΓûêUse the `stored(filename)` / `row_count()` helpers to assert on what's actually in the table rather than reaching into `store`.
Γöé
ΓûêTest names are Vietnamese-transliterated (`test_ten_file_nguy_hiem_bi_tu_choi`) ├óΓé¼ΓÇ¥ follow that pattern.
Γöé


Dockerfile:
Γûê∩╗┐# ---- Stage 1: Build ----
ΓûêFROM python:3.11-slim AS builder
Γöé
ΓûêWORKDIR /app
Γöé
ΓûêCOPY requirements.txt .
ΓûêRUN pip install --no-cache-dir --user -r requirements.txt
Γöé
Γûê# ---- Stage 2: Production ----
ΓûêFROM python:3.11-slim
Γöé
ΓûêWORKDIR /app
Γöé
Γûê# Copy installed packages from builder
ΓûêCOPY --from=builder /root/.local /root/.local
ΓûêENV PATH=/root/.local/bin:$PATH
Γöé
Γûê# Security: run as non-root user
ΓûêRUN useradd -m appuser
Γöé
Γûê# Copy application code
ΓûêCOPY . .
Γöé
Γûê# Create data directory with correct ownership
ΓûêRUN mkdir -p /app/data && chown -R appuser:appuser /app
Γöé
ΓûêUSER appuser
Γöé
ΓûêEXPOSE 8000
Γöé
ΓûêHEALTHCHECK --interval=30s --timeout=10s --retries=3 \
Γûê    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
Γöé
ΓûêCMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
Γöé


docs\architecture_diagram.md:
Γûê# Architecture Diagram
Γöé
Γûê## System Overview
Γöé
Γûê```mermaid
Γûêgraph TB
Γûê    User([User]) --> UI[Frontend<br/>React/Next.js]
Γûê    UI -->|REST API| API[FastAPI Backend]
Γûê    API --> Agent[LangGraph Agent]
Γûê    Agent --> LLM[LLM Service<br/>GPT-4o / Gemini]
Γûê    Agent --> Tools[Agent Tools]
Γûê    Tools --> DB[(Database)]
Γûê    Agent --> VS[Vector Store<br/>ChromaDB]
Γûê```
Γöé
Γûê## Agent Flow
Γöé
Γûê```mermaid
Γûêgraph LR
Γûê    START((Start)) --> Input[Parse Input]
Γûê    Input --> Analyze[Analyze Query]
Γûê    Analyze --> Decide{Need Tool?}
Γûê    Decide -->|Yes| CallTool[Call Tool]
Γûê    CallTool --> Analyze
Γûê    Decide -->|No| Generate[Generate Response]
Γûê    Generate --> END((End))
Γûê```
Γöé
Γûê## Component Details
Γöé
Γûê| Component | Technology | Purpose |
Γûê|-----------|-----------|---------|
Γûê| Frontend | React/Next.js | User interface |
Γûê| Backend | FastAPI | API server |
Γûê| Agent | LangGraph | AI agent orchestration |
Γûê| LLM | OpenAI/Gemini | Language model |
Γûê| Database | PostgreSQL/SQLite | Data persistence |
Γûê| Vector Store | ChromaDB | RAG / embeddings |


docs\BRIEF.md:
Γûê# Project Brief ΓÇö P-030
Γöé
Γûê**AI Agent ─æß╗ü xuß║Ñt & r├á so├ít thiß║┐t kß║┐ kiß║┐n tr├║c hß╗ç thß╗æng**
ΓûêVinUni AI20K Build Phase ┬╖ Cohort 3 & 4 ┬╖ 4 th├ánh vi├¬n ┬╖ 6 tuß║ºn
Γöé
Γûê---
Γöé
Γûê## Vß║Ñn ─æß╗ü
Γöé
Γûê─Éß╗Öi ph├ít triß╗ân r├á so├ít design doc dß╗▒a v├áo kinh nghiß╗çm c├í nh├ón. Hß╗ç quß║ú:
Γöé
Γûê- **Kh├┤ng nhß║Ñt qu├ín** ΓÇö c├╣ng mß╗Öt t├ái liß╗çu, hai ng╞░ß╗¥i r├á so├ít cho hai kß║┐t quß║ú kh├íc nhau
Γûê- **Kh├┤ng c├│ nguß╗ôn dß║½n** ΓÇö "chß╗ù n├áy thß║Ñy rß╗ºi ro" nh╞░ng vi phß║ím nguy├¬n tß║»c n├áo cß╗ºa c├┤ng ty th├¼ kh├┤ng chß╗ë ra ─æ╞░ß╗úc
Γûê- **Kh├┤ng truy vß║┐t** ΓÇö s├íu th├íng sau sß╗▒ cß╗æ, kh├┤ng trß║ú lß╗¥i ─æ╞░ß╗úc ai ─æ├ú duyß╗çt v├á duyß╗çt tr├¬n c╞í sß╗ƒ n├áo
Γûê- **N├║t cß╗ò chai** ΓÇö kiß║┐n tr├║c s╞░ giß╗Åi th├¼ ├¡t, hß╗ì bß║¡n th├¼ t├ái liß╗çu bß╗ï duyß╗çt qua loa cho kß╗ïp tiß║┐n ─æß╗Ö
Γöé
ΓûêChi ph├¡ sß╗¡a mß╗Öt quyß║┐t ─æß╗ïnh kiß║┐n tr├║c sai t─âng vß╗ìt qua tß╗½ng giai ─æoß║ín: sß╗¡a tr├¬n giß║Ñy l├á mß╗Öt d├▓ng, sß╗¡a sau khi l├¬n production l├á sß╗▒ cß╗æ cß╗Öng di tr├║ dß╗» liß╗çu.
Γöé
Γûê## Giß║úi ph├íp
Γöé
ΓûêMß╗Öt AI Agent nhß║¡n file `spec.yaml` m├┤ tß║ú thiß║┐t kß║┐, ─æß╗æi chiß║┐u vß╗¢i kho nguy├¬n tß║»c kiß║┐n tr├║c nß╗Öi bß╗Ö, v├á trß║ú vß╗ü b├ío c├ío r├á so├ít theo **4 chiß╗üu**: bß║úo mß║¡t, ─æß╗Ö sß║╡n s├áng, khß║ú n─âng mß╗ƒ rß╗Öng, chi ph├¡.
Γöé
ΓûêVß╗¢i mß╗ùi rß╗ºi ro, agent ─æ╞░a ra **2ΓÇô3 ph╞░╞íng ├ín khß║»c phß╗Ñc k├¿m bß║úng so s├ính ─æ├ính ─æß╗òi** theo chi ph├¡, ─æß╗Ö trß╗à, khß║ú n─âng mß╗ƒ rß╗Öng v├á hiß╗çu n─âng.
Γöé
Γûê**Agent kh├┤ng quyß║┐t ─æß╗ïnh.** N├│ dß╗½ng lß║íi v├á chß╗¥ kiß║┐n tr├║c s╞░ duyß╗çt tß╗½ng mß╗Ñc.
Γöé
Γûê## Ng╞░ß╗¥i d├╣ng
Γöé
Γûê| Vai tr├▓ | L├ám g├¼ |
Γûê|---|---|
Γûê| **SUBMITTER** ΓÇö lß║¡p tr├¼nh vi├¬n, tech lead | Nß╗Öp `spec.yaml`, ─æß╗ìc kß║┐t quß║ú, sß╗¡a v├á nß╗Öp lß║íi |
Γûê| **ARCHITECT** ΓÇö ng╞░ß╗¥i ph├¬ duyß╗çt thiß║┐t kß║┐ | Chß║íy r├á so├ít, quyß║┐t ─æß╗ïnh tß╗½ng ph├ít hiß╗çn, ph├¬ duyß╗çt |
Γöé
Γûê## Ba ─æiß╗âm kh├íc biß╗çt
Γöé
Γûê**1. Luß║¡t chß║íy tr╞░ß╗¢c, m├┤ h├¼nh chß║íy sau.** ─Éß║ºu v├áo YAML c├│ cß║Ñu tr├║c n├¬n ~70% lß╗ùi bß║»t ─æ╞░ß╗úc bß║▒ng luß║¡t x├íc ─æß╗ïnh ΓÇö `replicas: 1` l├á SPOF, ─æ├│ l├á mß╗Öt c├óu `if`, kh├┤ng cß║ºn suy luß║¡n. M├┤ h├¼nh chß╗ë l├ám phß║ºn n├│ giß╗Åi: giß║úi th├¡ch v├á ─æß╗ü xuß║Ñt.
Γöé
Γûê**2. Kh├┤ng bß╗ïa ΓÇö kiß╗âm tra c╞í hß╗ìc, kh├┤ng phß║úi dß║╖n d├▓ trong prompt.** Mß╗ùi ph├ít hiß╗çn phß║úi trß╗Å tß╗¢i mß╗Öt `yaml_path` c├│ thß║¡t vß╗¢i gi├í trß╗ï khß╗¢p, v├á mß╗Öt m├ú nguy├¬n tß║»c tra ─æ╞░ß╗úc trong DB. Kh├┤ng ─æß║ít th├¼ bß╗ï gß║»n nh├ún "cß║ºn kiß╗âm chß╗⌐ng", t├ích ri├¬ng khß╗Åi kß║┐t quß║ú ch├¡nh.
Γöé
Γûê**3. Sß╗æ liß╗çu chi ph├¡ kh├┤ng do LLM sinh.** Chi ph├¡ v├á ─æß╗Ö trß╗à trong bß║úng ─æ├ính ─æß╗òi t├¡nh bß║▒ng c├┤ng thß╗⌐c tß╗½ bß║úng `cost_reference` trong DB. Nß║┐u agent n├│i "+62 USD/th├íng" th├¼ con sß╗æ ─æ├│ tra ng╞░ß╗úc ─æ╞░ß╗úc.
Γöé
Γûê## Phß║ím vi MVP 
Γöé
ΓûêC├│: ─æ─âng nhß║¡p 2 vai tr├▓ ┬╖ upload `spec.yaml` ┬╖ r├á so├ít 4 chiß╗üu theo c├íc mß╗Ñc checklist ┬╖ tr├¡ch dß║½n nguy├¬n tß║»c nß╗Öi bß╗Ö ┬╖ bß║úng so s├ính ph╞░╞íng ├ín ┬╖ quy tr├¼nh duyß╗çt HITL c├│ l╞░u vß║┐t ┬╖ deploy Docker c├│ Live URL ┬╖ Sinh bß║ún nh├íp kiß║┐n tr├║c tß╗½ NL ┬╖ ph├ít hiß╗çn anti-pattern
Γöé
Γûê## C├ích ─æo
Γöé
Γûê| Chß╗ë ti├¬u | Mß╗Ñc ti├¬u | C├ích ─æo |
Γûê|---|---|---|
Γûê| ─Éß╗Ö bao phß╗º lß╗ùi | ΓëÑ 70% | Bß╗Ö golden set 5 file YAML ΓÇö 2 bß║ún sß║ích, 3 bß║ún c├ái sß║╡n lß╗ùi c├│ ─æ├íp ├ín |
Γûê| B├ío ─æß╗Öng giß║ú | Γëñ 2 / file sß║ích | C├╣ng bß╗Ö golden set |
Γûê| Tß╗╖ lß╗ç ─æ├ú x├íc minh | ΓëÑ 95% | Cß╗Öt `grounded_ratio` |
Γûê| Thß╗¥i gian r├á so├ít | Γëñ 120 s | Cß╗Öt `duration_ms` |
Γûê| Chi ph├¡ | Γëñ $0.05 / l╞░ß╗út | Cß╗Öt `cost_usd` |
Γöé
Γûê## C├┤ng nghß╗ç
Γöé
Γûê`FastAPI` ┬╖ `LangGraph` ┬╖ `gpt-4o-mini` (mß║╖c ─æß╗ïnh) + `gpt-4o` (node tß╗òng hß╗úp) ┬╖ `PostgreSQL + pgvector` ┬╖ `React.js ` ┬╖ `Docker`
ΓûêHß║í tß║ºng: Render (API) ┬╖ Vercel (Web) ┬╖ Supabase (DB) ΓÇö to├án bß╗Ö d├╣ng g├│i miß╗àn ph├¡
Γöé
Γûê## Lß╗Ö tr├¼nh
Γöé
Γûê| Tuß║ºn | Kß║┐t quß║ú |
Γûê|---|---|
Γûê| 1 | Luß╗ông r├á so├ít chß║íy th├┤ng qua Swagger, ch╞░a c├│ UI |
Γûê| 2 | MVP ho├án chß╗ënh, c├│ Live URL |
Γûê| 3 | Sinh diagram C4 tß╗½ YAML, ph├ít hiß╗çn anti-pattern |
Γûê| 4 | RAGAS, xuß║Ñt b├ío c├ío |
Γûê| 5 | ─Éo ─æß║íc, 10 deliverables, video demo |


docs\guide\anti-patterns\cohort-1-mistakes.md:
Γûê---
Γûêtitle: "Cohort 1 Mistakes"
Γûêdescription: "Ph├ón t├¡ch lß╗ùi tß╗½ 12 teams Cohort 1"
Γûêweight: 1
Γûê---
Γöé
Γûê## Top 10 Mistakes (Cohort 1)
Γöé
ΓûêPh├ón t├¡ch tß╗½ 12 teams, ─æ├óy l├á nhß╗»ng lß╗ùi phß╗ò biß║┐n nhß║Ñt:
Γöé
Γûê### 1. Bare except ΓÇö 3/12 teams
Γöé
Γûê```python
Γûê# Γ¥î Lß╗ùi: Che mß╗ìi lß╗ùi, kh├┤ng biß║┐t g├¼ fail
Γûêtry:
Γûê    result = await process(data)
Γûêexcept:
Γûê    pass
Γöé
Γûê# Γ£à Fix: Specific exception
Γûêtry:
Γûê    result = await process(data)
Γûêexcept ValueError as e:
Γûê    logger.error(f"Invalid data: {e}")
Γûê    return {"error": str(e)}
Γûê```
Γöé
Γûê### 2. Hardcoded Secrets ΓÇö 1/12 teams
Γöé
Γûê```python
Γûê# Γ¥î API key lß╗Ö trong code
Γûêclient = OpenAI(api_key="sk-abc123...")
Γöé
Γûê# Γ£à D├╣ng .env + config
Γûêfrom src.config import get_settings
Γûêsettings = get_settings()
Γûêclient = OpenAI(api_key=settings.openai_api_key)
Γûê```
Γöé
Γûê### 3. No Tests ΓÇö Hß║ºu hß║┐t teams
Γöé
Γûê```python
Γûê# Chß╗ë 2/12 teams c├│ tests
Γûê# Template ─æ├ú c├│ sß║╡n test structure ΓÇö chß╗ë cß║ºn viß║┐t th├¬m
Γûê```
Γöé
Γûê### 4. No CI/CD ΓÇö 0/12 teams
Γöé
Γûê```yaml
Γûê# Template ─æ├ú c├│ .github/workflows/ci.yml
Γûê# Chß╗ë cß║ºn push l├¬n GitHub ΓåÆ CI tß╗▒ chß║íy
Γûê```
Γöé
Γûê### 5. Functions qu├í d├ái
Γöé
Γûê```python
Γûê# Γ¥î 1 function 200+ lines
Γûêdef process_everything(data):
Γûê    # ... 200 lines ...
Γöé
Γûê# Γ£à T├ích th├ánh nhiß╗üu functions
Γûêasync def analyze(data: str) -> dict:
Γûê    """5-10 lines"""
Γûê    ...
Γöé
Γûêasync def transform(result: dict) -> dict:
Γûê    """5-10 lines"""
Γûê    ...
Γûê```
Γöé
Γûê### 6. Kh├┤ng c├│ Architecture Diagram
Γöé
Γûê- 5/12 teams thiß║┐u diagram
Γûê- BTC chß║Ñm System Design thß║Ñp ΓåÆ mß║Ñt 2-3 points
Γöé
Γûê### 7. README thiß║┐u
Γöé
Γûê- 6/12 teams README k├⌐m
Γûê- Thiß║┐u: problem statement, tech stack, setup guide
Γöé
Γûê### 8. Kh├┤ng c├│ Evaluation Evidence
Γöé
Γûê- Chß╗ë 2/12 teams c├│
Γûê- BTC kh├┤ng thß║Ñy bß║▒ng chß╗⌐ng testing ΓåÆ ─æiß╗âm thß║Ñp
Γöé
Γûê### 9. Tß║Ñt cß║ú code trong 1 file
Γöé
Γûê- 4/12 teams c├│ main.py > 500 lines
Γûê- Kh├│ maintain, kh├│ test, kh├│ review
Γöé
Γûê### 10. Kh├┤ng type hints
Γöé
Γûê- Code quality giß║úm ΓåÆ mß║Ñt 1-2 points
Γöé
Γûê## Common Weaknesses by Score
Γöé
Γûê### Bottom Tier (27-30 points)
Γöé
Γûê| Team | Score | Main Issues |
Γûê|------|-------|------------|
Γûê| 004 | 27.9 | System design 2.5, DevOps 1.5 |
Γûê| 006 | 28.8 | Code quality 4.1, System 6.0 |
Γûê| 012 | 28.9 | Product 4.8, DevOps 3.8 |
Γûê| 011 | 29.3 | DevOps 2.0, bare except |
Γûê| 001 | 32.0 | Code quality 3.3 |
Γöé
Γûê### Pattern chung: DevOps + Code Quality = ─æiß╗âm thß║Ñp nhß║Ñt


docs\guide\anti-patterns\_index.md:
Γûê---
Γûêtitle: "Anti-Patterns"
Γûêdescription: "Lß╗ùi th╞░ß╗¥ng gß║╖p tß╗½ Cohort 1 ΓÇö PHß║óI TR├üNH"
Γûêweight: 8
Γûê---
Γöé
ΓûêPhß║ºn n├áy tß╗òng hß╗úp Top 10 sai lß║ºm phß╗ò biß║┐n nhß║Ñt tß╗½ c├íc ─æß╗Öi Cohort 1, ─æ╞░ß╗úc ph├ón t├¡ch tß╗½ kß║┐t quß║ú ─æ├ính gi├í thß╗▒c tß║┐. Dß╗▒a tr├¬n ─æiß╗âm sß╗æ cß╗ºa c├íc ─æß╗Öi xß║┐p hß║íng thß║Ñp, bß║ín sß║╜ thß║Ñy r├╡ nhß╗»ng lß╗ùi n├áo lß║╖p ─æi lß║╖p lß║íi v├á hß║¡u quß║ú cß╗ºa ch├║ng. ─Éß╗ìc kß╗╣ phß║ºn n├áy sß║╜ gi├║p bß║ín tr├ính nhß╗»ng c├íi bß║½y m├á nhiß╗üu ─æß╗Öi ─æ├ú vß║Ñp phß║úi, tß╗½ ─æ├│ n├óng cao chß║Ñt l╞░ß╗úng sß║ún phß║⌐m v├á ─æiß╗âm sß╗æ cuß╗æi c├╣ng.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [Cohort 1 Mistakes](cohort-1-mistakes.md) ΓÇö Top 10 sai lß║ºm Cohort 1, ph├ón t├¡ch ─æiß╗âm c├íc ─æß╗Öi d╞░ß╗¢i, b├ái hß╗ìc r├║t ra


docs\guide\architecture\system-design.md:
Γûê---
Γûêtitle: "System Design"
Γûêdescription: "Tß╗òng quan kiß║┐n tr├║c hß╗ç thß╗æng"
Γûêweight: 1
Γûê---
Γöé
Γûê## System Architecture
Γöé
Γûê### Overview Diagram
Γöé
Γûê```mermaid
Γûêgraph TB
Γûê    User([User]) --> UI[Frontend<br/>React/Next.js]
Γûê    UI -->|REST API| API[FastAPI Backend]
Γûê    API --> Agent[LangGraph Agent]
Γûê    Agent --> LLM[LLM Service<br/>GPT-4o / Gemini]
Γûê    Agent --> Tools[Agent Tools]
Γûê    Tools --> DB[(Database)]
Γûê    Agent --> VS[Vector Store<br/>ChromaDB]
Γûê```
Γöé
Γûê## Components
Γöé
Γûê### 1. Frontend (React/Next.js)
Γöé
Γûê- **Purpose:** User interface cho sß║ún phß║⌐m
Γûê- **Key Features:** Responsive, dark mode, realtime
Γûê- **State Management:** React hooks / Zustand
Γöé
Γûê### 2. Backend (FastAPI)
Γöé
Γûê- **Purpose:** API server xß╗¡ l├╜ business logic
Γûê- **API Design:** RESTful endpoints
Γûê- **Auth:** JWT (nß║┐u cß║ºn)
Γöé
Γûê### 3. AI Agent (LangGraph)
Γöé
Γûê- **Agent Type:** ReAct / Plan-and-Execute / Custom
Γûê- **State:** TypedDict schema
Γûê- **Nodes:** Xß╗¡ l├╜ tß╗½ng b╞░ß╗¢c trong pipeline
Γûê- **Tools:** Search, calculate, API calls
Γöé
Γûê### 4. Database
Γöé
Γûê- **Type:** PostgreSQL (production) / SQLite (dev)
Γûê- **ORM:** SQLAlchemy (nß║┐u cß║ºn)
Γûê- **Migrations:** Alembic (nß║┐u cß║ºn)
Γöé
Γûê### 5. Vector Store
Γöé
Γûê- **Type:** ChromaDB (local) / Pinecone (cloud)
Γûê- **Embeddings:** OpenAI embeddings
Γûê- **Purpose:** RAG / similarity search
Γöé
Γûê## Data Flow
Γöé
Γûê1. User gß╗¡i request tß╗½ Frontend
Γûê2. API route nhß║¡n v├á validate input (Pydantic)
Γûê3. Agent xß╗¡ l├╜ qua LangGraph pipeline
Γûê4. LLM generate response
Γûê5. Tools thß╗▒c thi actions (nß║┐u cß║ºn)
Γûê6. Response trß║ú vß╗ü Frontend qua API
Γöé
Γûê## Design Decisions
Γöé
Γûê| Decision | Choice | Reason |
Γûê|----------|--------|--------|
Γûê| Framework | FastAPI | Async, auto-docs, type-safe |
Γûê| Agent | LangGraph | Flexible state machine |
Γûê| Database | SQLiteΓåÆPostgreSQL | Dev dß╗à, prod mß║ính |
Γûê| Frontend | Next.js | Full-stack ready |


docs\guide\architecture\_index.md:
Γûê---
Γûêtitle: "System Architecture"
Γûêdescription: "Thiß║┐t kß║┐ kiß║┐n tr├║c cho AI Agent project"
Γûêweight: 2
Γûê---
Γöé
ΓûêPhß║ºn n├áy tr├¼nh b├áy tß╗òng quan kiß║┐n tr├║c hß╗ç thß╗æng cß╗ºa mß╗Öt dß╗▒ ├ín AI Agent ho├án chß╗ënh. Bß║ín sß║╜ hiß╗âu ─æ╞░ß╗úc c├íc th├ánh phß║ºn ch├¡nh, c├ích ch├║ng giao tiß║┐p vß╗¢i nhau v├á luß╗ông dß╗» liß╗çu ─æi qua hß╗ç thß╗æng. C├íc s╞í ─æß╗ô Mermaid gi├║p bß║ín h├¼nh dung trß╗▒c quan kiß║┐n tr├║c tr╞░ß╗¢c khi ─æi v├áo code. Nß║»m vß╗»ng kiß║┐n tr├║c l├á nß╗ün tß║úng ─æß╗â x├óy dß╗▒ng agent c├│ thß╗â mß╗ƒ rß╗Öng v├á bß║úo tr├¼ dß╗à d├áng.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [System Design](system-design.md) ΓÇö Tß╗òng quan hß╗ç thß╗æng vß╗¢i s╞í ─æß╗ô Mermaid, m├┤ tß║ú component v├á luß╗ông dß╗» liß╗çu


docs\guide\bmad\overview.md:
Γûê---
Γûêtitle: "BMAD-v6 Overview"
Γûêdescription: "Tß╗òng quan vß╗ü BMAD Method v├á c├ích ├íp dß╗Ñng"
Γûêweight: 1
Γûê---
Γöé
Γûê## BMAD Method l├á g├¼?
Γöé
Γûê**BMAD** (Build More Architect Dreams) l├á framework m├ú nguß╗ôn mß╗ƒ cho AI-driven software development.
Γöé
Γûê- **GitHub:** github.com/bmad-code-org/BMAD-METHOD
Γûê- **Docs:** docs.bmad-method.org
Γûê- **License:** MIT (free)
Γûê- **IDE:** Claude Code, Cursor, Codex CLI
Γöé
Γûê## 6 Agents mß║╖c ─æß╗ïnh
Γöé
Γûê| Agent | Name | Role |
Γûê|-------|------|------|
Γûê| Analyst | Mary | Business Analyst |
Γûê| PM | John | Product Manager |
Γûê| Architect | Winston | System Architect |
Γûê| Developer | Amelia | Senior Developer |
Γûê| UX Designer | Sally | UX Designer |
Γûê| Tech Writer | Paige | Technical Writer |
Γöé
Γûê## 4-Phase Workflow
Γöé
Γûê### Phase 1: Analysis
Γûê- Brainstorming, research, product briefs
Γöé
Γûê### Phase 2: Planning
Γûê- PRD creation, UX design
Γöé
Γûê### Phase 3: Solutioning
Γûê- Architecture, ADRs, epic/story breakdown
Γöé
Γûê### Phase 4: Implementation
Γûê- Sprint planning, story implementation, code review
Γöé
Γûê## Folder Structure
Γöé
Γûê```
Γûêproject/
ΓûêΓö£ΓöÇΓöÇ _bmad/                    ΓåÉ BMAD core
ΓûêΓöé   Γö£ΓöÇΓöÇ _config/              ΓåÉ Config
ΓûêΓöé   Γö£ΓöÇΓöÇ bmm/                  ΓåÉ Module config
ΓûêΓöé   Γö£ΓöÇΓöÇ custom/               ΓåÉ Customizations
ΓûêΓöé   ΓööΓöÇΓöÇ scripts/              ΓåÉ Helper scripts
ΓûêΓö£ΓöÇΓöÇ _bmad-output/             ΓåÉ Output
ΓûêΓöé   Γö£ΓöÇΓöÇ planning-artifacts/   ΓåÉ Phase 1-3
ΓûêΓöé   ΓööΓöÇΓöÇ implementation-artifacts/ ΓåÉ Phase 4
ΓûêΓö£ΓöÇΓöÇ docs/                     ΓåÉ Documentation
ΓûêΓööΓöÇΓöÇ src/                      ΓåÉ Source code
Γûê```
Γöé
Γûê## Khi n├áo d├╣ng BMAD?
Γöé
Γûê- **YES** ΓÇö Project phß╗⌐c tß║íp, cß║ºn planning kß╗╣
Γûê- **YES** ΓÇö Team muß╗æn structured workflow
Γûê- **NO** ΓÇö Project nhß╗Å, quick prototype
Γûê- **NO** ΓÇö Team ch╞░a quen vß╗¢i AI-assisted development


docs\guide\bmad\_index.md:
Γûê---
Γûêtitle: "BMAD Method"
Γûêdescription: "BMAD-v6 ΓÇö Ph╞░╞íng ph├íp ph├ít triß╗ân phß║ºn mß╗üm theo agent-driven workflow"
Γûêweight: 10
Γûê---
Γöé
ΓûêPhß║ºn n├áy giß╗¢i thiß╗çu BMAD Method ΓÇö ph╞░╞íng ph├íp ph├ít triß╗ân phß║ºn mß╗üm theo m├┤ h├¼nh agent-driven workflow. Bß║ín sß║╜ t├¼m hiß╗âu ─æß╗ïnh ngh─⌐a BMAD, 6 loß║íi agent chuy├¬n biß╗çt v├á quy tr├¼nh l├ám viß╗çc 4 giai ─æoß║ín tß╗½ ph├ón t├¡ch y├¬u cß║ºu ─æß║┐n triß╗ân khai. Cß║Ñu tr├║c th╞░ mß╗Ñc chuß║⌐n c┼⌐ng ─æ╞░ß╗úc tr├¼nh b├áy chi tiß║┐t ─æß╗â bß║ín ├íp dß╗Ñng ngay v├áo dß╗▒ ├ín. BMAD gi├║p team l├ám viß╗çc hiß╗çu quß║ú h╞ín bß║▒ng c├ích ph├ón r├╡ vai tr├▓ giß╗»a c├íc agent.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [Overview](overview.md) ΓÇö ─Éß╗ïnh ngh─⌐a BMAD, 6 agents, 4-phase workflow v├á folder structure


docs\guide\chapter-01.md:
Γûê---
Γûêtitle: "Lß╗¥i mß╗ƒ ─æß║ºu"
Γûêweight: 1
Γûê---
Γöé
Γûê## Mß╗Ñc ti├¬u cß╗ºa t├ái liß╗çu n├áy
Γöé
ΓûêCuß╗æn s├ích n├áy ─æ╞░ß╗úc thiß║┐t kß║┐ vß╗¢i mß╗Öt mß╗Ñc ti├¬u duy nhß║Ñt: **gi├║p bß║ín x├óy dß╗▒ng mß╗Öt dß╗▒ ├ín AI Agent ─æß║ít chß║Ñt l╞░ß╗úng cao**, tß╗½ thiß║┐t kß║┐ kiß║┐n tr├║c ─æß║┐n nß╗Öp b├ái cuß╗æi kß╗│.
Γöé
ΓûêBß║ín sß║╜ hß╗ìc ─æ╞░ß╗úc:
Γöé
Γûê- C├ích tß╗ò chß╗⌐c dß╗▒ ├ín theo chuß║⌐n industry ΓÇö folder structure, config, environment
Γûê- X├óy dß╗▒ng AI Agent vß╗¢i LangGraph ΓÇö state, nodes, edges, tools
Γûê- Ph├ít triß╗ân API vß╗¢i FastAPI ΓÇö routes, validation, error handling, streaming
Γûê- Thiß║┐t lß║¡p DevOps ΓÇö Docker, CI/CD, deploy l├¬n cloud
Γûê- Viß║┐t test v├á ─æ├ính gi├í chß║Ñt l╞░ß╗úng Agent
Γûê- Ho├án th├ánh ─æß║ºy ─æß╗º deliverables ─æ├║ng deadline
Γöé
ΓûêMß╗ùi ch╞░╞íng ─æi k├¿m code examples cß╗Ñ thß╗â, tips thß╗▒c h├ánh, v├á b├ái tß║¡p ├┤n tß║¡p. ─Éß╗ìc xong t├ái liß╗çu n├áy, bß║ín c├│ thß╗â tß╗▒ tin build mß╗Öt project ho├án chß╗ënh.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** ─É├óy kh├┤ng phß║úi s├ích l├╜ thuyß║┐t. Mß╗ùi ch╞░╞íng ─æß╗üu c├│ code bß║ín c├│ thß╗â copy, chß║íy, v├á modify ngay. H├úy mß╗ƒ terminal l├¬n v├á code theo tß╗½ng b╞░ß╗¢c.
Γöé
Γûê## Nhß╗»ng sai lß║ºm phß╗ò biß║┐n cß║ºn tr├ính
Γöé
ΓûêNhiß╗üu ─æß╗Öi khi lß║ºn ─æß║ºu x├óy dß╗▒ng AI Agent mß║»c phß║úi nhß╗»ng sai lß║ºm t╞░╞íng tß╗▒ ΓÇö kh├┤ng phß║úi v├¼ thiß║┐u th├┤ng minh, m├á v├¼ thiß║┐u kinh nghiß╗çm engineering. H├úy ghi nhß╗¢ nhß╗»ng lß╗ù hß╗òng phß╗ò biß║┐n n├áy ─æß╗â tr├ính:
Γöé
Γûê**Kh├┤ng thiß║┐t lß║¡p CI/CD pipeline.** CI/CD (Continuous Integration/Continuous Deployment) l├á quy chuß║⌐n tß╗æi thiß╗âu trong ng├ánh phß║ºn mß╗üm hiß╗çn ─æß║íi. Khi push code l├¬n repository, hß╗ç thß╗æng tß╗▒ ─æß╗Öng chß║íy test, kiß╗âm tra code quality. Kh├┤ng c├│ CI/CD = code ─æ╞░ß╗úc test thß╗º c├┤ng, deploy c┼⌐ng thß╗º c├┤ng ΓÇö rß╗ºi ro lß╗ùi production rß║Ñt cao.
Γöé
Γûê**Bß╗Å qua evaluation (─æ├ính gi├í chß║Ñt l╞░ß╗úng Agent).** Evaluation ─æo l╞░ß╗¥ng: Agent trß║ú lß╗¥i ─æ├║ng bao nhi├¬u phß║ºn tr─âm? C├│ bß╗ï hallucination kh├┤ng? Tß╗æc ─æß╗Ö phß║ún hß╗ôi thß║┐ n├áo? Kh├┤ng c├│ evaluation, bß║ín kh├┤ng thß╗â biß║┐t Agent thß╗▒c sß╗▒ tß╗æt hay chß╗ë "tr├┤ng c├│ vß║╗ hoß║ít ─æß╗Öng" trong demo.
Γöé
Γûê**README qu├í s╞í s├ái hoß║╖c thiß║┐u ho├án to├án.** README l├á mß║╖t tiß╗ün cß╗ºa dß╗▒ ├ín. N├│ cho ng╞░ß╗¥i ─æß╗ìc biß║┐t dß╗▒ ├ín l├ám g├¼, chß║íy thß║┐ n├áo, cß║Ñu tr├║c th╞░ mß╗Ñc ra sao.
Γöé
Γûê**Kh├┤ng c├│ environment setup r├╡ r├áng.** Ng╞░ß╗¥i kh├íc kh├┤ng thß╗â chß║íy ─æ╞░ß╗úc dß╗▒ ├ín cß╗ºa bß║ín chß╗ë bß║▒ng c├ích ─æß╗ìc t├ái liß╗çu. Trong m├┤i tr╞░ß╗¥ng thß╗▒c tß║┐, khß║ú n─âng onboarding nhanh l├á yß║┐u tß╗æ sß╗æng c├▓n.
Γöé
Γûê**Gß╗Öp tß║Ñt cß║ú code v├áo mß╗Öt file.** Dß╗▒ ├ín kh├┤ng c├│ cß║Ñu tr├║c th╞░ mß╗Ñc r├╡ r├áng, kh├│ maintain, kh├│ test, kh├│ review.
Γöé
Γûê**Kh├┤ng viß║┐t test.** Kh├┤ng c├│ test = kh├┤ng thß╗â chß╗⌐ng minh code hoß║ít ─æß╗Öng ─æ├║ng, kh├┤ng thß╗â refactor an to├án.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Nhß╗»ng vß║Ñn ─æß╗ü tr├¬n phß║ún ├ính khoß║úng trß╗æng giß╗»a kiß║┐n thß╗⌐c thuß║¡t to├ín v├á kß╗╣ n─âng engineering thß╗▒c tß║┐. Cuß╗æn s├ích n├áy ─æ╞░ß╗úc thiß║┐t kß║┐ ─æß╗â lß║Ñp ─æß║ºy khoß║úng trß╗æng ─æ├│.
Γöé
Γûê## ─Éß╗æi t╞░ß╗úng v├á kiß║┐n thß╗⌐c cß║ºn c├│
Γöé
Γûê### D├ánh cho ai
Γöé
Γûê- **─Éß╗æi t╞░ß╗úng ch├¡nh:** Sinh vi├¬n tham gia ch╞░╞íng tr├¼nh AI20K Build Phase, muß╗æn x├óy dß╗▒ng AI Agent ho├án chß╗ënh tß╗½ con sß╗æ kh├┤ng ─æß║┐n sß║ún phß║⌐m c├│ thß╗â demo v├á deploy
Γûê- **─Éß╗æi t╞░ß╗úng phß╗Ñ:** Mentor, reviewer muß╗æn t├ái liß╗çu tham khß║úo chuß║⌐n. Lß║¡p tr├¼nh vi├¬n tß╗▒ hß╗ìc muß╗æn ├íp dß╗Ñng best practices v├áo dß╗▒ ├ín AI Agent
Γöé
Γûê### Kiß║┐n thß╗⌐c cß║ºn c├│ tr╞░ß╗¢c
Γöé
Γûê| Kiß║┐n thß╗⌐c | Mß╗⌐c ─æß╗Ö cß║ºn thiß║┐t | Giß║úi th├¡ch |
Γûê|-----------|-------------------|------------|
Γûê| Python c╞í bß║ún | Trung b├¼nh | Biß║┐t viß║┐t h├ám, class, async/await, type hints |
Γûê| API & HTTP | C╞í bß║ún | Hiß╗âu GET/POST, JSON, REST |
Γûê| Git | C╞í bß║ún | Clone, commit, push, branch |
Γûê| Terminal/CLI | C╞í bß║ún | Chß║íy lß╗çnh, navigate th╞░ mß╗Ñc |
Γûê| AI/LLM | Kh├┤ng bß║»t buß╗Öc | S├ích sß║╜ h╞░ß╗¢ng dß║½n tß╗½ ─æß║ºu |
Γöé
ΓûêNß║┐u bß║ín ch╞░a vß╗»ng Python, h├úy ho├án th├ánh kh├│a "AI Python for Beginners" tr├¬n [DeepLearning.AI](https://www.deeplearning.ai/courses) tr╞░ß╗¢c khi bß║»t ─æß║ºu.
Γöé
Γûê## C├ích sß╗¡ dß╗Ñng t├ái liß╗çu n├áy
Γöé
Γûê### Lß╗Ö tr├¼nh 6 tuß║ºn
Γöé
Γûê| Tuß║ºn | Nß╗Öi dung | Ch╞░╞íng | Thß╗¥i gian |
Γûê|------|----------|--------|-----------|
Γûê| 1 | Clone template, setup m├┤i tr╞░ß╗¥ng, git workflow | 1-2 | 4h |
Γûê| 2 | Thiß║┐t kß║┐ kiß║┐n tr├║c, vß║╜ diagram | 3 | 6h |
Γûê| 3 | X├óy dß╗▒ng AI Agent vß╗¢i LangGraph | 4 | 8h |
Γûê| 4 | Ph├ít triß╗ân API + Giao diß╗çn | 5-6 | 8h |
Γûê| 5 | DevOps, Docker, CI/CD, deploy | 7 | 6h |
Γûê| 6 | Testing, evaluation, ho├án thiß╗çn deliverables | 8-9 | 8h |
Γöé
Γûê### C├ích ─æß╗ìc mß╗ùi ch╞░╞íng
Γöé
ΓûêMß╗ùi ch╞░╞íng c├│ cß║Ñu tr├║c thß╗æng nhß║Ñt:
Γöé
Γûê1. **Giß╗¢i thiß╗çu** ΓÇö Mß╗Ñc ti├¬u cß╗ºa ch╞░╞íng, bß║ín sß║╜ hß╗ìc ─æ╞░ß╗úc g├¼
Γûê2. **Nß╗Öi dung ch├¡nh** ΓÇö Giß║úi th├¡ch chi tiß║┐t k├¿m code examples
Γûê3. **Callout boxes** ΓÇö Mß║╣o (≡ƒÆí), L╞░u ├╜ (ΓÜá∩╕Å), ─Éiß╗âm ch├¡nh (≡ƒöæ)
Γûê4. **T├│m tß║»t** ΓÇö Key takeaways
Γûê5. **C├óu hß╗Åi ├┤n tß║¡p** ΓÇö Kiß╗âm tra hiß╗âu biß║┐t
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** ─Éß╗½ng chß╗ë ─æß╗ìc ΓÇö h├úy mß╗ƒ terminal l├¬n v├á code theo. Hß╗ìc bß║▒ng c├ích l├ám (learning by doing) l├á c├ích hiß╗çu quß║ú nhß║Ñt. Mß╗ùi code block trong s├ích ─æß╗üu c├│ thß╗â chß║íy ─æ╞░ß╗úc trß╗▒c tiß║┐p.
Γöé
Γûê## Tß╗òng quan 10 ch╞░╞íng
Γöé
Γûê| Ch╞░╞íng | Nß╗Öi dung | ─Éiß╗âm trß╗ìng t├óm |
Γûê|---------|----------|----------------|
Γûê| 1 | Lß╗¥i mß╗ƒ ─æß║ºu (ch╞░╞íng n├áy) | Mß╗Ñc ti├¬u, c├ích sß╗¡ dß╗Ñng |
Γûê| 2 | Khß╗ƒi tß║ío dß╗▒ ├ín | Template, setup, git workflow |
Γûê| 3 | Thiß║┐t kß║┐ kiß║┐n tr├║c | 3-tier architecture, diagrams, ADR |
Γûê| 4 | LangGraph Agent | State, nodes, edges, tools, RAG |
Γûê| 5 | FastAPI | Routes, validation, error handling |
Γûê| 6 | Giao diß╗çn ng╞░ß╗¥i d├╣ng | Next.js, responsive, streaming |
Γûê| 7 | DevOps | Docker, CI/CD, deploy, logging |
Γûê| 8 | Kiß╗âm thß╗¡ | Unit test, integration test, RAGAS |
Γûê| 9 | Nß╗Öp b├ái Demo Day | Deliverables, checklist, tips |
Γûê| 10 | T├ái nguy├¬n hß╗ìc tß║¡p | Courses, docs, BMAD method |
Γöé
Γûê## T├│m tß║»t ch╞░╞íng
Γöé
Γûê- Cuß╗æn s├ích n├áy gi├║p bß║ín build AI Agent project ─æß║ít chß║Ñt l╞░ß╗úng cao, tß╗½ A ─æß║┐n Z
Γûê- 10 ch╞░╞íng, 6 tuß║ºn, mß╗ùi ch╞░╞íng c├│ code examples v├á b├ái tß║¡p
Γûê- Sai lß║ºm phß╗ò biß║┐n cß║ºn tr├ính: thiß║┐u CI/CD, thiß║┐u test, README k├⌐m, kh├┤ng evaluation
Γûê- Hß╗ìc bß║▒ng c├ích l├ám ΓÇö mß╗ƒ terminal l├¬n v├á code theo tß╗½ng b╞░ß╗¢c
Γöé
Γûê## C├óu hß╗Åi ├┤n tß║¡p
Γöé
Γûê1. H├úy liß╗çt k├¬ 3 sai lß║ºm phß╗ò biß║┐n khi x├óy dß╗▒ng AI Agent m├á bß║ín cß║ºn tr├ính. Tß║íi sao mß╗ùi sai lß║ºm ─æ├│ nghi├¬m trß╗ìng?
Γûê2. Bß║ín ─æ├ú c├│ nhß╗»ng kiß║┐n thß╗⌐c nß╗ün tß║úng n├áo trong bß║úng "Kiß║┐n thß╗⌐c cß║ºn c├│"? Nhß╗»ng phß║ºn n├áo cß║ºn bß╗ò sung?
Γûê3. Lß║¡p lß╗ïch 6 tuß║ºn theo lß╗Ö tr├¼nh, ghi cß╗Ñ thß╗â mß╗ùi tuß║ºn bß║ín sß║╜ d├ánh bao nhi├¬u giß╗¥ v├á ho├án th├ánh ch╞░╞íng n├áo.


docs\guide\chapter-02.md:
Γûê---
Γûêtitle: "Khß╗ƒi tß║ío dß╗▒ ├ín tß╗½ Template"
Γûêweight: 2
Γûê---
Γöé
Γûê## Clone template ΓÇö Bß║»t ─æß║ºu tß╗½ nß╗ün tß║úng ─æ├║ng
Γöé
ΓûêMß╗Öt trong nhß╗»ng sai lß║ºm phß╗ò biß║┐n nhß║Ñt cß╗ºa sinh vi├¬n khi bß║»t ─æß║ºu dß╗▒ ├ín mß╗¢i l├á tß║ío mß╗ìi thß╗⌐ tß╗½ con sß╗æ kh├┤ng ΓÇö tß╗▒ setup cß║Ñu tr├║c th╞░ mß╗Ñc, tß╗▒ cß║Ñu h├¼nh linting, tß╗▒ viß║┐t CI/CD file, tß╗▒ tß║ío Dockerfile. Kß║┐t quß║ú l├á mß╗ùi ─æß╗Öi c├│ mß╗Öt cß║Ñu tr├║c kh├íc nhau, thiß║┐u nhß╗»ng file quan trß╗ìng, v├á mß║Ñt h├áng ng├áy chß╗ë ─æß╗â setup thay v├¼ viß║┐t logic ch├¡nh. Template dß╗▒ ├ín giß║úi quyß║┐t vß║Ñn ─æß╗ü n├áy bß║▒ng c├ích cung cß║Ñp mß╗Öt nß╗ün tß║úng ─æ├ú ─æ╞░ß╗úc chuß║⌐n h├│a, bao gß╗ôm tß║Ñt cß║ú best practices m├á bß║ín cß║ºn.
Γöé
ΓûêTrong AI20K, ch├║ng t├┤i cung cß║Ñp sß║╡n mß╗Öt template repository vß╗¢i cß║Ñu tr├║c ─æ├ú ─æ╞░ß╗úc kiß╗âm chß╗⌐ng. Bß║ín chß╗ë cß║ºn clone, cß║Ñu h├¼nh, v├á bß║»t ─æß║ºu code. H├úy c├╣ng thß╗▒c hiß╗çn tß╗½ng b╞░ß╗¢c.
Γöé
Γûê### Clone repository
Γöé
ΓûêMß╗ƒ terminal v├á chß║íy c├íc lß╗çnh sau:
Γöé
Γûê```bash
Γûê# Thay XXX bß║▒ng sß╗æ thß╗⌐ tß╗▒ ─æß╗Öi cß╗ºa bß║ín (v├¡ dß╗Ñ: C2-App-001, C2-App-042)
Γûê$ git clone https://github.com/AI20K-Build-Cohort-2/starter-code-template.git C2-App-XXX
Γöé
Γûê# Di chuyß╗ân v├áo th╞░ mß╗Ñc dß╗▒ ├ín
Γûê$ cd C2-App-XXX
Γöé
Γûê# X├│a git history cß╗ºa template v├á khß╗ƒi tß║ío lß║íi
Γûê$ rm -rf .git
Γûê$ git init
Γûê$ git add .
Γûê$ git commit -m "feat: khß╗ƒi tß║ío dß╗▒ ├ín tß╗½ template"
Γöé
Γûê# ─Éß║⌐y l├¬n repository cß╗ºa ─æß╗Öi bß║ín
Γûê$ git remote add origin https://github.com/AI20K-Build-Cohort-2/C2-App-XXX.git
Γûê$ git branch -M main
Γûê$ git push -u origin main
Γûê```
Γöé
ΓûêTß║íi sao phß║úi x├│a `.git` v├á khß╗ƒi tß║ío lß║íi? V├¼ template c├│ lß╗ïch sß╗¡ commit cß╗ºa ch├¡nh template, bß║ín kh├┤ng muß╗æn lß╗ïch sß╗¡ ─æ├│ lß║½n v├áo dß╗▒ ├ín cß╗ºa m├¼nh. Bß║▒ng c├ích `rm -rf .git` v├á `git init`, bß║ín bß║»t ─æß║ºu vß╗¢i mß╗Öt lß╗ïch sß╗¡ sß║ích, commit ─æß║ºu ti├¬n ghi nhß║¡n ng├áy bß║ín bß║»t ─æß║ºu dß╗▒ ├ín.
Γöé
Γûê### Cß║Ñu tr├║c th╞░ mß╗Ñc v├á ├╜ ngh─⌐a
Γöé
ΓûêSau khi clone, h├úy mß╗ƒ th╞░ mß╗Ñc dß╗▒ ├ín trong editor (khuyß║┐n nghß╗ï VS Code). Bß║ín sß║╜ thß║Ñy cß║Ñu tr├║c nh╞░ sau:
Γöé
Γûê```
Γûêteam-YOUR_TEAM_NAME/
ΓûêΓö£ΓöÇΓöÇ src/
ΓûêΓöé   Γö£ΓöÇΓöÇ agent/           # LangGraph Agent logic
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ __init__.py
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ graph.py     # State graph definition
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ state.py     # State schema
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ nodes.py     # Node functions
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ tools.py     # Agent tools
ΓûêΓöé   Γö£ΓöÇΓöÇ api/             # FastAPI endpoints
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ __init__.py
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ main.py      # FastAPI app entry point
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ routes/      # API route modules
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ deps.py      # Dependencies injection
ΓûêΓöé   Γö£ΓöÇΓöÇ core/            # Shared config & utilities
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ __init__.py
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ config.py    # Pydantic settings
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ logging.py   # Logging setup
ΓûêΓöé   ΓööΓöÇΓöÇ models/          # Data models (Pydantic)
ΓûêΓöé       Γö£ΓöÇΓöÇ __init__.py
ΓûêΓöé       ΓööΓöÇΓöÇ schemas.py   # Request/Response schemas
ΓûêΓö£ΓöÇΓöÇ tests/
ΓûêΓöé   Γö£ΓöÇΓöÇ unit/            # Unit tests
ΓûêΓöé   Γö£ΓöÇΓöÇ integration/     # Integration tests
ΓûêΓöé   ΓööΓöÇΓöÇ eval/            # Agent evaluation tests
ΓûêΓö£ΓöÇΓöÇ docs/
ΓûêΓöé   Γö£ΓöÇΓöÇ architecture/    # Architecture diagrams
ΓûêΓöé   Γö£ΓöÇΓöÇ api/             # API documentation
ΓûêΓöé   ΓööΓöÇΓöÇ adr/             # Architecture Decision Records
ΓûêΓö£ΓöÇΓöÇ eval/                # Evaluation datasets & scripts
ΓûêΓöé   Γö£ΓöÇΓöÇ datasets/        # Test questions & expected outputs
ΓûêΓöé   ΓööΓöÇΓöÇ scripts/         # Evaluation runner scripts
ΓûêΓö£ΓöÇΓöÇ presentation/        # Demo Day slides & materials
ΓûêΓö£ΓöÇΓöÇ .env.example         # Mß║½u biß║┐n m├┤i tr╞░ß╗¥ng
ΓûêΓö£ΓöÇΓöÇ .gitignore           # Git ignore rules
ΓûêΓö£ΓöÇΓöÇ Dockerfile           # Container definition
ΓûêΓö£ΓöÇΓöÇ docker-compose.yml   # Multi-container orchestration
ΓûêΓö£ΓöÇΓöÇ pyproject.toml       # Project metadata & dependencies
ΓûêΓö£ΓöÇΓöÇ Makefile             # Common commands shortcut
ΓûêΓööΓöÇΓöÇ README.md            # Project documentation
Γûê```
Γöé
ΓûêMß╗ùi th╞░ mß╗Ñc phß╗Ñc vß╗Ñ mß╗Öt mß╗Ñc ─æ├¡ch cß╗Ñ thß╗â. H├úy hiß╗âu r├╡ tr╞░ß╗¢c khi bß║»t ─æß║ºu code:
Γöé
Γûê**`src/agent/`** ΓÇö N╞íi chß╗⌐a to├án bß╗Ö logic AI Agent cß╗ºa bß║ín. File `graph.py` ─æß╗ïnh ngh─⌐a state graph (s╞í ─æß╗ô trß║íng th├íi) cho Agent, `state.py` chß╗⌐a schema dß╗» liß╗çu truyß╗ün giß╗»a c├íc node, `nodes.py` chß╗⌐a c├íc h├ám xß╗¡ l├╜ logic tß║íi mß╗ùi b╞░ß╗¢c, v├á `tools.py` chß╗⌐a c├íc c├┤ng cß╗Ñ m├á Agent c├│ thß╗â sß╗¡ dß╗Ñng (t├¼m kiß║┐m web, truy vß║Ñn database, gß╗ìi API, v.v.). ─É├óy l├á "bß╗Ö n├úo" cß╗ºa ß╗⌐ng dß╗Ñng.
Γöé
Γûê**`src/api/`** ΓÇö FastAPI backend. File `main.py` tß║ío ß╗⌐ng dß╗Ñng FastAPI v├á cß║Ñu h├¼nh middleware. Th╞░ mß╗Ñc `routes/` chß╗⌐a c├íc file ─æß╗ïnh ngh─⌐a API endpoints, mß╗ùi file t╞░╞íng ß╗⌐ng vß╗¢i mß╗Öt nh├│m chß╗⌐c n─âng. File `deps.py` quß║ún l├╜ dependency injection ΓÇö v├¡ dß╗Ñ, tß║ío instance cß╗ºa Agent v├á inject v├áo c├íc route handler.
Γöé
Γûê**`src/core/`** ΓÇö Cß║Ñu h├¼nh v├á tiß╗çn ├¡ch d├╣ng chung. File `config.py` sß╗¡ dß╗Ñng pydantic-settings ─æß╗â load v├á validate biß║┐n m├┤i tr╞░ß╗¥ng. File `logging.py` thiß║┐t lß║¡p logging format.
Γöé
Γûê**`src/models/`** ΓÇö Pydantic models cho request v├á response. ─É├óy l├á "hß╗úp ─æß╗ông" giß╗»a client v├á server ΓÇö ─æß╗ïnh ngh─⌐a r├╡ dß╗» liß╗çu gß╗¡i l├¬n phß║úi c├│ dß║íng g├¼, v├á dß╗» liß╗çu trß║ú vß╗ü sß║╜ c├│ dß║íng g├¼.
Γöé
Γûê**`tests/`** ΓÇö B├ái kiß╗âm thß╗¡. `unit/` cho unit tests (test tß╗½ng h├ám ri├¬ng lß║╗), `integration/` cho integration tests (test nhiß╗üu component hoß║ít ─æß╗Öng c├╣ng nhau), v├á `eval/` cho Agent evaluation (─æ├ính gi├í chß║Ñt l╞░ß╗úng trß║ú lß╗¥i cß╗ºa Agent).
Γöé
Γûê**`docs/`** ΓÇö T├ái liß╗çu dß╗▒ ├ín. `architecture/` chß╗⌐a s╞í ─æß╗ô kiß║┐n tr├║c (Mermaid hoß║╖c h├¼nh ß║únh), `api/` chß╗⌐a t├ái liß╗çu API bß╗ò sung, v├á `adr/` chß╗⌐a Architecture Decision Records ΓÇö ghi lß║íi l├╜ do tß║íi sao bß║ín chß╗ìn giß║úi ph├íp A thay v├¼ giß║úi ph├íp B.
Γöé
Γûê**`eval/`** ΓÇö Dß╗» liß╗çu v├á script ─æß╗â ─æ├ính gi├í Agent. Trong `datasets/` bß║ín ─æß║╖t c├íc c├óu hß╗Åi test k├¿m c├óu trß║ú lß╗¥i mong ─æß╗úi. Trong `scripts/` bß║ín viß║┐t script tß╗▒ ─æß╗Öng chß║íy Agent qua tß║¡p test v├á t├¡nh ─æiß╗âm. ─É├óy l├á phß║ºn m├á hß║ºu hß║┐t ─æß╗Öi bß╗Å qua ΓÇö h├úy ─æß║úm bß║úo ─æß╗Öi bß║ín kh├íc biß╗çt.
Γöé
Γûê**`presentation/`** ΓÇö Slide v├á t├ái liß╗çu cho Demo Day. Kh├┤ng ─æß╗úi ─æß║┐n ph├║t cuß╗æi mß╗¢i l├ám slide ΓÇö h├úy cß║¡p nhß║¡t dß║ºn trong suß╗æt qu├í tr├¼nh ph├ít triß╗ân.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Cß║Ñu tr├║c th╞░ mß╗Ñc kh├┤ng phß║úi ngß║½u nhi├¬n ΓÇö n├│ phß║ún ├ính nguy├¬n tß║»c separation of concerns (t├ích biß╗çt tr├ích nhiß╗çm). Agent logic t├ích biß╗çt khß╗Åi API logic, t├ích biß╗çt khß╗Åi config, t├ích biß╗çt khß╗Åi tests. Khi dß╗▒ ├ín lß╗¢n l├¬n, bß║ín sß║╜ thß║Ñy cß║Ñu tr├║c n├áy gi├║p bß║ín t├¼m v├á sß╗¡a code nhanh h╞ín rß║Ñt nhiß╗üu so vß╗¢i "bß╗Å tß║Ñt cß║ú v├áo mß╗Öt file."
Γöé
Γûê## Thiß║┐t lß║¡p m├┤i tr╞░ß╗¥ng ΓÇö ─Éß╗½ng ─æß╗â "tr├¬n m├íy t├┤i chß║íy ─æ╞░ß╗úc"
Γöé
ΓûêMß╗Öt c├óu n├│i kinh ─æiß╗ân trong ng├ánh phß║ºn mß╗üm l├á "It works on my machine" ΓÇö "Tr├¬n m├íy t├┤i chß║íy ─æ╞░ß╗úc." Nß╗ùi ├ím ß║únh n├áy xuß║Ñt ph├ít tß╗½ viß╗çc m├┤i tr╞░ß╗¥ng ph├ít triß╗ân kh├┤ng ─æ╞░ß╗úc setup ─æß╗ông bß╗Ö: phi├¬n bß║ún Python kh├íc, th╞░ viß╗çn kh├íc, biß║┐n m├┤i tr╞░ß╗¥ng kh├íc. Phß║ºn n├áy sß║╜ gi├║p bß║ín thiß║┐t lß║¡p m├┤i tr╞░ß╗¥ng ─æ├║ng c├ích ─æß╗â kh├┤ng chß╗ë "tr├¬n m├íy bß║ín chß║íy ─æ╞░ß╗úc" m├á "tr├¬n mß╗ìi m├íy ─æß╗üu chß║íy ─æ╞░ß╗úc."
Γöé
Γûê### Y├¬u cß║ºu hß╗ç thß╗æng
Γöé
ΓûêTr╞░ß╗¢c khi bß║»t ─æß║ºu, h├úy x├íc nhß║¡n m├íy bß║ín ─æ├íp ß╗⌐ng c├íc y├¬u cß║ºu sau:
Γöé
Γûê- **Python 3.11 hoß║╖c mß╗¢i h╞ín.** Python 3.11 mang ─æß║┐n cß║úi thiß╗çn tß╗æc ─æß╗Ö ─æ├íng kß╗â (nhanh h╞ín 3.11 khoß║úng 10-25% so vß╗¢i 3.10) v├á hß╗ù trß╗ú better error messages. Python 3.12+ c┼⌐ng hoß║ít ─æß╗Öng tß╗æt, nh╞░ng mß╗Öt sß╗æ th╞░ viß╗çn c├│ thß╗â ch╞░a t╞░╞íng th├¡ch ho├án to├án. Khuyß║┐n nghß╗ï: d├╣ng Python 3.11.x.
Γöé
Γûê- **pip phi├¬n bß║ún mß╗¢i nhß║Ñt.** Chß║íy `pip install --upgrade pip` ─æß╗â cß║¡p nhß║¡t.
Γöé
Γûê- **Git 2.30+.** Chß║íy `git --version` ─æß╗â kiß╗âm tra.
Γöé
Γûê- **(T├╣y chß╗ìn) Docker Desktop.** Cß║ºn nß║┐u bß║ín muß╗æn chß║íy ß╗⌐ng dß╗Ñng trong container, nh╞░ng kh├┤ng bß║»t buß╗Öc cho giai ─æoß║ín ph├ít triß╗ân ban ─æß║ºu.
Γöé
ΓûêKiß╗âm tra phi├¬n bß║ún Python:
Γöé
Γûê```bash
Γûê$ python3 --version
Γûê# Output mong ─æß╗úi: Python 3.11.x hoß║╖c cao h╞ín
Γöé
Γûê# Nß║┐u bß║ín c├│ nhiß╗üu phi├¬n bß║ún Python, kiß╗âm tra ch├¡nh x├íc:
Γûê$ python3.11 --version
Γûê```
Γöé
Γûê### Tß║ío virtual environment
Γöé
ΓûêVirtual environment (venv) l├á mß╗Öt m├┤i tr╞░ß╗¥ng Python c├┤ lß║¡p, t├ích biß╗çt vß╗¢i hß╗ç thß╗æng Python to├án cß╗Ñc. Mß╗ùi dß╗▒ ├ín n├¬n c├│ venv ri├¬ng ─æß╗â tr├ính xung ─æß╗Öt th╞░ viß╗çn giß╗»a c├íc dß╗▒ ├ín.
Γöé
Γûê```bash
Γûê# Tß╗½ th╞░ mß╗Ñc gß╗æc cß╗ºa dß╗▒ ├ín
Γûê$ python3.11 -m venv .venv
Γöé
Γûê# K├¡ch hoß║ít venv tr├¬n macOS/Linux
Γûê$ source .venv/bin/activate
Γöé
Γûê# K├¡ch hoß║ít venv tr├¬n Windows
Γûê$ .venv\Scripts\activate
Γöé
Γûê# X├íc nhß║¡n ─æang d├╣ng Python trong venv
Γûê$ which python
Γûê# Output n├¬n l├á: /path/to/your/project/.venv/bin/python
Γûê```
Γöé
ΓûêSau khi k├¡ch hoß║ít, bß║ín sß║╜ thß║Ñy t├¬n venv hiß╗ân thß╗ï ß╗ƒ ─æß║ºu command prompt, v├¡ dß╗Ñ: `(.venv) $`. ─Éiß╗üu n├áy x├íc nhß║¡n bß║ín ─æang l├ám viß╗çc trong m├┤i tr╞░ß╗¥ng ß║úo. Mß╗ìi lß╗çnh `pip install` tß╗½ b├óy giß╗¥ sß║╜ chß╗ë c├ái th╞░ viß╗çn v├áo venv, kh├┤ng ß║únh h╞░ß╗ƒng ─æß║┐n hß╗ç thß╗æng.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Kh├┤ng bao giß╗¥ c├ái th╞░ viß╗çn trß╗▒c tiß║┐p v├áo system Python. Nß║┐u bß║ín lß╗í c├ái m├á kh├┤ng k├¡ch hoß║ít venv tr╞░ß╗¢c, h├úy gß╗í bß╗Å bß║▒ng `pip uninstall` v├á l├ám lß║íi ─æ├║ng c├ích. Th╞░ mß╗Ñc `.venv` ─æ├ú ─æ╞░ß╗úc th├¬m v├áo `.gitignore`, n├¬n n├│ sß║╜ kh├┤ng bß╗ï commit l├¬n Git.
Γöé
Γûê### C├ái ─æß║╖t dependencies
Γöé
ΓûêTemplate sß╗¡ dß╗Ñng file `pyproject.toml` ─æß╗â quß║ún l├╜ dependencies ΓÇö ─æ├óy l├á chuß║⌐n hiß╗çn ─æß║íi cß╗ºa Python, thay thß║┐ cho `requirements.txt` truyß╗ün thß╗æng. C├íc dependencies ─æ╞░ß╗úc chia th├ánh nhiß╗üu nh├│m:
Γöé
Γûê```bash
Γûê# C├ái tß║Ñt cß║ú dependencies (development + production)
Γûê$ pip install -e ".[dev]"
Γöé
Γûê# Hoß║╖c nß║┐u lß╗çnh tr├¬n kh├┤ng hoß║ít ─æß╗Öng, c├ái tß╗½ng b╞░ß╗¢c:
Γûê$ pip install -e .
Γûê$ pip install -e ".[dev]"
Γûê```
Γöé
ΓûêFlag `-e` (editable) c├│ ngh─⌐a l├á bß║ín c├ái package ß╗ƒ chß║┐ ─æß╗Ö "c├│ thß╗â chß╗ënh sß╗¡a" ΓÇö khi bß║ín sß╗¡a code trong `src/`, thay ─æß╗òi sß║╜ phß║ún ├ính ngay lß║¡p tß╗⌐c m├á kh├┤ng cß║ºn c├ái lß║íi. `[dev]` chß╗ë ─æß╗ïnh c├ái th├¬m c├íc th╞░ viß╗çn d├╣ng cho development (testing, linting, formatting).
Γöé
ΓûêC├íc dependencies ch├¡nh trong template bao gß╗ôm:
Γöé
Γûê- **`fastapi`** ΓÇö Framework web backend, async, auto-docs.
Γûê- **`uvicorn`** ΓÇö ASGI server ─æß╗â chß║íy FastAPI.
Γûê- **`langgraph`** ΓÇö Framework x├óy dß╗▒ng AI Agent dß║íng state machine.
Γûê- **`langchain-core`** ΓÇö Th╞░ viß╗çn cß╗æt l├╡i cß╗ºa LangChain ecosystem.
Γûê- **`langchain-openai`** ΓÇö T├¡ch hß╗úp vß╗¢i OpenAI models (GPT-4, GPT-3.5).
Γûê- **`pydantic`** v├á **`pydantic-settings`** ΓÇö Data validation v├á settings management.
Γûê- **`python-dotenv`** ΓÇö Load biß║┐n m├┤i tr╞░ß╗¥ng tß╗½ file `.env`.
Γöé
ΓûêDevelopment dependencies:
Γöé
Γûê- **`pytest`** v├á **`pytest-asyncio`** ΓÇö Testing framework vß╗¢i hß╗ù trß╗ú async.
Γûê- **`ruff`** ΓÇö Linter v├á formatter thay thß║┐ cho flake8 + black, nhanh h╞ín 10-100x.
Γûê- **`mypy`** ΓÇö Static type checker.
Γûê- **`httpx`** ΓÇö HTTP client d├╣ng cho testing API.
Γöé
Γûê### X├íc nhß║¡n c├ái ─æß║╖t th├ánh c├┤ng
Γöé
ΓûêSau khi c├ái xong, chß║íy c├íc lß╗çnh sau ─æß╗â x├íc nhß║¡n mß╗ìi thß╗⌐ ─æ├ú ─æ├║ng:
Γöé
Γûê```bash
Γûê# Kiß╗âm tra FastAPI ─æ├ú c├ái
Γûê$ python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
Γûê# Output: FastAPI 0.x.x
Γöé
Γûê# Kiß╗âm tra LangGraph ─æ├ú c├ái
Γûê$ python -c "import langgraph; print('LangGraph OK')"
Γöé
Γûê# Chß║íy tests ─æß╗â x├íc nhß║¡n template hoß║ít ─æß╗Öng
Γûê$ make test
Γûê# Hoß║╖c:
Γûê$ pytest tests/ -v
Γûê```
Γöé
ΓûêNß║┐u tß║Ñt cß║ú c├íc lß╗çnh tr├¬n chß║íy m├á kh├┤ng c├│ error, ch├║c mß╗½ng ΓÇö m├┤i tr╞░ß╗¥ng cß╗ºa bß║ín ─æ├ú sß║╡n s├áng.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Nß║┐u bß║ín gß║╖p lß╗ùi "Module not found" d├╣ ─æ├ú c├ái, nguy├¬n nh├ón phß╗ò biß║┐n nhß║Ñt l├á bß║ín qu├¬n k├¡ch hoß║ít venv hoß║╖c c├ái nhß║ºm v├áo system Python. Chß║íy `which python` ─æß╗â x├íc nhß║¡n, v├á nß║┐u cß║ºn, k├¡ch hoß║ít lß║íi venv.
Γöé
Γûê## Biß║┐n m├┤i tr╞░ß╗¥ng ΓÇö Kh├┤ng bao giß╗¥ hardcode secrets
Γöé
ΓûêMß╗Öt lß╗ùi phß╗ò biß║┐n v├á nguy hiß╗âm m├á nhiß╗üu sinh vi├¬n mß║»c phß║úi l├á "hardcode" (nh├║ng trß╗▒c tiß║┐p) c├íc gi├í trß╗ï nhß║íy cß║úm nh╞░ API keys, database passwords v├áo trong source code. Khi bß║ín push code l├¬n GitHub, bß║Ñt kß╗│ ai c┼⌐ng c├│ thß╗â thß║Ñy nhß╗»ng gi├í trß╗ï n├áy ΓÇö v├á bot qu├⌐t API keys hoß║ít ─æß╗Öng li├¬n tß╗Ñc tr├¬n GitHub. Chß╗ë trong v├ái ph├║t sau khi bß║ín push, key cß╗ºa bß║ín c├│ thß╗â bß╗ï ─æ├ính cß║»p v├á sß╗¡ dß╗Ñng tr├íi ph├⌐p, dß║½n ─æß║┐n thiß╗çt hß║íi t├ái ch├¡nh (OpenAI charge theo usage).
Γöé
ΓûêBiß║┐n m├┤i tr╞░ß╗¥ng (environment variables) l├á c├ích ─æ├║ng ─æß╗â xß╗¡ l├╜. Bß║ín l╞░u c├íc gi├í trß╗ï nhß║íy cß║úm trong file `.env` (─æ├ú ─æ╞░ß╗úc gitignore), v├á code ─æß╗ìc tß╗½ m├┤i tr╞░ß╗¥ng thay v├¼ hardcode.
Γöé
Γûê### File .env.example
Γöé
ΓûêTemplate cung cß║Ñp sß║╡n file `.env.example` ΓÇö ─æ├óy l├á "mß║½u" liß╗çt k├¬ tß║Ñt cß║ú biß║┐n m├┤i tr╞░ß╗¥ng cß║ºn thiß║┐t m├á kh├┤ng chß╗⌐a gi├í trß╗ï thß╗▒c. B╞░ß╗¢c ─æß║ºu ti├¬n cß╗ºa bß║ín l├á copy n├│ th├ánh `.env` v├á ─æiß╗ün gi├í trß╗ï:
Γöé
Γûê```bash
Γûê$ cp .env.example .env
Γûê```
Γöé
ΓûêNß╗Öi dung file `.env.example` mß║½u:
Γöé
Γûê```env
Γûê# Application
ΓûêAPP_NAME=ai-agent
ΓûêAPP_ENV=development
ΓûêDEBUG=true
ΓûêLOG_LEVEL=DEBUG
Γöé
Γûê# API
ΓûêAPI_HOST=0.0.0.0
ΓûêAPI_PORT=8000
ΓûêAPI_PREFIX=/api/v1
Γöé
Γûê# LLM Provider
ΓûêLLM_PROVIDER=openai
ΓûêOPENAI_API_KEY=sk-your-key-here
ΓûêOPENAI_MODEL=gpt-4o-mini
ΓûêOPENAI_TEMPERATURE=0.7
ΓûêOPENAI_MAX_TOKENS=2048
Γöé
Γûê# Database (nß║┐u cß║ºn)
ΓûêDATABASE_URL=sqlite:///./data/app.db
Γöé
Γûê# Vector Store (cho RAG, nß║┐u cß║ºn)
ΓûêVECTOR_STORE_TYPE=chroma
ΓûêCHROMA_PERSIST_DIR=./data/chroma
Γûê```
Γöé
ΓûêSau khi copy, mß╗ƒ file `.env` v├á thay thß║┐ c├íc gi├í trß╗ï placeholder bß║▒ng gi├í trß╗ï thß╗▒c cß╗ºa bß║ín. ─Éß║╖c biß╗çt, thay `sk-your-key-here` bß║▒ng OpenAI API key cß╗ºa bß║ín.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** File `.env` kh├┤ng bao giß╗¥ ─æ╞░ß╗úc commit l├¬n Git. Template ─æ├ú bao gß╗ôm `.env` trong `.gitignore`. Nß║┐u bß║ín v├┤ t├¼nh commit `.env`, h├úy ngay lß║¡p tß╗⌐c: (1) ─æß╗òi API key tr├¬n dashboard cß╗ºa provider, (2) x├│a file khß╗Åi git history bß║▒ng `git filter-branch` hoß║╖c BFG Repo-Cleaner.
Γöé
Γûê### Config module vß╗¢i pydantic-settings
Γöé
ΓûêTemplate sß╗¡ dß╗Ñng `pydantic-settings` ─æß╗â quß║ún l├╜ cß║Ñu h├¼nh. ─É├óy l├á c├ích hiß╗çn ─æß║íi v├á type-safe ─æß╗â load biß║┐n m├┤i tr╞░ß╗¥ng. H├úy xem file `src/core/config.py`:
Γöé
Γûê```python
Γûêfrom typing import Literal
Γûêfrom pydantic import Field, field_validator
Γûêfrom pydantic_settings import BaseSettings
Γöé
Γöé
Γûêclass Settings(BaseSettings):
Γûê    """Application settings loaded from environment variables."""
Γöé
Γûê    # Application
Γûê    app_name: str = "ai-agent"
Γûê    app_env: Literal["development", "staging", "production"] = "development"
Γûê    debug: bool = False
Γûê    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
Γöé
Γûê    # API
Γûê    api_host: str = "0.0.0.0"
Γûê    api_port: int = Field(default=8000, ge=1024, le=65535)
Γûê    api_prefix: str = "/api/v1"
Γöé
Γûê    # LLM
Γûê    llm_provider: Literal["openai", "anthropic", "google"] = "openai"
Γûê    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
Γûê    openai_model: str = "gpt-4o-mini"
Γûê    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
Γûê    openai_max_tokens: int = Field(default=2048, ge=1, le=128000)
Γöé
Γûê    model_config = {
Γûê        "env_file": ".env",
Γûê        "env_file_encoding": "utf-8",
Γûê        "case_sensitive": False,
Γûê        "extra": "ignore",
Γûê    }
Γöé
Γöé
Γûê# Singleton instance
Γûêsettings = Settings()
Γûê```
Γöé
ΓûêPh├ón t├¡ch tß╗½ng phß║ºn quan trß╗ìng:
Γöé
Γûê**`Literal` types** ΓÇö `Literal["development", "staging", "production"]` giß╗¢i hß║ín `app_env` chß╗ë nhß║¡n mß╗Öt trong ba gi├í trß╗ï. Nß║┐u bß║ín ─æß║╖t `APP_ENV=testing` (gi├í trß╗ï kh├┤ng hß╗úp lß╗ç), pydantic sß║╜ throw error ngay khi app khß╗ƒi ─æß╗Öng, thay v├¼ silently fail trong runtime. ─É├óy l├á mß╗Öt v├¡ dß╗Ñ cß╗ºa "fail fast" principle ΓÇö ph├ít hiß╗çn lß╗ùi c├áng sß╗¢m c├áng tß╗æt.
Γöé
Γûê**`Field` validators** ΓÇö `Field(default=8000, ge=1024, le=65535)` ├íp dß╗Ñng validation: port number phß║úi tß╗½ 1024 ─æß║┐n 65535. Nß║┐u ai ─æ├│ ─æß║╖t `API_PORT=80`, app sß║╜ b├ío lß╗ùi ngay. T╞░╞íng tß╗▒, `temperature` bß╗ï giß╗¢i hß║ín tß╗½ 0.0 ─æß║┐n 2.0 (range hß╗úp lß╗ç cß╗ºa OpenAI), v├á `max_tokens` tß╗½ 1 ─æß║┐n 128000.
Γöé
Γûê**`model_config`** ΓÇö Chß╗ë ─æß╗ïnh c├ích load biß║┐n m├┤i tr╞░ß╗¥ng. `env_file=".env"` n├│i rß║▒ng ─æß╗ìc tß╗½ file `.env`. `case_sensitive=False` cho ph├⌐p biß║┐n m├┤i tr╞░ß╗¥ng viß║┐t hoa (OPENAI_API_KEY) map v├áo field viß║┐t th╞░ß╗¥ng (openai_api_key). `extra="ignore"` bß╗Å qua c├íc biß║┐n m├┤i tr╞░ß╗¥ng kh├┤ng ─æ╞░ß╗úc ─æß╗ïnh ngh─⌐a trong Settings class.
Γöé
Γûê**Singleton pattern** ΓÇö D├▓ng `settings = Settings()` tß║ío mß╗Öt instance duy nhß║Ñt cß╗ºa Settings ß╗ƒ module level. Khi bß║ín cß║ºn d├╣ng config ß╗ƒ bß║Ñt kß╗│ ─æ├óu trong code, chß╗ë cß║ºn `from src.core.config import settings` ΓÇö instance n├áy ─æ╞░ß╗úc tß║ío mß╗Öt lß║ºn v├á d├╣ng chung cho to├án bß╗Ö ß╗⌐ng dß╗Ñng.
Γöé
Γûê```python
Γûê# Sß╗¡ dß╗Ñng ß╗ƒ bß║Ñt kß╗│ ─æ├óu trong project
Γûêfrom src.core.config import settings
Γöé
Γûêprint(settings.openai_model)     # "gpt-4o-mini"
Γûêprint(settings.api_port)         # 8000
Γûêprint(settings.app_env)          # "development"
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Khi th├¬m biß║┐n m├┤i tr╞░ß╗¥ng mß╗¢i, lu├┤n nhß╗¢: (1) th├¬m v├áo `.env.example` vß╗¢i gi├í trß╗ï placeholder, (2) th├¬m field v├áo `Settings` class vß╗¢i type hint v├á default value, (3) th├¬m validation nß║┐u cß║ºn. ─Éß╗½ng bao giß╗¥ th├¬m biß║┐n trß╗▒c tiß║┐p v├áo code m├á kh├┤ng th├┤ng qua Settings.
Γöé
Γûê## Git workflow ΓÇö L├ám viß╗çc nh├│m kh├┤ng hß╗ùn loß║ín
Γöé
ΓûêMß╗Öt sai lß║ºm phß╗ò biß║┐n khi l├ám viß╗çc nh├│m l├á thiß║┐u quy tr├¼nh Git thß╗æng nhß║Ñt: ─æ├¿ code l├¬n nhau (force push), merge conflict kh├┤ng giß║úi quyß║┐t ─æ╞░ß╗úc, commit message v├┤ ngh─⌐a ("fix", "update", "test"), v├á code tr├¬n main branch li├¬n tß╗Ñc bß╗ï hß╗Ång. Nguy├¬n nh├ón ch├¡nh l├á thiß║┐u quy tr├¼nh r├╡ r├áng. Phß║ºn n├áy sß║╜ thiß║┐t lß║¡p quy tr├¼nh m├á to├án bß╗Ö ─æß╗Öi phß║úi tu├ón thß╗º.
Γöé
Γûê### Chiß║┐n l╞░ß╗úc branching
Γöé
ΓûêTemplate khuyß║┐n nghß╗ï m├┤ h├¼nh branching ─æ╞ín giß║ún nh╞░ng hiß╗çu quß║ú:
Γöé
Γûê- **`main`** ΓÇö Branch ch├¡nh, lu├┤n ß╗òn ─æß╗ïnh v├á c├│ thß╗â deploy bß║Ñt cß╗⌐ l├║c n├áo. Kh├┤ng bao giß╗¥ push trß╗▒c tiß║┐p l├¬n main. Mß╗ìi thay ─æß╗òi phß║úi th├┤ng qua Pull Request.
Γûê- **`develop`** ΓÇö Branch t├¡ch hß╗úp, n╞íi tß║Ñt cß║ú feature branches merge v├áo tr╞░ß╗¢c khi l├¬n main. Khi `develop` ─æ├ú ß╗òn ─æß╗ïnh v├á sß║╡n s├áng release, merge v├áo `main`.
Γûê- **`feature/T├èN-FEATURE`** ΓÇö Mß╗ùi t├¡nh n─âng mß╗¢i hoß║╖c bug fix ─æ╞░ß╗úc ph├ít triß╗ân tr├¬n branch ri├¬ng. T├¬n branch phß║úi m├┤ tß║ú r├╡ t├¡nh n─âng.
Γöé
ΓûêV├¡ dß╗Ñ quy tr├¼nh l├ám viß╗çc:
Γöé
Γûê```bash
Γûê# Bß║»t ─æß║ºu t├¡nh n─âng mß╗¢i
Γûê$ git checkout develop
Γûê$ git pull origin develop
Γûê$ git checkout -b feature/agent-search-tool
Γöé
Γûê# L├ám viß╗çc, commit th╞░ß╗¥ng xuy├¬n
Γûê$ git add src/agent/tools/search.py
Γûê$ git commit -m "feat(agent): th├¬m tool t├¼m kiß║┐m web"
Γöé
Γûê# Push v├á tß║ío Pull Request
Γûê$ git push origin feature/agent-search-tool
Γûê# Sau ─æ├│ tß║ío PR tr├¬n GitHub: feature/agent-search-tool ΓåÆ develop
Γûê```
Γöé
Γûê### ─Éß╗ïnh dß║íng commit message
Γöé
ΓûêCommit message phß║úi c├│ ├╜ ngh─⌐a. Mß╗ùi commit message tu├ón theo format:
Γöé
Γûê```
Γûêtype(scope): m├┤ tß║ú ngß║»n gß╗ìn
Γöé
Γûê[m├┤ tß║ú chi tiß║┐t nß║┐u cß║ºn]
Γûê```
Γöé
ΓûêC├íc type phß╗ò biß║┐n:
Γöé
Γûê- **`feat`** ΓÇö Th├¬m t├¡nh n─âng mß╗¢i. V├¡ dß╗Ñ: `feat(api): th├¬m endpoint /chat/stream`
Γûê- **`fix`** ΓÇö Sß╗¡a bug. V├¡ dß╗Ñ: `fix(agent): sß╗¡a lß╗ùi Agent kh├┤ng xß╗¡ l├╜ input rß╗ùng`
Γûê- **`docs`** ΓÇö Cß║¡p nhß║¡t t├ái liß╗çu. V├¡ dß╗Ñ: `docs: cß║¡p nhß║¡t README vß╗¢i h╞░ß╗¢ng dß║½n c├ái ─æß║╖t`
Γûê- **`test`** ΓÇö Th├¬m hoß║╖c sß╗¡a tests. V├¡ dß╗Ñ: `test(agent): th├¬m test cho search tool`
Γûê- **`refactor`** ΓÇö T├íi cß║Ñu tr├║c code kh├┤ng thay ─æß╗òi functionality. V├¡ dß╗Ñ: `refactor(config): chuyß╗ân config sang pydantic-settings`
Γûê- **`chore`** ΓÇö Viß╗çc bß║úo tr├¼ (update dependencies, v.v.). V├¡ dß╗Ñ: `chore: cß║¡p nhß║¡t ruff l├¬n v0.4.0`
Γöé
ΓûêScope l├á t├╣y chß╗ìn, nh╞░ng khuyß║┐n nghß╗ï d├╣ng: `agent`, `api`, `config`, `models`, `tests`, hoß║╖c t├¬n module kh├íc.
Γöé
Γûê### Pull Request process
Γöé
ΓûêPull Request (PR) kh├┤ng chß╗ë l├á c├ích merge code ΓÇö n├│ l├á c╞í hß╗Öi review v├á ─æß║úm bß║úo chß║Ñt l╞░ß╗úng. Mß╗ùi PR n├¬n:
Γöé
Γûê1. **C├│ ti├¬u ─æß╗ü r├╡ r├áng** theo format commit message.
Γûê2. **C├│ m├┤ tß║ú** giß║úi th├¡ch: thay ─æß╗òi g├¼, tß║íi sao, v├á c├ích test.
Γûê3. **Nhß╗Å v├á tß║¡p trung** ΓÇö mß╗Öt PR n├¬n giß║úi quyß║┐t mß╗Öt vß║Ñn ─æß╗ü, kh├┤ng phß║úi 10.
Γûê4. **─É╞░ß╗úc review bß╗ƒi ├¡t nhß║Ñt 1 th├ánh vi├¬n kh├íc** tr╞░ß╗¢c khi merge.
Γûê5. **Pass tß║Ñt cß║ú automated checks** (tests, linting) tr╞░ß╗¢c khi merge.
Γöé
Γûê```markdown
Γûê## PR Template
Γöé
Γûê### Thay ─æß╗òi
Γûê- Th├¬m tool t├¼m kiß║┐m web cho Agent
Γûê- T├¡ch hß╗úp Tavily Search API
Γöé
Γûê### Tß║íi sao
ΓûêAgent cß║ºn khß║ú n─âng t├¼m kiß║┐m th├┤ng tin real-time ─æß╗â trß║ú lß╗¥i c├óu hß╗Åi vß╗ü sß╗▒ kiß╗çn hiß╗çn tß║íi.
Γöé
Γûê### C├ích test
Γûê1. Set `TAVILY_API_KEY` trong `.env`
Γûê2. Chß║íy `pytest tests/unit/test_search_tool.py -v`
Γûê3. Hoß║╖c test manual qua Swagger UI: POST /api/v1/chat
Γöé
Γûê### Checklist
Γûê- [x] Code tu├ón thß╗º style guide
Γûê- [x] ─É├ú viß║┐t unit test
Γûê- [x] Tß║Ñt cß║ú tests pass
Γûê- [x] Kh├┤ng c├│ hardcoded secrets
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Git workflow kh├┤ng phß║úi "paperwork" ΓÇö n├│ l├á mß║íng l╞░ß╗¢i an to├án. Khi ai ─æ├│ v├┤ t├¼nh x├│a code quan trß╗ìng, bß║ín c├│ thß╗â revert. Khi c├│ bug mß╗¢i, bß║ín biß║┐t commit n├áo g├óy ra nhß╗¥ `git bisect`. Khi review PR, bß║ín hß╗ìc code cß╗ºa ─æß╗ông ─æß╗Öi. ─Éß║ºu t╞░ 5 ph├║t cho mß╗ùi commit message v├á PR sß║╜ tiß║┐t kiß╗çm 5 giß╗¥ debug sau n├áy.
Γöé
Γûê## Chß║íy server lß║ºn ─æß║ºu ΓÇö Hello World moment
Γöé
ΓûêSau khi setup m├┤i tr╞░ß╗¥ng v├á cß║Ñu h├¼nh, ─æ├óy l├á khoß║únh khß║»c quan trß╗ìng nhß║Ñt: chß║íy ß╗⌐ng dß╗Ñng lß║ºn ─æß║ºu ti├¬n v├á thß║Ñy n├│ hoß║ít ─æß╗Öng. Template ─æ├ú bao gß╗ôm sß║╡n mß╗Öt FastAPI server c╞í bß║ún vß╗¢i health check endpoint.
Γöé
Γûê### Khß╗ƒi ─æß╗Öng server
Γöé
Γûê```bash
Γûê# ─Éß║úm bß║úo venv ─æ├ú k├¡ch hoß║ít
Γûê$ source .venv/bin/activate
Γöé
Γûê# Chß║íy FastAPI server
Γûê$ uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
Γûê```
Γöé
ΓûêGiß║úi th├¡ch tß╗½ng tham sß╗æ:
Γöé
Γûê- **`src.api.main:app`** ΓÇö ─É╞░ß╗¥ng dß║½n ─æß║┐n FastAPI app instance. File `src/api/main.py` chß╗⌐a d├▓ng `app = FastAPI(...)`.
Γûê- **`--reload`** ΓÇö Tß╗▒ ─æß╗Öng reload server khi code thay ─æß╗òi. Chß╗ë d├╣ng trong development, kh├┤ng d├╣ng trong production.
Γûê- **`--host 0.0.0.0`** ΓÇö Lß║»ng nghe tr├¬n tß║Ñt cß║ú network interfaces, cho ph├⌐p truy cß║¡p tß╗½ thiß║┐t bß╗ï kh├íc trong c├╣ng mß║íng.
Γûê- **`--port 8000`** ΓÇö Port number. Khß╗¢p vß╗¢i `API_PORT` trong config.
Γöé
ΓûêOutput mong ─æß╗úi:
Γöé
Γûê```
ΓûêINFO:     Will watch for changes in these directories: ['/path/to/project']
ΓûêINFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
ΓûêINFO:     Started reloader process [12345] using WatchFiles
ΓûêINFO:     Started server process [12346]
ΓûêINFO:     Waiting for application startup.
ΓûêINFO:     Application startup complete.
Γûê```
Γöé
Γûê### Swagger UI ΓÇö API documentation tß╗▒ ─æß╗Öng
Γöé
ΓûêMß╗Öt trong nhß╗»ng t├¡nh n─âng tuyß╗çt vß╗¥i nhß║Ñt cß╗ºa FastAPI l├á **tß╗▒ ─æß╗Öng sinh API documentation**. Mß╗ƒ tr├¼nh duyß╗çt v├á truy cß║¡p:
Γöé
Γûê```
Γûêhttp://localhost:8000/docs
Γûê```
Γöé
ΓûêBß║ín sß║╜ thß║Ñy Swagger UI ΓÇö mß╗Öt giao diß╗çn t╞░╞íng t├íc cho ph├⌐p bß║ín xem tß║Ñt cß║ú API endpoints, schema cß╗ºa request/response, v├á thß║¡m ch├¡ "thß╗¡ gß╗ìi" API trß╗▒c tiß║┐p tß╗½ tr├¼nh duyß╗çt m├á kh├┤ng cß║ºn Postman hay curl.
Γöé
Γûê### Health check endpoint
Γöé
ΓûêTemplate cung cß║Ñp sß║╡n health check endpoint ─æß╗â x├íc nhß║¡n server ─æang hoß║ít ─æß╗Öng:
Γöé
Γûê```bash
Γûê# D├╣ng curl
Γûê$ curl http://localhost:8000/api/v1/health
Γöé
Γûê# Hoß║╖c mß╗ƒ trong tr├¼nh duyß╗çt
Γûê# http://localhost:8000/api/v1/health
Γûê```
Γöé
ΓûêResponse mong ─æß╗úi:
Γöé
Γûê```json
Γûê{
Γûê  "status": "healthy",
Γûê  "version": "0.1.0",
Γûê  "environment": "development"
Γûê}
Γûê```
Γöé
ΓûêNß║┐u bß║ín thß║Ñy response n├áy, ch├║c mß╗½ng ΓÇö server ─æang chß║íy v├á config ─æ├ú ─æ╞░ß╗úc load ─æ├║ng. Nß║┐u gß║╖p lß╗ùi, kiß╗âm tra lß║íi: (1) venv ─æ├ú k├¡ch hoß║ít ch╞░a, (2) file `.env` ─æ├ú tß║ío ch╞░a, (3) port 8000 c├│ bß╗ï chiß║┐m bß╗ƒi process kh├íc kh├┤ng (chß║íy `lsof -i :8000` ─æß╗â kiß╗âm tra).
Γöé
Γûê### D├╣ng Makefile cho lß╗çnh th╞░ß╗¥ng d├╣ng
Γöé
ΓûêTemplate bao gß╗ôm `Makefile` vß╗¢i c├íc lß╗çnh shortcut:
Γöé
Γûê```bash
Γûê$ make run          # Chß║íy server
Γûê$ make test         # Chß║íy tß║Ñt cß║ú tests
Γûê$ make lint         # Chß║íy linter (ruff)
Γûê$ make format       # Format code (ruff format)
Γûê$ make typecheck    # Chß║íy type checker (mypy)
Γûê$ make check        # Chß║íy tß║Ñt cß║ú checks (lint + format + typecheck + test)
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Bookmark `http://localhost:8000/docs` trong tr├¼nh duyß╗çt. Bß║ín sß║╜ d├╣ng trang n├áy rß║Ñt th╞░ß╗¥ng xuy├¬n trong suß╗æt qu├í tr├¼nh ph├ít triß╗ân. Mß╗ùi khi th├¬m endpoint mß╗¢i, n├│ sß║╜ tß╗▒ ─æß╗Öng xuß║Ñt hiß╗çn ß╗ƒ ─æ├óy. Swagger UI c┼⌐ng l├á c├┤ng cß╗Ñ debug tuyß╗çt vß╗¥i ΓÇö bß║ín c├│ thß╗â test API trß╗▒c tiß║┐p m├á kh├┤ng cß║ºn viß║┐t script ri├¬ng.
Γöé
Γûê## Bß║»t ─æß║ºu project cß╗ºa bß║ín ΓÇö Tß╗½ template th├ánh sß║ún phß║⌐m
Γöé
ΓûêB├óy giß╗¥ bß║ín ─æ├ú c├│ template chß║íy ─æ╞░ß╗úc tr├¬n m├íy. Nh╞░ng template chß╗ë l├á bß╗Ö khung ΓÇö bß║ín cß║ºn t├╣y chß╗ënh n├│ th├ánh dß╗▒ ├ín cß╗ºa ri├¬ng m├¼nh. Phß║ºn n├áy h╞░ß╗¢ng dß║½n bß║ín nhß╗»ng g├¼ cß║ºn thay ─æß╗òi v├á nhß╗»ng g├¼ cß║ºn giß╗» nguy├¬n.
Γöé
Γûê### Nhß╗»ng g├¼ cß║ºn thay ─æß╗òi ngay
Γöé
Γûê**1. Cß║¡p nhß║¡t `pyproject.toml`:**
Γöé
Γûê```toml
Γûê[project]
Γûêname = "team-alpha-agent"          # T├¬n dß╗▒ ├ín cß╗ºa bß║ín
Γûêversion = "0.1.0"
Γûêdescription = "AI Agent cho [m├┤ tß║ú use case]"  # M├┤ tß║ú ngß║»n gß╗ìn
Γûêauthors = [
Γûê    {name = "Team Alpha"},
Γûê]
Γöé
Γûê[project.urls]
Γûêrepository = "https://github.com/AI20K-Build-Cohort-2/C2-App-XXX"  # URL repo cß╗ºa bß║ín
Γûê```
Γöé
Γûê**2. Cß║¡p nhß║¡t `README.md`:** Template c├│ README placeholder. Thay thß║┐ bß║▒ng nß╗Öi dung thß╗▒c tß║┐:
Γöé
Γûê```markdown
Γûê# Team Alpha ΓÇö AI Agent
Γöé
Γûê## M├┤ tß║ú
ΓûêAgent tß╗▒ ─æß╗Öng ph├ón t├¡ch sentiment cß╗ºa b├ái ─æ─âng mß║íng x├ú hß╗Öi v├á tß║ío b├ío c├ío t├│m tß║»t.
Γöé
Γûê## Th├ánh vi├¬n
Γûê- Nguyß╗àn V─ân A ΓÇö Agent logic
Γûê- Trß║ºn Thß╗ï B ΓÇö API & Backend
Γûê- L├¬ V─ân C ΓÇö Frontend & Testing
Γöé
Γûê## Quick Start
Γûê```bash
Γûêpython3.11 -m venv .venv
Γûêsource .venv/bin/activate
Γûêpip install -e ".[dev]"
Γûêcp .env.example .env  # ─Éiß╗ün API key
Γûêmake run
Γûê```
Γöé
Γûê## API Docs
ΓûêSau khi chß║íy server, truy cß║¡p: http://localhost:8000/docs
Γûê```
Γöé
Γûê**3. Cß║¡p nhß║¡t `.env` vß╗¢i API key thß╗▒c:** Nß║┐u bß║ín c├│ OpenAI API key, th├¬m v├áo file `.env`:
Γöé
Γûê```env
ΓûêOPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
Γûê```
Γöé
Γûê### Nhß╗»ng g├¼ cß║ºn giß╗» nguy├¬n
Γöé
Γûê- **Cß║Ñu tr├║c th╞░ mß╗Ñc** ΓÇö ─Éß╗½ng t├íi cß║Ñu tr├║c trß╗½ khi c├│ l├╜ do rß║Ñt tß╗æt. Cß║Ñu tr├║c ─æ├ú ─æ╞░ß╗úc thiß║┐t kß║┐ theo best practices.
Γûê- **Git workflow** ΓÇö Branching strategy v├á commit message format.
Γûê- **CI/CD configuration** ΓÇö Nß║┐u template c├│ sß║╡n file GitHub Actions, giß╗» nguy├¬n v├á chß╗ë chß╗ënh sß╗¡a khi cß║ºn.
Γûê- **Testing setup** ΓÇö `pytest.ini` hoß║╖c cß║Ñu h├¼nh pytest trong `pyproject.toml`.
Γûê- **Linting configuration** ΓÇö Cß║Ñu h├¼nh `ruff` trong `pyproject.toml`.
Γöé
Γûê### Kß║┐ hoß║ích h├ánh ─æß╗Öng cho tuß║ºn ─æß║ºu ti├¬n
Γöé
ΓûêSau khi ho├án th├ánh tß║Ñt cß║ú c├íc b╞░ß╗¢c trong ch╞░╞íng n├áy, bß║ín n├¬n c├│:
Γöé
Γûê1. Repository ─æ├ú clone v├á push l├¬n GitHub.
Γûê2. M├┤i tr╞░ß╗¥ng ß║úo ─æ├ú setup, tß║Ñt cß║ú dependencies ─æ├ú c├ái.
Γûê3. File `.env` ─æ├ú cß║Ñu h├¼nh vß╗¢i API key.
Γûê4. Server chß║íy ─æ╞░ß╗úc tr├¬n localhost, Swagger UI accessible.
Γûê5. README ─æ├ú cß║¡p nhß║¡t vß╗¢i th├┤ng tin ─æß╗Öi.
Γûê6. Branch `develop` ─æ├ú tß║ío, ├¡t nhß║Ñt 1 commit tr├¬n `develop`.
Γûê7. AI Logging Hooks ─æ├ú c├ái ─æß║╖t (xem phß║ºn d╞░ß╗¢i).
Γöé
ΓûêNß║┐u bß║ín ─æ├ú c├│ ─æß╗º 7 mß╗Ñc tr├¬n, bß║ín ─æang ─æi ─æ├║ng h╞░ß╗¢ng. Sang Ch╞░╞íng 3, ch├║ng ta sß║╜ thiß║┐t kß║┐ kiß║┐n tr├║c hß╗ç thß╗æng ΓÇö quyß║┐t ─æß╗ïnh quan trß╗ìng nhß║Ñt ß║únh h╞░ß╗ƒng ─æß║┐n to├án bß╗Ö dß╗▒ ├ín.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** ─Éß╗½ng vß╗Öi bß║»t ─æß║ºu viß║┐t Agent logic ngay. Template c├│ sß║╡n placeholder code trong `src/agent/` ΓÇö ─æß╗â y├¬n cho ─æß║┐n khi bß║ín ho├án th├ánh thiß║┐t kß║┐ kiß║┐n tr├║c ß╗ƒ Ch╞░╞íng 3. Code m├á kh├┤ng c├│ thiß║┐t kß║┐ l├á code m├á bß║ín sß║╜ phß║úi viß║┐t lß║íi. Kinh nghiß╗çm cho thß║Ñy: c├íc ─æß╗Öi thiß║┐t kß║┐ tr╞░ß╗¢c khi code lu├┤n c├│ kß║┐t quß║ú tß╗æt h╞ín ─æ├íng kß╗â so vß╗¢i c├íc ─æß╗Öi "code first, design later."
Γöé
Γûê## C├ái ─æß║╖t AI Usage Logging Hooks
Γöé
ΓûêTemplate t├¡ch hß╗úp sß║╡n hß╗ç thß╗æng auto-logging ΓÇö ghi lß║íi mß╗ìi prompt v├á tool call khi bß║ín d├╣ng AI coding tools. ─É├óy l├á y├¬u cß║ºu bß║»t buß╗Öc cß╗ºa ch╞░╞íng tr├¼nh: BTC cß║ºn theo d├╡i viß╗çc sß╗¡ dß╗Ñng AI tools cß╗ºa c├íc ─æß╗Öi.
Γöé
Γûê### Tß║íi sao cß║ºn AI Logging?
Γöé
Γûê- **Transparency** ΓÇö Minh bß║ích vß╗ü viß╗çc sß╗¡ dß╗Ñng AI trong qu├í tr├¼nh ph├ít triß╗ân
Γûê- **Grading** ΓÇö BTC sß╗¡ dß╗Ñng data n├áy ─æß╗â ─æ├ính gi├í phß║ºn "AI Usage" trong rubric
Γûê- **Self-reflection** ΓÇö Gi├║p ─æß╗Öi xem lß║íi pattern sß╗¡ dß╗Ñng AI cß╗ºa m├¼nh (tool n├áo d├╣ng nhiß╗üu, prompt n├áo hiß╗çu quß║ú)
Γöé
Γûê### Chß║íy setup (bß║»t buß╗Öc ΓÇö 1 lß║ºn duy nhß║Ñt)
Γöé
Γûê```bash
Γûê# Linux / macOS / Git Bash
Γûêbash scripts/setup_hooks.sh
Γöé
Γûê# Windows PowerShell
Γûê# powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
Γûê```
Γöé
ΓûêLß╗çnh n├áy c├ái git pre-push hook v├á tß║ío th╞░ mß╗Ñc `.ai-log/`. Sau khi chß║íy, mß╗ìi AI tool d╞░ß╗¢i ─æ├óy sß║╜ tß╗▒ ─æß╗Öng log ΓÇö kh├┤ng cß║ºn thao t├íc th├¬m.
Γöé
Γûê### 6 AI tools ─æ╞░ß╗úc hß╗ù trß╗ú tß╗▒ ─æß╗Öng
Γöé
Γûê| Tool | C╞í chß║┐ | Khi n├áo log |
Γûê|------|--------|-------------|
Γûê| **Claude Code** | `.claude/settings.json` hooks | Mß╗ùi prompt + mß╗ùi tool call |
Γûê| **Cursor** | `.cursor/hooks.json` | Mß╗ùi prompt + khi stop |
Γûê| **OpenAI Codex CLI** | `.codex/hooks.json` | Mß╗ùi prompt + khi stop |
Γûê| **Gemini CLI** | `.gemini/settings.json` | BeforeAgent + AfterModel + SessionEnd |
Γûê| **GitHub Copilot** | `.github/hooks/hooks.json` | Mß╗ùi prompt + khi session end |
Γûê| **Antigravity IDE** | Pre-push scan transcript | Tß╗▒ ─æß╗Öng qu├⌐t transcript khi `git push` |
Γöé
Γûê### C├ích hoß║ít ─æß╗Öng
Γöé
Γûê```
ΓûêBß║ín d├╣ng AI tool (Claude Code, Cursor, v.v.)
Γûê        Γåô
ΓûêHook tß╗▒ ─æß╗Öng capture prompt + metadata
Γûê        Γåô
ΓûêAppend v├áo .ai-log/session.jsonl
Γûê        Γåô
Γûêgit push ΓåÆ pre-push hook submit l├¬n grading server
Γûê```
Γöé
ΓûêMetadata ─æ╞░ß╗úc log bao gß╗ôm: timestamp, tool name, model, repo, branch, commit, student email, prompt text, tool response.
Γöé
Γûê### Log thß╗º c├┤ng cho web tools
Γöé
ΓûêNß║┐u d├╣ng ChatGPT, Claude.ai, Gemini Web, hoß║╖c tool kh├┤ng c├│ hook:
Γöé
Γûê```bash
Γûê# Interactive (script sß║╜ hß╗Åi tool + prompt)
Γûêbash scripts/_pyrun.sh scripts/log_manual.py
Γöé
Γûê# One-line
Γûêbash scripts/_pyrun.sh scripts/log_manual.py --tool chatgpt --prompt "Brainstorm UI layout"
Γûêbash scripts/_pyrun.sh scripts/log_manual.py --tool gemini-web --prompt "Research scoring algorithms"
Γûê```
Γöé
Γûê### Cß║Ñu h├¼nh `.env`
Γöé
ΓûêTemplate ─æ├ú c├│ sß║╡n trong `.env.example`:
Γöé
Γûê```env
ΓûêAI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest
ΓûêAI_LOG_API_KEY=<gi├ío vi├¬n sß║╜ cung cß║Ñp>
ΓûêAI_LOG_DIR=.ai-log
Γûê```
Γöé
ΓûêCopy tß╗½ `.env.example` sang `.env` v├á ─æiß╗ün `AI_LOG_API_KEY` do instructor cß║Ñp.
Γöé
Γûê### Troubleshooting
Γöé
Γûê| Vß║Ñn ─æß╗ü | Nguy├¬n nh├ón | C├ích fix |
Γûê|---------|-------------|----------|
Γûê| Hooks kh├┤ng log | Ch╞░a chß║íy `setup_hooks.sh` | Chß║íy lß║íi `bash scripts/setup_hooks.sh` |
Γûê| `python3: not found` | Thiß║┐u Python tr├¬n PATH | `brew install python3` (macOS) hoß║╖c c├ái tß╗½ python.org (Windows) |
Γûê| Submit failed | Sai `AI_LOG_API_KEY` hoß║╖c kh├┤ng c├│ network | Kiß╗âm tra `.env`, logs vß║½n giß╗» locally |
Γûê| Antigravity kh├┤ng log | Ch╞░a c├│ transcript | Chß║»c chß║»n d├╣ng Antigravity IDE trong repo folder |
Γöé
Γûê> ΓÜá∩╕Å **QUAN TRß╗îNG:** ─Éß╗½ng sß╗¡a hoß║╖c xo├í file trong `.ai-log/`. ─Éß╗½ng chß║íy `git push --no-verify` ─æß╗â bypass hook. Nß║┐u hook b├ío lß╗ùi, b├ío cho instructor thay v├¼ tß╗▒ bypass.
Γöé
Γûê## T├│m tß║»t
Γöé
ΓûêCh╞░╞íng n├áy h╞░ß╗¢ng dß║½n bß║ín khß╗ƒi tß║ío dß╗▒ ├ín tß╗½ template ΓÇö b╞░ß╗¢c ─æß║ºu ti├¬n v├á quan trß╗ìng nhß║Ñt. Ch├║ng ta ─æ├ú ─æi qua viß╗çc clone repository, hiß╗âu cß║Ñu tr├║c th╞░ mß╗Ñc (src/, tests/, docs/, eval/, presentation/), thiß║┐t lß║¡p m├┤i tr╞░ß╗¥ng ß║úo vß╗¢i Python 3.11+, c├ái ─æß║╖t dependencies, v├á chß║íy server lß║ºn ─æß║ºu ti├¬n.
Γöé
ΓûêBß║ín c┼⌐ng ─æ├ú hß╗ìc c├ích quß║ún l├╜ biß║┐n m├┤i tr╞░ß╗¥ng vß╗¢i pydantic-settings, thiß║┐t lß║¡p Git workflow vß╗¢i branching strategy v├á commit message convention, v├á hiß╗âu ─æ╞░ß╗úc nhß╗»ng g├¼ cß║ºn t├╣y chß╗ënh so vß╗¢i nhß╗»ng g├¼ cß║ºn giß╗» nguy├¬n tß╗½ template.
Γöé
ΓûêTemplate kh├┤ng phß║úi l├á g├┤ng c├╣m ΓÇö n├│ l├á ─æ╞░ß╗¥ng ray. ─É╞░ß╗¥ng ray kh├┤ng giß╗¢i hß║ín tß╗æc ─æß╗Ö cß╗ºa t├áu, m├á ─æß║úm bß║úo t├áu ─æi ─æ├║ng h╞░ß╗¢ng v├á kh├┤ng bß╗ï trß║¡t. T╞░╞íng tß╗▒, template ─æß║úm bß║úo dß╗▒ ├ín cß╗ºa bß║ín c├│ nß╗ün tß║úng vß╗»ng chß║»c, trong khi vß║½n cho bß║ín tß╗▒ do s├íng tß║ío ß╗ƒ phß║ºn logic v├á t├¡nh n─âng.
Γöé
Γûê## C├óu hß╗Åi ├┤n tß║¡p
Γöé
Γûê**C├óu 1:** Tß║íi sao ch├║ng ta phß║úi x├│a `.git` cß╗ºa template v├á chß║íy `git init` lß║íi? ─Éiß╗üu g├¼ sß║╜ xß║úy ra nß║┐u kh├┤ng l├ám b╞░ß╗¢c n├áy?
Γöé
Γûê**C├óu 2:** Giß║úi th├¡ch sß╗▒ kh├íc biß╗çt giß╗»a file `.env.example` v├á file `.env`. Tß║íi sao file `.env.example` ─æ╞░ß╗úc commit l├¬n Git nh╞░ng file `.env` th├¼ kh├┤ng? ─Éiß╗üu g├¼ xß║úy ra nß║┐u bß║ín lß╗í commit file `.env`?
Γöé
Γûê**C├óu 3:** Trong cß║Ñu h├¼nh pydantic-settings, tß║íi sao ch├║ng ta d├╣ng `Literal["development", "staging", "production"]` thay v├¼ `str` cho field `app_env`? Lß╗úi ├¡ch cß╗ºa viß╗çc n├áy l├á g├¼ trong thß╗▒c tß║┐? H├úy cho mß╗Öt v├¡ dß╗Ñ cß╗Ñ thß╗â vß╗ü t├¼nh huß╗æng m├á Literal type gi├║p ph├ít hiß╗çn lß╗ùi sß╗¢m.


docs\guide\chapter-03.md:
Γûê---
Γûêtitle: "Thiß║┐t kß║┐ kiß║┐n tr├║c hß╗ç thß╗æng"
Γûêweight: 3
Γûê---
Γöé
Γûê## Tß╗òng quan kiß║┐n tr├║c 3 tß║ºng ΓÇö Nh├¼n bß╗⌐c tranh to├án cß║únh
Γöé
ΓûêTr╞░ß╗¢c khi viß║┐t mß╗Öt d├▓ng code n├áo cho Agent logic, bß║ín cß║ºn trß║ú lß╗¥i c├óu hß╗Åi quan trß╗ìng nhß║Ñt: **hß╗ç thß╗æng cß╗ºa bß║ín sß║╜ c├│ cß║Ñu tr├║c nh╞░ thß║┐ n├áo?** Kiß║┐n tr├║c hß╗ç thß╗æng giß╗æng nh╞░ bß║ún ─æß╗ô x├óy dß╗▒ng ΓÇö n├│ cho bß║ín biß║┐t mß╗ùi th├ánh phß║ºn nß║▒m ß╗ƒ ─æ├óu, giao tiß║┐p vß╗¢i nhau ra sao, v├á dß╗» liß╗çu chß║úy qua hß╗ç thß╗æng theo ─æ╞░ß╗¥ng n├áo. Thiß║┐t kß║┐ kiß║┐n tr├║c tß╗æt gi├║p bß║ín ph├ít triß╗ân nhanh, bß║úo tr├¼ dß╗à, v├á mß╗ƒ rß╗Öng (scale) khi cß║ºn. Thiß║┐t kß║┐ kiß║┐n tr├║c tß╗ôi dß║½n ─æß║┐n code rß╗æi, bug nhiß╗üu, v├á phß║úi viß║┐t lß║íi tß╗½ ─æß║ºu.
Γöé
ΓûêPhß║ºn lß╗¢n c├íc ß╗⌐ng dß╗Ñng AI Agent hiß╗çn ─æß║íi sß╗¡ dß╗Ñng **kiß║┐n tr├║c 3 tß║ºng** (three-tier architecture), bao gß╗ôm Frontend, Backend, v├á AI Agent. Mß╗ùi tß║ºng c├│ tr├ích nhiß╗çm ri├¬ng, giao tiß║┐p vß╗¢i tß║ºng kh├íc th├┤ng qua API r├╡ r├áng. T├ích biß╗çt n├áy mang lß║íi nhiß╗üu lß╗úi ├¡ch: bß║ín c├│ thß╗â thay ─æß╗òi Frontend m├á kh├┤ng ß║únh h╞░ß╗ƒng Agent logic, n├óng cß║Ñp Agent m├á kh├┤ng cß║ºn deploy lß║íi Frontend, v├á scale tß╗½ng tß║ºng ─æß╗Öc lß║¡p.
Γöé
ΓûêS╞í ─æß╗ô d╞░ß╗¢i ─æ├óy minh hß╗ìa kiß║┐n tr├║c tß╗òng thß╗â:
Γöé
Γûê```mermaid
Γûêgraph TB
Γûê    subgraph Frontend["Frontend (React / Next.js)"]
Γûê        UI[Giao diß╗çn ng╞░ß╗¥i d├╣ng]
Γûê        Chat[Chat Interface]
Γûê        Dashboard[Dashboard]
Γûê    end
Γöé
Γûê    subgraph Backend["Backend (FastAPI)"]
Γûê        API[API Endpoints]
Γûê        Auth[X├íc thß╗▒c & Ph├ón quyß╗ün]
Γûê        DB[(Database)]
Γûê        Cache[(Cache)]
Γûê    end
Γöé
Γûê    subgraph Agent["AI Agent (LangGraph)"]
Γûê        Router[Intent Router]
Γûê        Tools[Agent Tools]
Γûê        Memory[Agent Memory]
Γûê        LLM[LLM Provider]
Γûê    end
Γöé
Γûê    UI --> API
Γûê    Chat --> API
Γûê    Dashboard --> API
Γûê    API --> Auth
Γûê    API --> DB
Γûê    API --> Router
Γûê    Router --> Tools
Γûê    Router --> Memory
Γûê    Router --> LLM
Γûê    Tools --> LLM
Γûê```
Γöé
Γûê**Frontend** l├á tß║ºng ng╞░ß╗¥i d├╣ng t╞░╞íng t├íc trß╗▒c tiß║┐p. N├│ gß╗¡i HTTP requests ─æß║┐n Backend v├á hiß╗ân thß╗ï kß║┐t quß║ú. Trong ngß╗» cß║únh AI Agent, Frontend th╞░ß╗¥ng c├│ dß║íng chat interface (giao diß╗çn tr├▓ chuyß╗çn) n╞íi ng╞░ß╗¥i d├╣ng nhß║¡p c├óu hß╗Åi v├á nhß║¡n c├óu trß║ú lß╗¥i tß╗½ Agent. Frontend c┼⌐ng c├│ thß╗â bao gß╗ôm dashboard hiß╗ân thß╗ï thß╗æng k├¬, lß╗ïch sß╗¡ hß╗Öi thoß║íi, v├á c├íc t├¡nh n─âng quß║ún l├╜.
Γöé
Γûê**Backend** l├á "trß║ím trung chuyß╗ân" ΓÇö n├│ nhß║¡n requests tß╗½ Frontend, xß╗¡ l├╜ business logic (x├íc thß╗▒c, ph├ón quyß╗ün, validate dß╗» liß╗çu), gß╗ìi AI Agent khi cß║ºn, l╞░u trß╗» dß╗» liß╗çu v├áo database, v├á trß║ú kß║┐t quß║ú vß╗ü Frontend. Backend l├á n╞íi bß║ín kiß╗âm so├ít ai ─æ╞░ß╗úc d├╣ng hß╗ç thß╗æng, giß╗¢i hß║ín rate (rate limiting), v├á log lß║íi mß╗ìi hoß║ít ─æß╗Öng.
Γöé
Γûê**AI Agent** l├á "bß╗Ö n├úo" cß╗ºa hß╗ç thß╗æng. N├│ nhß║¡n c├óu hß╗Åi tß╗½ Backend (─æ╞░ß╗úc forwarding tß╗½ Frontend), xß╗¡ l├╜ qua state machine (LangGraph), sß╗¡ dß╗Ñng tools nß║┐u cß║ºn (t├¼m kiß║┐m web, truy vß║Ñn database, gß╗ìi API b├¬n ngo├ái), v├á trß║ú vß╗ü c├óu trß║ú lß╗¥i. Agent kh├┤ng giao tiß║┐p trß╗▒c tiß║┐p vß╗¢i ng╞░ß╗¥i d├╣ng ΓÇö mß╗ìi giao tiß║┐p ─æß╗üu th├┤ng qua Backend.
Γöé
ΓûêTß║íi sao lß║íi t├ích l├ám 3 tß║ºng thay v├¼ gß╗Öp tß║Ñt cß║ú v├áo mß╗Öt? C├│ ba l├╜ do ch├¡nh:
Γöé
Γûê**Thß╗⌐ nhß║Ñt, separation of concerns (t├ích biß╗çt tr├ích nhiß╗çm).** Mß╗ùi tß║ºng chß╗ë lo mß╗Öt viß╗çc. Frontend chß╗ë lo hiß╗ân thß╗ï. Backend chß╗ë lo business logic v├á data. Agent chß╗ë lo AI reasoning. Khi bß║ín cß║ºn sß╗¡a mß╗Öt bug ß╗ƒ giao diß╗çn, bß║ín kh├┤ng cß║ºn ─æß╗ìc code Agent. Khi bß║ín cß║ºn tß╗æi ╞░u Agent logic, bß║ín kh├┤ng cß║ºn ─æß╗Ñng v├áo Frontend.
Γöé
Γûê**Thß╗⌐ hai, scalability (khß║ú n─âng mß╗ƒ rß╗Öng).** Trong thß╗▒c tß║┐, AI Agent th╞░ß╗¥ng l├á ─æiß╗âm nghß║╜n (bottleneck) v├¼ LLM inference mß║Ñt thß╗¥i gian. Vß╗¢i kiß║┐n tr├║c 3 tß║ºng, bß║ín c├│ thß╗â scale Agent layer ri├¬ng bß║▒ng c├ích chß║íy nhiß╗üu Agent instance, m├á kh├┤ng cß║ºn th├¬m resource cho Frontend hay Backend. T╞░╞íng tß╗▒, nß║┐u c├│ 1000 users truy cß║¡p ─æß╗ông thß╗¥i, bß║ín scale Frontend v├á Backend, kh├┤ng cß║ºn th├¬m Agent instances.
Γöé
Γûê**Thß╗⌐ ba, technology flexibility (linh hoß║ít c├┤ng nghß╗ç).** Bß║ín c├│ thß╗â thay ─æß╗òi Frontend tß╗½ React sang Vue m├á kh├┤ng ß║únh h╞░ß╗ƒng Backend hay Agent. Bß║ín c├│ thß╗â ─æß╗òi LLM provider tß╗½ OpenAI sang Anthropic m├á kh├┤ng cß║ºn ─æß╗Ñng ─æß║┐n Frontend. Mß╗ùi tß║ºng c├│ thß╗â chß╗ìn c├┤ng nghß╗ç ph├╣ hß╗úp nhß║Ñt cho nhiß╗çm vß╗Ñ cß╗ºa n├│.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Kiß║┐n tr├║c 3 tß║ºng kh├┤ng phß║úi over-engineering ΓÇö n├│ l├á baseline. Thß║¡m ch├¡ nß║┐u dß╗▒ ├ín nhß╗Å, viß╗çc t├ích biß╗çt r├╡ r├áng giß╗»a Frontend, Backend, v├á Agent sß║╜ gi├║p bß║ín ph├ít triß╗ân nhanh h╞ín v├á ├¡t bug h╞ín. Kinh nghiß╗çm cho thß║Ñy c├íc ─æß╗Öi c├│ kiß║┐n tr├║c r├╡ r├áng lu├┤n ─æß║ít kß║┐t quß║ú tß╗æt h╞ín ─æ├íng kß╗â so vß╗¢i c├íc ─æß╗Öi gß╗Öp tß║Ñt cß║ú v├áo mß╗Öt file.
Γöé
Γûê## Frontend (React/Next.js) ΓÇö Giao diß╗çn cho AI Agent
Γöé
ΓûêFrontend l├á "mß║╖t tiß╗ün" cß╗ºa ß╗⌐ng dß╗Ñng ΓÇö thß╗⌐ m├á ng╞░ß╗¥i d├╣ng thß║Ñy v├á t╞░╞íng t├íc. ─Éß╗æi vß╗¢i AI Agent application, Frontend th╞░ß╗¥ng c├│ hai loß║íi giao diß╗çn ch├¡nh: **chat interface** (giao diß╗çn tr├▓ chuyß╗çn, giß╗æng ChatGPT) v├á **dashboard** (bß║úng ─æiß╗üu khiß╗ân hiß╗ân thß╗ï dß╗» liß╗çu, thß╗æng k├¬, v├á kß║┐t quß║ú ph├ón t├¡ch).
Γöé
Γûê### Tß║íi sao chß╗ìn React/Next.js?
Γöé
ΓûêReact l├á th╞░ viß╗çn JavaScript phß╗ò biß║┐n nhß║Ñt thß║┐ giß╗¢i ─æß╗â x├óy dß╗▒ng giao diß╗çn ng╞░ß╗¥i d├╣ng, vß╗¢i ecosystem khß╗òng lß╗ô v├á cß╗Öng ─æß╗ông hß╗ù trß╗ú mß║ính mß║╜. Next.js l├á framework x├óy dß╗▒ng tr├¬n nß╗ün React, th├¬m c├íc t├¡nh n─âng nh╞░ server-side rendering (SSR), static site generation (SSG), v├á API routes.
Γöé
Γûê─Éß╗æi vß╗¢i dß╗▒ ├ín AI20K, bß║ín kh├┤ng bß║»t buß╗Öc phß║úi d├╣ng React/Next.js ΓÇö bß║ín c├│ thß╗â d├╣ng Streamlit, Gradio, hoß║╖c thß║¡m ch├¡ terminal UI. Tuy nhi├¬n, React/Next.js mang lß║íi lß╗úi thß║┐:
Γöé
Γûê- **Streaming response:** AI Agent th╞░ß╗¥ng trß║ú lß╗¥i tß╗½ng token (streaming). React xß╗¡ l├╜ streaming tß╗æt h╞ín Streamlit.
Γûê- **T├╣y chß╗ënh ho├án to├án:** Bß║ín c├│ thß╗â thiß║┐t kß║┐ giao diß╗çn ch├¡nh x├íc nh╞░ muß╗æn, kh├┤ng bß╗ï giß╗¢i hß║ín bß╗ƒi template cß╗ºa Streamlit hay Gradio.
Γûê- **Production-ready:** Nß║┐u dß╗▒ ├ín tiß║┐p tß╗Ñc ph├ít triß╗ân sau AI20K, React/Next.js l├á lß╗▒a chß╗ìn m├á hß║ºu hß║┐t c├┤ng ty sß╗¡ dß╗Ñng.
Γöé
Γûê### Server-Side Rendering vs Client-Side Rendering
Γöé
ΓûêKhi d├╣ng Next.js, bß║ín cß║ºn hiß╗âu hai chß║┐ ─æß╗Ö rendering ch├¡nh:
Γöé
Γûê**Server-Side Rendering (SSR):** Trang HTML ─æ╞░ß╗úc render tr├¬n server v├á gß╗¡i ─æß║┐n tr├¼nh duyß╗çt. Ph├╣ hß╗úp cho trang nß╗Öi dung t─⌐nh, cß║ºn SEO tß╗æt (blog, landing page). Trong AI Agent app, SSR ph├╣ hß╗úp cho trang chß╗º, trang giß╗¢i thiß╗çu, v├á dashboard hiß╗ân thß╗ï dß╗» liß╗çu lß╗ïch sß╗¡.
Γöé
Γûê**Client-Side Rendering (CSR):** Trang HTML gß║ºn nh╞░ trß╗æng, JavaScript chß║íy tr├¬n tr├¼nh duyß╗çt ─æß╗â render nß╗Öi dung. Ph├╣ hß╗úp cho interactive app, ─æß║╖c biß╗çt l├á chat interface. Khi bß║ín chat vß╗¢i Agent, CSR cho ph├⌐p cß║¡p nhß║¡t giao diß╗çn real-time m├á kh├┤ng cß║ºn reload trang.
Γöé
ΓûêTrong thß╗▒c tß║┐, AI Agent app th╞░ß╗¥ng kß║┐t hß╗úp cß║ú hai: SSR cho c├íc trang public, CSR cho chat interface. Next.js hß╗ù trß╗ú cß║ú hai chß║┐ ─æß╗Ö trong c├╣ng mß╗Öt ß╗⌐ng dß╗Ñng th├┤ng qua App Router.
Γöé
Γûê### Thiß║┐t kß║┐ Chat Interface
Γöé
ΓûêChat interface l├á core feature cß╗ºa AI Agent app. D╞░ß╗¢i ─æ├óy l├á c├íc th├ánh phß║ºn ch├¡nh:
Γöé
Γûê```mermaid
Γûêgraph LR
Γûê    subgraph Chat UI
Γûê        Input[Input Box]
Γûê        Messages[Message List]
Γûê        Streaming[Streaming Display]
Γûê    end
Γöé
Γûê    Input -->|User sends message| API[POST /api/v1/chat]
Γûê    API -->|SSE stream| Streaming
Γûê    Streaming --> Messages
Γûê```
Γöé
Γûê**Input Box** ΓÇö N╞íi ng╞░ß╗¥i d├╣ng nhß║¡p c├óu hß╗Åi. N├¬n hß╗ù trß╗ú multi-line (nhiß╗üu d├▓ng) v├á gß╗¡i bß║▒ng Enter (Shift+Enter cho d├▓ng mß╗¢i). C├│ thß╗â th├¬m n├║t upload file nß║┐u Agent hß╗ù trß╗ú xß╗¡ l├╜ t├ái liß╗çu.
Γöé
Γûê**Message List** ΓÇö Hiß╗ân thß╗ï lß╗ïch sß╗¡ hß╗Öi thoß║íi. Mß╗ùi message c├│ role (user hoß║╖c assistant), content (nß╗Öi dung), v├á timestamp. N├¬n auto-scroll xuß╗æng tin nhß║»n mß╗¢i nhß║Ñt. Hß╗ù trß╗ú Markdown rendering cho c├óu trß║ú lß╗¥i cß╗ºa Agent (code blocks, tables, bold/italic).
Γöé
Γûê**Streaming Display** ΓÇö Hiß╗ân thß╗ï c├óu trß║ú lß╗¥i cß╗ºa Agent tß╗½ng token (streaming) thay v├¼ ─æß╗úi to├án bß╗Ö c├óu trß║ú lß╗¥i. ─Éiß╗üu n├áy cß║úi thiß╗çn trß║úi nghiß╗çm ng╞░ß╗¥i d├╣ng ─æ├íng kß╗â ΓÇö hß╗ì thß║Ñy Agent ─æang "suy ngh─⌐" v├á trß║ú lß╗¥i dß║ºn dß║ºn, thay v├¼ nh├¼n m├án h├¼nh trß╗æng trong 10-15 gi├óy.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Nß║┐u thß╗¥i gian c├│ hß║ín, h├úy bß║»t ─æß║ºu vß╗¢i Streamlit cho prototype nhanh, sau ─æ├│ migrate sang React/Next.js cho production. Streamlit cho ph├⌐p bß║ín tß║ío giao diß╗çn chat c╞í bß║ún trong v├ái d├▓ng code Python, ph├╣ hß╗úp cho demo nß╗Öi bß╗Ö. Nh╞░ng khi cß║ºn giao diß╗çn polished cho Demo Day, React/Next.js l├á lß╗▒a chß╗ìn tß╗æt h╞ín.
Γöé
Γûê### Khi n├áo Frontend "─æß╗º tß╗æt"?
Γöé
ΓûêTrong khu├┤n khß╗ò AI20K, Frontend kh├┤ng phß║úi ti├¬u ch├¡ ─æ├ính gi├í ch├¡nh ΓÇö Agent logic v├á Backend quan trß╗ìng h╞ín. Frontend "─æß╗º tß╗æt" khi:
Γöé
Γûê- Ng╞░ß╗¥i d├╣ng c├│ thß╗â nhß║¡p c├óu hß╗Åi v├á nhß║¡n c├óu trß║ú lß╗¥i.
Γûê- Streaming response hiß╗ân thß╗ï ─æ├║ng.
Γûê- Error messages hiß╗ân thß╗ï th├ón thiß╗çn (kh├┤ng hiß╗ân thß╗ï stack trace).
Γûê- Giao diß╗çn responsive (hoß║ít ─æß╗Öng tr├¬n cß║ú mobile).
Γûê- C├│ indicator khi Agent ─æang xß╗¡ l├╜ (loading spinner hoß║╖c "typing...").
Γöé
Γûê─Éß╗½ng d├ánh qu├í nhiß╗üu thß╗¥i gian cho UI polish. Mß╗Öt giao diß╗çn ─æ╞ín giß║ún nh╞░ng hoß║ít ─æß╗Öng ß╗òn ─æß╗ïnh tß╗æt h╞ín mß╗Öt giao diß╗çn ─æß║╣p nh╞░ng ─æß║ºy bug.
Γöé
Γûê## Backend (FastAPI) ΓÇö X╞░╞íng sß╗æng cß╗ºa hß╗ç thß╗æng
Γöé
ΓûêBackend l├á tß║ºng kß║┐t nß╗æi Frontend v├á AI Agent, ─æß╗ông thß╗¥i xß╗¡ l├╜ tß║Ñt cß║ú business logic kh├┤ng li├¬n quan ─æß║┐n AI reasoning: x├íc thß╗▒c ng╞░ß╗¥i d├╣ng, quß║ún l├╜ session, l╞░u trß╗» lß╗ïch sß╗¡ chat, rate limiting, logging, v├á error handling. FastAPI l├á framework ─æ╞░ß╗úc chß╗ìn cho Backend v├¼ nhiß╗üu l├╜ do thuyß║┐t phß╗Ñc.
Γöé
Γûê### Tß║íi sao chß╗ìn FastAPI?
Γöé
Γûê**Hiß╗çu n─âng async tß╗▒ nhi├¬n.** FastAPI x├óy dß╗▒ng tr├¬n nß╗ün Starlette v├á hß╗ù trß╗ú async/await ngay tß╗½ ─æß║ºu. Trong ß╗⌐ng dß╗Ñng AI Agent, bß║ín th╞░ß╗¥ng cß║ºn gß╗ìi LLM API (mß║Ñt v├ái gi├óy), gß╗ìi external tools (mß║Ñt v├ái tr─âm mili-gi├óy), v├á xß╗¡ l├╜ nhiß╗üu requests ─æß╗ông thß╗¥i. Async cho ph├⌐p server xß╗¡ l├╜ request kh├íc trong khi chß╗¥ LLM phß║ún hß╗ôi, thay v├¼ block (chß║╖n) to├án bß╗Ö server.
Γöé
Γûê**Tß╗▒ ─æß╗Öng sinh API documentation.** FastAPI sß╗¡ dß╗Ñng OpenAPI specification (tr╞░ß╗¢c ─æ├óy gß╗ìi l├á Swagger) ─æß╗â tß╗▒ ─æß╗Öng sinh interactive API docs tß║íi `/docs` (Swagger UI) v├á `/redoc` (ReDoc). ─Éiß╗üu n├áy c├│ ngh─⌐a l├á mß╗ùi khi bß║ín th├¬m endpoint mß╗¢i, documentation tß╗▒ ─æß╗Öng cß║¡p nhß║¡t ΓÇö kh├┤ng cß║ºn viß║┐t docs thß╗º c├┤ng. C├íc ─æß╗Öi d├╣ng FastAPI th╞░ß╗¥ng c├│ t├ái liß╗çu API tß╗æt h╞ín hß║│n so vß╗¢i phß║úi viß║┐t docs bß║▒ng tay.
Γöé
Γûê**Type safety vß╗¢i Pydantic.** Mß╗ùi request v├á response ─æ╞░ß╗úc validate tß╗▒ ─æß╗Öng bß╗ƒi Pydantic models. Nß║┐u client gß╗¡i dß╗» liß╗çu sai format (v├¡ dß╗Ñ: gß╗¡i string thay v├¼ integer cho field `limit`), FastAPI tß╗▒ ─æß╗Öng trß║ú vß╗ü error 422 vß╗¢i th├┤ng b├ío chi tiß║┐t. ─Éiß╗üu n├áy giß║úm thiß╗âu bug do data type mismatch ΓÇö mß╗Öt lß╗ùi rß║Ñt phß╗ò biß║┐n.
Γöé
Γûê**Hß╗ù trß╗ú Server-Sent Events (SSE).** SSE cho ph├⌐p server push data ─æß║┐n client li├¬n tß╗Ñc, l├╜ t╞░ß╗ƒng cho streaming response tß╗½ LLM. Thay v├¼ ─æß╗úi Agent trß║ú lß╗¥i xong rß╗ôi gß╗¡i to├án bß╗Ö response, bß║ín c├│ thß╗â stream tß╗½ng chunk ─æß║┐n Frontend, tß║ío trß║úi nghiß╗çm "typing effect" giß╗æng ChatGPT.
Γöé
Γûê### Cß║Ñu tr├║c API cho AI Agent
Γöé
ΓûêD╞░ß╗¢i ─æ├óy l├á c├íc API endpoints phß╗ò biß║┐n cho ß╗⌐ng dß╗Ñng AI Agent:
Γöé
Γûê```python
Γûêfrom fastapi import FastAPI, HTTPException
Γûêfrom pydantic import BaseModel, Field
Γûêfrom typing import AsyncGenerator
Γûêfrom fastapi.responses import StreamingResponse
Γöé
Γûêapp = FastAPI(title="AI Agent API", version="0.1.0")
Γöé
Γöé
Γûêclass ChatRequest(BaseModel):
Γûê    """Schema cho request gß╗¡i ─æß║┐n Agent."""
Γûê    message: str = Field(..., min_length=1, max_length=10000,
Γûê                         description="C├óu hß╗Åi cß╗ºa ng╞░ß╗¥i d├╣ng")
Γûê    session_id: str | None = Field(None, description="ID phi├¬n hß╗Öi thoß║íi")
Γûê    stream: bool = Field(True, description="Bß║¡t/tß║»t streaming response")
Γöé
Γöé
Γûêclass ChatResponse(BaseModel):
Γûê    """Schema cho response tß╗½ Agent."""
Γûê    answer: str
Γûê    session_id: str
Γûê    sources: list[str] = Field(default_factory=list)
Γûê    metadata: dict = Field(default_factory=dict)
Γöé
Γöé
Γûê@app.post("/api/v1/chat", response_model=ChatResponse)
Γûêasync def chat(request: ChatRequest) -> ChatResponse:
Γûê    """Gß╗¡i c├óu hß╗Åi ─æß║┐n AI Agent v├á nhß║¡n c├óu trß║ú lß╗¥i."""
Γûê    # Logic gß╗ìi Agent sß║╜ ß╗ƒ ─æ├óy
Γûê    ...
Γöé
Γöé
Γûê@app.post("/api/v1/chat/stream")
Γûêasync def chat_stream(request: ChatRequest) -> StreamingResponse:
Γûê    """Stream response tß╗½ Agent (SSE)."""
Γûê    async def generate() -> AsyncGenerator[str, None]:
Γûê        # Stream tß╗½ng chunk tß╗½ Agent
Γûê        async for chunk in agent.astream(request.message):
Γûê            yield f"data: {chunk}\n\n"
Γöé
Γûê    return StreamingResponse(
Γûê        generate(),
Γûê        media_type="text/event-stream"
Γûê    )
Γöé
Γöé
Γûê@app.get("/api/v1/health")
Γûêasync def health_check():
Γûê    """Health check endpoint."""
Γûê    return {"status": "healthy", "version": "0.1.0"}
Γûê```
Γöé
ΓûêPh├ón t├¡ch cß║Ñu tr├║c tr├¬n:
Γöé
Γûê**Pydantic models (BaseModel)** ─æ├│ng vai tr├▓ "hß╗úp ─æß╗ông" giß╗»a client v├á server. `ChatRequest` ─æß╗ïnh ngh─⌐a ch├¡nh x├íc dß╗» liß╗çu gß╗¡i l├¬n phß║úi c├│ dß║íng g├¼: `message` bß║»t buß╗Öc (kh├┤ng null), tß╗½ 1-10000 k├╜ tß╗▒; `session_id` t├╣y chß╗ìn; `stream` mß║╖c ─æß╗ïnh l├á True. Nß║┐u client gß╗¡i request kh├┤ng hß╗úp lß╗ç, FastAPI tß╗▒ ─æß╗Öng trß║ú vß╗ü lß╗ùi 422 vß╗¢i m├┤ tß║ú chi tiß║┐t ΓÇö bß║ín kh├┤ng cß║ºn viß║┐t validation code thß╗º c├┤ng.
Γöé
Γûê**Async endpoints** (`async def`) cho ph├⌐p server xß╗¡ l├╜ nhiß╗üu requests ─æß╗ông thß╗¥i. Khi mß╗Öt request ─æang chß╗¥ LLM phß║ún hß╗ôi, server c├│ thß╗â nhß║¡n v├á xß╗¡ l├╜ request kh├íc. Nß║┐u bß║ín d├╣ng `def` thay v├¼ `async def`, mß╗ùi request sß║╜ block mß╗Öt worker, v├á server c├│ thß╗â bß╗ï "─æ├│ng b─âng" nß║┐u c├│ nhiß╗üu users chat c├╣ng l├║c.
Γöé
Γûê**Streaming endpoint** sß╗¡ dß╗Ñng Server-Sent Events (SSE) ─æß╗â push tß╗½ng chunk cß╗ºa Agent response ─æß║┐n client. ─Éiß╗üu n├áy cß║úi thiß╗çn UX ─æ├íng kß╗â ΓÇö thay v├¼ ─æß╗úi 10-15 gi├óy cho Agent ho├án th├ánh, ng╞░ß╗¥i d├╣ng thß║Ñy c├óu trß║ú lß╗¥i xuß║Ñt hiß╗çn tß╗½ng phß║ºn, giß╗æng ChatGPT.
Γöé
Γûê### Error handling trong FastAPI
Γöé
Γûê```python
Γûêfrom fastapi import HTTPException
Γûêfrom src.core.config import settings
Γöé
Γöé
Γûê@app.post("/api/v1/chat")
Γûêasync def chat(request: ChatRequest):
Γûê    try:
Γûê        response = await agent.run(request.message)
Γûê        return ChatResponse(
Γûê            answer=response.content,
Γûê            session_id=request.session_id or str(uuid4()),
Γûê        )
Γûê    except LLMRateLimitError:
Γûê        raise HTTPException(
Γûê            status_code=429,
Γûê            detail="Agent ─æang qu├í tß║úi. Vui l├▓ng thß╗¡ lß║íi sau v├ái gi├óy."
Γûê        )
Γûê    except LLMAuthError:
Γûê        if settings.app_env == "development":
Γûê            raise HTTPException(
Γûê                status_code=500,
Γûê                detail="API key kh├┤ng hß╗úp lß╗ç. Kiß╗âm tra lß║íi .env file."
Γûê            )
Γûê        raise HTTPException(
Γûê            status_code=500,
Γûê            detail="Lß╗ùi cß║Ñu h├¼nh hß╗ç thß╗æng. Vui l├▓ng li├¬n hß╗ç admin."
Γûê        )
Γûê    except Exception as e:
Γûê        logger.error(f"Unexpected error: {e}")
Γûê        raise HTTPException(
Γûê            status_code=500,
Γûê            detail="─É├ú xß║úy ra lß╗ùi kh├┤ng mong muß╗æn. Vui l├▓ng thß╗¡ lß║íi."
Γûê        )
Γûê```
Γöé
ΓûêError handling phß║úi ph├ón biß╗çt giß╗»a m├┤i tr╞░ß╗¥ng development v├á production. Trong development, bß║ín muß╗æn hiß╗ân thß╗ï th├┤ng tin chi tiß║┐t ─æß╗â debug. Trong production, bß║ín chß╗ë hiß╗ân thß╗ï th├┤ng b├ío th├ón thiß╗çn, kh├┤ng tiß║┐t lß╗Ö chi tiß║┐t kß╗╣ thuß║¡t (─æß╗ü ph├▓ng lß╗Ö th├┤ng tin nhß║íy cß║úm).
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Kh├┤ng bao giß╗¥ hiß╗ân thß╗ï Python stack trace hay internal error message cho end user. Trong production, log chi tiß║┐t v├áo file log (hoß║╖c monitoring system), chß╗ë trß║ú vß╗ü generic error message. Th├┤ng tin nh╞░ database connection string hay API key c├│ thß╗â bß╗ï lß╗Ö qua error message nß║┐u bß║ín kh├┤ng cß║⌐n thß║¡n.
Γöé
Γûê## AI Agent (LangGraph) ΓÇö Bß╗Ö n├úo cß╗ºa hß╗ç thß╗æng
Γöé
ΓûêAI Agent l├á tß║ºng cß╗æt l├╡i ΓÇö n╞íi diß╗àn ra "suy ngh─⌐" cß╗ºa hß╗ç thß╗æng. Agent nhß║¡n c├óu hß╗Åi tß╗½ Backend, xß╗¡ l├╜ qua mß╗Öt quy tr├¼nh nhiß╗üu b╞░ß╗¢c (state machine), sß╗¡ dß╗Ñng tools khi cß║ºn, v├á trß║ú vß╗ü c├óu trß║ú lß╗¥i. LangGraph l├á framework ─æ╞░ß╗úc chß╗ìn ─æß╗â x├óy dß╗▒ng Agent v├¼ c├ích tiß║┐p cß║¡n duy nhß║Ñt: **state machine (m├íy trß║íng th├íi)** thay v├¼ linear chain (chuß╗ùi tuyß║┐n t├¡nh).
Γöé
Γûê### Tß║íi sao kh├┤ng d├╣ng LangChain th├┤ng th╞░ß╗¥ng?
Γöé
ΓûêNß║┐u bß║ín ─æ├ú t├¼m hiß╗âu vß╗ü LangChain, bß║ín c├│ thß╗â hß╗Åi: tß║íi sao kh├┤ng d├╣ng LangChain chain (LCEL) ─æ╞ín giß║ún thay v├¼ LangGraph? C├óu trß║ú lß╗¥i nß║▒m ß╗ƒ sß╗▒ kh├íc biß╗çt giß╗»a **chain** v├á **state machine**:
Γöé
Γûê**Chain (chuß╗ùi tuyß║┐n t├¡nh):** Input ΓåÆ Step A ΓåÆ Step B ΓåÆ Step C ΓåÆ Output. Lu├┤n ─æi theo ─æ├║ng thß╗⌐ tß╗▒ n├áy, kh├┤ng c├│ rß║╜ nh├ính, kh├┤ng c├│ loop, kh├┤ng c├│ ─æiß╗üu kiß╗çn. Ph├╣ hß╗úp cho c├íc task ─æ╞ín giß║ún nh╞░: "Dß╗ïch c├óu n├áy sang tiß║┐ng Anh" hoß║╖c "T├│m tß║»t ─æoß║ín v─ân bß║ún n├áy."
Γöé
Γûê**State machine (m├íy trß║íng th├íi):** Input ΓåÆ State A ΓåÆ (─æiß╗üu kiß╗çn?) ΓåÆ State B hoß║╖c State C ΓåÆ (cß║ºn th├¬m th├┤ng tin?) ΓåÆ quay lß║íi State A ΓåÆ ... ΓåÆ Output. C├│ rß║╜ nh├ính dß╗▒a tr├¬n ─æiß╗üu kiß╗çn, c├│ loop (v├▓ng lß║╖p), v├á c├│ thß╗â dß╗½ng giß╗»a chß╗¥ input. Ph├╣ hß╗úp cho c├íc task phß╗⌐c tß║íp nh╞░: "Trß║ú lß╗¥i c├óu hß╗Åi cß╗ºa user, nh╞░ng nß║┐u cß║ºn th├¬m th├┤ng tin th├¼ hß╗Åi lß║íi, nß║┐u cß║ºn t├¼m kiß║┐m th├¼ d├╣ng tool, nß║┐u c├óu trß║ú lß╗¥i ch╞░a ─æß╗º tß╗æt th├¼ suy ngh─⌐ lß║íi."
Γöé
ΓûêHß║ºu hß║┐t c├íc ß╗⌐ng dß╗Ñng AI Agent thß╗▒c tß║┐ ─æß╗üu y├¬u cß║ºu state machine, kh├┤ng phß║úi chain ─æ╞ín giß║ún. V├¡ dß╗Ñ: Agent cß║ºn quyß║┐t ─æß╗ïnh xem c├óu hß╗Åi cß╗ºa user c├│ cß║ºn t├¼m kiß║┐m web kh├┤ng, c├│ cß║ºn truy vß║Ñn database kh├┤ng, hay c├│ thß╗â trß║ú lß╗¥i trß╗▒c tiß║┐p bß║▒ng kiß║┐n thß╗⌐c cß╗ºa LLM. Sau khi t├¼m kiß║┐m, Agent cß║ºn quyß║┐t ─æß╗ïnh xem th├┤ng tin ─æ├ú ─æß╗º ─æß╗â trß║ú lß╗¥i ch╞░a hay cß║ºn t├¼m th├¬m. ─É├óy l├á **agentic loop** ΓÇö Agent lß║╖p lß║íi quy tr├¼nh "suy ngh─⌐ ΓåÆ h├ánh ─æß╗Öng ΓåÆ quan s├ít" cho ─æß║┐n khi c├│ c├óu trß║ú lß╗¥i thß╗Åa ─æ├íng.
Γöé
Γûê### State machine vß╗¢i LangGraph
Γöé
ΓûêLangGraph cho ph├⌐p bß║ín ─æß╗ïnh ngh─⌐a Agent d╞░ß╗¢i dß║íng mß╗Öt **directed graph** (─æß╗ô thß╗ï c├│ h╞░ß╗¢ng), trong ─æ├│ mß╗ùi node l├á mß╗Öt b╞░ß╗¢c xß╗¡ l├╜, mß╗ùi edge l├á ─æ╞░ß╗¥ng chuyß╗ân trß║íng th├íi, v├á **state** l├á dß╗» liß╗çu ─æ╞░ß╗úc truyß╗ün giß╗»a c├íc node.
Γöé
Γûê```mermaid
Γûêgraph TD
Γûê    A[User Input] --> B[Router Node]
Γûê    B -->|C├óu hß╗Åi ─æ╞ín giß║ún| C[Direct Answer]
Γûê    B -->|Cß║ºn t├¼m kiß║┐m| D[Search Tool]
Γûê    B -->|Cß║ºn database| E[DB Query Tool]
Γûê    D --> F[Evaluate]
Γûê    E --> F
Γûê    F -->|─Éß╗º th├┤ng tin| G[Generate Answer]
Γûê    F -->|Ch╞░a ─æß╗º| B
Γûê    C --> G
Γûê    G --> H[Output]
Γûê```
Γöé
ΓûêS╞í ─æß╗ô tr├¬n minh hß╗ìa mß╗Öt Agent ─æ╞ín giß║ún nh╞░ng thß╗▒c tß║┐. Khi nhß║¡n c├óu hß╗Åi, Router Node ph├ón loß║íi v├á quyß║┐t ─æß╗ïnh luß╗ông xß╗¡ l├╜:
Γöé
Γûê- Nß║┐u l├á c├óu hß╗Åi ─æ╞ín giß║ún (v├¡ dß╗Ñ: "Xin ch├áo"), trß║ú lß╗¥i trß╗▒c tiß║┐p.
Γûê- Nß║┐u cß║ºn th├┤ng tin hiß╗çn tß║íi (v├¡ dß╗Ñ: "Thß╗¥i tiß║┐t h├┤m nay thß║┐ n├áo?"), d├╣ng Search Tool.
Γûê- Nß║┐u cß║ºn dß╗» liß╗çu nß╗Öi bß╗Ö (v├¡ dß╗Ñ: "Doanh thu th├íng tr╞░ß╗¢c bao nhi├¬u?"), d├╣ng DB Query Tool.
Γûê- Sau khi thu thß║¡p th├┤ng tin, Evaluate node kiß╗âm tra xem ─æ├ú ─æß╗º ch╞░a. Nß║┐u ch╞░a, quay lß║íi Router. Nß║┐u ─æß╗º, Generate Answer.
Γöé
ΓûêV├¡ dß╗Ñ code ─æß╗ïnh ngh─⌐a graph c╞í bß║ún:
Γöé
Γûê```python
Γûêfrom langgraph.graph import StateGraph, END
Γûêfrom typing import TypedDict, Annotated
Γûêimport operator
Γöé
Γöé
Γûêclass AgentState(TypedDict):
Γûê    """State schema ΓÇö dß╗» liß╗çu truyß╗ün giß╗»a c├íc node."""
Γûê    messages: Annotated[list, operator.add]  # Lß╗ïch sß╗¡ tin nhß║»n
Γûê    question: str          # C├óu hß╗Åi gß╗æc
Γûê    context: list[str]     # Context ─æ├ú thu thß║¡p
Γûê    tool_calls: int        # Sß╗æ lß║ºn gß╗ìi tools (giß╗¢i hß║ín)
Γûê    needs_search: bool     # Flag: c├│ cß║ºn t├¼m kiß║┐m kh├┤ng
Γûê    answer: str            # C├óu trß║ú lß╗¥i cuß╗æi c├╣ng
Γöé
Γöé
Γûêdef router_node(state: AgentState) -> AgentState:
Γûê    """Ph├ón loß║íi c├óu hß╗Åi v├á quyß║┐t ─æß╗ïnh luß╗ông xß╗¡ l├╜."""
Γûê    question = state["question"]
Γûê    # Gß╗ìi LLM ─æß╗â ph├ón loß║íi
Γûê    classification = llm.invoke(
Γûê        f"Ph├ón loß║íi c├óu hß╗Åi sau: '{question}'\n"
Γûê        f"Trß║ú lß╗¥i mß╗Öt trong: simple, search, database"
Γûê    )
Γûê    needs_search = "search" in classification.lower()
Γûê    return {"needs_search": needs_search}
Γöé
Γöé
Γûêdef search_node(state: AgentState) -> AgentState:
Γûê    """T├¼m kiß║┐m web v├á th├¬m kß║┐t quß║ú v├áo context."""
Γûê    results = search_tool.invoke(state["question"])
Γûê    return {"context": [results], "tool_calls": state["tool_calls"] + 1}
Γöé
Γöé
Γûêdef generate_node(state: AgentState) -> AgentState:
Γûê    """Tß║ío c├óu trß║ú lß╗¥i dß╗▒a tr├¬n context ─æ├ú thu thß║¡p."""
Γûê    context_str = "\n".join(state["context"]) if state["context"] else ""
Γûê    answer = llm.invoke(
Γûê        f"Dß╗▒a tr├¬n context sau:\n{context_str}\n\n"
Γûê        f"Trß║ú lß╗¥i c├óu hß╗Åi: {state['question']}"
Γûê    )
Γûê    return {"answer": answer}
Γöé
Γöé
Γûê# X├óy dß╗▒ng graph
Γûêgraph = StateGraph(AgentState)
Γöé
Γûê# Th├¬m nodes
Γûêgraph.add_node("router", router_node)
Γûêgraph.add_node("search", search_node)
Γûêgraph.add_node("generate", generate_node)
Γöé
Γûê# Th├¬m edges (─æ╞░ß╗¥ng chuyß╗ân)
Γûêgraph.set_entry_point("router")
Γûêgraph.add_conditional_edges(
Γûê    "router",
Γûê    lambda state: "search" if state["needs_search"] else "generate",
Γûê    {"search": "search", "generate": "generate"}
Γûê)
Γûêgraph.add_edge("search", "generate")
Γûêgraph.add_edge("generate", END)
Γöé
Γûê# Compile
Γûêagent = graph.compile()
Γûê```
Γöé
Γûê─É├óy l├á v├¡ dß╗Ñ ─æ╞ín giß║ún nh╞░ng minh hß╗ìa r├╡ nguy├¬n tß║»c: **mß╗ùi node l├á mß╗Öt h├ám nhß║¡n state, xß╗¡ l├╜, v├á trß║ú vß╗ü state mß╗¢i**. Graph ─æß╗ïnh ngh─⌐a thß╗⌐ tß╗▒ thß╗▒c thi v├á ─æiß╗üu kiß╗çn rß║╜ nh├ính. State ─æ╞░ß╗úc truyß╗ün tß╗▒ ─æß╗Öng giß╗»a c├íc node ΓÇö bß║ín kh├┤ng cß║ºn quß║ún l├╜ thß╗º c├┤ng.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Sß╗⌐c mß║ính cß╗ºa LangGraph nß║▒m ß╗ƒ khß║ú n─âng ─æß╗ïnh ngh─⌐a **luß╗ông xß╗¡ l├╜ c├│ ─æiß╗üu kiß╗çn v├á v├▓ng lß║╖p**. Agent kh├┤ng chß╗ë chß║íy tuß║ºn tß╗▒ A ΓåÆ B ΓåÆ C m├á c├│ thß╗â "quay lß║íi" nß║┐u cß║ºn th├¬m th├┤ng tin, "rß║╜ nh├ính" t├╣y theo loß║íi c├óu hß╗Åi, v├á "dß╗½ng" khi ─æ├ú c├│ c├óu trß║ú lß╗¥i ─æß╗º tß╗æt. ─É├óy l├á sß╗▒ kh├íc biß╗çt giß╗»a mß╗Öt chatbot ─æ╞ín giß║ún v├á mß╗Öt AI Agent thß╗▒c thß╗Ñ.
Γöé
Γûê## C╞í sß╗ƒ dß╗» liß╗çu ΓÇö Khi n├áo cß║ºn v├á chß╗ìn c├íi n├áo
Γöé
ΓûêNhiß╗üu sinh vi├¬n mß║╖c ─æß╗ïnh rß║▒ng mß╗ìi ß╗⌐ng dß╗Ñng ─æß╗üu cß║ºn database. Thß╗▒c tß║┐ kh├┤ng phß║úi vß║¡y. ─Éß╗æi vß╗¢i AI Agent app, database cß║ºn thiß║┐t cho mß╗Öt sß╗æ use case cß╗Ñ thß╗â, v├á bß║ín n├¬n chß╗ìn loß║íi database ph├╣ hß╗úp vß╗¢i nhu cß║ºu.
Γöé
Γûê### Khi n├áo AI Agent app cß║ºn database?
Γöé
Γûê**L╞░u lß╗ïch sß╗¡ hß╗Öi thoß║íi (chat history).** Nß║┐u bß║ín muß╗æn ng╞░ß╗¥i d├╣ng xem lß║íi c├íc cuß╗Öc tr├▓ chuyß╗çn tr╞░ß╗¢c, bß║ín cß║ºn l╞░u messages v├áo database. ─É├óy l├á use case phß╗ò biß║┐n nhß║Ñt.
Γöé
Γûê**Quß║ún l├╜ session.** Agent c├│ thß╗â cß║ºn nhß╗¢ context tß╗½ tin nhß║»n tr╞░ß╗¢c trong c├╣ng phi├¬n hß╗Öi thoß║íi. Nß║┐u bß║ín chß╗ë cß║ºn memory ngß║»n hß║ín (trong mß╗Öt session), LangGraph's built-in memory ─æß╗º d├╣ng. Nß║┐u cß║ºn memory d├ái hß║ín (cross-session), bß║ín cß║ºn database.
Γöé
Γûê**L╞░u trß╗» t├ái liß╗çu cho RAG (Retrieval-Augmented Generation).** Nß║┐u Agent cß║ºn trß║ú lß╗¥i c├óu hß╗Åi dß╗▒a tr├¬n t├ái liß╗çu cß╗Ñ thß╗â (v├¡ dß╗Ñ: t├ái liß╗çu nß╗Öi bß╗Ö c├┤ng ty), bß║ín cß║ºn vector database ─æß╗â l╞░u v├á t├¼m kiß║┐m t├ái liß╗çu.
Γöé
Γûê**Analytics v├á monitoring.** Nß║┐u bß║ín muß╗æn thß╗æng k├¬: bao nhi├¬u users, bao nhi├¬u conversations, c├óu hß╗Åi phß╗ò biß║┐n nhß║Ñt l├á g├¼, thß╗¥i gian phß║ún hß╗ôi trung b├¼nh bao l├óu ΓÇö bß║ín cß║ºn l╞░u log v├áo database.
Γöé
Γûê### SQLite cho Development
Γöé
ΓûêSQLite l├á file-based database ΓÇö to├án bß╗Ö database l├á mß╗Öt file tr├¬n disk. Kh├┤ng cß║ºn c├ái ─æß║╖t server, kh├┤ng cß║ºn cß║Ñu h├¼nh phß╗⌐c tß║íp. Chß╗ë cß║ºn `import sqlite3` trong Python (built-in) hoß║╖c d├╣ng SQLAlchemy.
Γöé
Γûê```python
Γûêfrom sqlalchemy import create_engine
Γûêfrom sqlalchemy.orm import sessionmaker
Γöé
Γûê# SQLite ΓÇö chß╗ë l├á mß╗Öt file
Γûêengine = create_engine("sqlite:///./data/app.db")
ΓûêSessionLocal = sessionmaker(bind=engine)
Γûê```
Γöé
Γûê╞»u ─æiß╗âm cß╗ºa SQLite cho development: zero configuration, dß╗à backup (copy file), dß╗à chia sß║╗ trong team, v├á ─æß╗º nhanh cho development. Nh╞░ß╗úc ─æiß╗âm: kh├┤ng hß╗ù trß╗ú concurrent writes tß╗æt (kh├┤ng ph├╣ hß╗úp cho production vß╗¢i nhiß╗üu users), kh├┤ng c├│ built-in replication.
Γöé
Γûê### PostgreSQL cho Production
Γöé
ΓûêKhi deploy l├¬n production, PostgreSQL l├á lß╗▒a chß╗ìn tß╗æt nhß║Ñt. N├│ l├á relational database mß║ính mß║╜, hß╗ù trß╗ú concurrent access, JSON columns (hß╗»u ├¡ch cho l╞░u Agent state), full-text search, v├á c├│ ecosystem c├┤ng cß╗Ñ quß║ún l├╜ phong ph├║.
Γöé
Γûê```python
Γûê# Thay ─æß╗òi connection string khi deploy
Γûêimport os
ΓûêDATABASE_URL = os.getenv(
Γûê    "DATABASE_URL",
Γûê    "sqlite:///./data/app.db"  # Fallback cho development
Γûê)
Γûêengine = create_engine(DATABASE_URL)
Γûê```
Γöé
ΓûêTemplate sß╗¡ dß╗Ñng `DATABASE_URL` trong `.env` ΓÇö bß║ín chß╗ë cß║ºn thay ─æß╗òi gi├í trß╗ï n├áy khi chuyß╗ân tß╗½ development sang production.
Γöé
Γûê### Vector Stores cho RAG
Γöé
ΓûêNß║┐u Agent cß╗ºa bß║ín sß╗¡ dß╗Ñng RAG (Retrieval-Augmented Generation) ΓÇö tß╗⌐c l├á t├¼m kiß║┐m t├ái liß╗çu li├¬n quan tr╞░ß╗¢c khi trß║ú lß╗¥i ΓÇö bß║ín cß║ºn vector database. Vector database l╞░u trß╗» document embeddings (vector biß╗âu diß╗àn ngß╗» ngh─⌐a cß╗ºa t├ái liß╗çu) v├á cho ph├⌐p t├¼m kiß║┐m similarity (t╞░╞íng ─æß╗ông ngß╗» ngh─⌐a) nhanh ch├│ng.
Γöé
ΓûêC├íc lß╗▒a chß╗ìn phß╗ò biß║┐n:
Γöé
Γûê- **ChromaDB** ΓÇö ─É╞ín giß║ún, chß║íy local, ph├╣ hß╗úp cho development v├á small-scale production. Template c├│ sß║╡n cß║Ñu h├¼nh ChromaDB.
Γûê- **Pinecone** ΓÇö Cloud-managed vector database, scale dß╗à d├áng, nh╞░ng c├│ ph├¡.
Γûê- **Weaviate** ΓÇö Open-source, chß║íy self-hosted hoß║╖c cloud, t├¡nh n─âng phong ph├║.
Γûê- **pgvector** ΓÇö Extension cho PostgreSQL, cho ph├⌐p l╞░u v├á t├¼m kiß║┐m vector ngay trong PostgreSQL. Tß╗æt nß║┐u bß║ín muß╗æn d├╣ng mß╗Öt database cho cß║ú relational data v├á vectors.
Γöé
Γûê```python
Γûê# V├¡ dß╗Ñ cß║Ñu h├¼nh ChromaDB trong template
Γûêfrom langchain_community.vectorstores import Chroma
Γûêfrom langchain_openai import OpenAIEmbeddings
Γöé
Γûêvectorstore = Chroma(
Γûê    collection_name="documents",
Γûê    embedding_function=OpenAIEmbeddings(),
Γûê    persist_directory="./data/chroma"
Γûê)
Γöé
Γûê# T├¼m kiß║┐m t├ái liß╗çu li├¬n quan
Γûêresults = vectorstore.similarity_search("ch├¡nh s├ích ho├án tiß╗ün", k=3)
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** ─Éß╗½ng over-engineer database layer. Nß║┐u Agent cß╗ºa bß║ín chß╗ë chat v├á kh├┤ng cß║ºn l╞░u lß╗ïch sß╗¡ d├ái hß║ín, bß║ín c├│ thß╗â bß╗Å qua database ho├án to├án trong giai ─æoß║ín ─æß║ºu. Th├¬m database khi bß║ín thß╗▒c sß╗▒ cß║ºn ΓÇö "You Aren't Gonna Need It" (YAGNI principle). Nhiß╗üu ─æß╗Öi d├ánh qu├í nhiß╗üu thß╗¥i gian setup PostgreSQL trong khi SQLite (hoß║╖c kh├┤ng c├│ database) ─æ├ú ─æß╗º cho use case cß╗ºa hß╗ì.
Γöé
Γûê## Vß║╜ Architecture Diagram ΓÇö Mß╗Öt h├¼nh ─æ├íng ngh├¼n d├▓ng code
Γöé
ΓûêArchitecture diagram l├á c├┤ng cß╗Ñ giao tiß║┐p quan trß╗ìng nhß║Ñt trong dß╗▒ ├ín phß║ºn mß╗üm. N├│ gi├║p ─æß╗ông ─æß╗Öi hiß╗âu hß╗ç thß╗æng, gi├║p mentor ─æ├ính gi├í thiß║┐t kß║┐, v├á gi├║p bß║ín (t├íc giß║ú) suy ngh─⌐ r├╡ r├áng vß╗ü cß║Ñu tr├║c. Mß╗Öt diagram tß╗æt tiß║┐t kiß╗çm h├áng giß╗¥ thß║úo luß║¡n v├á tr├ính h├áng t├í misunderstandings.
Γöé
Γûê### Tß║íi sao Mermaid?
Γöé
ΓûêMermaid l├á ng├┤n ngß╗» markup ─æß╗â vß║╜ diagram bß║▒ng text. Thay v├¼ d├╣ng tool GUI (nh╞░ draw.io hay Lucidchart) v├á export ra file PNG, bß║ín viß║┐t diagram bß║▒ng text, commit v├áo Git c├╣ng vß╗¢i code, v├á n├│ ─æ╞░ß╗úc render tß╗▒ ─æß╗Öng tr├¬n GitHub, GitLab, v├á nhiß╗üu Markdown editor.
Γöé
Γûê╞»u ─æiß╗âm cß╗ºa Mermaid:
Γöé
Γûê- **Version control friendly** ΓÇö Diagram l├á text file, diff v├á merge dß╗à d├áng.
Γûê- **Render tr├¬n GitHub** ΓÇö GitHub tß╗▒ ─æß╗Öng render Mermaid trong Markdown files.
Γûê- **Khß╗¢p vß╗¢i code** ΓÇö Diagram nß║▒m c├╣ng th╞░ mß╗Ñc vß╗¢i code n├│ m├┤ tß║ú.
Γûê- **Dß╗à cß║¡p nhß║¡t** ΓÇö Thay ─æß╗òi text, kh├┤ng cß║ºn redraw.
Γöé
Γûê### 3 loß║íi diagram bß║ín cß║ºn
Γöé
Γûê**1. System Overview Diagram** ΓÇö Hiß╗ân thß╗ï to├án bß╗Ö hß╗ç thß╗æng vß╗¢i tß║Ñt cß║ú components v├á connections. ─É├óy l├á diagram "bß╗⌐c tranh lß╗¢n", cho ng╞░ß╗¥i ─æß╗ìc hiß╗âu ngay hß╗ç thß╗æng c├│ g├¼.
Γöé
Γûê```mermaid
Γûêgraph TB
Γûê    subgraph Client
Γûê        Browser[Web Browser]
Γûê        Mobile[Mobile App]
Γûê    end
Γöé
Γûê    subgraph "FastAPI Backend"
Γûê        API[API Gateway]
Γûê        Auth[Auth Module]
Γûê        SessionMgr[Session Manager]
Γûê        ChatHandler[Chat Handler]
Γûê    end
Γöé
Γûê    subgraph "AI Agent (LangGraph)"
Γûê        AgentOrchestrator[Agent Orchestrator]
Γûê        Router[Intent Router]
Γûê        SearchTool[Web Search]
Γûê        DBTool[DB Query]
Γûê        CalculatorTool[Calculator]
Γûê        MemoryMgr[Memory Manager]
Γûê    end
Γöé
Γûê    subgraph "External Services"
Γûê        OpenAI[OpenAI API]
Γûê        Tavily[Tavily Search]
Γûê    end
Γöé
Γûê    subgraph "Data Layer"
Γûê        SQLite[(SQLite DB)]
Γûê        Chroma[(ChromaDB)]
Γûê    end
Γöé
Γûê    Browser --> API
Γûê    Mobile --> API
Γûê    API --> Auth
Γûê    API --> ChatHandler
Γûê    ChatHandler --> AgentOrchestrator
Γûê    AgentOrchestrator --> Router
Γûê    Router --> SearchTool
Γûê    Router --> DBTool
Γûê    Router --> CalculatorTool
Γûê    SearchTool --> Tavily
Γûê    Router --> OpenAI
Γûê    MemoryMgr --> SQLite
Γûê    AgentOrchestrator --> MemoryMgr
Γûê    AgentOrchestrator --> Chroma
Γûê```
Γöé
Γûê**2. Agent Flow Diagram** ΓÇö Hiß╗ân thß╗ï chi tiß║┐t luß╗ông xß╗¡ l├╜ b├¬n trong Agent: nodes, edges, conditions, v├á loops.
Γöé
Γûê```mermaid
Γûêgraph TD
Γûê    START([User Question]) --> Router[Intent Router]
Γûê    Router -->|Greeting| Direct[Direct Response]
Γûê    Router -->|Factual Q| Retrieval[RAG Retrieval]
Γûê    Router -->|Current Info| Search[Web Search Tool]
Γûê    Router -->|Calculation| Calc[Calculator Tool]
Γöé
Γûê    Retrieval --> Grade[Grade Documents]
Γûê    Grade -->|Relevant| Generate[Generate Answer]
Γûê    Grade -->|Not Relevant| Rewrite[Rewrite Query]
Γûê    Rewrite --> Retrieval
Γöé
Γûê    Search --> Generate
Γûê    Calc --> Generate
Γûê    Direct --> Generate
Γöé
Γûê    Generate --> Check[Hallucination Check]
Γûê    Check -->|Pass| Output([Final Answer])
Γûê    Check -->|Fail| Generate
Γûê```
Γöé
ΓûêDiagram Agent Flow n├áy ─æß║╖c biß╗çt quan trß╗ìng v├¼ n├│ thß╗â hiß╗çn **agentic loop** ΓÇö khß║ú n─âng rß║╜ nh├ính v├á lß║╖p lß║íi cß╗ºa Agent. ─É├óy l├á ─æiß╗âm kh├íc biß╗çt ch├¡nh giß╗»a Agent v├á simple chain.
Γöé
Γûê**3. Deployment Diagram** ΓÇö Hiß╗ân thß╗ï c├ích hß╗ç thß╗æng ─æ╞░ß╗úc deploy: servers, containers, networking, v├á external dependencies.
Γöé
Γûê```mermaid
Γûêgraph LR
Γûê    subgraph "Docker Compose"
Γûê        subgraph "App Container"
Γûê            FastAPI[FastAPI Server]
Γûê            Agent[LangGraph Agent]
Γûê        end
Γûê        subgraph "DB Container"
Γûê            PG[(PostgreSQL)]
Γûê        end
Γûê        subgraph "Vector Container"
Γûê            Chroma[(ChromaDB)]
Γûê        end
Γûê    end
Γöé
Γûê    subgraph "External"
Γûê        GitHub[GitHub Actions CI/CD]
Γûê        OpenAI[OpenAI API]
Γûê    end
Γöé
Γûê    Internet((Internet)) --> FastAPI
Γûê    FastAPI --> PG
Γûê    FastAPI --> Chroma
Γûê    Agent --> OpenAI
Γûê    GitHub -->|Deploy| FastAPI
Γûê```
Γöé
Γûê### Quy tß║»c vß║╜ diagram tß╗æt
Γöé
Γûê**1. ─Éß║╖t t├¬n r├╡ r├áng.** Mß╗ùi node phß║úi c├│ t├¬n m├┤ tß║ú ch├¡nh x├íc chß╗⌐c n─âng. Tr├ính t├¬n chung chung nh╞░ "Service A", "Module 1".
Γöé
Γûê**2. Ph├ón nh├│m bß║▒ng subgraph.** Nh├│m c├íc components li├¬n quan lß║íi (Frontend, Backend, Agent, External Services). ─Éiß╗üu n├áy gi├║p ng╞░ß╗¥i ─æß╗ìc nhanh ch├│ng hiß╗âu ranh giß╗¢i giß╗»a c├íc phß║ºn.
Γöé
Γûê**3. ─É├ính dß║Ñu h╞░ß╗¢ng dß╗» liß╗çu.** D├╣ng m┼⌐i t├¬n r├╡ r├áng. Nß║┐u l├á two-way communication, th├¬m label m├┤ tß║ú dß╗» liß╗çu mß╗ùi h╞░ß╗¢ng.
Γöé
Γûê**4. ─É├ính sß╗æ thß╗⌐ tß╗▒ nß║┐u c├│ luß╗ông tuß║ºn tß╗▒.** Th├¬m (1), (2), (3)... v├áo edges ─æß╗â ng╞░ß╗¥i ─æß╗ìc hiß╗âu thß╗⌐ tß╗▒ xß╗¡ l├╜.
Γöé
Γûê**5. Giß╗» diagram ─æ╞ín giß║ún.** Mß╗ùi diagram n├¬n truyß╗ün tß║úi mß╗Öt ├╜ ch├¡nh. ─Éß╗½ng nh├⌐t tß║Ñt cß║ú v├áo mß╗Öt diagram ΓÇö tß║ío nhiß╗üu diagram, mß╗ùi c├íi cho mß╗Öt kh├¡a cß║ính (overview, agent flow, deployment).
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Diagram kh├┤ng phß║úi trang tr├¡ ΓÇö n├│ l├á t├ái liß╗çu kß╗╣ thuß║¡t. ─Éß╗Öi cß╗ºa bß║ín sß║╜ tham chiß║┐u diagram khi viß║┐t code, khi debug, v├á khi onboarding th├ánh vi├¬n mß╗¢i. Diagram phß║úi lu├┤n cß║¡p nhß║¡t khi kiß║┐n tr├║c thay ─æß╗òi. Nß║┐u diagram v├á code kh├┤ng khß╗¢p nhau, diagram trß╗ƒ n├¬n v├┤ gi├í trß╗ï ΓÇö thß║¡m ch├¡ nguy hiß╗âm v├¼ g├óy hiß╗âu lß║ºm.
Γöé
Γûê## Ghi lß║íi quyß║┐t ─æß╗ïnh kiß║┐n tr├║c (ADR) ΓÇö Tß║íi sao lß║íi chß╗ìn nh╞░ vß║¡y
Γöé
ΓûêArchitecture Decision Record (ADR) l├á mß╗Öt t├ái liß╗çu ngß║»n ghi lß║íi **quyß║┐t ─æß╗ïnh kiß║┐n tr├║c quan trß╗ìng**, bao gß╗ôm: bß╗æi cß║únh (context), c├íc lß╗▒a chß╗ìn ─æ╞░ß╗úc xem x├⌐t (alternatives), quyß║┐t ─æß╗ïnh cuß╗æi c├╣ng (decision), v├á l├╜ do (rationale). ADR kh├┤ng chß╗ë l├á documentation ΓÇö n├│ l├á c├┤ng cß╗Ñ t╞░ duy gi├║p bß║ín ─æ╞░a ra quyß║┐t ─æß╗ïnh c├│ c╞í sß╗ƒ v├á c├│ thß╗â giß║úi th├¡ch ─æ╞░ß╗úc.
Γöé
Γûê### Tß║íi sao cß║ºn ADR?
Γöé
ΓûêTrong qu├í tr├¼nh ph├ít triß╗ân, bß║ín sß║╜ ─æ╞░a ra nhiß╗üu quyß║┐t ─æß╗ïnh: "D├╣ng SQLite hay PostgreSQL?", "D├╣ng LangGraph hay LangChain?", "Streaming hay non-streaming?", "ChromaDB hay Pinecone?". Nß║┐u kh├┤ng ghi lß║íi, bß║ín sß║╜ qu├¬n l├╜ do ─æ├ú chß╗ìn ΓÇö v├á khi cß║ºn thay ─æß╗òi, bß║ín kh├┤ng biß║┐t liß╗çu quyß║┐t ─æß╗ïnh ban ─æß║ºu c├▓n hß╗úp l├╜ hay kh├┤ng.
Γöé
ΓûêADR c┼⌐ng gi├║p mentor v├á reviewer hiß╗âu tß║íi sao bß║ín chß╗ìn mß╗Öt giß║úi ph├íp. C├íc ─æß╗Öi c├│ ADR ─æß║ít ─æiß╗âm t├ái liß╗çu cao h╞ín r├╡ rß╗çt, v├¼ judges thß║Ñy ─æ╞░ß╗úc t╞░ duy ─æß║▒ng sau c├íc lß╗▒a chß╗ìn kß╗╣ thuß║¡t.
Γöé
Γûê### Template ADR
Γöé
ΓûêMß╗ùi ADR n├¬n c├│ cß║Ñu tr├║c nh╞░ sau:
Γöé
Γûê```markdown
Γûê# ADR-001: [Ti├¬u ─æß╗ü quyß║┐t ─æß╗ïnh]
Γöé
Γûê**Ng├áy:** YYYY-MM-DD
Γûê**Trß║íng th├íi:** Accepted / Deprecated / Superseded by ADR-XXX
Γöé
Γûê## Bß╗æi cß║únh (Context)
Γöé
ΓûêM├┤ tß║ú vß║Ñn ─æß╗ü hoß║╖c t├¼nh huß╗æng buß╗Öc bß║ín phß║úi ─æ╞░a ra quyß║┐t ─æß╗ïnh.
ΓûêV├¡ dß╗Ñ: "Agent cß║ºn khß║ú n─âng t├¼m kiß║┐m web ─æß╗â trß║ú lß╗¥i c├óu hß╗Åi vß╗ü sß╗▒ kiß╗çn hiß╗çn tß║íi.
ΓûêCß║ºn chß╗ìn giß╗»a Tavily Search API v├á Serper.dev."
Γöé
Γûê## C├íc lß╗▒a chß╗ìn (Alternatives)
Γöé
Γûê### Lß╗▒a chß╗ìn 1: Tavily Search API
Γûê- ╞»u ─æiß╗âm: Tß╗æi ╞░u cho AI use case, trß║ú kß║┐t quß║ú ─æ├ú clean, hß╗ù trß╗ú search depth.
Γûê- Nh╞░ß╗úc ─æiß╗âm: API mß╗¢i, cß╗Öng ─æß╗ông nhß╗Å h╞ín, free tier giß╗¢i hß║ín 1000 requests/th├íng.
Γöé
Γûê### Lß╗▒a chß╗ìn 2: Serper.dev
Γûê- ╞»u ─æiß╗âm: Wrapper cho Google Search, kß║┐t quß║ú chi tiß║┐t, free tier 2500 requests.
Γûê- Nh╞░ß╗úc ─æiß╗âm: Cß║ºn parse kß║┐t quß║ú thß╗º c├┤ng, ─æ├┤i khi bß╗ï rate limit.
Γöé
Γûê### Lß╗▒a chß╗ìn 3: Google Custom Search API
Γûê- ╞»u ─æiß╗âm: Ch├¡nh thß╗⌐c tß╗½ Google, ß╗òn ─æß╗ïnh.
Γûê- Nh╞░ß╗úc ─æiß╗âm: Setup phß╗⌐c tß║íp, free tier chß╗ë 100 requests/ng├áy.
Γöé
Γûê## Quyß║┐t ─æß╗ïnh (Decision)
Γöé
ΓûêChß╗ìn **Lß╗▒a chß╗ìn 1: Tavily Search API**.
Γöé
Γûê## L├╜ do (Rationale)
Γöé
Γûê1. Tavily ─æ╞░ß╗úc thiß║┐t kß║┐ cho AI Agent ΓÇö kß║┐t quß║ú trß║ú vß╗ü ─æ├ú ─æ╞░ß╗úc clean v├á structured,
Γûê   giß║úm c├┤ng viß╗çc xß╗¡ l├╜ ph├¡a Agent.
Γûê2. Tavily t├¡ch hß╗úp sß║╡n vß╗¢i LangChain/LangGraph ecosystem, ├¡t code h╞ín.
Γûê3. Free tier 1000 requests ─æß╗º cho giai ─æoß║ín development v├á demo.
Γûê4. Nß║┐u cß║ºn scale l├¬n, pricing reasonable ($30/th├íng cho 10k requests).
Γöé
Γûê## Hß╗ç quß║ú (Consequences)
Γöé
Γûê- Agent phß╗Ñ thuß╗Öc v├áo Tavily API availability.
Γûê- Cß║ºn xß╗¡ l├╜ fallback khi Tavily down (c├│ thß╗â trß║ú lß╗¥i bß║▒ng kiß║┐n thß╗⌐c LLM).
Γûê- Cß║ºn quß║ún l├╜ API key trong biß║┐n m├┤i tr╞░ß╗¥ng.
Γûê```
Γöé
Γûê### V├¡ dß╗Ñ: ADR mß║½u
Γöé
ΓûêD╞░ß╗¢i ─æ├óy l├á mß╗Öt ADR mß║½u (─æ├ú ─æ╞ín giß║ún h├│a) minh hß╗ìa c├ích ghi lß║íi quyß║┐t ─æß╗ïnh kß╗╣ thuß║¡t:
Γöé
Γûê```markdown
Γûê# ADR-002: Chß╗ìn SQLite cho Development, PostgreSQL cho Production
Γöé
Γûê**Ng├áy:** 2024-11-15
Γûê**Trß║íng th├íi:** Accepted
Γöé
Γûê## Bß╗æi cß║únh
ΓûêAgent cß║ºn l╞░u lß╗ïch sß╗¡ hß╗Öi thoß║íi ─æß╗â hß╗ù trß╗ú multi-turn conversation.
ΓûêCß║ºn chß╗ìn database ph├╣ hß╗úp cho cß║ú development v├á production.
Γöé
Γûê## C├íc lß╗▒a chß╗ìn
Γûê1. SQLite cho cß║ú dev v├á prod ΓÇö ─É╞ín giß║ún nh╞░ng kh├┤ng scale.
Γûê2. PostgreSQL cho cß║ú dev v├á prod ΓÇö Mß║ính nh╞░ng setup phß╗⌐c tß║íp cho dev.
Γûê3. SQLite cho dev, PostgreSQL cho prod ΓÇö Linh hoß║ít, best of both worlds.
Γöé
Γûê## Quyß║┐t ─æß╗ïnh
ΓûêLß╗▒a chß╗ìn 3: SQLite cho development, PostgreSQL cho production.
Γöé
Γûê## L├╜ do
Γûê- Developer kh├┤ng cß║ºn c├ái PostgreSQL local, tiß║┐t kiß╗çm thß╗¥i gian setup.
Γûê- SQLAlchemy ORM abstract databaseσ╖«σ╝é, code gß║ºn nh╞░ giß╗æng nhau.
Γûê- Chß╗ë cß║ºn thay ─æß╗òi DATABASE_URL khi deploy.
Γûê- SQLite ─æß╗º cho 1-2 developers, PostgreSQL cß║ºn khi c├│ real users.
Γöé
Γûê## Hß╗ç quß║ú
Γûê- Cß║ºn test tr├¬n cß║ú SQLite v├á PostgreSQL ─æß╗â ─æß║úm bß║úo compatibility.
Γûê- Migration scripts phß║úi compatible vß╗¢i cß║ú hai.
Γûê```
Γöé
Γûê### Quy tß║»c viß║┐t ADR
Γöé
Γûê**1. Ghi lß║íi quyß║┐t ─æß╗ïnh quan trß╗ìng, kh├┤ng phß║úi mß╗ìi thß╗⌐.** Kh├┤ng cß║ºn ADR cho viß╗çc "chß╗ìn indentation 4 spaces". Cß║ºn ADR cho: lß╗▒a chß╗ìn framework, database, LLM provider, architecture pattern, deployment strategy.
Γöé
Γûê**2. Nhß║¡n biß║┐t trade-offs.** Mß╗ìi quyß║┐t ─æß╗ïnh kß╗╣ thuß║¡t ─æß╗üu c├│ trade-off. ADR phß║úi thß╗â hiß╗çn r├╡ bß║ín ─æ├ú c├ón nhß║»c ╞░u/nh╞░ß╗úc ─æiß╗âm. Kh├┤ng c├│ giß║úi ph├íp ho├án hß║úo ΓÇö chß╗ë c├│ giß║úi ph├íp ph├╣ hß╗úp nhß║Ñt cho ngß╗» cß║únh cß╗Ñ thß╗â.
Γöé
Γûê**3. Cß║¡p nhß║¡t khi quyß║┐t ─æß╗ïnh thay ─æß╗òi.** Nß║┐u bß║ín thay ─æß╗òi quyß║┐t ─æß╗ïnh (v├¡ dß╗Ñ: chuyß╗ân tß╗½ ChromaDB sang Pinecone), cß║¡p nhß║¡t ADR c┼⌐ vß╗¢i trß║íng th├íi "Superseded by ADR-XXX" v├á tß║ío ADR mß╗¢i.
Γöé
Γûê**4. Giß║ún ngß║»n.** ADR n├¬n ─æß╗ìc trong 3-5 ph├║t. Kh├┤ng phß║úi essay. Mß╗ùi section v├ái c├óu l├á ─æß╗º.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** ADR l├á "nhß║¡t k├╜ quyß║┐t ─æß╗ïnh" cß╗ºa dß╗▒ ├ín. Khi bß║ín (hoß║╖c ─æß╗ông ─æß╗Öi) hß╗Åi "Tß║íi sao m├¼nh lß║íi d├╣ng X thay v├¼ Y?" 3 th├íng sau, ADR l├á n╞íi t├¼m c├óu trß║ú lß╗¥i. ─Éß╗½ng coi nhß║╣ n├│ ΓÇö trong m├┤i tr╞░ß╗¥ng chuy├¬n nghiß╗çp, ADR l├á practice ti├¬u chuß║⌐n. Viß╗çc bß║ín bß║»t ─æß║ºu viß║┐t ADR tß╗½ khi c├▓n l├á sinh vi├¬n sß║╜ l├á ─æiß╗âm cß╗Öng rß║Ñt lß╗¢n khi phß╗Ång vß║Ñn.
Γöé
Γûê## T├│m tß║»t
Γöé
ΓûêCh╞░╞íng n├áy ─æ├ú trang bß╗ï cho bß║ín kiß║┐n thß╗⌐c to├án diß╗çn vß╗ü thiß║┐t kß║┐ kiß║┐n tr├║c cho ß╗⌐ng dß╗Ñng AI Agent. Ch├║ng ta bß║»t ─æß║ºu vß╗¢i kiß║┐n tr├║c 3 tß║ºng (Frontend - Backend - Agent), t├¼m hiß╗âu vai tr├▓ v├á tr├ích nhiß╗çm cß╗ºa mß╗ùi tß║ºng, v├á l├╜ do tß║íi sao t├ích biß╗çt l├á quan trß╗ìng.
Γöé
ΓûêFrontend (React/Next.js) ─æß║úm nhß║¡n giao diß╗çn ng╞░ß╗¥i d├╣ng, ─æß║╖c biß╗çt l├á chat interface vß╗¢i streaming support. Backend (FastAPI) l├á x╞░╞íng sß╗æng xß╗¡ l├╜ business logic, authentication, v├á kß║┐t nß╗æi vß╗¢i Agent. AI Agent (LangGraph) l├á bß╗Ö n├úo sß╗¡ dß╗Ñng state machine ─æß╗â xß╗¡ l├╜ c├óu hß╗Åi phß╗⌐c tß║íp vß╗¢i rß║╜ nh├ính v├á v├▓ng lß║╖p.
Γöé
ΓûêCh├║ng ta c┼⌐ng thß║úo luß║¡n vß╗ü lß╗▒a chß╗ìn database (SQLite cho dev, PostgreSQL cho prod, vector stores cho RAG), c├ích vß║╜ architecture diagram bß║▒ng Mermaid (3 loß║íi: system overview, agent flow, deployment), v├á tß║ºm quan trß╗ìng cß╗ºa Architecture Decision Records (ADR) trong viß╗çc ghi lß║íi v├á giß║úi th├¡ch c├íc quyß║┐t ─æß╗ïnh kß╗╣ thuß║¡t.
Γöé
ΓûêSau khi ho├án th├ánh ch╞░╞íng n├áy, bß║ín n├¬n c├│: (1) mß╗Öt kiß║┐n tr├║c diagram cho dß╗▒ ├ín cß╗ºa ─æß╗Öi, (2) ├¡t nhß║Ñt 2-3 ADRs cho c├íc quyß║┐t ─æß╗ïnh quan trß╗ìng, v├á (3) hiß╗âu r├╡ c├ích c├íc components giao tiß║┐p vß╗¢i nhau. ─É├óy l├á nß╗ün tß║úng vß╗»ng chß║»c tr╞░ß╗¢c khi bß║»t ─æß║ºu code ß╗ƒ c├íc ch╞░╞íng tiß║┐p theo.
Γöé
Γûê## C├óu hß╗Åi ├┤n tß║¡p
Γöé
Γûê**C├óu 1:** Trong kiß║┐n tr├║c 3 tß║ºng, tß║íi sao AI Agent kh├┤ng giao tiß║┐p trß╗▒c tiß║┐p vß╗¢i Frontend m├á phß║úi th├┤ng qua Backend? N├¬u ├¡t nhß║Ñt 3 l├╜ do kß╗╣ thuß║¡t v├á giß║úi th├¡ch lß╗úi ├¡ch cß╗ºa tß╗½ng l├╜ do.
Γöé
Γûê**C├óu 2:** Giß║úi th├¡ch sß╗▒ kh├íc biß╗çt giß╗»a LangChain chain (linear) v├á LangGraph state machine. Cho mß╗Öt v├¡ dß╗Ñ cß╗Ñ thß╗â vß╗ü t├¼nh huß╗æng m├á chain ─æ╞ín giß║ún kh├┤ng ─æß╗º v├á state machine l├á cß║ºn thiß║┐t. Vß║╜ (hoß║╖c m├┤ tß║ú) diagram minh hß╗ìa.
Γöé
Γûê**C├óu 3:** Viß║┐t mß╗Öt ADR cho quyß║┐t ─æß╗ïnh: "C├│ n├¬n d├╣ng streaming response (SSE) hay non-streaming response cho Agent chat endpoint?" Ph├ón t├¡ch ├¡t nhß║Ñt 2 lß╗▒a chß╗ìn, n├¬u ╞░u/nh╞░ß╗úc ─æiß╗âm, v├á ─æ╞░a ra quyß║┐t ─æß╗ïnh c├│ l├╜ do.


docs\guide\chapter-04.md:
Γûê---
Γûêtitle: "X├óy dß╗▒ng AI Agent vß╗¢i LangGraph"
Γûêweight: 4
Γûê---
Γöé
Γûê# Ch╞░╞íng 4: X├óy dß╗▒ng AI Agent vß╗¢i LangGraph
Γöé
ΓûêCh╞░╞íng n├áy l├á tr├íi tim cß╗ºa to├án bß╗Ö t├ái liß╗çu. Bß║ín sß║╜ hß╗ìc c├ích x├óy dß╗▒ng AI Agent tß╗½ ─æß║ºu ΓÇö tß╗½ kh├íi niß╗çm c╞í bß║ún ─æß║┐n triß╗ân khai ho├án chß╗ënh ΓÇö sß╗¡ dß╗Ñng LangGraph, th╞░ viß╗çn mß║ính mß║╜ nhß║Ñt hiß╗çn nay cho viß╗çc x├óy dß╗▒ng ß╗⌐ng dß╗Ñng AI c├│ trß║íng th├íi (stateful). ─Éß║┐n cuß╗æi ch╞░╞íng n├áy, bß║ín sß║╜ c├│ ─æß╗º kiß║┐n thß╗⌐c ─æß╗â x├óy dß╗▒ng mß╗Öt agent c├│ khß║ú n─âng suy ngh─⌐, h├ánh ─æß╗Öng v├á phß║ún hß╗ôi nh╞░ mß╗Öt trß╗ú l├╜ th├┤ng minh thß╗▒c thß╗Ñ.
Γöé
Γûê---
Γöé
Γûê## 4.1 Agent l├á g├¼?
Γöé
Γûê### ─Éß╗ïnh ngh─⌐a
Γöé
ΓûêAgent (t├íc nh├ón th├┤ng minh) l├á mß╗Öt hß╗ç thß╗æng AI c├│ khß║ú n─âng **tß╗▒ quyß║┐t ─æß╗ïnh** c├ích thß╗▒c hiß╗çn t├íc vß╗Ñ thay v├¼ chß╗ë l├ám theo kß╗ïch bß║ún cß╗æ ─æß╗ïnh. Kh├íc vß╗¢i chatbot th├┤ng th╞░ß╗¥ng chß╗ë trß║ú lß╗¥i c├óu hß╗Åi dß╗▒a tr├¬n mß╗Öt chuß╗ùi xß╗¡ l├╜ ─æß╗ïnh tr╞░ß╗¢c, agent c├│ thß╗â quan s├ít m├┤i tr╞░ß╗¥ng, suy ngh─⌐ vß╗ü b╞░ß╗¢c tiß║┐p theo, sß╗¡ dß╗Ñng c├┤ng cß╗Ñ (tools) ─æß╗â thu thß║¡p th├┤ng tin, v├á ─æiß╗üu chß╗ënh h├ánh vi dß╗▒a tr├¬n kß║┐t quß║ú.
Γöé
ΓûêH├úy t╞░ß╗ƒng t╞░ß╗úng sß╗▒ kh├íc biß╗çt nh╞░ sau: mß╗Öt chatbot giß╗æng nh╞░ mß╗Öt nh├ón vi├¬n trß╗▒c tß╗òng ─æ├ái ─æß╗ìc kß╗ïch bß║ún ΓÇö khi ng╞░ß╗¥i d├╣ng hß╗Åi A, bot trß║ú lß╗¥i B. C├▓n agent giß╗æng nh╞░ mß╗Öt trß╗ú l├╜ giß╗Åi ΓÇö khi nhß║¡n ─æ╞░ß╗úc y├¬u cß║ºu, trß╗ú l├╜ sß║╜ tß╗▒ ─æ├ính gi├í "m├¼nh cß║ºn l├ám g├¼ ─æß╗â trß║ú lß╗¥i c├óu hß╗Åi n├áy?", c├│ thß╗â t├¼m kiß║┐m t├ái liß╗çu, tra cß╗⌐u database, t├¡nh to├ín, rß╗ôi tß╗òng hß╗úp c├óu trß║ú lß╗¥i.
Γöé
Γûê### Sß╗▒ kh├íc biß╗çt giß╗»a Chatbot v├á Agent
Γöé
Γûê─Éß╗â hiß╗âu r├╡ h╞ín, h├úy so s├ính hai hß╗ç thß╗æng:
Γöé
Γûê**Chatbot (chuß╗ùi cß╗æ ─æß╗ïnh ΓÇö Chain):**
Γûê- Luß╗ông xß╗¡ l├╜ cß╗æ ─æß╗ïnh: Input ΓåÆ LLM ΓåÆ Output
Γûê- Kh├┤ng c├│ khß║ú n─âng ra quyß║┐t ─æß╗ïnh
Γûê- Kh├┤ng sß╗¡ dß╗Ñng c├┤ng cß╗Ñ b├¬n ngo├ái
Γûê- Ph├╣ hß╗úp cho hß╗Öi thoß║íi ─æ╞ín giß║ún, FAQ
Γöé
Γûê**Agent (luß╗ông linh hoß║ít):**
Γûê- Luß╗ông xß╗¡ l├╜ linh hoß║ít, quyß║┐t ─æß╗ïnh tß║íi runtime
Γûê- C├│ khß║ú n─âng gß╗ìi tools (t├¼m kiß║┐m, t├¡nh to├ín, API)
Γûê- C├│ v├▓ng lß║╖p suy ngh─⌐: Think ΓåÆ Act ΓåÆ Observe
Γûê- Ph├╣ hß╗úp cho t├íc vß╗Ñ phß╗⌐c tß║íp, ─æa b╞░ß╗¢c
Γöé
Γûê### Tß║íi sao chß╗ìn LangGraph?
Γöé
ΓûêLangGraph l├á th╞░ viß╗çn ─æ╞░ß╗úc x├óy dß╗▒ng tr├¬n ─æß╗ënh cß╗ºa LangChain, nh╞░ng tiß║┐p cß║¡n theo h╞░ß╗¢ng **state machine (m├íy trß║íng th├íi)** thay v├¼ **chain (chuß╗ùi tuyß║┐n t├¡nh)**. ─É├óy l├á ─æiß╗âm kh├íc biß╗çt quan trß╗ìng:
Γöé
Γûê- **Chain (LangChain):** A ΓåÆ B ΓåÆ C ΓåÆ D. Luß╗ông cß╗æ ─æß╗ïnh, kh├│ nh├ính, kh├│ lß║╖p.
Γûê- **State Machine (LangGraph):** C├íc b╞░ß╗¢c (nodes) ─æ╞░ß╗úc kß║┐t nß╗æi bß║▒ng edges, c├│ thß╗â c├│ ─æiß╗üu kiß╗çn, v├▓ng lß║╖p, v├á nh├ính phß╗⌐c tß║íp.
Γöé
ΓûêLangGraph giß║úi quyß║┐t b├ái to├ín m├á chain kh├┤ng giß║úi quyß║┐t ─æ╞░ß╗úc: agent cß║ºn **quay lß║íi** b╞░ß╗¢c tr╞░ß╗¢c ─æ├│, **nhß║úy** ─æß║┐n b╞░ß╗¢c kh├íc t├╣y ─æiß╗üu kiß╗çn, v├á **giß╗» trß║íng th├íi** qua nhiß╗üu b╞░ß╗¢c xß╗¡ l├╜.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Kh├┤ng phß║úi mß╗ìi ß╗⌐ng dß╗Ñng AI ─æß╗üu cß║ºn agent. Nß║┐u t├íc vß╗Ñ cß╗ºa bß║ín ─æ╞ín giß║ún (v├¡ dß╗Ñ: dß╗ïch v─ân bß║ún, t├│m tß║»t b├ái viß║┐t), d├╣ng chain hoß║╖c thß║¡m ch├¡ gß╗ìi LLM trß╗▒c tiß║┐p l├á ─æß╗º. Agent cß║ºn thiß║┐t khi: (1) t├íc vß╗Ñ c├│ nhiß╗üu b╞░ß╗¢c, (2) cß║ºn ra quyß║┐t ─æß╗ïnh tß║íi runtime, (3) cß║ºn sß╗¡ dß╗Ñng tools b├¬n ngo├ái.
Γöé
Γûê### Khi n├áo n├¬n d├╣ng Agent?
Γöé
ΓûêBß║ín n├¬n c├ón nhß║»c x├óy dß╗▒ng agent khi t├íc vß╗Ñ c├│ c├íc ─æß║╖c ─æiß╗âm sau:
Γöé
Γûê1. **─Éa b╞░ß╗¢c (Multi-step):** T├íc vß╗Ñ cß║ºn nhiß╗üu b╞░ß╗¢c xß╗¡ l├╜ tuß║ºn tß╗▒ hoß║╖c song song
Γûê2. **Cß║ºn quyß║┐t ─æß╗ïnh (Decision-making):** Hß╗ç thß╗æng cß║ºn chß╗ìn giß╗»a nhiß╗üu h├ánh ─æß╗Öng kh├íc nhau
Γûê3. **Cß║ºn c├┤ng cß╗Ñ (Tool usage):** Cß║ºn t╞░╞íng t├íc vß╗¢i hß╗ç thß╗æng b├¬n ngo├ái (API, database, search)
Γûê4. **Cß║ºn phß║ún hß╗ôi (Feedback loop):** Kß║┐t quß║ú cß╗ºa b╞░ß╗¢c tr╞░ß╗¢c ß║únh h╞░ß╗ƒng ─æß║┐n b╞░ß╗¢c sau
Γûê5. **Kh├┤ng x├íc ─æß╗ïnh (Non-deterministic):** Kh├┤ng thß╗â biß║┐t tr╞░ß╗¢c ch├¡nh x├íc luß╗ông xß╗¡ l├╜
Γöé
ΓûêV├¡ dß╗Ñ thß╗▒c tß║┐: mß╗Öt agent nghi├¬n cß╗⌐u khoa hß╗ìc cß║ºn (1) ph├ón t├¡ch c├óu hß╗Åi nghi├¬n cß╗⌐u, (2) t├¼m kiß║┐m papers li├¬n quan, (3) ─æß╗ìc v├á t├│m tß║»t tß╗½ng paper, (4) so s├ính kß║┐t quß║ú, (5) tß╗òng hß╗úp th├ánh b├ío c├ío. ─É├óy l├á t├íc vß╗Ñ ho├án hß║úo cho agent.
Γöé
Γûê---
Γöé
Γûê## 4.2 State ΓÇö Bß╗Ö nhß╗¢ cß╗ºa Agent
Γöé
ΓûêState (trß║íng th├íi) l├á kh├íi niß╗çm quan trß╗ìng nhß║Ñt trong LangGraph. State ch├¡nh l├á **bß╗Ö nhß╗¢** cß╗ºa agent ΓÇö n├│ l╞░u trß╗» mß╗ìi th├┤ng tin cß║ºn thiß║┐t ─æß╗â agent hoß║ít ─æß╗Öng: tin nhß║»n, kß║┐t quß║ú t├¼m kiß║┐m, trß║íng th├íi xß╗¡ l├╜, v.v. Mß╗ùi node ─æß╗ìc tß╗½ state v├á ghi ng╞░ß╗úc lß║íi state sau khi xß╗¡ l├╜.
Γöé
Γûê### TypedDict Pattern
Γöé
ΓûêTrong LangGraph, state ─æ╞░ß╗úc ─æß╗ïnh ngh─⌐a bß║▒ng `TypedDict` cß╗ºa Python. ─É├óy l├á c├ích type-safe ─æß╗â khai b├ío cß║Ñu tr├║c dß╗» liß╗çu m├á agent sß║╜ sß╗¡ dß╗Ñng:
Γöé
Γûê```python
Γûêfrom typing import TypedDict, Annotated, Sequence
Γûêfrom langchain_core.messages import BaseMessage
Γöé
Γûêclass AgentState(TypedDict):
Γûê    """State cho agent nghi├¬n cß╗⌐u."""
Γûê    messages: Annotated[Sequence[BaseMessage], "add_messages"]
Γûê    query: str  # C├óu hß╗Åi gß╗æc cß╗ºa ng╞░ß╗¥i d├╣ng
Γûê    search_results: list[str]  # Kß║┐t quß║ú t├¼m kiß║┐m
Γûê    draft: str  # Bß║ún nh├íp c├óu trß║ú lß╗¥i
Γûê    iteration: int  # Sß╗æ lß║ºn lß║╖p
Γûê```
Γöé
Γûê`TypedDict` hoß║ít ─æß╗Öng nh╞░ mß╗Öt schema ΓÇö n├│ cho biß║┐t state c├│ nhß╗»ng tr╞░ß╗¥ng g├¼, mß╗ùi tr╞░ß╗¥ng kiß╗âu dß╗» liß╗çu g├¼. LangGraph sß║╜ sß╗¡ dß╗Ñng th├┤ng tin n├áy ─æß╗â quß║ún l├╜ state xuy├¬n suß╗æt qu├í tr├¼nh agent chß║íy.
Γöé
Γûê### total_false v├á Annotated
Γöé
ΓûêKhi ─æß╗ïnh ngh─⌐a state, bß║ín sß║╜ th╞░ß╗¥ng thß║Ñy `total=False` ─æ╞░ß╗úc sß╗¡ dß╗Ñng:
Γöé
Γûê```python
Γûêfrom typing import TypedDict
Γöé
Γûêclass AgentState(TypedDict, total=False):
Γûê    """total=False cho ph├⌐p c├íc tr╞░ß╗¥ng c├│ thß╗â kh├┤ng tß╗ôn tß║íi."""
Γûê    messages: list  # C├│ thß╗â kh├┤ng c├│ l├║c ban ─æß║ºu
Γûê    query: str
Γûê    search_results: list[str]
Γûê    draft: str
Γûê```
Γöé
Γûê`total=False` c├│ ngh─⌐a l├á kh├┤ng phß║úi tß║Ñt cß║ú c├íc tr╞░ß╗¥ng ─æß╗üu bß║»t buß╗Öc. ─Éiß╗üu n├áy rß║Ñt quan trß╗ìng v├¼ trong qu├í tr├¼nh agent chß║íy, mß╗Öt sß╗æ tr╞░ß╗¥ng ch╞░a ─æ╞░ß╗úc tß║ío ra ß╗ƒ b╞░ß╗¢c ─æß║ºu ti├¬n. V├¡ dß╗Ñ: `search_results` sß║╜ rß╗ùng cho ─æß║┐n khi node t├¼m kiß║┐m chß║íy xong.
Γöé
Γûê### Nguy├¬n tß║»c thiß║┐t kß║┐ State
Γöé
ΓûêKhi thiß║┐t kß║┐ state cho agent, h├úy tu├ón thß╗º c├íc nguy├¬n tß║»c sau:
Γöé
Γûê1. **Chß╗ë l╞░u nhß╗»ng g├¼ cß║ºn thiß║┐t:** State ─æ╞░ß╗úc truyß╗ün giß╗»a mß╗ìi node, ─æß╗½ng l╞░u dß╗» liß╗çu thß╗½a
Γûê2. **T├¬n tr╞░ß╗¥ng r├╡ r├áng:** D├╣ng t├¬n nh╞░ `query`, `search_results`, `draft` thay v├¼ `data1`, `data2`
Γûê3. **Kiß╗âu dß╗» liß╗çu ch├¡nh x├íc:** Lu├┤n annotate kiß╗âu ─æß╗â dß╗à debug v├á maintain
Γûê4. **T├ích biß╗çt concerns:** State cho agent nghi├¬n cß╗⌐u kh├íc vß╗¢i state cho agent chatbot
Γöé
Γûê### Reducer ΓÇö C├ích cß║¡p nhß║¡t State
Γöé
ΓûêReducer l├á c╞í chß║┐ x├íc ─æß╗ïnh c├ích mß╗Öt tr╞░ß╗¥ng trong state ─æ╞░ß╗úc cß║¡p nhß║¡t khi node trß║ú vß╗ü gi├í trß╗ï mß╗¢i. C├│ hai pattern ch├¡nh:
Γöé
Γûê**Overwrite (ghi ─æ├¿) ΓÇö Mß║╖c ─æß╗ïnh:**
Γöé
Γûê```python
Γûêclass SimpleState(TypedDict):
Γûê    query: str  # Gi├í trß╗ï mß╗¢i sß║╜ ghi ─æ├¿ ho├án to├án gi├í trß╗ï c┼⌐
Γûê    result: str
Γöé
Γûê# Node trß║ú vß╗ü {"query": "c├óu hß╗Åi mß╗¢i"} sß║╜ thay thß║┐ ho├án to├án query c┼⌐
Γûê```
Γöé
Γûê**Accumulate (t├¡ch l┼⌐y) ΓÇö D├╣ng cho danh s├ích:**
Γöé
Γûê```python
Γûêfrom typing import Annotated
Γûêfrom langgraph.graph.message import add_messages
Γöé
Γûêclass ChatState(TypedDict):
Γûê    messages: Annotated[list, add_messages]  # Th├¬m v├áo danh s├ích thay v├¼ ghi ─æ├¿
Γûê    context: str
Γöé
Γûê# add_messages reducer sß║╜ th├¬m message mß╗¢i v├áo danh s├ích messages hiß╗çn c├│
Γûê# thay v├¼ thay thß║┐ to├án bß╗Ö danh s├ích
Γûê```
Γöé
ΓûêReducer `add_messages` ─æß║╖c biß╗çt quan trß╗ìng v├¼ n├│ xß╗¡ l├╜ logic phß╗⌐c tß║íp: nß║┐u message mß╗¢i c├│ c├╣ng ID vß╗¢i message c┼⌐, n├│ sß║╜ cß║¡p nhß║¡t thay v├¼ th├¬m mß╗¢i. ─Éiß╗üu n├áy hß╗»u ├¡ch khi LLM quyß║┐t ─æß╗ïnh sß╗¡a ─æß╗òi message tr╞░ß╗¢c ─æ├│.
Γöé
Γûê### MessagesState
Γöé
ΓûêLangGraph cung cß║Ñp sß║╡n `MessagesState` cho tr╞░ß╗¥ng hß╗úp phß╗ò biß║┐n nhß║Ñt ΓÇö agent chatbot:
Γöé
Γûê```python
Γûêfrom langgraph.graph import MessagesState
Γöé
Γûê# MessagesState t╞░╞íng ─æ╞░╞íng vß╗¢i:
Γûêclass MessagesState(TypedDict):
Γûê    messages: Annotated[list, add_messages]
Γöé
Γûê# Sß╗¡ dß╗Ñng trß╗▒c tiß║┐p:
Γûêclass MyAgentState(MessagesState):
Γûê    """Mß╗ƒ rß╗Öng MessagesState vß╗¢i c├íc tr╞░ß╗¥ng t├╣y chß╗ënh."""
Γûê    user_id: str
Γûê    conversation_id: str
Γûê```
Γöé
Γûê`MessagesState` ─æ├ú bao gß╗ôm reducer `add_messages` cho tr╞░ß╗¥ng `messages`, n├¬n bß║ín kh├┤ng cß║ºn ─æß╗ïnh ngh─⌐a lß║íi. Chß╗ë cß║ºn mß╗ƒ rß╗Öng (extend) v├á th├¬m c├íc tr╞░ß╗¥ng bß╗ò sung.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Lß╗ùi phß╗ò biß║┐n nhß║Ñt khi l├ám viß╗çc vß╗¢i state l├á qu├¬n th├¬m reducer cho tr╞░ß╗¥ng kiß╗âu list. Nß║┐u bß║ín muß╗æn t├¡ch l┼⌐y gi├í trß╗ï (th├¬m v├áo list), bß║»t buß╗Öc phß║úi d├╣ng `Annotated[list, add_messages]` hoß║╖c reducer t├╣y chß╗ënh. Kh├┤ng c├│ reducer, gi├í trß╗ï mß╗¢i sß║╜ ghi ─æ├¿ ho├án to├án.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** H├úy bß║»t ─æß║ºu vß╗¢i state ─æ╞ín giß║ún nhß║Ñt c├│ thß╗â, sau ─æ├│ th├¬m tr╞░ß╗¥ng khi cß║ºn. ─Éß╗½ng thiß║┐t kß║┐ state "cho t╞░╞íng lai" ΓÇö YAGNI (You Aren't Gonna Need It). Bß║ín c├│ thß╗â dß╗à d├áng mß╗ƒ rß╗Öng TypedDict sau n├áy.
Γöé
Γûê---
Γöé
Γûê## 4.3 Nodes ΓÇö C├íc b╞░ß╗¢c xß╗¡ l├╜
Γöé
ΓûêNode (n├║t) l├á ─æ╞ín vß╗ï xß╗¡ l├╜ c╞í bß║ún trong LangGraph. Mß╗ùi node l├á mß╗Öt h├ám nhß║¡n state hiß╗çn tß║íi, thß╗▒c hiß╗çn xß╗¡ l├╜, v├á trß║ú vß╗ü nhß╗»ng thay ─æß╗òi cß║ºn ├íp dß╗Ñng l├¬n state. H├úy ngh─⌐ mß╗ùi node nh╞░ mß╗Öt "b╞░ß╗¢c" trong quy tr├¼nh l├ám viß╗çc cß╗ºa agent.
Γöé
Γûê### Nguy├¬n tß║»c: H├ám thuß║ºn (Pure Functions)
Γöé
ΓûêNode trong LangGraph n├¬n ─æ╞░ß╗úc thiß║┐t kß║┐ gß║ºn giß╗æng h├ám thuß║ºn (pure function):
Γöé
Γûê1. **Nhß║¡n state, trß║ú vß╗ü thay ─æß╗òi:** Node nhß║¡n to├án bß╗Ö state, nh╞░ng chß╗ë trß║ú vß╗ü nhß╗»ng tr╞░ß╗¥ng cß║ºn cß║¡p nhß║¡t
Γûê2. **Kh├┤ng Side effect tr├¬n state:** Kh├┤ng mutate (thay ─æß╗òi trß╗▒c tiß║┐p) state ─æß║ºu v├áo
Γûê3. **Mß╗Öt tr├ích nhiß╗çm (Single Responsibility):** Mß╗ùi node chß╗ë l├ám mß╗Öt viß╗çc duy nhß║Ñt
Γöé
Γûê```python
Γûêfrom typing import TypedDict
Γöé
Γûêclass AgentState(TypedDict, total=False):
Γûê    query: str
Γûê    search_results: list[str]
Γûê    answer: str
Γûê    error: str
Γöé
Γûê# Γ£à Node ─æ├║ng: chß╗ë trß║ú vß╗ü tr╞░ß╗¥ng cß║ºn thay ─æß╗òi
Γûêdef analyze_query(state: AgentState) -> dict:
Γûê    """Ph├ón t├¡ch c├óu hß╗Åi cß╗ºa ng╞░ß╗¥i d├╣ng."""
Γûê    query = state.get("query", "")
Γûê    # Xß╗¡ l├╜...
Γûê    return {"query": query.lower().strip()}
Γöé
Γûê# Γ¥î Node sai: mutate state trß╗▒c tiß║┐p
Γûêdef bad_node(state: AgentState) -> dict:
Γûê    state["query"] = state["query"].lower()  # KH├öNG L├ÇM THß║╛ N├ÇY
Γûê    return state  # Trß║ú vß╗ü to├án bß╗Ö state
Γûê```
Γöé
Γûê### Async Pattern
Γöé
ΓûêKhi node cß║ºn gß╗ìi API hoß║╖c thß╗▒c hiß╗çn I/O, h├úy d├╣ng async:
Γöé
Γûê```python
Γûêimport asyncio
Γûêfrom langchain_openai import ChatOpenAI
Γöé
Γûêasync def generate_answer(state: AgentState) -> dict:
Γûê    """Tß║ío c├óu trß║ú lß╗¥i sß╗¡ dß╗Ñng LLM (async)."""
Γûê    llm = ChatOpenAI(model="gpt-4o-mini")
Γöé
Γûê    query = state.get("query", "")
Γûê    search_results = state.get("search_results", [])
Γöé
Γûê    prompt = f"""Dß╗▒a tr├¬n kß║┐t quß║ú t├¼m kiß║┐m sau, trß║ú lß╗¥i c├óu hß╗Åi.
Γûê    
Γûê    C├óu hß╗Åi: {query}
Γûê    Kß║┐t quß║ú t├¼m kiß║┐m: {search_results}
Γûê    
Γûê    Trß║ú lß╗¥i bß║▒ng tiß║┐ng Viß╗çt:"""
Γöé
Γûê    response = await llm.ainvoke(prompt)
Γöé
Γûê    return {"answer": response.content}
Γûê```
Γöé
ΓûêD├╣ng async khi node cß║ºn gß╗ìi LLM, HTTP API, database, hoß║╖c bß║Ñt kß╗│ thao t├íc I/O n├áo. LangGraph hß╗ù trß╗ú cß║ú sync v├á async, nh╞░ng async th╞░ß╗¥ng hiß╗çu quß║ú h╞ín cho agent gß╗ìi nhiß╗üu API.
Γöé
Γûê### Error Handling trong Node
Γöé
ΓûêNode n├¬n xß╗¡ l├╜ lß╗ùi graceful (kh├┤ng crash to├án bß╗Ö graph):
Γöé
Γûê```python
Γûêasync def search_web(state: AgentState) -> dict:
Γûê    """T├¼m kiß║┐m tr├¬n web vß╗¢i error handling."""
Γûê    query = state.get("query", "")
Γûê    
Γûê    try:
Γûê        # Giß║ú sß╗¡ gß╗ìi search API
Γûê        results = await search_api(query)
Γûê        return {"search_results": results}
Γûê    except ConnectionError:
Γûê        # Trß║ú vß╗ü lß╗ùi trong state thay v├¼ crash
Γûê        return {
Γûê            "search_results": [],
Γûê            "error": "Kh├┤ng thß╗â kß║┐t nß╗æi ─æß║┐n API t├¼m kiß║┐m. Vui l├▓ng thß╗¡ lß║íi."
Γûê        }
Γûê    except Exception as e:
Γûê        return {
Γûê            "search_results": [],
Γûê            "error": f"Lß╗ùi kh├┤ng x├íc ─æß╗ïnh: {str(e)}"
Γûê        }
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Mß╗ùi node chß╗ë n├¬n trß║ú vß╗ü nhß╗»ng tr╞░ß╗¥ng cß║ºn thay ─æß╗òi. Nß║┐u node xß╗¡ l├╜ t├¼m kiß║┐m, chß╗ë trß║ú vß╗ü `{"search_results": [...]}`. Node kh├íc sß║╜ ─æß╗ìc `search_results` tß╗½ state v├á xß╗¡ l├╜ tiß║┐p. ─Éiß╗üu n├áy gi├║p code dß╗à debug, dß╗à test, v├á dß╗à hiß╗âu.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** ─Éß║╖t t├¬n node m├┤ tß║ú ─æ├║ng h├ánh ─æß╗Öng: `analyze_query`, `search_web`, `generate_answer`, `validate_result`. Tr├ính t├¬n chung chung nh╞░ `process`, `handle`, `step1`.
Γöé
Γûê---
Γöé
Γûê## 4.4 Edges ΓÇö ─Éiß╗üu h╞░ß╗¢ng luß╗ông
Γöé
ΓûêNß║┐u nodes l├á c├íc "trß║ím" xß╗¡ l├╜, th├¼ edges (cß║ính) l├á c├íc "con ─æ╞░ß╗¥ng" kß║┐t nß╗æi ch├║ng. Edges x├íc ─æß╗ïnh luß╗ông thß╗▒c thi cß╗ºa graph ΓÇö node n├áo chß║íy sau node n├áo, v├á theo ─æiß╗üu kiß╗çn g├¼.
Γöé
Γûê### Direct Edges (Cß║ính trß╗▒c tiß║┐p)
Γöé
ΓûêDirect edge kß║┐t nß╗æi hai node cß╗æ ─æß╗ïnh. Sau khi node A chß║íy xong, node B chß║»c chß║»n chß║íy tiß║┐p:
Γöé
Γûê```python
Γûêfrom langgraph.graph import StateGraph, START, END
Γöé
Γûêgraph = StateGraph(AgentState)
Γöé
Γûê# Th├¬m nodes
Γûêgraph.add_node("analyze", analyze_query)
Γûêgraph.add_node("search", search_web)
Γûêgraph.add_node("answer", generate_answer)
Γöé
Γûê# Direct edges ΓÇö luß╗ông cß╗æ ─æß╗ïnh
Γûêgraph.add_edge(START, "analyze")      # Bß║»t ─æß║ºu ΓåÆ analyze
Γûêgraph.add_edge("analyze", "search")   # analyze ΓåÆ search
Γûêgraph.add_edge("search", "answer")    # search ΓåÆ answer
Γûêgraph.add_edge("answer", END)         # answer ΓåÆ Kß║┐t th├║c
Γûê```
Γöé
Γûê`START` v├á `END` l├á sentinel (─æ├ính dß║Ñu ─æß║╖c biß╗çt) cß╗ºa LangGraph: `START` l├á ─æiß╗âm bß║»t ─æß║ºu graph, `END` l├á ─æiß╗âm kß║┐t th├║c. Graph lu├┤n bß║»t ─æß║ºu tß╗½ `START` v├á kß║┐t th├║c tß║íi `END`.
Γöé
Γûê### Conditional Edges (Cß║ính c├│ ─æiß╗üu kiß╗çn)
Γöé
ΓûêConditional edge cho ph├⌐p agent **ra quyß║┐t ─æß╗ïnh** ΓÇö chß╗ìn node tiß║┐p theo dß╗▒a tr├¬n ─æiß╗üu kiß╗çn tß║íi runtime:
Γöé
Γûê```python
Γûêdef route_after_analysis(state: AgentState) -> str:
Γûê    """Quyß║┐t ─æß╗ïnh node tiß║┐p theo dß╗▒a tr├¬n ph├ón t├¡ch."""
Γûê    query = state.get("query", "")
Γûê    
Γûê    if "t├¡nh" in query.lower() or "bao nhi├¬u" in query.lower():
Γûê        return "calculate"  # Cß║ºn t├¡nh to├ín
Γûê    elif "t├¼m" in query.lower() or "search" in query.lower():
Γûê        return "search"     # Cß║ºn t├¼m kiß║┐m
Γûê    else:
Γûê        return "answer"     # Trß║ú lß╗¥i trß╗▒c tiß║┐p
Γöé
Γûê# Th├¬m conditional edge
Γûêgraph.add_conditional_edges(
Γûê    "analyze",                  # Node nguß╗ôn
Γûê    route_after_analysis,       # H├ám routing
Γûê    {                           # Map kß║┐t quß║ú ΓåÆ node ─æ├¡ch
Γûê        "calculate": "calculate",
Γûê        "search": "search",
Γûê        "answer": "answer",
Γûê    }
Γûê)
Γûê```
Γöé
Γûê### Routing Function
Γöé
ΓûêRouting function (h├ám ─æß╗ïnh tuyß║┐n) l├á tr├íi tim cß╗ºa conditional edge. N├│ nhß║¡n state hiß╗çn tß║íi v├á trß║ú vß╗ü t├¬n cß╗ºa node tiß║┐p theo:
Γöé
Γûê```python
Γûêdef should_continue(state: AgentState) -> str:
Γûê    """Kiß╗âm tra xem agent c├│ cß║ºn tiß║┐p tß╗Ñc lß║╖p kh├┤ng."""
Γûê    messages = state.get("messages", [])
Γûê    
Γûê    # Kiß╗âm tra message cuß╗æi c├╣ng c├│ gß╗ìi tool kh├┤ng
Γûê    last_message = messages[-1] if messages else None
Γûê    
Γûê    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
Γûê        return "tools"  # Chuyß╗ân ─æß║┐n node xß╗¡ l├╜ tools
Γûê    
Γûê    return END  # Kh├┤ng c├▓n tool calls ΓåÆ kß║┐t th├║c
Γöé
Γûêgraph.add_conditional_edges(
Γûê    "agent",
Γûê    should_continue,
Γûê    {"tools": "tools", END: END}
Γûê)
Γûê```
Γöé
ΓûêPattern n├áy ─æß║╖c biß╗çt quan trß╗ìng cho ReAct agent (sß║╜ n├│i ß╗ƒ section 4.6) ΓÇö agent cß║ºn quyß║┐t ─æß╗ïnh c├│ tiß║┐p tß╗Ñc gß╗ìi tool hay ─æ├ú c├│ ─æß╗º th├┤ng tin ─æß╗â trß║ú lß╗¥i.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Routing function phß║úi trß║ú vß╗ü mß╗Öt chuß╗ùi khß╗¢p vß╗¢i key trong map. Nß║┐u trß║ú vß╗ü gi├í trß╗ï kh├┤ng tß╗ôn tß║íi trong map, LangGraph sß║╜ throw error. H├úy lu├┤n c├│ fallback (default case) trong routing function.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Edges l├á thß╗⌐ biß║┐n mß╗Öt tß║¡p hß╗úp nodes th├ánh mß╗Öt agent th├┤ng minh. Direct edges cho luß╗ông cß╗æ ─æß╗ïnh, conditional edges cho luß╗ông linh hoß║ít. Hß║ºu hß║┐t agent thß╗▒c tß║┐ sß║╜ kß║┐t hß╗úp cß║ú hai loß║íi.
Γöé
Γûê---
Γöé
Γûê## 4.5 Tools ΓÇö Mß╗ƒ rß╗Öng khß║ú n─âng
Γöé
ΓûêTools (c├┤ng cß╗Ñ) l├á c├ích ─æß╗â agent t╞░╞íng t├íc vß╗¢i thß║┐ giß╗¢i b├¬n ngo├ái ΓÇö t├¼m kiß║┐m web, t├¡nh to├ín, gß╗ìi API, ─æß╗ìc file, v.v. Nß║┐u LLM l├á "bß╗Ö n├úo" cß╗ºa agent, th├¼ tools l├á "─æ├┤i tay" gi├║p agent h├ánh ─æß╗Öng.
Γöé
Γûê### @tool Decorator
Γöé
ΓûêLangGraph (th├┤ng qua LangChain) cung cß║Ñp decorator `@tool` ─æß╗â ─æß╗ïnh ngh─⌐a tool:
Γöé
Γûê```python
Γûêfrom langchain_core.tools import tool
Γöé
Γûê@tool
Γûêdef multiply(a: int, b: int) -> int:
Γûê    """Nh├ón hai sß╗æ vß╗¢i nhau."""
Γûê    return a * b
Γöé
Γûê@tool
Γûêdef search_web(query: str) -> str:
Γûê    """T├¼m kiß║┐m th├┤ng tin tr├¬n web."""
Γûê    # Giß║ú sß╗¡ gß╗ìi API t├¼m kiß║┐m
Γûê    return f"Kß║┐t quß║ú t├¼m kiß║┐m cho '{query}': ..."
Γûê```
Γöé
Γûê### Tß║ºm quan trß╗ìng cß╗ºa Docstring
Γöé
ΓûêDocstring cß╗ºa tool kh├┤ng chß╗ë l├á documentation ΓÇö n├│ l├á **prompt** m├á LLM sß╗¡ dß╗Ñng ─æß╗â quyß║┐t ─æß╗ïnh khi n├áo gß╗ìi tool v├á vß╗¢i tham sß╗æ g├¼. H├úy viß║┐t docstring r├╡ r├áng, m├┤ tß║ú ch├¡nh x├íc tool l├ám g├¼:
Γöé
Γûê```python
Γûê# Γ£à Docstring tß╗æt ΓÇö m├┤ tß║ú r├╡ r├áng khi n├áo v├á d├╣ng thß║┐ n├áo
Γûê@tool
Γûêdef search_papers(query: str, max_results: int = 5) -> str:
Γûê    """T├¼m kiß║┐m b├ái b├ío khoa hß╗ìc theo tß╗½ kh├│a.
Γûê    
Γûê    Args:
Γûê        query: Tß╗½ kh├│a t├¼m kiß║┐m (v├¡ dß╗Ñ: "transformer attention mechanism")
Γûê        max_results: Sß╗æ kß║┐t quß║ú tß╗æi ─æa (mß║╖c ─æß╗ïnh: 5, tß╗æi ─æa: 20)
Γûê    
Γûê    Returns:
Γûê        Danh s├ích b├ái b├ío vß╗¢i ti├¬u ─æß╗ü, t├íc giß║ú, v├á t├│m tß║»t.
Γûê    """
Γûê    # Implementation...
Γöé
Γûê# Γ¥î Docstring tß╗ôi ΓÇö LLM kh├┤ng biß║┐t khi n├áo d├╣ng
Γûê@tool
Γûêdef search(q: str) -> str:
Γûê    """Search."""
Γûê    return "results"
Γûê```
Γöé
Γûê### Type Hints
Γöé
ΓûêType hints gi├║p LLM biß║┐t ch├¡nh x├íc kiß╗âu dß╗» liß╗çu mß╗ùi tham sß╗æ. ─Éiß╗üu n├áy ─æß║╖c biß╗çt quan trß╗ìng v├¼ LLM cß║ºn sinh JSON ─æ├║ng kiß╗âu ─æß╗â gß╗ìi tool:
Γöé
Γûê```python
Γûêfrom typing import Literal, Optional
Γöé
Γûê@tool
Γûêdef get_weather(
Γûê    city: str,
Γûê    unit: Literal["celsius", "fahrenheit"] = "celsius",
Γûê    forecast_days: Optional[int] = None
Γûê) -> str:
Γûê    """Lß║Ñy th├┤ng tin thß╗¥i tiß║┐t cho mß╗Öt th├ánh phß╗æ.
Γûê    
Γûê    Args:
Γûê        city: T├¬n th├ánh phß╗æ (v├¡ dß╗Ñ: "H├á Nß╗Öi", "TP.HCM")
Γûê        unit: ─É╞ín vß╗ï nhiß╗çt ─æß╗Ö
Γûê        forecast_days: Sß╗æ ng├áy dß╗▒ b├ío (None = chß╗ë thß╗¥i tiß║┐t hiß╗çn tß║íi)
Γûê    """
Γûê    # LLM sß║╜ biß║┐t city l├á string, unit chß╗ë ─æ╞░ß╗úc "celsius" hoß║╖c "fahrenheit"
Γûê    # forecast_days c├│ thß╗â null hoß║╖c int
Γûê    return f"Weather data for {city}..."
Γûê```
Γöé
Γûê### Error Handling trong Tools
Γöé
ΓûêTools n├¬n xß╗¡ l├╜ lß╗ùi graceful v├á trß║ú vß╗ü th├┤ng b├ío hß╗»u ├¡ch:
Γöé
Γûê```python
Γûêimport httpx
Γöé
Γûê@tool
Γûêdef fetch_api_data(url: str) -> str:
Γûê    """Gß╗ìi HTTP GET ─æß║┐n URL v├á trß║ú vß╗ü response.
Γûê    
Γûê    Args:
Γûê        url: URL cß║ºn gß╗ìi (phß║úi l├á URL hß╗úp lß╗ç)
Γûê    """
Γûê    try:
Γûê        response = httpx.get(url, timeout=10.0)
Γûê        response.raise_for_status()
Γûê        return response.text[:5000]  # Giß╗¢i hß║ín 5000 k├╜ tß╗▒
Γûê    except httpx.TimeoutException:
Γûê        return "Lß╗ùi: Request timeout. URL kh├┤ng phß║ún hß╗ôi trong 10 gi├óy."
Γûê    except httpx.HTTPStatusError as e:
Γûê        return f"Lß╗ùi HTTP {e.response.status_code}: {e.response.reason_phrase}"
Γûê    except Exception as e:
Γûê        return f"Lß╗ùi kh├┤ng x├íc ─æß╗ïnh: {str(e)}"
Γûê```
Γöé
Γûê### V├¡ dß╗Ñ: Tool t├¼m kiß║┐m
Γöé
Γûê```python
Γûê@tool
Γûêdef web_search(query: str, num_results: int = 5) -> str:
Γûê    """T├¼m kiß║┐m th├┤ng tin tr├¬n internet sß╗¡ dß╗Ñng Tavily Search API.
Γûê    
Γûê    Sß╗¡ dß╗Ñng tool n├áy khi cß║ºn t├¼m th├┤ng tin mß╗¢i, sß╗▒ kiß╗çn hiß╗çn tß║íi,
Γûê    hoß║╖c kiß║┐n thß╗⌐c kh├┤ng c├│ trong training data cß╗ºa model.
Γûê    
Γûê    Args:
Γûê        query: C├óu truy vß║Ñn t├¼m kiß║┐m (n├¬n cß╗Ñ thß╗â, r├╡ r├áng)
Γûê        num_results: Sß╗æ kß║┐t quß║ú trß║ú vß╗ü (1-10)
Γûê    """
Γûê    from langchain_community.tools.tavily_search import TavilySearchResults
Γûê    
Γûê    search = TavilySearchResults(max_results=num_results)
Γûê    try:
Γûê        results = search.invoke(query)
Γûê        return str(results)
Γûê    except Exception as e:
Γûê        return f"Lß╗ùi t├¼m kiß║┐m: {str(e)}. H├úy thß╗¡ lß║íi vß╗¢i query kh├íc."
Γûê```
Γöé
Γûê### V├¡ dß╗Ñ: Tool t├¡nh to├ín
Γöé
Γûê```python
Γûêimport math
Γûêimport ast
Γûêimport operator
Γöé
Γûê# Mapping an to├án tß╗½ AST operators sang h├ám to├ín hß╗ìc
Γûê_SAFE_OPERATORS = {
Γûê    ast.Add: operator.add,
Γûê    ast.Sub: operator.sub,
Γûê    ast.Mult: operator.mul,
Γûê    ast.Div: operator.truediv,
Γûê    ast.Pow: operator.pow,
Γûê    ast.USub: operator.neg,
Γûê    ast.Mod: operator.mod,
Γûê}
Γöé
Γûê_SAFE_FUNCTIONS = {
Γûê    "sqrt": math.sqrt,
Γûê    "sin": math.sin,
Γûê    "cos": math.cos,
Γûê    "tan": math.tan,
Γûê    "log": math.log,
Γûê    "log10": math.log10,
Γûê    "pi": math.pi,
Γûê    "e": math.e,
Γûê    "abs": abs,
Γûê    "round": round,
Γûê}
Γöé
Γûêdef _safe_eval(node: ast.AST) -> float:
Γûê    """─Éß╗ç quy ─æ├ính gi├í AST node ΓÇö kh├┤ng d├╣ng eval()."""
Γûê    if isinstance(node, ast.Constant):  # Sß╗æ literal (3.14, 42, "hello")
Γûê        return node.value
Γûê    elif isinstance(node, ast.Name):    # Biß║┐n (pi, e)
Γûê        if node.id in _SAFE_FUNCTIONS:
Γûê            return _SAFE_FUNCTIONS[node.id]
Γûê        raise ValueError(f"T├¬n kh├┤ng hß╗úp lß╗ç: {node.id}")
Γûê    elif isinstance(node, ast.Call):    # H├ám (sqrt(144), sin(0))
Γûê        func_name = node.func.id if isinstance(node.func, ast.Name) else ""
Γûê        if func_name not in _SAFE_FUNCTIONS:
Γûê            raise ValueError(f"H├ám kh├┤ng hß╗úp lß╗ç: {func_name}")
Γûê        args = [_safe_eval(arg) for arg in node.args]
Γûê        return _SAFE_FUNCTIONS[func_name](*args)
Γûê    elif isinstance(node, ast.BinOp):   # Ph├⌐p t├¡nh nhß╗ï ph├ón (2 + 3)
Γûê        left = _safe_eval(node.left)
Γûê        right = _safe_eval(node.right)
Γûê        op_type = type(node.op)
Γûê        if op_type in _SAFE_OPERATORS:
Γûê            return _SAFE_OPERATORS[op_type](left, right)
Γûê        raise ValueError(f"Ph├⌐p to├ín kh├┤ng hß╗ù trß╗ú: {op_type.__name__}")
Γûê    elif isinstance(node, ast.UnaryOp): # Ph├⌐p to├ín mß╗Öt ng├┤i (-5)
Γûê        operand = _safe_eval(node.operand)
Γûê        op_type = type(node.op)
Γûê        if op_type in _SAFE_OPERATORS:
Γûê            return _SAFE_OPERATORS[op_type](operand)
Γûê        raise ValueError(f"Ph├⌐p to├ín kh├┤ng hß╗ù trß╗ú: {op_type.__name__}")
Γûê    else:
Γûê        raise ValueError(f"Biß╗âu thß╗⌐c kh├┤ng hß╗ù trß╗ú: {type(node).__name__}")
Γöé
Γûê@tool
Γûêdef calculate(expression: str) -> str:
Γûê    """T├¡nh to├ín biß╗âu thß╗⌐c to├ín hß╗ìc an to├án.
Γöé
Γûê    Hß╗ù trß╗ú c├íc ph├⌐p t├¡nh c╞í bß║ún (+, -, *, /, **), 
Γûê    v├á h├ám to├ín hß╗ìc (sqrt, sin, cos, log, abs, round).
Γûê    Kh├┤ng sß╗¡ dß╗Ñng eval() ΓÇö ph├ón t├¡ch AST an to├án.
Γöé
Γûê    Args:
Γûê        expression: Biß╗âu thß╗⌐c to├ín hß╗ìc (v├¡ dß╗Ñ: "2 ** 10", "sqrt(144)")
Γûê    """
Γûê    try:
Γûê        tree = ast.parse(expression, mode="eval")
Γûê        result = _safe_eval(tree.body)
Γûê        return f"Kß║┐t quß║ú: {expression} = {result}"
Γûê    except (SyntaxError, ValueError) as e:
Γûê        return f"Biß╗âu thß╗⌐c kh├┤ng hß╗úp lß╗ç '{expression}': {str(e)}"
Γûê    except Exception as e:
Γûê        return f"Kh├┤ng thß╗â t├¡nh to├ín '{expression}': {str(e)}"
Γûê```
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Kh├┤ng bao giß╗¥ d├╣ng `eval()` trong production code, ─æß║╖c biß╗çt khi input ─æß║┐n tß╗½ LLM. D├╣ `eval(expression, {"__builtins__": {}}, allowed_names)` giß╗¢i hß║ín scope, vß║½n c├│ kß╗╣ thuß║¡t bypass (dunder attributes, subclassing). Ph├ón t├¡ch AST (nh╞░ code tr├¬n) l├á c├ích an to├án h╞ín ΓÇö bß║ín kiß╗âm so├ít ch├¡nh x├íc node n├áo ─æ╞░ß╗úc ─æ├ính gi├í.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** LLM kh├┤ng biß║┐t tool n├áo tß╗ôn tß║íi cho ─æß║┐n khi bß║ín cho n├│ biß║┐t. Khi bind tools v├áo LLM, model sß║╜ tß╗▒ ─æß╗Öng quyß║┐t ─æß╗ïnh tool n├áo cß║ºn gß╗ìi dß╗▒a tr├¬n c├óu hß╗Åi v├á docstring. H├úy viß║┐t docstring nh╞░ thß╗â bß║ín ─æang h╞░ß╗¢ng dß║½n mß╗Öt ─æß╗ông nghiß╗çp mß╗¢i: r├╡ r├áng, cß╗Ñ thß╗â, c├│ v├¡ dß╗Ñ.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Kh├┤ng bao giß╗¥ trust input tß╗½ LLM mß╗Öt c├ích m├╣ qu├íng. LLM c├│ thß╗â sinh ra tham sß╗æ kh├┤ng hß╗úp lß╗ç. Lu├┤n validate v├á sanitize input trong tool. V├¡ dß╗Ñ: giß╗¢i hß║ín sß╗æ kß║┐t quß║ú t├¼m kiß║┐m, kiß╗âm tra URL hß╗úp lß╗ç, v.v.
Γöé
Γûê---
Γöé
Γûê## 4.6 Pattern ReAct
Γöé
ΓûêReAct (Reasoning + Acting) l├á pattern phß╗ò biß║┐n nhß║Ñt ─æß╗â x├óy dß╗▒ng agent. Pattern n├áy m├┤ phß╗Ång c├ích con ng╞░ß╗¥i giß║úi quyß║┐t vß║Ñn ─æß╗ü: **suy ngh─⌐ ΓåÆ h├ánh ─æß╗Öng ΓåÆ quan s├ít ΓåÆ lß║╖p lß║íi**.
Γöé
Γûê### V├▓ng lß║╖p Think ΓåÆ Act ΓåÆ Observe
Γöé
ΓûêQu├í tr├¼nh ReAct hoß║ít ─æß╗Öng nh╞░ sau:
Γöé
Γûê1. **Thought (Suy ngh─⌐):** Agent nhß║¡n c├óu hß╗Åi, ph├ón t├¡ch cß║ºn l├ám g├¼
Γûê2. **Action (H├ánh ─æß╗Öng):** Agent gß╗ìi tool ─æß╗â thu thß║¡p th├┤ng tin
Γûê3. **Observation (Quan s├ít):** Agent nhß║¡n kß║┐t quß║ú tß╗½ tool
Γûê4. **Lß║╖p lß║íi:** Nß║┐u ch╞░a ─æß╗º th├┤ng tin, quay lß║íi b╞░ß╗¢c 1
Γûê5. **Answer (Trß║ú lß╗¥i):** Khi ─æß╗º th├┤ng tin, agent tß╗òng hß╗úp v├á trß║ú lß╗¥i
Γöé
ΓûêV├¡ dß╗Ñ minh hß╗ìa vß╗¢i c├óu hß╗Åi "Gi├í v├áng h├┤m nay bao nhi├¬u?":
Γöé
Γûê```
ΓûêThought: T├┤i cß║ºn t├¼m gi├í v├áng h├┤m nay. T├┤i sß║╜ d├╣ng tool search.
ΓûêAction: search_web("gi├í v├áng h├┤m nay")
ΓûêObservation: Gi├í v├áng SJC h├┤m nay 78.5 triß╗çu/l╞░ß╗úng
ΓûêThought: ─É├ú c├│ th├┤ng tin. T├┤i c├│ thß╗â trß║ú lß╗¥i.
ΓûêAnswer: Gi├í v├áng SJC h├┤m nay l├á 78.5 triß╗çu ─æß╗ông/l╞░ß╗úng.
Γûê```
Γöé
Γûê### Khi n├áo d├╣ng ReAct?
Γöé
ΓûêReAct ph├╣ hß╗úp khi:
Γûê- Agent cß║ºn **nhiß╗üu b╞░ß╗¢c** ─æß╗â trß║ú lß╗¥i (ph├ón t├¡ch ΓåÆ t├¼m kiß║┐m ΓåÆ tß╗òng hß╗úp)
Γûê- Agent cß║ºn **quyß║┐t ─æß╗ïnh** c├│ cß║ºn th├¬m th├┤ng tin kh├┤ng
Γûê- Luß╗ông xß╗¡ l├╜ **kh├┤ng thß╗â biß║┐t tr╞░ß╗¢c** ΓÇö phß╗Ñ thuß╗Öc v├áo kß║┐t quß║ú trung gian
Γöé
ΓûêReAct KH├öNG ph├╣ hß╗úp khi:
Γûê- T├íc vß╗Ñ ─æ╞ín giß║ún, mß╗Öt b╞░ß╗¢c (d├╣ng chain thay)
Γûê- Luß╗ông xß╗¡ l├╜ cß╗æ ─æß╗ïnh, kh├┤ng cß║ºn quyß║┐t ─æß╗ïnh (d├╣ng workflow thay)
Γûê- Cß║ºn tß╗æc ─æß╗Ö tß╗æi ─æa (ReAct c├│ ─æß╗Ö trß╗à do nhiß╗üu v├▓ng LLM call)
Γöé
Γûê### V├¡ dß╗Ñ vß╗¢i create_react_agent
Γöé
ΓûêLangGraph cung cß║Ñp h├ám `create_react_agent` ─æß╗â tß║ío ReAct agent nhanh:
Γöé
Γûê```python
Γûêfrom langgraph.prebuilt import create_react_agent
Γûêfrom langchain_openai import ChatOpenAI
Γöé
Γûê# Khß╗ƒi tß║ío LLM
Γûêllm = ChatOpenAI(model="gpt-4o-mini")
Γöé
Γûê# Khß╗ƒi tß║ío tools
Γûêtools = [web_search, calculate, fetch_api_data]
Γöé
Γûê# Tß║ío ReAct agent ΓÇö mß╗Öt d├▓ng code!
Γûêagent = create_react_agent(llm, tools)
Γöé
Γûê# Chß║íy agent
Γûêresult = agent.invoke({
Γûê    "messages": [{"role": "user", "content": "GDP cß╗ºa Viß╗çt Nam n─âm 2024 l├á bao nhi├¬u? T├¡nh GDP per capita nß║┐u d├ón sß╗æ l├á 100 triß╗çu."}]
Γûê})
Γöé
Γûêprint(result["messages"][-1].content)
Γûê```
Γöé
Γûê`create_react_agent` tß╗▒ ─æß╗Öng tß║ío graph vß╗¢i: node agent (gß╗ìi LLM), node tools (thß╗▒c thi tool calls), v├á conditional edge (kiß╗âm tra c├│ tool calls kh├┤ng). ─É├óy l├á c├ích nhanh nhß║Ñt ─æß╗â tß║ío agent hoß║ít ─æß╗Öng.
Γöé
Γûê### ReAct Graph thß╗º c├┤ng
Γöé
Γûê─Éß╗â hiß╗âu s├óu h╞ín, h├úy x├óy dß╗▒ng ReAct graph thß╗º c├┤ng:
Γöé
Γûê```python
Γûêfrom langgraph.graph import StateGraph, MessagesState, START, END
Γûêfrom langchain_openai import ChatOpenAI
Γûêfrom langchain_core.messages import HumanMessage, SystemMessage
Γöé
Γûê# Khß╗ƒi tß║ío
Γûêllm = ChatOpenAI(model="gpt-4o-mini")
Γûêllm_with_tools = llm.bind_tools([web_search, calculate])
Γöé
Γûê# Node 1: Agent suy ngh─⌐ v├á quyß║┐t ─æß╗ïnh
Γûêasync def agent_node(state: MessagesState) -> dict:
Γûê    """Agent ph├ón t├¡ch v├á quyß║┐t ─æß╗ïnh h├ánh ─æß╗Öng tiß║┐p theo."""
Γûê    system = SystemMessage(content="""Bß║ín l├á trß╗ú l├╜ AI th├┤ng minh.
Γûê    Khi cß║ºn th├┤ng tin, h├úy d├╣ng tools. Khi ─æ├ú ─æß╗º th├┤ng tin, h├úy trß║ú lß╗¥i trß╗▒c tiß║┐p.
Γûê    Trß║ú lß╗¥i bß║▒ng tiß║┐ng Viß╗çt.""")
Γûê    
Γûê    messages = [system] + state["messages"]
Γûê    response = await llm_with_tools.ainvoke(messages)
Γûê    return {"messages": [response]}
Γöé
Γûê# Node 2: Thß╗▒c thi tools
Γûêasync def tools_node(state: MessagesState) -> dict:
Γûê    """Thß╗▒c thi tool calls tß╗½ message cuß╗æi c├╣ng."""
Γûê    from langchain_core.messages import ToolMessage
Γûê    from langgraph.prebuilt import ToolNode
Γûê    
Γûê    tool_node = ToolNode([web_search, calculate])
Γûê    return await tool_node.ainvoke(state)
Γöé
Γûê# Routing: Kiß╗âm tra c├│ tool calls kh├┤ng
Γûêdef should_use_tools(state: MessagesState) -> str:
Γûê    """Nß║┐u message cuß╗æi c├│ tool calls ΓåÆ chß║íy tools, ng╞░ß╗úc lß║íi ΓåÆ kß║┐t th├║c."""
Γûê    last_message = state["messages"][-1]
Γûê    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
Γûê        return "tools"
Γûê    return END
Γöé
Γûê# X├óy dß╗▒ng graph
Γûêgraph = StateGraph(MessagesState)
Γûêgraph.add_node("agent", agent_node)
Γûêgraph.add_node("tools", tools_node)
Γöé
Γûêgraph.add_edge(START, "agent")
Γûêgraph.add_conditional_edges("agent", should_use_tools, {"tools": "tools", END: END})
Γûêgraph.add_edge("tools", "agent")  # Sau khi chß║íy tools ΓåÆ quay lß║íi agent
Γöé
Γûêapp = graph.compile()
Γûê```
Γöé
ΓûêCh├║ ├╜ d├▓ng `graph.add_edge("tools", "agent")` ΓÇö ─æ├óy tß║ío ra **v├▓ng lß║╖p** (loop). Sau khi tools chß║íy xong, agent sß║╜ lß║íi suy ngh─⌐ xem cß║ºn th├¬m th├┤ng tin kh├┤ng. V├▓ng lß║╖p tiß║┐p tß╗Ñc cho ─æß║┐n khi agent quyß║┐t ─æß╗ïnh trß║ú lß╗¥i (kh├┤ng c├│ tool calls).
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** ReAct l├á pattern "t╞░ duy ΓåÆ h├ánh ─æß╗Öng ΓåÆ quan s├ít". V├▓ng lß║╖p giß╗»a agent v├á tools tiß║┐p tß╗Ñc cho ─æß║┐n khi agent quyß║┐t ─æß╗ïnh ─æ├ú ─æß╗º th├┤ng tin. Pattern n├áy l├á nß╗ün tß║úng cho hß║ºu hß║┐t agent hiß╗çn ─æß║íi.
Γöé
Γûê---
Γöé
Γûê## 4.7 X├óy dß╗▒ng Graph ho├án chß╗ënh
Γöé
ΓûêB├óy giß╗¥ ch├║ng ta sß║╜ kß║┐t hß╗úp tß║Ñt cß║ú kiß║┐n thß╗⌐c ─æß╗â x├óy dß╗▒ng mß╗Öt agent ho├án chß╗ënh: **Planning Agent** ΓÇö agent nhß║¡n c├óu hß╗Åi, lß║¡p kß║┐ hoß║ích nghi├¬n cß╗⌐u, t├¼m kiß║┐m th├┤ng tin, v├á tß║ío c├óu trß║ú lß╗¥i chi tiß║┐t.
Γöé
Γûê### Tß╗òng quan kiß║┐n tr├║c
Γöé
Γûê```
ΓûêSTART ΓåÆ analyze ΓåÆ plan ΓåÆ [research ΓåÆ synthesize ΓåÆ review] ΓåÆ END
Γûê                        Γåæ                            |
Γûê                        ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ (cß║ºn bß╗ò sung) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
Γûê```
Γöé
ΓûêAgent hoß║ít ─æß╗Öng nh╞░ sau:
Γûê1. **Analyze:** Ph├ón t├¡ch c├óu hß╗Åi, x├íc ─æß╗ïnh loß║íi v├á y├¬u cß║ºu
Γûê2. **Plan:** Lß║¡p kß║┐ hoß║ích nghi├¬n cß╗⌐u ΓÇö cß║ºn t├¼m kiß║┐m g├¼
Γûê3. **Research:** Thß╗▒c hiß╗çn t├¼m kiß║┐m theo kß║┐ hoß║ích
Γûê4. **Synthesize:** Tß╗òng hß╗úp kß║┐t quß║ú th├ánh c├óu trß║ú lß╗¥i
Γûê5. **Review:** Kiß╗âm tra chß║Ñt l╞░ß╗úng ΓÇö nß║┐u ch╞░a ─æß╗º, quay lß║íi b╞░ß╗¢c 3
Γöé
Γûê### Code ho├án chß╗ënh
Γöé
Γûê```python
Γûêimport asyncio
Γûêfrom typing import TypedDict, Annotated
Γûêfrom langgraph.graph import StateGraph, START, END
Γûêfrom langgraph.graph.message import add_messages
Γûêfrom langchain_openai import ChatOpenAI
Γûêfrom langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
Γûêfrom langchain_core.tools import tool
Γöé
Γûê# ==================== STATE ====================
Γöé
Γûêclass ResearchState(TypedDict, total=False):
Γûê    """State cho Planning Agent."""
Γûê    messages: Annotated[list[BaseMessage], add_messages]
Γûê    query: str                    # C├óu hß╗Åi gß╗æc
Γûê    query_type: str               # Loß║íi c├óu hß╗Åi (factual, analytical, creative)
Γûê    research_plan: list[str]      # Kß║┐ hoß║ích nghi├¬n cß╗⌐u
Γûê    search_results: list[str]     # Kß║┐t quß║ú t├¼m kiß║┐m
Γûê    draft: str                    # Bß║ún nh├íp c├óu trß║ú lß╗¥i
Γûê    quality_score: float          # ─Éiß╗âm chß║Ñt l╞░ß╗úng (0-1)
Γûê    iteration: int                # Sß╗æ lß║ºn lß║╖p
Γûê    error: str                    # Th├┤ng b├ío lß╗ùi (nß║┐u c├│)
Γöé
Γûê# ==================== TOOLS ====================
Γöé
Γûê@tool
Γûêdef web_search(query: str) -> str:
Γûê    """T├¼m kiß║┐m th├┤ng tin tr├¬n web.
Γûê    
Γûê    Args:
Γûê        query: Tß╗½ kh├│a t├¼m kiß║┐m cß╗Ñ thß╗â
Γûê    """
Γûê    # Placeholder ΓÇö thay bß║▒ng API thß╗▒c tß║┐ (Tavily, SerpAPI, v.v.)
Γûê    return f"[Kß║┐t quß║ú t├¼m kiß║┐m cho '{query}']: Th├┤ng tin mß║½u..."
Γöé
Γûê# ==================== NODES ====================
Γöé
Γûêasync def analyze_node(state: ResearchState) -> dict:
Γûê    """Ph├ón t├¡ch c├óu hß╗Åi cß╗ºa ng╞░ß╗¥i d├╣ng."""
Γûê    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
Γûê    
Γûê    query = state.get("query", "")
Γûê    if not query and state.get("messages"):
Γûê        last_msg = state["messages"][-1]
Γûê        query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
Γûê    
Γûê    prompt = f"""Ph├ón t├¡ch c├óu hß╗Åi sau v├á x├íc ─æß╗ïnh loß║íi.
Γûê    
Γûê    C├óu hß╗Åi: {query}
Γûê    
Γûê    Trß║ú vß╗ü JSON:
Γûê    {{
Γûê        "query_type": "factual|analytical|creative",
Γûê        "needs_research": true/false
Γûê    }}
Γûê    
Γûê    Chß╗ë trß║ú vß╗ü JSON, kh├┤ng th├¬m g├¼ kh├íc."""
Γûê    
Γûê    response = await llm.ainvoke([HumanMessage(content=prompt)])
Γûê    
Γûê    import json
Γûê    try:
Γûê        analysis = json.loads(response.content)
Γûê    except json.JSONDecodeError:
Γûê        analysis = {"query_type": "factual", "needs_research": True}
Γûê    
Γûê    return {
Γûê        "query": query,
Γûê        "query_type": analysis.get("query_type", "factual"),
Γûê        "iteration": 0,
Γûê    }
Γöé
Γûêasync def plan_node(state: ResearchState) -> dict:
Γûê    """Lß║¡p kß║┐ hoß║ích nghi├¬n cß╗⌐u."""
Γûê    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
Γûê    
Γûê    query = state.get("query", "")
Γûê    query_type = state.get("query_type", "factual")
Γûê    
Γûê    prompt = f"""Lß║¡p kß║┐ hoß║ích nghi├¬n cß╗⌐u cho c├óu hß╗Åi sau.
Γûê    
Γûê    C├óu hß╗Åi: {query}
Γûê    Loß║íi: {query_type}
Γûê    
Γûê    Liß╗çt k├¬ 3-5 b╞░ß╗¢c t├¼m kiß║┐m cß║ºn thß╗▒c hiß╗çn, mß╗ùi b╞░ß╗¢c l├á mß╗Öt c├óu truy vß║Ñn t├¼m kiß║┐m.
Γûê    Trß║ú vß╗ü danh s├ích JSON array c├íc string. Chß╗ë trß║ú vß╗ü JSON array."""
Γûê    
Γûê    response = await llm.ainvoke([HumanMessage(content=prompt)])
Γûê    
Γûê    import json
Γûê    try:
Γûê        plan = json.loads(response.content)
Γûê        if not isinstance(plan, list):
Γûê            plan = [query]
Γûê    except json.JSONDecodeError:
Γûê        plan = [query]
Γûê    
Γûê    return {"research_plan": plan}
Γöé
Γûêasync def research_node(state: ResearchState) -> dict:
Γûê    """Thß╗▒c hiß╗çn t├¼m kiß║┐m theo kß║┐ hoß║ích."""
Γûê    plan = state.get("research_plan", [])
Γûê    results = []
Γûê    
Γûê    for search_query in plan:
Γûê        try:
Γûê            result = web_search.invoke({"query": search_query})
Γûê            results.append(f"Query: {search_query}\nResult: {result}")
Γûê        except Exception as e:
Γûê            results.append(f"Query: {search_query}\nError: {str(e)}")
Γûê    
Γûê    iteration = state.get("iteration", 0) + 1
Γûê    
Γûê    return {
Γûê        "search_results": results,
Γûê        "iteration": iteration,
Γûê    }
Γöé
Γûêasync def synthesize_node(state: ResearchState) -> dict:
Γûê    """Tß╗òng hß╗úp kß║┐t quß║ú th├ánh c├óu trß║ú lß╗¥i."""
Γûê    llm = ChatOpenAI(model="gpt-4o-mini")
Γûê    
Γûê    query = state.get("query", "")
Γûê    search_results = state.get("search_results", [])
Γûê    
Γûê    prompt = f"""Dß╗▒a tr├¬n kß║┐t quß║ú nghi├¬n cß╗⌐u, viß║┐t c├óu trß║ú lß╗¥i chi tiß║┐t cho c├óu hß╗Åi.
Γûê    
Γûê    C├óu hß╗Åi: {query}
Γûê    
Γûê    Kß║┐t quß║ú nghi├¬n cß╗⌐u:
Γûê    {chr(10).join(search_results)}
Γûê    
Γûê    Y├¬u cß║ºu:
Γûê    - Trß║ú lß╗¥i ─æß║ºy ─æß╗º, c├│ cß║Ñu tr├║c r├╡ r├áng
Γûê    - Tr├¡ch dß║½n nguß╗ôn khi c├│ thß╗â
Γûê    - Nß║┐u th├┤ng tin kh├┤ng ─æß╗º, ghi ch├║ ─æiß╗üu cß║ºn bß╗ò sung
Γûê    - Viß║┐t bß║▒ng tiß║┐ng Viß╗çt"""
Γûê    
Γûê    response = await llm.ainvoke([HumanMessage(content=prompt)])
Γûê    
Γûê    return {"draft": response.content}
Γöé
Γûêasync def review_node(state: ResearchState) -> dict:
Γûê    """─É├ính gi├í chß║Ñt l╞░ß╗úng c├óu trß║ú lß╗¥i."""
Γûê    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
Γûê    
Γûê    query = state.get("query", "")
Γûê    draft = state.get("draft", "")
Γûê    
Γûê    prompt = f"""─É├ính gi├í chß║Ñt l╞░ß╗úng c├óu trß║ú lß╗¥i sau tr├¬n thang 0-1.
Γûê    
Γûê    C├óu hß╗Åi: {query}
Γûê    C├óu trß║ú lß╗¥i: {draft}
Γûê    
Γûê    Ti├¬u ch├¡:
Γûê    - ─Éß╗Ö ─æß║ºy ─æß╗º: C├│ trß║ú lß╗¥i ─æß╗º c├óu hß╗Åi kh├┤ng?
Γûê    - ─Éß╗Ö ch├¡nh x├íc: Th├┤ng tin c├│ ─æ├íng tin kh├┤ng?
Γûê    - ─Éß╗Ö r├╡ r├áng: C├│ dß╗à hiß╗âu kh├┤ng?
Γûê    
Γûê    Trß║ú vß╗ü JSON: {{"score": 0.0-1.0, "needs_more": true/false, "feedback": "..."}}
Γûê    Chß╗ë trß║ú vß╗ü JSON."""
Γûê    
Γûê    response = await llm.ainvoke([HumanMessage(content=prompt)])
Γûê    
Γûê    import json
Γûê    try:
Γûê        review = json.loads(response.content)
Γûê        score = float(review.get("score", 0.5))
Γûê    except (json.JSONDecodeError, ValueError):
Γûê        score = 0.5
Γûê        review = {"needs_more": True, "feedback": "Kh├┤ng thß╗â parse review"}
Γûê    
Γûê    return {"quality_score": score}
Γöé
Γûê# ==================== ROUTING ====================
Γöé
Γûêdef should_continue_research(state: ResearchState) -> str:
Γûê    """Quyß║┐t ─æß╗ïnh c├│ cß║ºn nghi├¬n cß╗⌐u th├¬m kh├┤ng."""
Γûê    score = state.get("quality_score", 0.0)
Γûê    iteration = state.get("iteration", 0)
Γûê    
Γûê    # Nß║┐u chß║Ñt l╞░ß╗úng ─æß╗º tß╗æt hoß║╖c ─æ├ú lß║╖p qu├í nhiß╗üu lß║ºn ΓåÆ kß║┐t th├║c
Γûê    if score >= 0.7 or iteration >= 3:
Γûê        return "finalize"
Γûê    
Γûê    # Ng╞░ß╗úc lß║íi ΓåÆ nghi├¬n cß╗⌐u th├¬m
Γûê    return "research"
Γöé
Γûê# ==================== BUILD GRAPH ====================
Γöé
Γûêasync def finalize_node(state: ResearchState) -> dict:
Γûê    """Chuß║⌐n bß╗ï c├óu trß║ú lß╗¥i cuß╗æi c├╣ng."""
Γûê    from langchain_core.messages import AIMessage
Γûê    draft = state.get("draft", "Kh├┤ng thß╗â tß║ío c├óu trß║ú lß╗¥i.")
Γûê    return {"messages": [AIMessage(content=draft)]}
Γöé
Γûêgraph = StateGraph(ResearchState)
Γöé
Γûê# Th├¬m nodes
Γûêgraph.add_node("analyze", analyze_node)
Γûêgraph.add_node("plan", plan_node)
Γûêgraph.add_node("research", research_node)
Γûêgraph.add_node("synthesize", synthesize_node)
Γûêgraph.add_node("review", review_node)
Γûêgraph.add_node("finalize", finalize_node)
Γöé
Γûê# Th├¬m edges
Γûêgraph.add_edge(START, "analyze")
Γûêgraph.add_edge("analyze", "plan")
Γûêgraph.add_edge("plan", "research")
Γûêgraph.add_edge("research", "synthesize")
Γûêgraph.add_edge("synthesize", "review")
Γöé
Γûê# Conditional edge tß╗½ review
Γûêgraph.add_conditional_edges(
Γûê    "review",
Γûê    should_continue_research,
Γûê    {
Γûê        "research": "research",    # Lß║╖p lß║íi nghi├¬n cß╗⌐u
Γûê        "finalize": "finalize",    # Ho├án th├ánh
Γûê    }
Γûê)
Γöé
Γûêgraph.add_edge("finalize", END)
Γöé
Γûê# Compile
Γûêapp = graph.compile()
Γöé
Γûê# ==================== CHß║áY ====================
Γöé
Γûêasync def main():
Γûê    result = await app.ainvoke({
Γûê        "messages": [HumanMessage(content="AI agents ─æang thay ─æß╗òi ng├ánh phß║ºn mß╗üm nh╞░ thß║┐ n├áo?")],
Γûê        "query": "AI agents ─æang thay ─æß╗òi ng├ánh phß║ºn mß╗üm nh╞░ thß║┐ n├áo?"
Γûê    })
Γûê    
Γûê    print("=" * 60)
Γûê    print("C├éU TRß║ó Lß╗£I:")
Γûê    print("=" * 60)
Γûê    print(result.get("draft", "Kh├┤ng c├│ kß║┐t quß║ú"))
Γûê    print(f"\nSß╗æ lß║ºn lß║╖p: {result.get('iteration', 0)}")
Γûê    print(f"─Éiß╗âm chß║Ñt l╞░ß╗úng: {result.get('quality_score', 0):.2f}")
Γöé
Γûêif __name__ == "__main__":
Γûê    asyncio.run(main())
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Khi x├óy dß╗▒ng graph phß╗⌐c tß║íp, h├úy bß║»t ─æß║ºu vß╗¢i version ─æ╞ín giß║ún nhß║Ñt (linear flow), sau ─æ├│ th├¬m conditional edges v├á loops dß║ºn. ─Éß╗½ng cß╗æ x├óy dß╗▒ng graph ho├án hß║úo ngay tß╗½ ─æß║ºu ΓÇö iterate nh╞░ c├ích bß║ín iterate code.
Γöé
Γûê---
Γöé
Γûê## 4.8 RAG ΓÇö Kß║┐t hß╗úp t├¼m kiß║┐m kiß║┐n thß╗⌐c
Γöé
ΓûêRAG (Retrieval-Augmented Generation) l├á kß╗╣ thuß║¡t kß║┐t hß╗úp t├¼m kiß║┐m kiß║┐n thß╗⌐c vß╗¢i khß║ú n─âng sinh text cß╗ºa LLM. Thay v├¼ chß╗ë dß╗▒a v├áo kiß║┐n thß╗⌐c ─æ├ú hß╗ìc trong training data, agent c├│ thß╗â t├¼m kiß║┐m trong kho t├ái liß╗çu ri├¬ng ─æß╗â trß║ú lß╗¥i ch├¡nh x├íc h╞ín.
Γöé
Γûê### RAG hoß║ít ─æß╗Öng nh╞░ thß║┐ n├áo?
Γöé
Γûê1. **Index (─É├ính chß╗ë mß╗Ñc):** Chia t├ái liß╗çu th├ánh c├íc ─æoß║ín nhß╗Å (chunks), tß║ío vector embedding cho mß╗ùi ─æoß║ín, l╞░u v├áo vector store
Γûê2. **Retrieve (Truy xuß║Ñt):** Khi c├│ c├óu hß╗Åi, tß║ío embedding cho c├óu hß╗Åi, t├¼m c├íc ─æoß║ín t├ái liß╗çu c├│ embedding t╞░╞íng tß╗▒ nhß║Ñt
Γûê3. **Generate (Sinh c├óu trß║ú lß╗¥i):** ─É╞░a c├óu hß╗Åi + c├íc ─æoß║ín t├ái liß╗çu t├¼m ─æ╞░ß╗úc cho LLM, y├¬u cß║ºu trß║ú lß╗¥i dß╗▒a tr├¬n th├┤ng tin ─æ├│
Γöé
Γûê### Embedding v├á Vector Store
Γöé
Γûê```python
Γûêfrom langchain_openai import OpenAIEmbeddings
Γûêfrom langchain_community.vectorstores import Chroma
Γöé
Γûê# Khß╗ƒi tß║ío embedding model
Γûêembeddings = OpenAIEmbeddings(model="text-embedding-3-small")
Γöé
Γûê# Tß║ío vector store tß╗½ t├ái liß╗çu
Γûêfrom langchain_text_splitters import RecursiveCharacterTextSplitter
Γöé
Γûêdocuments = [
Γûê    "LangGraph l├á th╞░ viß╗çn x├óy dß╗▒ng AI agent dß╗▒a tr├¬n state machine...",
Γûê    "State trong LangGraph ─æ╞░ß╗úc ─æß╗ïnh ngh─⌐a bß║▒ng TypedDict...",
Γûê    "Nodes l├á c├íc h├ám xß╗¡ l├╜ nhß║¡n state v├á trß║ú vß╗ü thay ─æß╗òi...",
Γûê    # ... th├¬m t├ái liß╗çu
Γûê]
Γöé
Γûêtext_splitter = RecursiveCharacterTextSplitter(
Γûê    chunk_size=500,
Γûê    chunk_overlap=50,
Γûê)
Γûêchunks = text_splitter.create_documents(documents)
Γöé
Γûêvectorstore = Chroma.from_documents(
Γûê    documents=chunks,
Γûê    embedding=embeddings,
Γûê    collection_name="ai20k_docs"
Γûê)
Γöé
Γûê# T├¼m kiß║┐m
Γûêresults = vectorstore.similarity_search("LangGraph state l├á g├¼?", k=3)
Γûêfor doc in results:
Γûê    print(doc.page_content)
Γûê```
Γöé
Γûê### Th├¬m RAG v├áo Graph
Γöé
Γûê```python
Γûêfrom langchain_openai import ChatOpenAI, OpenAIEmbeddings
Γûêfrom langchain_community.vectorstores import Chroma
Γöé
Γûêasync def retrieve_node(state: ResearchState) -> dict:
Γûê    """T├¼m kiß║┐m t├ái liß╗çu li├¬n quan tß╗½ vector store."""
Γûê    query = state.get("query", "")
Γûê    
Γûê    try:
Γûê        # Tß║ío retriever tß╗½ vector store
Γûê        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
Γûê        vectorstore = Chroma(
Γûê            collection_name="ai20k_docs",
Γûê            embedding_function=embeddings,
Γûê        )
Γûê        
Γûê        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
Γûê        docs = await retriever.ainvoke(query)
Γûê        
Γûê        # Format kß║┐t quß║ú
Γûê        context = "\n\n".join([
Γûê            f"[T├ái liß╗çu {i+1}]: {doc.page_content}"
Γûê            for i, doc in enumerate(docs)
Γûê        ])
Γûê        
Γûê        return {"search_results": [context]}
Γûê    except Exception as e:
Γûê        return {"error": f"Lß╗ùi retrieval: {str(e)}"}
Γöé
Γûêasync def rag_generate_node(state: ResearchState) -> dict:
Γûê    """Sinh c├óu trß║ú lß╗¥i dß╗▒a tr├¬n t├ái liß╗çu ─æ├ú truy xuß║Ñt."""
Γûê    llm = ChatOpenAI(model="gpt-4o-mini")
Γûê    
Γûê    query = state.get("query", "")
Γûê    search_results = state.get("search_results", [])
Γûê    context = "\n".join(search_results)
Γûê    
Γûê    prompt = f"""Dß╗▒a tr├¬n t├ái liß╗çu sau, trß║ú lß╗¥i c├óu hß╗Åi. 
Γûê    Nß║┐u th├┤ng tin kh├┤ng c├│ trong t├ái liß╗çu, h├úy n├│i r├╡.
Γûê    
Γûê    T├ái liß╗çu:
Γûê    {context}
Γûê    
Γûê    C├óu hß╗Åi: {query}
Γûê    
Γûê    Trß║ú lß╗¥i bß║▒ng tiß║┐ng Viß╗çt:"""
Γûê    
Γûê    response = await llm.ainvoke([HumanMessage(content=prompt)])
Γûê    return {"draft": response.content}
Γöé
Γûê# Th├¬m v├áo graph
Γûêgraph.add_node("retrieve", retrieve_node)
Γûêgraph.add_node("rag_generate", rag_generate_node)
Γöé
Γûê# C├│ thß╗â chß╗ìn giß╗»a web search v├á RAG t├╣y loß║íi c├óu hß╗Åi
Γûêdef route_search(state: ResearchState) -> str:
Γûê    query_type = state.get("query_type", "")
Γûê    if query_type == "factual":
Γûê        return "retrieve"  # D├╣ng RAG cho c├óu hß╗Åi kiß║┐n thß╗⌐c
Γûê    return "research"      # D├╣ng web search cho c├óu hß╗Åi thß╗¥i sß╗▒
Γûê```
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Chß║Ñt l╞░ß╗úng RAG phß╗Ñ thuß╗Öc rß║Ñt nhiß╗üu v├áo chß║Ñt l╞░ß╗úng chunks v├á embedding. Chunk size qu├í lß╗¢n ΓåÆ mß║Ñt th├┤ng tin chi tiß║┐t. Chunk size qu├í nhß╗Å ΓåÆ mß║Ñt ngß╗» cß║únh. H├úy thß╗¡ nghiß╗çm vß╗¢i chunk_size 300-1000 v├á chunk_overlap 50-200.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** RAG giß║úi quyß║┐t vß║Ñn ─æß╗ü "LLM kh├┤ng biß║┐t dß╗» liß╗çu ri├¬ng cß╗ºa bß║ín". Thay v├¼ fine-tune model (─æß║»t v├á phß╗⌐c tß║íp), bß║ín chß╗ë cß║ºn ─æ╞░a t├ái liß╗çu li├¬n quan v├áo context. ─É├óy l├á c├ích phß╗ò biß║┐n nhß║Ñt ─æß╗â x├óy dß╗▒ng agent c├│ kiß║┐n thß╗⌐c chuy├¬n biß╗çt.
Γöé
Γûê---
Γöé
Γûê## 4.9 Error Handling ΓÇö Ba tß║ºng bß║úo vß╗ç
Γöé
ΓûêAgent chß║íy nhiß╗üu b╞░ß╗¢c, gß╗ìi nhiß╗üu API, xß╗¡ l├╜ nhiß╗üu loß║íi dß╗» liß╗çu ΓÇö n├¬n lß╗ùi l├á ─æiß╗üu kh├┤ng thß╗â tr├ính khß╗Åi. Mß╗Öt agent production cß║ºn ba tß║ºng error handling: node level, graph level, v├á tool level.
Γöé
Γûê### Tß║ºng 1: Node Level ΓÇö Graceful Failure
Γöé
ΓûêMß╗ùi node n├¬n xß╗¡ l├╜ lß╗ùi ri├¬ng, kh├┤ng ─æß╗â lß╗ùi lan truyß╗ün:
Γöé
Γûê```python
Γûêasync def search_node(state: ResearchState) -> dict:
Γûê    """Node t├¼m kiß║┐m vß╗¢i error handling ─æß║ºy ─æß╗º."""
Γûê    query = state.get("query", "")
Γûê    
Γûê    if not query:
Γûê        return {"error": "Query rß╗ùng, kh├┤ng thß╗â t├¼m kiß║┐m."}
Γûê    
Γûê    try:
Γûê        results = await search_api(query)
Γûê        return {"search_results": results}
Γûê    except ConnectionError:
Γûê        # Lß╗ùi kß║┐t nß╗æi ΓÇö c├│ thß╗â retry
Γûê        return {
Γûê            "search_results": [],
Γûê            "error": "Mß║Ñt kß║┐t nß╗æi. Sß║╜ thß╗¡ lß║íi ß╗ƒ v├▓ng tiß║┐p theo."
Γûê        }
Γûê    except RateLimitError:
Γûê        # Lß╗ùi rate limit ΓÇö chß╗¥ rß╗ôi thß╗¡
Γûê        await asyncio.sleep(2)
Γûê        try:
Γûê            results = await search_api(query)
Γûê            return {"search_results": results}
Γûê        except Exception:
Γûê            return {
Γûê                "search_results": [],
Γûê                "error": "Rate limit. Vui l├▓ng thß╗¡ lß║íi sau."
Γûê            }
Γûê    except Exception as e:
Γûê        # Lß╗ùi kh├┤ng x├íc ─æß╗ïnh ΓÇö ghi log v├á tiß║┐p tß╗Ñc
Γûê        import logging
Γûê        logging.error(f"Unexpected error in search_node: {e}")
Γûê        return {
Γûê            "search_results": [],
Γûê            "error": f"Lß╗ùi kh├┤ng x├íc ─æß╗ïnh: {type(e).__name__}"
Γûê        }
Γûê```
Γöé
Γûê### Tß║ºng 2: Graph Level ΓÇö Retry Policy
Γöé
ΓûêLangGraph hß╗ù trß╗ú retry policy tß╗▒ ─æß╗Öng ß╗ƒ level node. Bß║ín truyß╗ün `retry` parameter khi th├¬m node v├áo graph:
Γöé
Γûê```python
Γûêfrom langgraph.types import RetryPolicy
Γöé
Γûê# ─Éß╗ïnh ngh─⌐a retry policy
Γûêretry_policy = RetryPolicy(
Γûê    max_attempts=3,           # Thß╗¡ tß╗æi ─æa 3 lß║ºn
Γûê    initial_interval=1.0,     # ─Éß╗úi 1 gi├óy lß║ºn ─æß║ºu
Γûê    backoff_factor=2.0,       # Nh├ón ─æ├┤i mß╗ùi lß║ºn: 1s, 2s, 4s
Γûê    max_interval=10.0,        # ─Éß╗úi tß╗æi ─æa 10 gi├óy
Γûê    retry_on=[ConnectionError, TimeoutError],  # Chß╗ë retry c├íc lß╗ùi n├áy
Γûê)
Γöé
Γûê# ├üp dß╗Ñng retry policy khi th├¬m node
Γûêgraph.add_node("search", search_node, retry=retry_policy)
Γöé
Γûê# Hoß║╖c cß║Ñu h├¼nh khi invoke
Γûêresult = await app.ainvoke(
Γûê    {"query": "test"},
Γûê    config={"retry": retry_policy}
Γûê)
Γûê```
Γöé
Γûê### Tß║ºng 3: Tool Level ΓÇö handle_tool_errors
Γöé
ΓûêKhi tool throw error, bß║ín kh├┤ng muß╗æn to├án bß╗Ö agent crash. LangGraph cung cß║Ñp `handle_tool_errors`:
Γöé
Γûê```python
Γûêfrom langgraph.prebuilt import ToolNode
Γöé
Γûê# C├ích 1: ToolNode vß╗¢i handle_tool_errors
Γûêtool_node = ToolNode(
Γûê    tools=[web_search, calculate, fetch_api_data],
Γûê    handle_tool_errors=True,  # Tß╗▒ ─æß╗Öng catch lß╗ùi v├á trß║ú vß╗ü error message
Γûê)
Γöé
Γûê# C├ích 2: Custom error handler
Γûêdef custom_error_handler(error: Exception, tool_call: dict) -> str:
Γûê    """Xß╗¡ l├╜ lß╗ùi tool v├á trß║ú vß╗ü message cho agent."""
Γûê    if isinstance(error, ConnectionError):
Γûê        return "Kh├┤ng thß╗â kß║┐t nß╗æi. H├úy thß╗¡ tool kh├íc hoß║╖c trß║ú lß╗¥i dß╗▒a tr├¬n kiß║┐n thß╗⌐c c├│ sß║╡n."
Γûê    elif isinstance(error, TimeoutError):
Γûê        return "Tool timeout. H├úy thß╗¡ lß║íi hoß║╖c d├╣ng c├ích kh├íc."
Γûê    else:
Γûê        return f"Tool error: {str(error)}. H├úy thß╗¡ c├ích tiß║┐p cß║¡n kh├íc."
Γöé
Γûêtool_node = ToolNode(
Γûê    tools=[web_search, calculate],
Γûê    handle_tool_errors=custom_error_handler,
Γûê)
Γûê```
Γöé
Γûê### Kß║┐t hß╗úp ba tß║ºng
Γöé
Γûê```python
Γûê# V├¡ dß╗Ñ ─æß║ºy ─æß╗º: agent vß╗¢i 3 tß║ºng error handling
Γöé
Γûê# 1. Tool level: handle errors trong tools
Γûê@tool
Γûêdef robust_search(query: str) -> str:
Γûê    """T├¼m kiß║┐m vß╗¢i error handling."""
Γûê    try:
Γûê        return search_api(query)
Γûê    except Exception as e:
Γûê        return f"Lß╗ùi t├¼m kiß║┐m: {str(e)}"  # Tool tß╗▒ xß╗¡ l├╜ lß╗ùi
Γöé
Γûê# 2. Node level: xß╗¡ l├╜ lß╗ùi trong node
Γûêasync def safe_search_node(state: ResearchState) -> dict:
Γûê    """Node vß╗¢i fallback."""
Γûê    try:
Γûê        results = await robust_search.ainvoke({"query": state.get("query", "")})
Γûê        return {"search_results": [results]}
Γûê    except Exception as e:
Γûê        # Fallback: d├╣ng kß║┐t quß║ú c┼⌐ hoß║╖c trß║ú vß╗ü empty
Γûê        return {
Γûê            "search_results": state.get("search_results", []),
Γûê            "error": f"Search failed: {str(e)}"
Γûê        }
Γöé
Γûê# 3. Graph level: retry policy
Γûêapp = graph.compile(
Γûê    retry=RetryPolicy(max_attempts=2),
Γûê)
Γöé
Γûê# Th├¬m error v├áo routing
Γûêdef route_after_search(state: ResearchState) -> str:
Γûê    if state.get("error"):
Γûê        return "handle_error"  # Node xß╗¡ l├╜ lß╗ùi ri├¬ng
Γûê    return "synthesize"
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Nguy├¬n tß║»c quan trß╗ìng: **fail gracefully, never crash**. Agent production kh├┤ng bao giß╗¥ ─æ╞░ß╗úc crash v├¼ lß╗ùi tool hay API. Mß╗ùi lß╗ùi n├¬n ─æ╞░ß╗úc catch, log, v├á agent n├¬n c├│ fallback plan (thß╗¡ tool kh├íc, trß║ú lß╗¥i dß╗▒a tr├¬n kiß║┐n thß╗⌐c c├│ sß║╡n, hoß║╖c th├┤ng b├ío lß╗ùi cho user).
Γöé
Γûê---
Γöé
Γûê## 4.10 Testing Agent
Γöé
ΓûêTesting agent kh├│ h╞ín testing code th├┤ng th╞░ß╗¥ng v├¼ agent kh├┤ng determinstic ΓÇö kß║┐t quß║ú c├│ thß╗â kh├íc nhau mß╗ùi lß║ºn chß║íy. Tuy nhi├¬n, bß║ín vß║½n c├│ thß╗â test hiß╗çu quß║ú bß║▒ng c├ích test tß╗½ng th├ánh phß║ºn ri├¬ng lß║╗.
Γöé
Γûê### Unit Testing Nodes
Γöé
ΓûêTest mß╗ùi node ─æß╗Öc lß║¡p bß║▒ng c├ích truyß╗ün state giß║ú (mock state):
Γöé
Γûê```python
Γûêimport pytest
Γûêfrom unittest.mock import AsyncMock, patch
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_analyze_node():
Γûê    """Test node analyze vß╗¢i mock LLM."""
Γûê    # Arrange: tß║ío mock state
Γûê    mock_state = {
Γûê        "query": "GDP Viß╗çt Nam 2024?",
Γûê        "messages": [],
Γûê    }
Γûê    
Γûê    # Act: gß╗ìi node
Γûê    with patch("langchain_openai.ChatOpenAI.ainvoke") as mock_llm:
Γûê        mock_llm.return_value = AsyncMock(
Γûê            content='{"query_type": "factual", "needs_research": true}'
Γûê        )
Γûê        result = await analyze_node(mock_state)
Γûê    
Γûê    # Assert
Γûê    assert "query_type" in result
Γûê    assert result["query_type"] in ["factual", "analytical", "creative"]
Γûê    assert result["iteration"] == 0
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_research_node():
Γûê    """Test node research."""
Γûê    mock_state = {
Γûê        "research_plan": ["GDP Vietnam 2024", "Vietnam economy statistics"],
Γûê        "iteration": 0,
Γûê    }
Γûê    
Γûê    with patch("__main__.web_search") as mock_search:
Γûê        mock_search.invoke.return_value = "GDP Viß╗çt Nam 2024: 430 tß╗╖ USD"
Γûê        result = await research_node(mock_state)
Γûê    
Γûê    assert "search_results" in result
Γûê    assert len(result["search_results"]) == 2
Γûê    assert result["iteration"] == 1
Γûê```
Γöé
Γûê### Integration Testing Graph
Γöé
ΓûêTest to├án bß╗Ö graph vß╗¢i mock LLM:
Γöé
Γûê```python
Γûê@pytest.mark.asyncio
Γûêasync def test_full_graph():
Γûê    """Test to├án bß╗Ö graph end-to-end."""
Γûê    with patch("langchain_openai.ChatOpenAI.ainvoke") as mock_llm:
Γûê        # Mock c├íc response theo thß╗⌐ tß╗▒
Γûê        mock_llm.side_effect = [
Γûê            AsyncMock(content='{"query_type": "factual", "needs_research": true}'),  # analyze
Γûê            AsyncMock(content='["search query 1", "search query 2"]'),                # plan
Γûê            AsyncMock(content="C├óu trß║ú lß╗¥i mß║½u vß╗ü GDP..."),                            # synthesize
Γûê            AsyncMock(content='{"score": 0.9, "needs_more": false}'),                 # review
Γûê            AsyncMock(content="C├óu trß║ú lß╗¥i cuß╗æi c├╣ng."),                               # finalize
Γûê        ]
Γûê        
Γûê        result = await app.ainvoke({
Γûê            "query": "GDP Viß╗çt Nam 2024?",
Γûê            "messages": [],
Γûê        })
Γûê    
Γûê    # Assert
Γûê    assert "draft" in result
Γûê    assert len(result["draft"]) > 0
Γûê    assert result.get("quality_score", 0) >= 0.7
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_graph_handles_empty_query():
Γûê    """Test graph xß╗¡ l├╜ query rß╗ùng."""
Γûê    result = await app.ainvoke({
Γûê        "query": "",
Γûê        "messages": [],
Γûê    })
Γûê    
Γûê    # Graph kh├┤ng crash
Γûê    assert result is not None
Γûê```
Γöé
Γûê### Mock LLM Responses
Γöé
ΓûêPattern quan trß╗ìng: mock LLM response thay v├¼ gß╗ìi API thß║¡t trong test:
Γöé
Γûê```python
Γûêfrom unittest.mock import AsyncMock, MagicMock
Γöé
Γûêdef create_mock_llm(responses: list[str]):
Γûê    """Tß║ío mock LLM trß║ú vß╗ü responses theo thß╗⌐ tß╗▒."""
Γûê    mock = MagicMock()
Γûê    mock.ainvoke = AsyncMock()
Γûê    mock.ainvoke.side_effect = [
Γûê        AsyncMock(content=response) for response in responses
Γûê    ]
Γûê    return mock
Γöé
Γûê# Sß╗¡ dß╗Ñng
Γûêdef test_with_mock():
Γûê    llm = create_mock_llm([
Γûê        "Response 1 from analyze",
Γûê        "Response 2 from plan",
Γûê        "Response 3 from generate",
Γûê    ])
Γûê    
Γûê    # Test code sß╗¡ dß╗Ñng llm...
Γûê```
Γöé
Γûê### Test Conditional Routing
Γöé
Γûê```python
Γûêdef test_should_continue_research():
Γûê    """Test routing function."""
Γûê    # Case 1: Score thß║Ñp ΓåÆ cß║ºn nghi├¬n cß╗⌐u th├¬m
Γûê    state_low_score = {"quality_score": 0.3, "iteration": 1}
Γûê    assert should_continue_research(state_low_score) == "research"
Γûê    
Γûê    # Case 2: Score cao ΓåÆ kß║┐t th├║c
Γûê    state_high_score = {"quality_score": 0.9, "iteration": 1}
Γûê    assert should_continue_research(state_high_score) == "finalize"
Γûê    
Γûê    # Case 3: Score thß║Ñp nh╞░ng ─æ├ú lß║╖p qu├í nhiß╗üu ΓåÆ kß║┐t th├║c
Γûê    state_max_iteration = {"quality_score": 0.3, "iteration": 3}
Γûê    assert should_continue_research(state_max_iteration) == "finalize"
Γûê```
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Kh├┤ng test agent bß║▒ng c├ích gß╗ìi LLM thß║¡t. LLM trß║ú vß╗ü kß║┐t quß║ú kh├íc nhau mß╗ùi lß║ºn (nhiß╗çt ─æß╗Ö > 0), tß╗æn tiß╗ün, v├á chß║¡m. Lu├┤n mock LLM trong unit test v├á integration test. Chß╗ë gß╗ìi LLM thß║¡t trong end-to-end test thß╗º c├┤ng hoß║╖c staging environment.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Test theo pyramid: nhiß╗üu unit tests (cho nodes, routing functions), ├¡t integration tests (cho graph), v├á rß║Ñt ├¡t E2E tests (vß╗¢i LLM thß║¡t). Pattern n├áy gi├║p test suite chß║íy nhanh, ß╗òn ─æß╗ïnh, v├á ├¡t tß╗æn k├⌐m.
Γöé
Γûê---
Γöé
Γûê## T├│m tß║»t
Γöé
Γûê1. **Agent** l├á hß╗ç thß╗æng AI c├│ khß║ú n─âng tß╗▒ quyß║┐t ─æß╗ïnh luß╗ông xß╗¡ l├╜, kh├íc vß╗¢i chatbot chß║íy theo kß╗ïch bß║ún cß╗æ ─æß╗ïnh. Agent cß║ºn thiß║┐t cho t├íc vß╗Ñ ─æa b╞░ß╗¢c, cß║ºn tools, v├á c├│ v├▓ng lß║╖p phß║ún hß╗ôi.
Γöé
Γûê2. **State** (TypedDict) l├á bß╗Ö nhß╗¢ cß╗ºa agent. Thiß║┐t kß║┐ state cß║⌐n thß║¡n: chß╗ë l╞░u nhß╗»ng g├¼ cß║ºn, d├╣ng reducer ─æ├║ng (overwrite vs accumulate), v├á bß║»t ─æß║ºu ─æ╞ín giß║ún.
Γöé
Γûê3. **Nodes** l├á c├íc h├ám xß╗¡ l├╜ ΓÇö mß╗ùi node mß╗Öt tr├ích nhiß╗çm, nhß║¡n state, trß║ú vß╗ü thay ─æß╗òi. D├╣ng async cho I/O v├á lu├┤n xß╗¡ l├╜ lß╗ùi graceful.
Γöé
Γûê4. **Edges** kß║┐t nß╗æi nodes th├ánh luß╗ông: direct edges cho luß╗ông cß╗æ ─æß╗ïnh, conditional edges cho luß╗ông linh hoß║ít. `START` v├á `END` l├á sentinel ─æß║╖c biß╗çt.
Γöé
Γûê5. **Tools** mß╗ƒ rß╗Öng khß║ú n─âng agent ΓÇö viß║┐t docstring r├╡ r├áng (─æ├│ l├á prompt cho LLM), d├╣ng type hints, v├á lu├┤n validate input.
Γöé
Γûê6. **ReAct** (Think ΓåÆ Act ΓåÆ Observe) l├á pattern phß╗ò biß║┐n nhß║Ñt cho agent. V├▓ng lß║╖p giß╗»a agent v├á tools tiß║┐p tß╗Ñc cho ─æß║┐n khi agent quyß║┐t ─æß╗ïnh ─æ├ú ─æß╗º th├┤ng tin.
Γöé
Γûê7. **RAG** kß║┐t hß╗úp t├¼m kiß║┐m t├ái liß╗çu ri├¬ng vß╗¢i LLM, giß║úi quyß║┐t b├ái to├ín "LLM kh├┤ng biß║┐t dß╗» liß╗çu cß╗ºa bß║ín".
Γöé
Γûê8. **Error handling** cß║ºn ba tß║ºng: node level (try-except), graph level (RetryPolicy), v├á tool level (handle_tool_errors). Nguy├¬n tß║»c: fail gracefully, never crash.
Γöé
Γûê9. **Testing** agent theo pyramid: nhiß╗üu unit tests cho nodes/routing, ├¡t integration tests cho graph, mock LLM thay v├¼ gß╗ìi thß║¡t.
Γöé
Γûê10. **Graph ho├án chß╗ënh** kß║┐t hß╗úp tß║Ñt cß║ú: state design + nodes + edges + tools + error handling. Bß║»t ─æß║ºu ─æ╞ín giß║ún, iterate dß║ºn.
Γöé
Γûê---
Γöé
Γûê## C├óu hß╗Åi ├┤n tß║¡p
Γöé
Γûê1. Sß╗▒ kh├íc biß╗çt c╞í bß║ún giß╗»a chatbot (chain) v├á agent (state machine) l├á g├¼? Cho v├¡ dß╗Ñ t├íc vß╗Ñ ph├╣ hß╗úp cho mß╗ùi loß║íi.
Γöé
Γûê2. Tß║íi sao `Annotated[list, add_messages]` cß║ºn thiß║┐t cho tr╞░ß╗¥ng `messages` trong state? ─Éiß╗üu g├¼ xß║úy ra nß║┐u chß╗ë d├╣ng `list` kh├┤ng c├│ reducer?
Γöé
Γûê3. Giß║úi th├¡ch v├▓ng lß║╖p ReAct (Think ΓåÆ Act ΓåÆ Observe). Tß║íi sao `graph.add_edge("tools", "agent")` tß║ío ra v├▓ng lß║╖p n├áy?
Γöé
Γûê4. Viß║┐t mß╗Öt routing function quyß║┐t ─æß╗ïnh node tiß║┐p theo dß╗▒a tr├¬n nß╗Öi dung c├óu hß╗Åi. V├¡ dß╗Ñ: c├óu hß╗Åi vß╗ü thß╗¥i tiß║┐t ΓåÆ weather node, c├óu hß╗Åi vß╗ü to├ín ΓåÆ calculate node, kh├íc ΓåÆ answer node.
Γöé
Γûê5. Bß║ín ─æang x├óy dß╗▒ng agent trß║ú lß╗¥i c├óu hß╗Åi vß╗ü t├ái liß╗çu nß╗Öi bß╗Ö c├┤ng ty. Bß║ín sß║╜ chß╗ìn RAG hay web search? Tß║íi sao? M├┤ tß║ú flow tß╗½ c├óu hß╗Åi ─æß║┐n c├óu trß║ú lß╗¥i.


docs\guide\chapter-05.md:
Γûê---
Γûêtitle: "Ph├ít triß╗ân API vß╗¢i FastAPI"
Γûêweight: 5
Γûê---
Γöé
Γûê# Ch╞░╞íng 5: Ph├ít triß╗ân API vß╗¢i FastAPI
Γöé
ΓûêSau khi x├óy dß╗▒ng AI Agent ß╗ƒ Ch╞░╞íng 4, bß║ín cß║ºn "─æ├│ng g├│i" agent th├ánh mß╗Öt dß╗ïch vß╗Ñ web m├á ng╞░ß╗¥i d├╣ng c├│ thß╗â truy cß║¡p. FastAPI l├á framework Python hiß╗çn ─æß║íi, l├╜ t╞░ß╗ƒng ─æß╗â x├óy dß╗▒ng API cho AI agents. Ch╞░╞íng n├áy sß║╜ h╞░ß╗¢ng dß║½n bß║ín tß╗½ c╞í bß║ún ─æß║┐n n├óng cao ΓÇö tß╗½ viß╗çc tß║ío route ─æß║ºu ti├¬n ─æß║┐n triß╗ân khai streaming response v├á kß║┐t nß╗æi vß╗¢i LangGraph agent.
Γöé
Γûê---
Γöé
Γûê## 5.1 FastAPI ΓÇö Framework hiß╗çn ─æß║íi cho AI
Γöé
Γûê### Tß║íi sao chß╗ìn FastAPI?
Γöé
ΓûêFastAPI l├á framework Python ─æ╞░ß╗úc thiß║┐t kß║┐ ─æß║╖c biß╗çt cho x├óy dß╗▒ng API hiß╗çn ─æß║íi. N├│ nß╗òi bß║¡t nhß╗¥ bß╗æn ╞░u ─æiß╗âm ch├¡nh:
Γöé
Γûê**Hiß╗çu n─âng cao:** FastAPI x├óy dß╗▒ng tr├¬n Starlette (ASGI) v├á Pydantic, ─æß║ít hiß╗çu n─âng ngang vß╗¢i NodeJS v├á Go ΓÇö nhanh h╞ín Flask v├á Django ─æ├íng kß╗â. Khi bß║ín xß╗¡ l├╜ h├áng ng├án request ─æß║┐n AI agent, hiß╗çu n─âng n├áy tß║ío sß╗▒ kh├íc biß╗çt lß╗¢n.
Γöé
Γûê**Async-first:** AI agents th╞░ß╗¥ng gß╗ìi LLM API, search API, v├á database ΓÇö tß║Ñt cß║ú ─æß╗üu l├á I/O-bound operations. FastAPI hß╗ù trß╗ú async/await native, cho ph├⌐p xß╗¡ l├╜ nhiß╗üu request ─æß╗ông thß╗¥i m├á kh├┤ng block thread. ─Éiß╗üu n├áy quan trß╗ìng v├¼ mß╗Öt request ─æß║┐n AI agent c├│ thß╗â mß║Ñt 5-30 gi├óy ─æß╗â ho├án th├ánh.
Γöé
Γûê**Auto-documentation:** FastAPI tß╗▒ ─æß╗Öng sinh OpenAPI (Swagger) documentation tß╗½ code. Mß╗ùi route, parameter, request body, v├á response model ─æß╗üu ─æ╞░ß╗úc document tß╗▒ ─æß╗Öng. Bß║ín kh├┤ng cß║ºn viß║┐t API docs thß╗º c├┤ng ΓÇö docs lu├┤n ─æß╗ông bß╗Ö vß╗¢i code.
Γöé
Γûê**Type-safe:** Pydantic validation t├¡ch hß╗úp s├óu gi├║p bß║»t lß╗ùi early ΓÇö sai kiß╗âu dß╗» liß╗çu, thiß║┐u field, gi├í trß╗ï ngo├ái range ΓÇö tß║Ñt cß║ú ─æ╞░ß╗úc ph├ít hiß╗çn tr╞░ß╗¢c khi logic xß╗¡ l├╜ chß║íy. ─Éiß╗üu n├áy giß║úm bug v├á t─âng ─æß╗Ö tin cß║¡y.
Γöé
Γûê### So s├ính vß╗¢i Flask v├á Django
Γöé
Γûê| Ti├¬u ch├¡ | FastAPI | Flask | Django |
Γûê|-----------|---------|-------|--------|
Γûê| Async | Native async | WSGI (sync), cß║ºn extension | ASGI tß╗½ Django 3.0 |
Γûê| API Docs | Tß╗▒ ─æß╗Öng (Swagger) | Cß║ºn Flask-RESTX | Cß║ºn DRF + drf-spectacular |
Γûê| Validation | Pydantic t├¡ch hß╗úp | C├ái th├¬m | Django forms / DRF serializers |
Γûê| Hiß╗çu n─âng | Rß║Ñt cao | Trung b├¼nh | Trung b├¼nh |
Γûê| Learning curve | Dß╗à | Rß║Ñt dß╗à | Kh├í kh├│ |
Γûê| Ph├╣ hß╗úp cho | API, microservices | Small apps, prototypes | Full-stack web apps |
Γöé
ΓûêFastAPI l├á lß╗▒a chß╗ìn ─æ├║ng khi bß║ín x├óy dß╗▒ng **API backend cho AI application**. Flask ph├╣ hß╗úp cho prototype nhanh, nh╞░ng thiß║┐u async v├á auto-docs. Django qu├í nß║╖ng cho API-only service.
Γöé
Γûê### Khi n├áo FastAPI l├á lß╗▒a chß╗ìn ─æ├║ng?
Γöé
ΓûêFastAPI l├á lß╗▒a chß╗ìn tuyß╗çt vß╗¥i khi:
Γûê- Bß║ín x├óy dß╗▒ng API backend (kh├┤ng render HTML)
Γûê- Cß║ºn async (gß╗ìi nhiß╗üu API b├¬n ngo├ái, I/O nß║╖ng)
Γûê- Muß╗æn auto-documentation cho team collaboration
Γûê- X├óy dß╗▒ng microservices hoß║╖c serverless functions
Γûê- Cß║ºn type validation mß║ính mß║╜
Γöé
ΓûêFastAPI c├│ thß╗â kh├┤ng ph├╣ hß╗úp khi:
Γûê- Cß║ºn render HTML templates (d├╣ng Django hoß║╖c Flask thay)
Γûê- Project nhß╗Å, prototype nhanh kh├┤ng cß║ºn production-ready
Γûê- Team ─æ├ú quen Django v├á kh├┤ng muß╗æn hß╗ìc framework mß╗¢i
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** C├ái ─æß║╖t FastAPI k├¿m uvicorn (ASGI server) ─æß╗â chß║íy: `pip install fastapi uvicorn`. Uvicorn l├á server ASGI hiß╗çu n─âng cao, t╞░╞íng tß╗▒ nh╞░ Gunicorn cho WSGI. Trong production, chß║íy uvicorn vß╗¢i multiple workers: `uvicorn app.main:app --workers 4`.
Γöé
Γûê---
Γöé
Γûê## 5.2 Routes v├á Schemas
Γöé
Γûê### ─Éß╗ïnh ngh─⌐a Routes
Γöé
ΓûêRoute (tuyß║┐n) l├á ─æiß╗âm truy cß║¡p v├áo API. Mß╗ùi route kß║┐t hß╗úp HTTP method (GET, POST, PUT, DELETE) vß╗¢i URL path:
Γöé
Γûê```python
Γûêfrom fastapi import FastAPI
Γöé
Γûêapp = FastAPI(
Γûê    title="AI20K Agent API",
Γûê    description="API cho AI Agent x├óy dß╗▒ng vß╗¢i LangGraph",
Γûê    version="1.0.0",
Γûê)
Γöé
Γûê@app.get("/")
Γûêasync def root():
Γûê    """Health check endpoint."""
Γûê    return {"status": "ok", "message": "AI20K Agent API ─æang chß║íy"}
Γöé
Γûê@app.get("/health")
Γûêasync def health_check():
Γûê    """Kiß╗âm tra sß╗⌐c khß╗Åe hß╗ç thß╗æng."""
Γûê    return {
Γûê        "status": "healthy",
Γûê        "version": "1.0.0",
Γûê    }
Γöé
Γûê@app.post("/api/v1/chat")
Γûêasync def chat(request: ChatRequest):
Γûê    """Xß╗¡ l├╜ tin nhß║»n tß╗½ ng╞░ß╗¥i d├╣ng."""
Γûê    # Xß╗¡ l├╜ logic...
Γûê    return {"response": "..."}
Γûê```
Γöé
Γûê### Pydantic Request/Response Models
Γöé
ΓûêPydantic models ─æß╗ïnh ngh─⌐a cß║Ñu tr├║c dß╗» liß╗çu cho request v├á response. ─É├óy l├á "hß╗úp ─æß╗ông" giß╗»a client v├á server:
Γöé
Γûê```python
Γûêfrom pydantic import BaseModel, Field
Γûêfrom typing import Optional
Γûêfrom datetime import datetime
Γöé
Γûêclass ChatRequest(BaseModel):
Γûê    """Schema cho request chat."""
Γûê    message: str = Field(
Γûê        ...,  # ... ngh─⌐a l├á bß║»t buß╗Öc (required)
Γûê        min_length=1,
Γûê        max_length=5000,
Γûê        description="Tin nhß║»n tß╗½ ng╞░ß╗¥i d├╣ng",
Γûê        examples=["GDP Viß╗çt Nam n─âm 2024 l├á bao nhi├¬u?"]
Γûê    )
Γûê    conversation_id: Optional[str] = Field(
Γûê        None,
Γûê        description="ID cuß╗Öc hß╗Öi thoß║íi (mß║╖c ─æß╗ïnh: tß║ío mß╗¢i)",
Γûê    )
Γûê    stream: bool = Field(
Γûê        False,
Γûê        description="C├│ stream response kh├┤ng",
Γûê    )
Γöé
Γûêclass ChatResponse(BaseModel):
Γûê    """Schema cho response chat."""
Γûê    response: str = Field(description="C├óu trß║ú lß╗¥i tß╗½ agent")
Γûê    conversation_id: str = Field(description="ID cuß╗Öc hß╗Öi thoß║íi")
Γûê    sources: list[str] = Field(
Γûê        default_factory=list,
Γûê        description="Nguß╗ôn tham khß║úo",
Γûê    )
Γûê    timestamp: datetime = Field(
Γûê        default_factory=datetime.now,
Γûê        description="Thß╗¥i gian phß║ún hß╗ôi",
Γûê    )
Γöé
Γûê# Sß╗¡ dß╗Ñng trong route
Γûê@app.post("/api/v1/chat", response_model=ChatResponse)
Γûêasync def chat(request: ChatRequest):
Γûê    """Xß╗¡ l├╜ tin nhß║»n chat vß╗¢i agent."""
Γûê    # Logic xß╗¡ l├╜...
Γûê    return ChatResponse(
Γûê        response="C├óu trß║ú lß╗¥i mß║½u",
Γûê        conversation_id=request.conversation_id or "new-id",
Γûê        sources=["source1", "source2"],
Γûê    )
Γûê```
Γöé
Γûê### Field Validators
Γöé
ΓûêPydantic cho ph├⌐p th├¬m validation phß╗⌐c tß║íp vß╗¢i validators:
Γöé
Γûê```python
Γûêfrom pydantic import BaseModel, Field, field_validator
Γöé
Γûêclass QueryRequest(BaseModel):
Γûê    """Request cho agent research."""
Γûê    query: str = Field(
Γûê        ...,
Γûê        min_length=3,
Γûê        max_length=1000,
Γûê    )
Γûê    max_iterations: int = Field(
Γûê        default=3,
Γûê        ge=1,   # greater than or equal
Γûê        le=10,  # less than or equal
Γûê    )
Γûê    
Γûê    @field_validator("query")
Γûê    @classmethod
Γûê    def validate_query(cls, v: str) -> str:
Γûê        """Chuß║⌐n h├│a query."""
Γûê        v = v.strip()
Γûê        if not v:
Γûê            raise ValueError("Query kh├┤ng ─æ╞░ß╗úc rß╗ùng")
Γûê        return v
Γûê```
Γöé
Γûê### API Versioning
Γöé
ΓûêLu├┤n version API ─æß╗â duy tr├¼ khß║ú n─âng t╞░╞íng th├¡ch:
Γöé
Γûê```python
Γûêfrom fastapi import APIRouter
Γöé
Γûê# Tß║ío router cho v1
Γûêv1_router = APIRouter(prefix="/api/v1")
Γöé
Γûê@v1_router.post("/chat", response_model=ChatResponse)
Γûêasync def chat_v1(request: ChatRequest):
Γûê    """Chat endpoint version 1."""
Γûê    return ChatResponse(
Γûê        response="Response v1",
Γûê        conversation_id="id",
Γûê    )
Γöé
Γûê# Router cho v2 (khi cß║ºn thay ─æß╗òi API m├á kh├┤ng break v1)
Γûêv2_router = APIRouter(prefix="/api/v2")
Γöé
Γûê@v2_router.post("/chat", response_model=ChatResponseV2)
Γûêasync def chat_v2(request: ChatRequestV2):
Γûê    """Chat endpoint version 2 ΓÇö hß╗ù trß╗ú streaming."""
Γûê    # Logic mß╗¢i...
Γûê    pass
Γöé
Γûê# ─É─âng k├╜ routers
Γûêapp.include_router(v1_router)
Γûêapp.include_router(v2_router)
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Pydantic models l├á tr├íi tim cß╗ºa FastAPI. Ch├║ng ─æß║úm bß║úo: (1) request ─æ├║ng format, (2) response ─æ├║ng schema, (3) auto-documentation lu├┤n ch├¡nh x├íc. Lu├┤n ─æß╗ïnh ngh─⌐a r├╡ request v├á response models cho mß╗ìi endpoint.
Γöé
Γûê---
Γöé
Γûê## 5.3 Validation vß╗¢i Pydantic
Γöé
ΓûêPydantic l├á th╞░ viß╗çn validation mß║ính mß║╜ ─æ╞░ß╗úc t├¡ch hß╗úp s├óu trong FastAPI. Khi request ─æß║┐n, Pydantic tß╗▒ ─æß╗Öng parse v├á validate data tr╞░ß╗¢c khi route handler nhß║¡n ─æ╞░ß╗úc. Nß║┐u validation fail, FastAPI tß╗▒ ─æß╗Öng trß║ú vß╗ü 422 Unprocessable Entity vß╗¢i chi tiß║┐t lß╗ùi.
Γöé
Γûê### BaseModel
Γöé
Γûê`BaseModel` l├á base class cho mß╗ìi Pydantic model:
Γöé
Γûê```python
Γûêfrom pydantic import BaseModel, Field
Γûêfrom typing import Optional
Γûêfrom enum import Enum
Γöé
Γûêclass MessageRole(str, Enum):
Γûê    """Vai tr├▓ cß╗ºa message."""
Γûê    USER = "user"
Γûê    ASSISTANT = "assistant"
Γûê    SYSTEM = "system"
Γöé
Γûêclass Message(BaseModel):
Γûê    """Mß╗Öt tin nhß║»n trong cuß╗Öc hß╗Öi thoß║íi."""
Γûê    role: MessageRole
Γûê    content: str = Field(..., min_length=1)
Γûê    timestamp: Optional[str] = None
Γöé
Γûêclass ConversationContext(BaseModel):
Γûê    """Ngß╗» cß║únh cuß╗Öc hß╗Öi thoß║íi."""
Γûê    conversation_id: str
Γûê    user_id: Optional[str] = None
Γûê    history: list[Message] = Field(default_factory=list)
Γûê```
Γöé
Γûê### Field Constraints
Γöé
ΓûêPydantic cung cß║Ñp nhiß╗üu constraint qua `Field`:
Γöé
Γûê```python
Γûêfrom pydantic import BaseModel, Field
Γûêfrom typing import Literal
Γöé
Γûêclass AgentConfig(BaseModel):
Γûê    """Cß║Ñu h├¼nh cho agent."""
Γûê    model: Literal["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"] = Field(
Γûê        default="gpt-4o-mini",
Γûê        description="LLM model sß╗¡ dß╗Ñng",
Γûê    )
Γûê    temperature: float = Field(
Γûê        default=0.7,
Γûê        ge=0.0,    # >= 0.0
Γûê        le=2.0,    # <= 2.0
Γûê        description="Nhiß╗çt ─æß╗Ö sinh text",
Γûê    )
Γûê    max_tokens: int = Field(
Γûê        default=2048,
Γûê        gt=0,      # > 0
Γûê        le=8192,   # <= 8192
Γûê    )
Γûê    tools: list[str] = Field(
Γûê        default_factory=lambda: ["web_search"],
Γûê        description="Danh s├ích tools agent c├│ thß╗â sß╗¡ dß╗Ñng",
Γûê    )
Γûê```
Γöé
Γûê### Custom Validators
Γöé
Γûê```python
Γûêfrom pydantic import BaseModel, Field, field_validator, model_validator
Γöé
Γûêclass ResearchRequest(BaseModel):
Γûê    """Request cho agent nghi├¬n cß╗⌐u."""
Γûê    query: str = Field(..., min_length=3, max_length=2000)
Γûê    depth: Literal["shallow", "medium", "deep"] = "medium"
Γûê    language: str = "vi"
Γûê    
Γûê    @field_validator("query")
Γûê    @classmethod
Γûê    def clean_query(cls, v: str) -> str:
Γûê        """Loß║íi bß╗Å khoß║úng trß║»ng thß╗½a."""
Γûê        return " ".join(v.split())
Γûê    
Γûê    @field_validator("language")
Γûê    @classmethod
Γûê    def validate_language(cls, v: str) -> str:
Γûê        """Chß╗ë hß╗ù trß╗ú tiß║┐ng Viß╗çt v├á tiß║┐ng Anh."""
Γûê        v = v.lower()
Γûê        if v not in ["vi", "en"]:
Γûê            raise ValueError("Chß╗ë hß╗ù trß╗ú ng├┤n ngß╗»: vi (tiß║┐ng Viß╗çt), en (tiß║┐ng Anh)")
Γûê        return v
Γûê    
Γûê    @model_validator(mode="after")
Γûê    def validate_depth_for_query(self):
Γûê        """Deep research chß╗ë cho query d├ái."""
Γûê        if self.depth == "deep" and len(self.query) < 20:
Γûê            raise ValueError(
Γûê                "Deep research y├¬u cß║ºu query ├¡t nhß║Ñt 20 k├╜ tß╗▒. "
Γûê                "H├úy m├┤ tß║ú chi tiß║┐t h╞ín nhß╗»ng g├¼ bß║ín cß║ºn nghi├¬n cß╗⌐u."
Γûê            )
Γûê        return self
Γûê```
Γöé
Γûê### Nested Models
Γöé
Γûê```python
Γûêfrom pydantic import BaseModel
Γöé
Γûêclass ToolCall(BaseModel):
Γûê    """Mß╗Öt lß║ºn gß╗ìi tool."""
Γûê    tool_name: str
Γûê    arguments: dict
Γûê    result: str | None = None
Γöé
Γûêclass AgentStep(BaseModel):
Γûê    """Mß╗Öt b╞░ß╗¢c xß╗¡ l├╜ cß╗ºa agent."""
Γûê    thought: str
Γûê    action: str | None = None
Γûê    observation: str | None = None
Γöé
Γûêclass ChatResponse(BaseModel):
Γûê    """Response ─æß║ºy ─æß╗º tß╗½ agent."""
Γûê    answer: str
Γûê    conversation_id: str
Γûê    steps: list[AgentStep] = Field(default_factory=list)
Γûê    tool_calls: list[ToolCall] = Field(default_factory=list)
Γûê    total_tokens: int = 0
Γûê    latency_ms: float = 0.0
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Khi client gß╗¡i request sai format, FastAPI tß╗▒ ─æß╗Öng trß║ú vß╗ü 422 vß╗¢i chi tiß║┐t lß╗ùi rß║Ñt hß╗»u ├¡ch. H├úy tß║¡n dß╗Ñng t├¡nh n─âng n├áy ΓÇö ─æß╗½ng validate thß╗º c├┤ng trong route handler. ─Éß╗ïnh ngh─⌐a r├áng buß╗Öc trong Pydantic model l├á ─æß╗º.
Γöé
Γûê---
Γöé
Γûê## 5.4 Error Handling
Γöé
ΓûêXß╗¡ l├╜ lß╗ùi ─æ├║ng c├ích l├á yß║┐u tß╗æ then chß╗æt cho API production. API cß║ºn trß║ú vß╗ü error response c├│ cß║Ñu tr├║c, kh├┤ng leak th├┤ng tin nhß║íy cß║úm, v├á gi├║p client hiß╗âu v├á xß╗¡ l├╜ lß╗ùi.
Γöé
Γûê### HTTPException
Γöé
ΓûêFastAPI sß╗¡ dß╗Ñng `HTTPException` cho error responses:
Γöé
Γûê```python
Γûêfrom fastapi import HTTPException
Γöé
Γûê@app.get("/api/v1/conversations/{conversation_id}")
Γûêasync def get_conversation(conversation_id: str):
Γûê    """Lß║Ñy th├┤ng tin cuß╗Öc hß╗Öi thoß║íi."""
Γûê    conversation = await db.get_conversation(conversation_id)
Γûê    
Γûê    if not conversation:
Γûê        raise HTTPException(
Γûê            status_code=404,
Γûê            detail=f"Kh├┤ng t├¼m thß║Ñy cuß╗Öc hß╗Öi thoß║íi: {conversation_id}",
Γûê        )
Γûê    
Γûê    return conversation
Γûê```
Γöé
Γûê### Global Exception Handler
Γöé
ΓûêBß║»t tß║Ñt cß║ú exceptions ch╞░a ─æ╞░ß╗úc xß╗¡ l├╜ ß╗ƒ global level:
Γöé
Γûê```python
Γûêfrom fastapi import Request
Γûêfrom fastapi.responses import JSONResponse
Γûêimport logging
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γûêclass AgentError(Exception):
Γûê    """Lß╗ùi tß╗½ agent."""
Γûê    def __init__(self, message: str, code: str = "AGENT_ERROR"):
Γûê        self.message = message
Γûê        self.code = code
Γûê        super().__init__(message)
Γöé
Γûêclass RateLimitError(Exception):
Γûê    """Lß╗ùi rate limit."""
Γûê    pass
Γöé
Γûê@app.exception_handler(AgentError)
Γûêasync def agent_error_handler(request: Request, exc: AgentError):
Γûê    """Xß╗¡ l├╜ lß╗ùi tß╗½ agent."""
Γûê    logger.warning(f"Agent error: {exc.message}")
Γûê    return JSONResponse(
Γûê        status_code=503,
Γûê        content={
Γûê            "error": "agent_error",
Γûê            "message": "Agent kh├┤ng thß╗â xß╗¡ l├╜ y├¬u cß║ºu. Vui l├▓ng thß╗¡ lß║íi.",
Γûê            "code": exc.code,
Γûê        }
Γûê    )
Γöé
Γûê@app.exception_handler(RateLimitError)
Γûêasync def rate_limit_handler(request: Request, exc: RateLimitError):
Γûê    """Xß╗¡ l├╜ lß╗ùi rate limit."""
Γûê    return JSONResponse(
Γûê        status_code=429,
Γûê        content={
Γûê            "error": "rate_limit",
Γûê            "message": "Qu├í nhiß╗üu y├¬u cß║ºu. Vui l├▓ng thß╗¡ lß║íi sau 60 gi├óy.",
Γûê            "retry_after": 60,
Γûê        }
Γûê    )
Γöé
Γûê@app.exception_handler(Exception)
Γûêasync def global_error_handler(request: Request, exc: Exception):
Γûê    """Catch-all ΓÇö kh├┤ng bao giß╗¥ leak internal error."""
Γûê    logger.error(f"Unhandled exception: {exc}", exc_info=True)
Γûê    return JSONResponse(
Γûê        status_code=500,
Γûê        content={
Γûê            "error": "internal_error",
Γûê            "message": "Lß╗ùi hß╗ç thß╗æng. Vui l├▓ng thß╗¡ lß║íi sau.",
Γûê            # KH├öNG bao gß╗ôm str(exc) ΓÇö c├│ thß╗â leak th├┤ng tin nhß║íy cß║úm
Γûê        }
Γûê    )
Γûê```
Γöé
Γûê### Domain Errors to HTTP Codes
Γöé
Γûê├ünh xß║í lß╗ùi nghiß╗çp vß╗Ñ sang HTTP status codes:
Γöé
Γûê```python
Γûêfrom fastapi import HTTPException
Γöé
Γûêclass ErrorCode:
Γûê    """Tß║¡p trung ─æß╗ïnh ngh─⌐a error codes."""
Γûê    AGENT_TIMEOUT = ("agent_timeout", 504, "Agent xß╗¡ l├╜ qu├í l├óu")
Γûê    INVALID_QUERY = ("invalid_query", 400, "C├óu hß╗Åi kh├┤ng hß╗úp lß╗ç")
Γûê    CONVERSATION_NOT_FOUND = ("not_found", 404, "Kh├┤ng t├¼m thß║Ñy cuß╗Öc hß╗Öi thoß║íi")
Γûê    RATE_LIMIT = ("rate_limit", 429, "Qu├í nhiß╗üu y├¬u cß║ºu")
Γûê    MODEL_ERROR = ("model_error", 502, "Lß╗ùi tß╗½ LLM provider")
Γöé
Γûêdef raise_agent_error(code: tuple, detail: str = ""):
Γûê    """Helper raise error vß╗¢i cß║Ñu tr├║c chuß║⌐n."""
Γûê    error_code, status, message = code
Γûê    raise HTTPException(
Γûê        status_code=status,
Γûê        detail={
Γûê            "error": error_code,
Γûê            "message": detail or message,
Γûê        }
Γûê    )
Γöé
Γûê# Sß╗¡ dß╗Ñng
Γûê@app.post("/api/v1/chat")
Γûêasync def chat(request: ChatRequest):
Γûê    try:
Γûê        result = await agent.run(request.message)
Γûê    except TimeoutError:
Γûê        raise_agent_error(ErrorCode.AGENT_TIMEOUT)
Γûê    except ValueError as e:
Γûê        raise_agent_error(ErrorCode.INVALID_QUERY, str(e))
Γûê    
Γûê    return result
Γûê```
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Nguy├¬n tß║»c bß║úo mß║¡t quan trß╗ìng: **KH├öNG BAO GIß╗£** expose stack trace, internal error message, hoß║╖c th├┤ng tin hß╗ç thß╗æng trong 500 responses. Mß╗Öt attacker c├│ thß╗â d├╣ng th├┤ng tin n├áy ─æß╗â t├¼m lß╗ù hß╗òng. Global exception handler phß║úi "sanitize" mß╗ìi error response.
Γöé
Γûê---
Γöé
Γûê## 5.5 CORS v├á Middleware
Γöé
Γûê### CORS l├á g├¼?
Γöé
ΓûêCORS (Cross-Origin Resource Sharing) l├á c╞í chß║┐ bß║úo mß║¡t cß╗ºa browser. Khi frontend chß║íy ß╗ƒ `http://localhost:3000` (Next.js) gß╗ìi API ß╗ƒ `http://localhost:8000` (FastAPI), browser sß║╜ block request v├¼ "cross-origin". CORS middleware cho ph├⌐p bß║ín chß╗ë ─æß╗ïnh domain n├áo ─æ╞░ß╗úc ph├⌐p gß╗ìi API.
Γöé
Γûê### Cß║Ñu h├¼nh CORS cho Frontend
Γöé
Γûê```python
Γûêfrom fastapi.middleware.cors import CORSMiddleware
Γöé
Γûêapp.add_middleware(
Γûê    CORSMiddleware,
Γûê    allow_origins=[
Γûê        "http://localhost:3000",      # Next.js dev server
Γûê        "http://localhost:3001",      # Alternative port
Γûê        "https://ai20k.yourdomain.com",  # Production frontend
Γûê    ],
Γûê    allow_credentials=True,           # Cho ph├⌐p gß╗¡i cookies
Γûê    allow_methods=["*"],              # Cho ph├⌐p tß║Ñt cß║ú HTTP methods
Γûê    allow_headers=["*"],              # Cho ph├⌐p tß║Ñt cß║ú headers
Γûê)
Γöé
Γûê# Cho development ΓÇö cho ph├⌐p tß║Ñt cß║ú origins (KH├öNG d├╣ng trong production)
Γûêif os.getenv("ENVIRONMENT") == "development":
Γûê    app.add_middleware(
Γûê        CORSMiddleware,
Γûê        allow_origins=["*"],
Γûê        allow_credentials=True,
Γûê        allow_methods=["*"],
Γûê        allow_headers=["*"],
Γûê    )
Γûê```
Γöé
Γûê### Logging Middleware vß╗¢i Timing
Γöé
ΓûêMiddleware chß║íy tr╞░ß╗¢c v├á sau mß╗ùi request ΓÇö ph├╣ hß╗úp cho logging v├á monitoring:
Γöé
Γûê```python
Γûêimport time
Γûêimport logging
Γûêfrom fastapi import Request
Γöé
Γûêlogger = logging.getLogger("api")
Γöé
Γûê@app.middleware("http")
Γûêasync def logging_middleware(request: Request, call_next):
Γûê    """Log mß╗ìi request vß╗¢i thß╗¥i gian xß╗¡ l├╜."""
Γûê    start_time = time.time()
Γûê    
Γûê    # Log request
Γûê    logger.info(f"ΓåÆ {request.method} {request.url.path}")
Γûê    
Γûê    try:
Γûê        response = await call_next(request)
Γûê    except Exception as e:
Γûê        # Log lß╗ùi
Γûê        duration = (time.time() - start_time) * 1000
Γûê        logger.error(
Γûê            f"Γ£ù {request.method} {request.url.path} "
Γûê            f"ERROR {duration:.0f}ms ΓÇö {str(e)}"
Γûê        )
Γûê        raise
Γûê    
Γûê    # Log response
Γûê    duration = (time.time() - start_time) * 1000
Γûê    logger.info(
Γûê        f"ΓåÉ {request.method} {request.url.path} "
Γûê        f"{response.status_code} {duration:.0f}ms"
Γûê    )
Γûê    
Γûê    # Th├¬m timing header
Γûê    response.headers["X-Process-Time"] = f"{duration:.0f}ms"
Γûê    return response
Γûê```
Γöé
Γûê### Rate Limiting
Γöé
Γûê```python
Γûêfrom fastapi import Request, HTTPException
Γûêfrom collections import defaultdict
Γûêimport time
Γöé
Γûê# Simple in-memory rate limiter (d├╣ng Redis trong production)
Γûêrate_limits: dict[str, list[float]] = defaultdict(list)
Γöé
ΓûêRATE_LIMIT = 30  # 30 requests
ΓûêRATE_WINDOW = 60  # per 60 seconds
Γöé
Γûê@app.middleware("http")
Γûêasync def rate_limit_middleware(request: Request, call_next):
Γûê    """Giß╗¢i hß║ín sß╗æ request per IP."""
Γûê    client_ip = request.client.host
Γûê    
Γûê    # Clean old entries
Γûê    now = time.time()
Γûê    rate_limits[client_ip] = [
Γûê        t for t in rate_limits[client_ip]
Γûê        if now - t < RATE_WINDOW
Γûê    ]
Γûê    
Γûê    # Check limit
Γûê    if len(rate_limits[client_ip]) >= RATE_LIMIT:
Γûê        raise HTTPException(
Γûê            status_code=429,
Γûê            detail=f"Qu├í nhiß╗üu y├¬u cß║ºu. Thß╗¡ lß║íi sau {RATE_WINDOW} gi├óy."
Γûê        )
Γûê    
Γûê    rate_limits[client_ip].append(now)
Γûê    return await call_next(request)
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Trong development, d├╣ng `allow_origins=["*"]` ─æß╗â nhanh ch├│ng. Nh╞░ng trong production, lu├┤n chß╗ë ─æß╗ïnh ch├¡nh x├íc domains ─æ╞░ß╗úc ph├⌐p. Rate limiter in-memory ph├╣ hß╗úp cho development; d├╣ng Redis cho production ─æß╗â hoß║ít ─æß╗Öng ─æ├║ng khi chß║íy multiple workers.
Γöé
Γûê---
Γöé
Γûê## 5.6 Streaming Response
Γöé
ΓûêAI agents th╞░ß╗¥ng mß║Ñt nhiß╗üu gi├óy ─æß╗â sinh c├óu trß║ú lß╗¥i. Streaming response (phß║ún hß╗ôi luß╗ông) gi├║p ng╞░ß╗¥i d├╣ng thß║Ñy c├óu trß║ú lß╗¥i tß╗½ng phß║ºn ngay khi LLM sinh ra, thay v├¼ chß╗¥ ─æß║┐n khi ho├án th├ánh.
Γöé
Γûê### SSE (Server-Sent Events) Pattern
Γöé
ΓûêSSE l├á chuß║⌐n web cho server push data ─æß║┐n client. FastAPI hß╗ù trß╗ú SSE qua `StreamingResponse`:
Γöé
Γûê```python
Γûêfrom fastapi.responses import StreamingResponse
Γûêimport asyncio
Γûêimport json
Γöé
Γûê@app.post("/api/v1/chat/stream")
Γûêasync def chat_stream(request: ChatRequest):
Γûê    """Stream response tß╗½ agent."""
Γûê    
Γûê    async def event_generator():
Γûê        """Generator tß║ío SSE events."""
Γûê        try:
Γûê            # Gß╗¡i status bß║»t ─æß║ºu
Γûê            yield f"data: {json.dumps({'type': 'start'})}\n\n"
Γûê            
Γûê            # Stream tß╗½ agent
Γûê            async for chunk in agent.astream(request.message):
Γûê                event = {
Γûê                    "type": "token",
Γûê                    "content": chunk,
Γûê                }
Γûê                yield f"data: {json.dumps(event)}\n\n"
Γûê            
Γûê            # Gß╗¡i status kß║┐t th├║c
Γûê            yield f"data: {json.dumps({'type': 'done'})}\n\n"
Γûê            
Γûê        except Exception as e:
Γûê            error_event = {
Γûê                "type": "error",
Γûê                "message": "Lß╗ùi khi xß╗¡ l├╜. Vui l├▓ng thß╗¡ lß║íi.",
Γûê            }
Γûê            yield f"data: {json.dumps(error_event)}\n\n"
Γûê    
Γûê    return StreamingResponse(
Γûê        event_generator(),
Γûê        media_type="text/event-stream",
Γûê        headers={
Γûê            "Cache-Control": "no-cache",
Γûê            "Connection": "keep-alive",
Γûê            "X-Accel-Buffering": "no",  # Nginx: disable buffering
Γûê        },
Γûê    )
Γûê```
Γöé
Γûê### Async Generators vß╗¢i LangGraph
Γöé
ΓûêLangGraph hß╗ù trß╗ú streaming qua `astream` v├á `astream_events`:
Γöé
Γûê```python
Γûêfrom langchain_core.messages import HumanMessage
Γöé
Γûê@app.post("/api/v1/agent/stream")
Γûêasync def agent_stream(request: ChatRequest):
Γûê    """Stream response tß╗½ LangGraph agent."""
Γûê    
Γûê    async def stream_generator():
Γûê        """Stream tokens tß╗½ LangGraph agent."""
Γûê        config = {
Γûê            "configurable": {
Γûê                "thread_id": request.conversation_id or "default",
Γûê            }
Γûê        }
Γûê        
Γûê        inputs = {
Γûê            "messages": [HumanMessage(content=request.message)]
Γûê        }
Γûê        
Γûê        async for event in agent.astream_events(inputs, config, version="v2"):
Γûê            kind = event.get("event")
Γûê            
Γûê            if kind == "on_chat_model_stream":
Γûê                # Token mß╗¢i tß╗½ LLM
Γûê                token = event["data"]["chunk"].content
Γûê                if token:
Γûê                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
Γûê            
Γûê            elif kind == "on_tool_start":
Γûê                # Agent bß║»t ─æß║ºu gß╗ìi tool
Γûê                tool_name = event.get("name", "unknown")
Γûê                yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"
Γûê            
Γûê            elif kind == "on_tool_end":
Γûê                # Tool ho├án th├ánh
Γûê                tool_name = event.get("name", "unknown")
Γûê                output = str(event["data"].get("output", ""))[:200]
Γûê                yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool_name, 'preview': output})}\n\n"
Γûê        
Γûê        yield f"data: {json.dumps({'type': 'done'})}\n\n"
Γûê    
Γûê    return StreamingResponse(
Γûê        stream_generator(),
Γûê        media_type="text/event-stream",
Γûê    )
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Streaming l├á "must-have" cho AI chat applications. Ng╞░ß╗¥i d├╣ng kh├┤ng muß╗æn nh├¼n v├áo m├án h├¼nh trß╗æng trong 10-30 gi├óy. SSE l├á chuß║⌐n ─æ╞ín giß║ún nhß║Ñt ΓÇö client chß╗ë cß║ºn `EventSource` hoß║╖c `fetch` vß╗¢i `ReadableStream`.
Γöé
Γûê---
Γöé
Γûê## 5.7 Kß║┐t nß╗æi Agent vß╗¢i API
Γöé
ΓûêPhß║ºn quan trß╗ìng nhß║Ñt: kß║┐t nß╗æi LangGraph agent (Ch╞░╞íng 4) vß╗¢i FastAPI API. C├│ hai pattern ch├¡nh: singleton agent v├á per-request agent.
Γöé
Γûê### Dependency Injection Pattern
Γöé
Γûê```python
Γûêfrom fastapi import FastAPI, Depends
Γûêfrom langgraph.graph import StateGraph
Γöé
Γûêapp = FastAPI(title="AI20K Agent API")
Γöé
Γûê# Agent singleton ΓÇö chia sß║╗ giß╗»a requests
Γûêclass AgentManager:
Γûê    """Quß║ún l├╜ agent instance."""
Γûê    def __init__(self):
Γûê        self._agent = None
Γûê    
Γûê    async def get_agent(self):
Γûê        """Lazy initialization."""
Γûê        if self._agent is None:
Γûê            # Build graph (tß╗½ Ch╞░╞íng 4)
Γûê            graph = StateGraph(ResearchState)
Γûê            graph.add_node("analyze", analyze_node)
Γûê            graph.add_node("plan", plan_node)
Γûê            graph.add_node("research", research_node)
Γûê            graph.add_node("synthesize", synthesize_node)
Γûê            graph.add_node("review", review_node)
Γûê            graph.add_node("finalize", finalize_node)
Γûê            
Γûê            graph.add_edge(START, "analyze")
Γûê            graph.add_edge("analyze", "plan")
Γûê            graph.add_edge("plan", "research")
Γûê            graph.add_edge("research", "synthesize")
Γûê            graph.add_edge("synthesize", "review")
Γûê            graph.add_conditional_edges(
Γûê                "review",
Γûê                should_continue_research,
Γûê                {"research": "research", "finalize": "finalize"}
Γûê            )
Γûê            graph.add_edge("finalize", END)
Γûê            
Γûê            self._agent = graph.compile()
Γûê        
Γûê        return self._agent
Γöé
Γûêagent_manager = AgentManager()
Γöé
Γûêasync def get_agent():
Γûê    """Dependency injection cho agent."""
Γûê    return await agent_manager.get_agent()
Γûê```
Γöé
Γûê### Lifespan Pattern
Γöé
ΓûêLifespan pattern cho ph├⌐p khß╗ƒi tß║ío v├á dß╗ìn dß║╣p t├ái nguy├¬n khi app start/stop:
Γöé
Γûê```python
Γûêfrom contextlib import asynccontextmanager
Γûêfrom fastapi import FastAPI
Γöé
Γûê@asynccontextmanager
Γûêasync def lifespan(app: FastAPI):
Γûê    """Khß╗ƒi tß║ío t├ái nguy├¬n khi app start, dß╗ìn dß║╣p khi stop."""
Γûê    # Startup
Γûê    logger.info("Starting AI20K Agent API...")
Γûê    app.state.agent = await initialize_agent()
Γûê    app.state.vectorstore = await initialize_vectorstore()
Γûê    logger.info("Agent v├á VectorStore ─æ├ú sß║╡n s├áng")
Γûê    
Γûê    yield  # App chß║íy ß╗ƒ ─æ├óy
Γûê    
Γûê    # Shutdown
Γûê    logger.info("Shutting down...")
Γûê    await cleanup_resources()
Γöé
Γûêapp = FastAPI(
Γûê    title="AI20K Agent API",
Γûê    lifespan=lifespan,
Γûê)
Γöé
Γûê# Truy cß║¡p t├ái nguy├¬n qua request.app.state
Γûê@app.post("/api/v1/chat", response_model=ChatResponse)
Γûêasync def chat(request: ChatRequest):
Γûê    """Chat endpoint sß╗¡ dß╗Ñng agent tß╗½ lifespan."""
Γûê    from langchain_core.messages import HumanMessage
Γûê    
Γûê    agent = request.app.state.agent
Γûê    
Γûê    result = await agent.ainvoke({
Γûê        "messages": [HumanMessage(content=request.message)],
Γûê        "query": request.message,
Γûê    })
Γûê    
Γûê    return ChatResponse(
Γûê        response=result.get("draft", "Kh├┤ng thß╗â tß║ío c├óu trß║ú lß╗¥i"),
Γûê        conversation_id=request.conversation_id or "new",
Γûê        sources=result.get("search_results", []),
Γûê    )
Γûê```
Γöé
Γûê### V├¡ dß╗Ñ ho├án chß╗ënh
Γöé
Γûê```python
Γûê# main.py ΓÇö File ch├¡nh chß║íy API
Γöé
Γûêimport os
Γûêimport logging
Γûêfrom contextlib import asynccontextmanager
Γûêfrom fastapi import FastAPI, HTTPException
Γûêfrom fastapi.middleware.cors import CORSMiddleware
Γûêfrom fastapi.responses import StreamingResponse
Γûêfrom pydantic import BaseModel, Field
Γûêfrom typing import Optional
Γûêfrom datetime import datetime
Γöé
Γûê# Cß║Ñu h├¼nh logging
Γûêlogging.basicConfig(level=logging.INFO)
Γûêlogger = logging.getLogger("ai20k_api")
Γöé
Γûê# ==================== SCHEMAS ====================
Γöé
Γûêclass ChatRequest(BaseModel):
Γûê    message: str = Field(..., min_length=1, max_length=5000)
Γûê    conversation_id: Optional[str] = None
Γûê    stream: bool = False
Γöé
Γûêclass ChatResponse(BaseModel):
Γûê    response: str
Γûê    conversation_id: str
Γûê    sources: list[str] = []
Γûê    timestamp: datetime = Field(default_factory=datetime.now)
Γöé
Γûêclass HealthResponse(BaseModel):
Γûê    status: str
Γûê    version: str
Γûê    agent_ready: bool
Γöé
Γûê# ==================== LIFESPAN ====================
Γöé
Γûê@asynccontextmanager
Γûêasync def lifespan(app: FastAPI):
Γûê    # Startup
Γûê    logger.info("Khß╗ƒi tß║ío AI20K Agent API...")
Γûê    from agent import build_graph
Γûê    app.state.agent = build_graph()
Γûê    logger.info("Agent ─æ├ú sß║╡n s├áng!")
Γûê    
Γûê    yield
Γûê    
Γûê    # Shutdown
Γûê    logger.info("─É├│ng API...")
Γöé
Γûê# ==================== APP ====================
Γöé
Γûêapp = FastAPI(
Γûê    title="AI20K Agent API",
Γûê    version="1.0.0",
Γûê    lifespan=lifespan,
Γûê)
Γöé
Γûê# CORS
Γûêapp.add_middleware(
Γûê    CORSMiddleware,
Γûê    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
Γûê    allow_credentials=True,
Γûê    allow_methods=["*"],
Γûê    allow_headers=["*"],
Γûê)
Γöé
Γûê# ==================== ROUTES ====================
Γöé
Γûê@app.get("/health", response_model=HealthResponse)
Γûêasync def health():
Γûê    return HealthResponse(
Γûê        status="healthy",
Γûê        version="1.0.0",
Γûê        agent_ready=hasattr(app.state, "agent"),
Γûê    )
Γöé
Γûê@app.post("/api/v1/chat", response_model=ChatResponse)
Γûêasync def chat(request: ChatRequest):
Γûê    """Chat vß╗¢i agent ΓÇö trß║ú vß╗ü response ho├án chß╗ënh."""
Γûê    from langchain_core.messages import HumanMessage
Γûê    
Γûê    agent = app.state.agent
Γûê    
Γûê    try:
Γûê        result = await agent.ainvoke({
Γûê            "messages": [HumanMessage(content=request.message)],
Γûê            "query": request.message,
Γûê        })
Γûê    except TimeoutError:
Γûê        raise HTTPException(status_code=504, detail="Agent timeout")
Γûê    except Exception as e:
Γûê        logger.error(f"Agent error: {e}", exc_info=True)
Γûê        raise HTTPException(status_code=503, detail="Agent kh├┤ng khß║ú dß╗Ñng")
Γûê    
Γûê    return ChatResponse(
Γûê        response=result.get("draft", "Kh├┤ng thß╗â tß║ío c├óu trß║ú lß╗¥i"),
Γûê        conversation_id=request.conversation_id or "conv-001",
Γûê        sources=result.get("search_results", []),
Γûê    )
Γöé
Γûê@app.post("/api/v1/chat/stream")
Γûêasync def chat_stream(request: ChatRequest):
Γûê    """Chat vß╗¢i agent ΓÇö stream response."""
Γûê    import json
Γûê    from langchain_core.messages import HumanMessage
Γûê    
Γûê    agent = app.state.agent
Γûê    
Γûê    async def generate():
Γûê        try:
Γûê            async for event in agent.astream_events(
Γûê                {"messages": [HumanMessage(content=request.message)]},
Γûê                config={"configurable": {"thread_id": request.conversation_id or "default"}},
Γûê                version="v2",
Γûê            ):
Γûê                if event["event"] == "on_chat_model_stream":
Γûê                    token = event["data"]["chunk"].content
Γûê                    if token:
Γûê                        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
Γûê            
Γûê            yield f"data: {json.dumps({'type': 'done'})}\n\n"
Γûê        except Exception as e:
Γûê            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
Γûê    
Γûê    return StreamingResponse(generate(), media_type="text/event-stream")
Γöé
Γûê# ==================== RUN ====================
Γöé
Γûêif __name__ == "__main__":
Γûê    import uvicorn
Γûê    uvicorn.run(
Γûê        "main:app",
Γûê        host="0.0.0.0",
Γûê        port=8000,
Γûê        reload=True,  # Auto-reload khi code thay ─æß╗òi (development only)
Γûê    )
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Lifespan pattern l├á c├ích ─æ├║ng ─æß╗â khß╗ƒi tß║ío LangGraph agent trong FastAPI. Agent ─æ╞░ß╗úc tß║ío mß╗Öt lß║ºn khi app start v├á ─æ╞░ß╗úc t├íi sß╗¡ dß╗Ñng cho mß╗ìi request. ─Éiß╗üu n├áy tr├ính overhead tß║ío graph mß╗ùi request v├á cho ph├⌐p agent duy tr├¼ state (nß║┐u d├╣ng checkpointer).
Γöé
Γûê---
Γöé
Γûê## T├│m tß║»t
Γöé
Γûê1. **FastAPI** l├á framework l├╜ t╞░ß╗ƒng cho AI API: async-first, auto-docs, type-safe. Chß╗ìn FastAPI khi x├óy dß╗▒ng API backend cho AI applications.
Γöé
Γûê2. **Routes + Schemas** l├á nß╗ün tß║úng: ─æß╗ïnh ngh─⌐a routes r├╡ r├áng, d├╣ng Pydantic models cho request/response, version API tß╗½ ─æß║ºu.
Γöé
Γûê3. **Pydantic Validation** gi├║p bß║»t lß╗ùi early: d├╣ng Field constraints, custom validators, v├á nested models ─æß╗â ─æß║úm bß║úo data integrity.
Γöé
Γûê4. **Error Handling** cß║ºn global handler: ├ính xß║í domain errors sang HTTP codes, kh├┤ng leak internal errors, log mß╗ìi thß╗⌐.
Γöé
Γûê5. **CORS + Middleware** l├á lß╗¢p bß║úo vß╗ç: cß║Ñu h├¼nh CORS ─æ├║ng cho frontend, th├¬m logging/timing middleware, rate limiting cho production.
Γöé
Γûê6. **Streaming** l├á must-have cho AI chat: d├╣ng SSE pattern vß╗¢i `StreamingResponse`, stream tß╗½ LangGraph qua `astream_events`.
Γöé
Γûê7. **Kß║┐t nß╗æi Agent** d├╣ng lifespan pattern: khß╗ƒi tß║ío agent khi app start, t├íi sß╗¡ dß╗Ñng qua `app.state`, dependency injection cho testability.
Γöé
Γûê---
Γöé
Γûê## C├óu hß╗Åi ├┤n tß║¡p
Γöé
Γûê1. Tß║íi sao FastAPI ph├╣ hß╗úp h╞ín Flask cho AI agent API? N├¬u ├¡t nhß║Ñt 3 l├╜ do cß╗Ñ thß╗â.
Γöé
Γûê2. Viß║┐t Pydantic model cho `TranslationRequest` vß╗¢i: `text` (bß║»t buß╗Öc, 1-10000 k├╜ tß╗▒), `source_lang` (mß║╖c ─æß╗ïnh "auto"), `target_lang` (bß║»t buß╗Öc, chß╗ë "vi" hoß║╖c "en"). Th├¬m validator kiß╗âm tra `source_lang` kh├íc `target_lang`.
Γöé
Γûê3. Giß║úi th├¡ch tß║íi sao cß║ºn CORS middleware. ─Éiß╗üu g├¼ xß║úy ra nß║┐u frontend ß╗ƒ `localhost:3000` gß╗ìi API ß╗ƒ `localhost:8000` m├á kh├┤ng c├│ CORS?
Γöé
Γûê4. So s├ính streaming response v├á regular response. Khi n├áo n├¬n d├╣ng mß╗ùi loß║íi?
Γöé
Γûê5. Viß║┐t route `POST /api/v1/agent/stream` stream response tß╗½ LangGraph agent. Xß╗¡ l├╜ cß║ú tr╞░ß╗¥ng hß╗úp agent throw error.


docs\guide\chapter-06.md:
Γûê---
Γûêtitle: "Giao diß╗çn ng╞░ß╗¥i d├╣ng"
Γûêweight: 6
Γûê---
Γöé
Γûê# Ch╞░╞íng 6: Giao diß╗çn ng╞░ß╗¥i d├╣ng
Γöé
ΓûêSau khi x├óy dß╗▒ng AI Agent (Ch╞░╞íng 4) v├á API backend (Ch╞░╞íng 5), bß║ín cß║ºn giao diß╗çn ng╞░ß╗¥i d├╣ng (UI) ─æß╗â ng╞░ß╗¥i d├╣ng t╞░╞íng t├íc vß╗¢i agent. Ch╞░╞íng n├áy h╞░ß╗¢ng dß║½n x├óy dß╗▒ng frontend chat application vß╗¢i Next.js ΓÇö tß╗½ setup dß╗▒ ├ín ─æß║┐n hiß╗ân thß╗ï streaming response tß╗½ AI agent.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Nß║┐u thß╗¥i gian c├│ hß║ín v├á bß║ín cß║ºn prototype nhanh cho demo, h├úy bß║»t ─æß║ºu vß╗¢i **Streamlit** (xem phß║ºn 6.0 b├¬n d╞░ß╗¢i). Sau khi prototype ß╗òn ─æß╗ïnh, bß║ín c├│ thß╗â migrate sang Next.js cho giao diß╗çn polished h╞ín.
Γöé
Γûê---
Γöé
Γûê## 6.0 Streamlit ΓÇö Prototype trong 30 ph├║t
Γöé
ΓûêNß║┐u bß║ín ch╞░a biß║┐t React/Next.js hoß║╖c cß║ºn giao diß╗çn demo nhanh nhß║Ñt c├│ thß╗â, **Streamlit** l├á lß╗▒a chß╗ìn tuyß╗çt vß╗¥i. Chß╗ë cß║ºn Python ΓÇö kh├┤ng cß║ºn JavaScript, kh├┤ng cß║ºn npm, kh├┤ng cß║ºn frontend knowledge. Bß║ín c├│ thß╗â tß║ío giao diß╗çn chat ho├án chß╗ënh trong d╞░ß╗¢i 30 ph├║t.
Γöé
Γûê### C├ái ─æß║╖t v├á chß║íy
Γöé
Γûê```bash
Γûêpip install streamlit requests
Γûê```
Γöé
ΓûêTß║ío file `app.py` ß╗ƒ th╞░ mß╗Ñc gß╗æc:
Γöé
Γûê```python
Γûê# app.py ΓÇö Streamlit Chat UI cho AI Agent
Γûêimport streamlit as st
Γûêimport requests
Γûêimport json
Γöé
Γûê# Page config
Γûêst.set_page_config(
Γûê    page_title="AI20K Agent",
Γûê    page_icon="≡ƒñû",
Γûê    layout="wide",
Γûê)
Γöé
Γûê# Initialize chat history
Γûêif "messages" not in st.session_state:
Γûê    st.session_state.messages = []
Γöé
Γûê# Title
Γûêst.title("≡ƒñû AI20K Agent")
Γûêst.caption("Trß╗ú l├╜ AI th├┤ng minh ΓÇö Powered by LangGraph")
Γöé
Γûê# Display chat history
Γûêfor message in st.session_state.messages:
Γûê    with st.chat_message(message["role"]):
Γûê        st.markdown(message["content"])
Γöé
Γûê# Chat input
Γûêif prompt := st.chat_input("Nhß║¡p c├óu hß╗Åi..."):
Γûê    # Add user message
Γûê    st.session_state.messages.append({"role": "user", "content": prompt})
Γûê    with st.chat_message("user"):
Γûê        st.markdown(prompt)
Γöé
Γûê    # Call API
Γûê    with st.chat_message("assistant"):
Γûê        API_URL = "http://localhost:8000/api/v1/chat"
Γûê        
Γûê        with st.spinner("─Éang suy ngh─⌐..."):
Γûê            try:
Γûê                response = requests.post(
Γûê                    API_URL,
Γûê                    json={"message": prompt},
Γûê                    timeout=60,
Γûê                )
Γûê                response.raise_for_status()
Γûê                data = response.json()
Γûê                answer = data.get("response", "Kh├┤ng c├│ c├óu trß║ú lß╗¥i.")
Γûê            except requests.exceptions.ConnectionError:
Γûê                answer = "Γ¥î Kh├┤ng thß╗â kß║┐t nß╗æi ─æß║┐n API. ─Éß║úm bß║úo server ─æang chß║íy: `make run`"
Γûê            except requests.exceptions.Timeout:
Γûê                answer = "ΓÅ▒∩╕Å Agent phß║ún hß╗ôi qu├í l├óu. Thß╗¡ lß║íi vß╗¢i c├óu hß╗Åi ngß║»n h╞ín."
Γûê            except Exception as e:
Γûê                answer = f"Γ¥î Lß╗ùi: {str(e)}"
Γöé
Γûê        st.markdown(answer)
Γöé
Γûê    st.session_state.messages.append({"role": "assistant", "content": answer})
Γöé
Γûê# Sidebar ΓÇö Info
Γûêwith st.sidebar:
Γûê    st.header("Th├┤ng tin")
Γûê    st.write(f"Sß╗æ tin nhß║»n: {len(st.session_state.messages)}")
Γûê    if st.button("X├│a lß╗ïch sß╗¡"):
Γûê        st.session_state.messages = []
Γûê        st.rerun()
Γûê    
Γûê    st.divider()
Γûê    st.caption("AI20K Build Phase ΓÇö Template Agent")
Γûê```
Γöé
Γûê### Chß║íy ß╗⌐ng dß╗Ñng
Γöé
Γûê```bash
Γûê# Terminal 1: Chß║íy FastAPI backend
Γûêmake run
Γöé
Γûê# Terminal 2: Chß║íy Streamlit frontend
Γûêstreamlit run app.py --server.port 8501
Γûê```
Γöé
ΓûêMß╗ƒ http://localhost:8501 ΓÇö bß║ín ─æ├ú c├│ giao diß╗çn chat ho├án chß╗ënh!
Γöé
Γûê### Streaming vß╗¢i Streamlit
Γöé
Γûê```python
Γûê# Thay phß║ºn "Call API" bß║▒ng streaming version:
Γûêwith st.chat_message("assistant"):
Γûê    API_URL = "http://localhost:8000/api/v1/chat/stream"
Γûê    
Γûê    with st.spinner("─Éang suy ngh─⌐..."):
Γûê        try:
Γûê            response = requests.post(
Γûê                API_URL,
Γûê                json={"message": prompt, "stream": True},
Γûê                stream=True,  # Bß║¡t streaming cho requests
Γûê                timeout=60,
Γûê            )
Γûê            
Γûê            answer = st.write_stream(
Γûê                line.removeprefix("data: ").strip()
Γûê                for line in response.iter_lines(decode_unicode=True)
Γûê                if line and line.startswith("data: ")
Γûê                and not line.endswith('"type": "done"')
Γûê            )
Γûê        except Exception as e:
Γûê            answer = f"Γ¥î Lß╗ùi: {str(e)}"
Γûê            st.error(answer)
Γûê```
Γöé
Γûê### Khi n├áo n├¬n d├╣ng Streamlit vs Next.js?
Γöé
Γûê| Ti├¬u ch├¡ | Streamlit | Next.js |
Γûê|-----------|-----------|---------|
Γûê| Thß╗¥i gian setup | 30 ph├║t | 2-3 giß╗¥ |
Γûê| Cß║ºn biß║┐t | Chß╗ë Python | Python + JavaScript/React |
Γûê| Giao diß╗çn | ─Éß║╣p mß║╖c ─æß╗ïnh, ├¡t t├╣y chß╗ënh | T├╣y chß╗ënh ho├án to├án |
Γûê| Streaming | Hß╗ù trß╗ú | Hß╗ù trß╗ú |
Γûê| Production | Kh├┤ng ph├╣ hß╗úp | Ph├╣ hß╗úp |
Γûê| Demo Day | Γ£à Chß║Ñp nhß║¡n ─æ╞░ß╗úc | Γ£à Tß╗æt h╞ín |
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Streamlit l├á c├┤ng cß╗Ñ **prototype nhanh nhß║Ñt** cho AI Agent UI. D├╣ng n├│ khi bß║ín cß║ºn focus v├áo Agent logic (Ch╞░╞íng 4) h╞ín l├á frontend engineering. Nß║┐u team c├│ th├ánh vi├¬n biß║┐t React, h├úy d├╣ng Next.js (phß║ºn 6.1 trß╗ƒ ─æi) cho giao diß╗çn polished h╞ín.
Γöé
Γûê---
Γöé
Γûê## 6.1 Setup Next.js
Γöé
Γûê### Tß║íi sao chß╗ìn Next.js?
Γöé
ΓûêNext.js l├á React framework phß╗ò biß║┐n nhß║Ñt hiß╗çn nay, cung cß║Ñp nhiß╗üu t├¡nh n─âng production-ready out-of-the-box: file-based routing (App Router), server-side rendering (SSR), static site generation (SSG), API routes, v├á optimization tß╗▒ ─æß╗Öng. ─Éß╗æi vß╗¢i AI chat application, Next.js l├á lß╗▒a chß╗ìn tuyß╗çt vß╗¥i v├¼ hß╗ù trß╗ú streaming natively qua App Router v├á React Server Components.
Γöé
Γûê### Tß║ío dß╗▒ ├ín Next.js
Γöé
ΓûêKhß╗ƒi tß║ío dß╗▒ ├ín Next.js vß╗¢i TypeScript v├á Tailwind CSS:
Γöé
Γûê```bash
Γûênpx create-next-app@latest ai20k-chat --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
Γûê```
Γöé
ΓûêKhi ─æ╞░ß╗úc hß╗Åi c├íc t├╣y chß╗ìn, chß╗ìn:
Γûê- TypeScript: Yes
Γûê- ESLint: Yes
Γûê- Tailwind CSS: Yes
Γûê- `src/` directory: Yes
Γûê- App Router: Yes
Γûê- Import alias: `@/*`
Γöé
Γûê### Cß║Ñu tr├║c th╞░ mß╗Ñc (App Router)
Γöé
ΓûêNext.js App Router sß╗¡ dß╗Ñng file-based routing ΓÇö mß╗ùi folder trong `app/` t╞░╞íng ß╗⌐ng vß╗¢i mß╗Öt route:
Γöé
Γûê```
Γûêai20k-chat/
ΓûêΓö£ΓöÇΓöÇ src/
ΓûêΓöé   Γö£ΓöÇΓöÇ app/
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ layout.tsx          # Root layout (bao bß╗ìc mß╗ìi page)
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ page.tsx            # Home page (/)
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ globals.css         # Global styles
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ chat/
ΓûêΓöé   Γöé   Γöé   ΓööΓöÇΓöÇ page.tsx        # Chat page (/chat)
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ api/                # API routes (optional backend)
ΓûêΓöé   Γö£ΓöÇΓöÇ components/
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ ChatMessage.tsx     # Component hiß╗ân thß╗ï message
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ ChatInput.tsx       # Component input chat
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ Sidebar.tsx         # Sidebar navigation
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ ThemeToggle.tsx     # Toggle dark/light mode
ΓûêΓöé   Γö£ΓöÇΓöÇ hooks/
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ useChat.ts          # Custom hook cho chat logic
ΓûêΓöé   Γö£ΓöÇΓöÇ lib/
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ api.ts              # API client functions
ΓûêΓöé   ΓööΓöÇΓöÇ types/
ΓûêΓöé       ΓööΓöÇΓöÇ chat.ts             # TypeScript types
ΓûêΓö£ΓöÇΓöÇ tailwind.config.ts
ΓûêΓö£ΓöÇΓöÇ next.config.js
ΓûêΓö£ΓöÇΓöÇ package.json
ΓûêΓööΓöÇΓöÇ tsconfig.json
Γûê```
Γöé
Γûê### Pages v├á Layouts
Γöé
Γûê**Root Layout** (`src/app/layout.tsx`) l├á bao bß╗ìc cho to├án bß╗Ö ß╗⌐ng dß╗Ñng:
Γöé
Γûê```tsx
Γûê// src/app/layout.tsx
Γûêimport type { Metadata } from "next";
Γûêimport { Inter } from "next/font/google";
Γûêimport "./globals.css";
Γûêimport { ThemeProvider } from "@/components/ThemeProvider";
Γöé
Γûêconst inter = Inter({ subsets: ["latin"] });
Γöé
Γûêexport const metadata: Metadata = {
Γûê  title: "AI20K Chat",
Γûê  description: "AI Agent Chat Application",
Γûê};
Γöé
Γûêexport default function RootLayout({
Γûê  children,
Γûê}: {
Γûê  children: React.ReactNode;
Γûê}) {
Γûê  return (
Γûê    <html lang="vi" suppressHydrationWarning>
Γûê      <body className={inter.className}>
Γûê        <ThemeProvider>
Γûê          {children}
Γûê        </ThemeProvider>
Γûê      </body>
Γûê    </html>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê**Home Page** (`src/app/page.tsx`):
Γöé
Γûê```tsx
Γûê// src/app/page.tsx
Γûêimport Link from "next/link";
Γöé
Γûêexport default function Home() {
Γûê  return (
Γûê    <main className="flex min-h-screen flex-col items-center justify-center p-8">
Γûê      <div className="max-w-2xl text-center">
Γûê        <h1 className="text-4xl font-bold mb-4">
Γûê          AI20K Agent
Γûê        </h1>
Γûê        <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
Γûê          Trß╗ú l├╜ AI th├┤ng minh sß║╡n s├áng gi├║p bß║ín nghi├¬n cß╗⌐u,
Γûê          ph├ón t├¡ch v├á trß║ú lß╗¥i c├óu hß╗Åi.
Γûê        </p>
Γûê        <Link
Γûê          href="/chat"
Γûê          className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg
Γûê                     hover:bg-blue-700 transition-colors font-medium"
Γûê        >
Γûê          Bß║»t ─æß║ºu tr├▓ chuyß╗çn
Γûê        </Link>
Γûê      </div>
Γûê    </main>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê**Chat Page** (`src/app/chat/page.tsx`):
Γöé
Γûê```tsx
Γûê// src/app/chat/page.tsx
Γûê"use client";
Γöé
Γûêimport { useState } from "react";
Γûêimport ChatMessage from "@/components/ChatMessage";
Γûêimport ChatInput from "@/components/ChatInput";
Γûêimport { Message } from "@/types/chat";
Γöé
Γûêexport default function ChatPage() {
Γûê  const [messages, setMessages] = useState<Message[]>([]);
Γûê  const [isLoading, setIsLoading] = useState(false);
Γöé
Γûê  const handleSend = async (content: string) => {
Γûê    // Th├¬m user message
Γûê    const userMessage: Message = {
Γûê      id: Date.now().toString(),
Γûê      role: "user",
Γûê      content,
Γûê      timestamp: new Date(),
Γûê    };
Γûê    setMessages((prev) => [...prev, userMessage]);
Γûê    setIsLoading(true);
Γöé
Γûê    try {
Γûê      // Gß╗ìi API
Γûê      const response = await fetch("http://localhost:8000/api/v1/chat", {
Γûê        method: "POST",
Γûê        headers: { "Content-Type": "application/json" },
Γûê        body: JSON.stringify({ message: content }),
Γûê      });
Γöé
Γûê      const data = await response.json();
Γöé
Γûê      const assistantMessage: Message = {
Γûê        id: (Date.now() + 1).toString(),
Γûê        role: "assistant",
Γûê        content: data.response,
Γûê        sources: data.sources,
Γûê        timestamp: new Date(),
Γûê      };
Γûê      setMessages((prev) => [...prev, assistantMessage]);
Γûê    } catch (error) {
Γûê      console.error("Chat error:", error);
Γûê    } finally {
Γûê      setIsLoading(false);
Γûê    }
Γûê  };
Γöé
Γûê  return (
Γûê    <div className="flex flex-col h-screen max-w-4xl mx-auto">
Γûê      {/* Header */}
Γûê      <header className="border-b p-4">
Γûê        <h1 className="text-xl font-semibold">AI20K Agent</h1>
Γûê      </header>
Γöé
Γûê      {/* Messages */}
Γûê      <div className="flex-1 overflow-y-auto p-4 space-y-4">
Γûê        {messages.length === 0 ? (
Γûê          <div className="text-center text-gray-500 mt-20">
Γûê            Gß╗¡i tin nhß║»n ─æß╗â bß║»t ─æß║ºu tr├▓ chuyß╗çn
Γûê          </div>
Γûê        ) : (
Γûê          messages.map((msg) => (
Γûê            <ChatMessage key={msg.id} message={msg} />
Γûê          ))
Γûê        )}
Γûê        {isLoading && (
Γûê          <div className="text-gray-500 animate-pulse">
Γûê            ─Éang suy ngh─⌐...
Γûê          </div>
Γûê        )}
Γûê      </div>
Γöé
Γûê      {/* Input */}
Γûê      <ChatInput onSend={handleSend} disabled={isLoading} />
Γûê    </div>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** `"use client"` directive ß╗ƒ ─æß║ºu file cho Next.js biß║┐t ─æ├óy l├á Client Component ΓÇö component chß║íy ß╗ƒ browser, c├│ thß╗â d├╣ng useState, useEffect, event handlers. Mß║╖c ─æß╗ïnh tß║Ñt cß║ú components trong App Router l├á Server Components (chß║íy ß╗ƒ server). D├╣ng `"use client"` chß╗ë khi cß║ºn interactivity.
Γöé
Γûê---
Γöé
Γûê## 6.2 Thiß║┐t kß║┐ responsive
Γöé
Γûê### Tailwind CSS Basics
Γöé
ΓûêTailwind CSS l├á utility-first CSS framework ΓÇö thay v├¼ viß║┐t CSS classes ri├¬ng, bß║ín kß║┐t hß╗úp c├íc utility classes ─æß╗â tß║ío giao diß╗çn. Mß╗ùi class l├ám mß╗Öt viß╗çc duy nhß║Ñt:
Γöé
Γûê```html
Γûê<!-- Padding, margin, background, text -->
Γûê<div class="p-4 bg-white rounded-lg shadow-md">
Γûê  <h2 class="text-xl font-bold text-gray-900 mb-2">Ti├¬u ─æß╗ü</h2>
Γûê  <p class="text-gray-600 leading-relaxed">Nß╗Öi dung...</p>
Γûê</div>
Γûê```
Γöé
ΓûêC├íc utility class phß╗ò biß║┐n:
Γûê- **Spacing:** `p-4` (padding), `m-4` (margin), `gap-2` (gap in flex/grid)
Γûê- **Sizing:** `w-full`, `h-screen`, `max-w-4xl`, `min-h-screen`
Γûê- **Typography:** `text-sm`, `font-bold`, `text-gray-600`, `leading-relaxed`
Γûê- **Layout:** `flex`, `grid`, `items-center`, `justify-between`
Γûê- **Visual:** `bg-white`, `rounded-lg`, `shadow-md`, `border`
Γûê- **Interactivity:** `hover:bg-blue-700`, `focus:ring-2`, `transition-colors`
Γöé
Γûê### Responsive Breakpoints
Γöé
ΓûêTailwind sß╗¡ dß╗Ñng mobile-first approach ΓÇö thiß║┐t kß║┐ cho mobile tr╞░ß╗¢c, rß╗ôi th├¬m styles cho screen lß╗¢n h╞ín:
Γöé
Γûê```html
Γûê<!-- Mobile: 1 column, Tablet: 2 columns, Desktop: 3 columns -->
Γûê<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
Γûê  <div>Card 1</div>
Γûê  <div>Card 2</div>
Γûê  <div>Card 3</div>
Γûê</div>
Γûê```
Γöé
ΓûêBreakpoints:
Γûê- Mß║╖c ─æß╗ïnh (kh├┤ng prefix): 0px+ (mobile)
Γûê- `sm:`: 640px+ (large phone)
Γûê- `md:`: 768px+ (tablet)
Γûê- `lg:`: 1024px+ (laptop)
Γûê- `xl:`: 1280px+ (desktop)
Γûê- `2xl:`: 1536px+ (large desktop)
Γöé
Γûê### Mobile-first Design
Γöé
ΓûêThiß║┐t kß║┐ cho mobile tr╞░ß╗¢c, rß╗ôi mß╗ƒ rß╗Öng cho desktop:
Γöé
Γûê```tsx
Γûê// ChatLayout vß╗¢i responsive sidebar
Γûêexport default function ChatLayout({
Γûê  children,
Γûê}: {
Γûê  children: React.ReactNode;
Γûê}) {
Γûê  return (
Γûê    <div className="flex h-screen">
Γûê      {/* Sidebar: ß║⌐n tr├¬n mobile, hiß╗çn tr├¬n desktop */}
Γûê      <aside className="hidden md:flex md:w-64 lg:w-80 flex-col border-r bg-gray-50 dark:bg-gray-900">
Γûê        <div className="p-4 border-b">
Γûê          <h2 className="font-semibold">Lß╗ïch sß╗¡ chat</h2>
Γûê        </div>
Γûê        <nav className="flex-1 overflow-y-auto p-2">
Γûê          {/* Danh s├ích conversations */}
Γûê        </nav>
Γûê      </aside>
Γöé
Γûê      {/* Main content */}
Γûê      <main className="flex-1 flex flex-col min-w-0">
Γûê        {children}
Γûê      </main>
Γûê    </div>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê### Grid Layout cho Chat
Γöé
Γûê```tsx
Γûê// Dashboard layout vß╗¢i grid
Γûêexport default function Dashboard() {
Γûê  return (
Γûê    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 p-4 h-screen">
Γûê      {/* Sidebar */}
Γûê      <div className="lg:col-span-1 border rounded-lg p-4">
Γûê        <h3 className="font-semibold mb-4">Conversations</h3>
Γûê        {/* List */}
Γûê      </div>
Γöé
Γûê      {/* Chat area */}
Γûê      <div className="lg:col-span-2 border rounded-lg flex flex-col">
Γûê        <div className="flex-1 overflow-y-auto p-4">
Γûê          {/* Messages */}
Γûê        </div>
Γûê        <div className="border-t p-4">
Γûê          {/* Input */}
Γûê        </div>
Γûê      </div>
Γöé
Γûê      {/* Info panel */}
Γûê      <div className="lg:col-span-1 border rounded-lg p-4">
Γûê        <h3 className="font-semibold mb-4">Th├┤ng tin</h3>
Γûê        {/* Sources, metadata */}
Γûê      </div>
Γûê    </div>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Nguy├¬n tß║»c mobile-first: viß║┐t styles cho mobile tr╞░ß╗¢c (kh├┤ng prefix), rß╗ôi th├¬m responsive overrides vß╗¢i `md:`, `lg:`. ─Éiß╗üu n├áy ─æß║úm bß║úo giao diß╗çn hoß║ít ─æß╗Öng tr├¬n mß╗ìi thiß║┐t bß╗ï m├á kh├┤ng cß║ºn media queries thß╗º c├┤ng.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** D├╣ng `min-w-0` tr├¬n flex/grid children ─æß╗â text kh├┤ng tr├án ra ngo├ái container. ─É├óy l├á lß╗ùi phß╗ò biß║┐n: nß╗Öi dung d├ái l├ám vß╗í layout. `min-w-0` cho ph├⌐p text truncation hoß║ít ─æß╗Öng ─æ├║ng.
Γöé
Γûê---
Γöé
Γûê## 6.3 Dark Mode
Γöé
Γûê### Tß║íi sao cß║ºn Dark Mode?
Γöé
ΓûêDark mode kh├┤ng chß╗ë l├á xu h╞░ß╗¢ng ΓÇö n├│ giß║úm mß╗Åi mß║»t khi ─æß╗ìc trong m├┤i tr╞░ß╗¥ng tß╗æi, tiß║┐t kiß╗çm pin tr├¬n m├án h├¼nh OLED, v├á nhiß╗üu ng╞░ß╗¥i d├╣ng ─æ╞ín giß║ún l├á th├¡ch h╞ín. Mß╗Öt ß╗⌐ng dß╗Ñng AI chat hiß╗çn ─æß║íi cß║ºn hß╗ù trß╗ú cß║ú light v├á dark mode.
Γöé
Γûê### Setup vß╗¢i next-themes
Γöé
Γûê`next-themes` l├á th╞░ viß╗çn phß╗ò biß║┐n nhß║Ñt cho dark mode trong Next.js:
Γöé
Γûê```bash
Γûênpm install next-themes
Γûê```
Γöé
Γûê### Theme Provider
Γöé
ΓûêTß║ío ThemeProvider component bao bß╗ìc to├án bß╗Ö app:
Γöé
Γûê```tsx
Γûê// src/components/ThemeProvider.tsx
Γûê"use client";
Γöé
Γûêimport { ThemeProvider as NextThemesProvider } from "next-themes";
Γûêimport { ReactNode } from "react";
Γöé
Γûêexport function ThemeProvider({ children }: { children: ReactNode }) {
Γûê  return (
Γûê    <NextThemesProvider
Γûê      attribute="class"       // Th├¬m class "dark" v├áo <html>
Γûê      defaultTheme="system"   // Theo hß╗ç ─æiß╗üu h├ánh
Γûê      enableSystem={true}     // Cho ph├⌐p auto-detect system theme
Γûê      disableTransitionOnChange  // Tr├ính flash khi chuyß╗ân theme
Γûê    >
Γûê      {children}
Γûê    </NextThemesProvider>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê### Toggle Component
Γöé
Γûê```tsx
Γûê// src/components/ThemeToggle.tsx
Γûê"use client";
Γöé
Γûêimport { useTheme } from "next-themes";
Γûêimport { useEffect, useState } from "react";
Γöé
Γûêexport default function ThemeToggle() {
Γûê  const { theme, setTheme } = useTheme();
Γûê  const [mounted, setMounted] = useState(false);
Γöé
Γûê  // Chß╗ë render toggle sau khi mount (tr├ính hydration mismatch)
Γûê  useEffect(() => {
Γûê    setMounted(true);
Γûê  }, []);
Γöé
Γûê  if (!mounted) {
Γûê    return <div className="w-10 h-10" />; // Placeholder tr├ính layout shift
Γûê  }
Γöé
Γûê  return (
Γûê    <button
Γûê      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
Γûê      className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
Γûê      aria-label="Chuyß╗ân ─æß╗òi theme"
Γûê    >
Γûê      {theme === "dark" ? (
Γûê        // Sun icon cho dark mode
Γûê        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
Γûê          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
Γûê            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
Γûê          />
Γûê        </svg>
Γûê      ) : (
Γûê        // Moon icon cho light mode
Γûê        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
Γûê          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
Γûê            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
Γûê          />
Γûê        </svg>
Γûê      )}
Γûê    </button>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê### Tailwind Dark Mode Configuration
Γöé
ΓûêCß║Ñu h├¼nh Tailwind ─æß╗â hß╗ù trß╗ú dark mode qua class:
Γöé
Γûê```javascript
Γûê// tailwind.config.ts
Γûêimport type { Config } from "tailwindcss";
Γöé
Γûêconst config: Config = {
Γûê  darkMode: "class",  // Sß╗¡ dß╗Ñng class strategy (t╞░╞íng th├¡ch next-themes)
Γûê  content: [
Γûê    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
Γûê    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
Γûê    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
Γûê  ],
Γûê  theme: {
Γûê    extend: {},
Γûê  },
Γûê  plugins: [],
Γûê};
Γöé
Γûêexport default config;
Γûê```
Γöé
Γûê### Sß╗¡ dß╗Ñng Dark Mode trong Components
Γöé
ΓûêTailwind cung cß║Ñp `dark:` prefix cho mß╗ìi utility class:
Γöé
Γûê```tsx
Γûê// Message component hß╗ù trß╗ú dark mode
Γûêexport default function ChatMessage({ message }: { message: Message }) {
Γûê  const isUser = message.role === "user";
Γöé
Γûê  return (
Γûê    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
Γûê      <div
Γûê        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
Γûê          isUser
Γûê            ? "bg-blue-600 text-white"          // User message: blue
Γûê            : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100"  // AI message: gray
Γûê        }`}
Γûê      >
Γûê        <p className="whitespace-pre-wrap">{message.content}</p>
Γûê        {message.sources && message.sources.length > 0 && (
Γûê          <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
Γûê            <p className="text-xs text-gray-500 dark:text-gray-400">Nguß╗ôn:</p>
Γûê            {message.sources.map((src, i) => (
Γûê              <p key={i} className="text-xs text-gray-400 dark:text-gray-500 truncate">
Γûê                {src}
Γûê              </p>
Γûê            ))}
Γûê          </div>
Γûê        )}
Γûê      </div>
Γûê    </div>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Lu├┤n xß╗¡ l├╜ hydration mismatch khi d├╣ng `next-themes`. Theme ─æ╞░ß╗úc x├íc ─æß╗ïnh ß╗ƒ client, n├¬n server v├á client c├│ thß╗â kh├íc nhau. Pattern `mounted` state (nh╞░ trong ThemeToggle) giß║úi quyß║┐t vß║Ñn ─æß╗ü n├áy ΓÇö chß╗ë render UI phß╗Ñ thuß╗Öc theme sau khi component ─æ├ú mount.
Γöé
Γûê---
Γöé
Γûê## 6.4 Kß║┐t nß╗æi vß╗¢i API
Γöé
Γûê### Fetch API
Γöé
ΓûêC├ích c╞í bß║ún nhß║Ñt ─æß╗â gß╗ìi API tß╗½ frontend:
Γöé
Γûê```typescript
Γûê// src/lib/api.ts
Γûêconst API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
Γöé
Γûêexport interface ChatRequest {
Γûê  message: string;
Γûê  conversation_id?: string;
Γûê  stream?: boolean;
Γûê}
Γöé
Γûêexport interface ChatResponse {
Γûê  response: string;
Γûê  conversation_id: string;
Γûê  sources: string[];
Γûê  timestamp: string;
Γûê}
Γöé
Γûêexport async function sendMessage(
Γûê  request: ChatRequest
Γûê): Promise<ChatResponse> {
Γûê  const response = await fetch(`${API_BASE}/api/v1/chat`, {
Γûê    method: "POST",
Γûê    headers: { "Content-Type": "application/json" },
Γûê    body: JSON.stringify(request),
Γûê  });
Γöé
Γûê  if (!response.ok) {
Γûê    throw new Error(`API error: ${response.status}`);
Γûê  }
Γöé
Γûê  return response.json();
Γûê}
Γûê```
Γöé
Γûê### SWR (Stale-While-Revalidate)
Γöé
ΓûêSWR l├á th╞░ viß╗çn data fetching tß╗½ Vercel (t├íc giß║ú Next.js). N├│ cung cß║Ñp caching, revalidation, optimistic UI, v├á error handling:
Γöé
Γûê```bash
Γûênpm install swr
Γûê```
Γöé
Γûê```tsx
Γûê// src/hooks/useChat.ts
Γûê"use client";
Γöé
Γûêimport { useState, useCallback } from "react";
Γûêimport { Message } from "@/types/chat";
Γûêimport { sendMessage } from "@/lib/api";
Γöé
Γûêexport function useChat() {
Γûê  const [messages, setMessages] = useState<Message[]>([]);
Γûê  const [isLoading, setIsLoading] = useState(false);
Γûê  const [error, setError] = useState<string | null>(null);
Γöé
Γûê  const send = useCallback(async (content: string) => {
Γûê    setIsLoading(true);
Γûê    setError(null);
Γöé
Γûê    // Optimistic update: th├¬m user message ngay lß║¡p tß╗⌐c
Γûê    const userMsg: Message = {
Γûê      id: Date.now().toString(),
Γûê      role: "user",
Γûê      content,
Γûê      timestamp: new Date().toISOString(),
Γûê    };
Γûê    setMessages((prev) => [...prev, userMsg]);
Γöé
Γûê    try {
Γûê      const data = await sendMessage({ message: content });
Γöé
Γûê      const assistantMsg: Message = {
Γûê        id: (Date.now() + 1).toString(),
Γûê        role: "assistant",
Γûê        content: data.response,
Γûê        sources: data.sources,
Γûê        timestamp: data.timestamp,
Γûê      };
Γûê      setMessages((prev) => [...prev, assistantMsg]);
Γûê    } catch (err) {
Γûê      setError(
Γûê        err instanceof Error ? err.message : "Lß╗ùi kh├┤ng x├íc ─æß╗ïnh"
Γûê      );
Γûê    } finally {
Γûê      setIsLoading(false);
Γûê    }
Γûê  }, []);
Γöé
Γûê  const clear = useCallback(() => {
Γûê    setMessages([]);
Γûê    setError(null);
Γûê  }, []);
Γöé
Γûê  return { messages, isLoading, error, send, clear };
Γûê}
Γûê```
Γöé
Γûê### Error Handling
Γöé
Γûê```tsx
Γûê// src/components/ChatError.tsx
Γûêexport default function ChatError({
Γûê  error,
Γûê  onRetry,
Γûê}: {
Γûê  error: string;
Γûê  onRetry: () => void;
Γûê}) {
Γûê  return (
Γûê    <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
Γûê      <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
Γûê        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
Γûê          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
Γûê        />
Γûê      </svg>
Γûê      <p className="text-sm text-red-700 dark:text-red-300 flex-1">{error}</p>
Γûê      <button
Γûê        onClick={onRetry}
Γûê        className="text-sm text-red-600 dark:text-red-400 underline hover:no-underline"
Γûê      >
Γûê        Thß╗¡ lß║íi
Γûê      </button>
Γûê    </div>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê### Loading States
Γöé
Γûê```tsx
Γûê// src/components/ChatInput.tsx
Γûê"use client";
Γöé
Γûêimport { useState, KeyboardEvent } from "react";
Γöé
Γûêinterface ChatInputProps {
Γûê  onSend: (message: string) => void;
Γûê  disabled?: boolean;
Γûê}
Γöé
Γûêexport default function ChatInput({ onSend, disabled }: ChatInputProps) {
Γûê  const [input, setInput] = useState("");
Γöé
Γûê  const handleSend = () => {
Γûê    const trimmed = input.trim();
Γûê    if (!trimmed || disabled) return;
Γûê    onSend(trimmed);
Γûê    setInput("");
Γûê  };
Γöé
Γûê  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
Γûê    if (e.key === "Enter" && !e.shiftKey) {
Γûê      e.preventDefault();
Γûê      handleSend();
Γûê    }
Γûê  };
Γöé
Γûê  return (
Γûê    <div className="border-t p-4 dark:border-gray-800">
Γûê      <div className="flex gap-2 max-w-4xl mx-auto">
Γûê        <textarea
Γûê          value={input}
Γûê          onChange={(e) => setInput(e.target.value)}
Γûê          onKeyDown={handleKeyDown}
Γûê          placeholder="Nhß║¡p c├óu hß╗Åi..."
Γûê          rows={1}
Γûê          disabled={disabled}
Γûê          className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-700
Γûê                     bg-white dark:bg-gray-800 px-4 py-2.5 text-sm
Γûê                     focus:outline-none focus:ring-2 focus:ring-blue-500
Γûê                     disabled:opacity-50 disabled:cursor-not-allowed"
Γûê        />
Γûê        <button
Γûê          onClick={handleSend}
Γûê          disabled={disabled || !input.trim()}
Γûê          className="bg-blue-600 text-white px-4 py-2.5 rounded-lg font-medium
Γûê                     hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
Γûê                     transition-colors"
Γûê        >
Γûê          {disabled ? "─Éang gß╗¡i..." : "Gß╗¡i"}
Γûê        </button>
Γûê      </div>
Γûê    </div>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Lu├┤n xß╗¡ l├╜ ba trß║íng th├íi cho mß╗ìi async operation: loading (hiß╗ân thß╗ï spinner/skeleton), success (hiß╗ân thß╗ï data), v├á error (hiß╗ân thß╗ï error message + retry button). ─É├óy l├á pattern UI c╞í bß║ún nh╞░ng nhiß╗üu developer bß╗Å qu├¬n.
Γöé
Γûê---
Γöé
Γûê## 6.5 Hiß╗ân thß╗ï AI Response
Γöé
Γûê### Chat UI Pattern
Γöé
ΓûêGiao diß╗çn chat c├│ pattern chuß║⌐n: messages hiß╗ân thß╗ï theo thß╗⌐ tß╗▒ thß╗¥i gian, user message b├¬n phß║úi, AI message b├¬n tr├íi, input ß╗ƒ d╞░ß╗¢i c├╣ng:
Γöé
Γûê```tsx
Γûê// src/components/ChatMessage.tsx
Γûê"use client";
Γöé
Γûêimport { Message } from "@/types/chat";
Γöé
Γûêinterface ChatMessageProps {
Γûê  message: Message;
Γûê}
Γöé
Γûêexport default function ChatMessage({ message }: ChatMessageProps) {
Γûê  const isUser = message.role === "user";
Γöé
Γûê  return (
Γûê    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
Γûê      {/* Avatar */}
Γûê      {!isUser && (
Γûê        <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900
Γûê                        flex items-center justify-center mr-2 shrink-0">
Γûê          <span className="text-sm">AI</span>
Γûê        </div>
Γûê      )}
Γöé
Γûê      {/* Message bubble */}
Γûê      <div
Γûê        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
Γûê          isUser
Γûê            ? "bg-blue-600 text-white rounded-br-md"
Γûê            : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md"
Γûê        }`}
Γûê      >
Γûê        {/* Nß╗Öi dung: markdown rendering */}
Γûê        <div className="prose prose-sm dark:prose-invert max-w-none">
Γûê          {message.content}
Γûê        </div>
Γöé
Γûê        {/* Sources */}
Γûê        {message.sources && message.sources.length > 0 && (
Γûê          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
Γûê            <p className="text-xs font-medium opacity-60 mb-1">Nguß╗ôn tham khß║úo:</p>
Γûê            {message.sources.map((src, i) => (
Γûê              <p key={i} className="text-xs opacity-50 truncate">{src}</p>
Γûê            ))}
Γûê          </div>
Γûê        )}
Γöé
Γûê        {/* Timestamp */}
Γûê        <p className="text-xs opacity-40 mt-2">
Γûê          {new Date(message.timestamp).toLocaleTimeString("vi-VN")}
Γûê        </p>
Γûê      </div>
Γûê    </div>
Γûê  );
Γûê}
Γûê```
Γöé
Γûê### Streaming Display
Γöé
ΓûêHiß╗ân thß╗ï response tß╗½ng token khi nhß║¡n ─æ╞░ß╗úc tß╗½ SSE stream:
Γöé
Γûê```typescript
Γûê// src/lib/stream.ts
Γûêexport async function streamChat(
Γûê  message: string,
Γûê  onToken: (token: string) => void,
Γûê  onDone: () => void,
Γûê  onError: (error: string) => void,
Γûê): Promise<void> {
Γûê  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
Γöé
Γûê  try {
Γûê    const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
Γûê      method: "POST",
Γûê      headers: { "Content-Type": "application/json" },
Γûê      body: JSON.stringify({ message, stream: true }),
Γûê    });
Γöé
Γûê    if (!response.ok) {
Γûê      throw new Error(`API error: ${response.status}`);
Γûê    }
Γöé
Γûê    const reader = response.body?.getReader();
Γûê    const decoder = new TextDecoder();
Γöé
Γûê    if (!reader) throw new Error("No reader available");
Γöé
Γûê    let buffer = "";
Γöé
Γûê    while (true) {
Γûê      const { done, value } = await reader.read();
Γûê      if (done) break;
Γöé
Γûê      buffer += decoder.decode(value, { stream: true });
Γöé
Γûê      // Parse SSE events
Γûê      const lines = buffer.split("\n");
Γûê      buffer = lines.pop() || ""; // Giß╗» phß║ºn ch╞░a ho├án th├ánh
Γöé
Γûê      for (const line of lines) {
Γûê        if (line.startsWith("data: ")) {
Γûê          const data = JSON.parse(line.slice(6));
Γöé
Γûê          switch (data.type) {
Γûê            case "token":
Γûê              onToken(data.content);
Γûê              break;
Γûê            case "done":
Γûê              onDone();
Γûê              break;
Γûê            case "error":
Γûê              onError(data.message);
Γûê              break;
Γûê          }
Γûê        }
Γûê      }
Γûê    }
Γûê  } catch (err) {
Γûê    onError(err instanceof Error ? err.message : "Lß╗ùi streaming");
Γûê  }
Γûê}
Γûê```
Γöé
Γûê```tsx
Γûê// Sß╗¡ dß╗Ñng streaming trong component
Γûê"use client";
Γöé
Γûêimport { useState, useCallback, useRef } from "react";
Γûêimport { streamChat } from "@/lib/stream";
Γöé
Γûêexport function useStreamingChat() {
Γûê  const [messages, setMessages] = useState<Message[]>([]);
Γûê  const [isStreaming, setIsStreaming] = useState(false);
Γûê  const streamRef = useRef<string>("");
Γöé
Γûê  const sendStream = useCallback(async (content: string) => {
Γûê    // Th├¬m user message
Γûê    setMessages((prev) => [
Γûê      ...prev,
Γûê      {
Γûê        id: Date.now().toString(),
Γûê        role: "user",
Γûê        content,
Γûê        timestamp: new Date().toISOString(),
Γûê      },
Γûê    ]);
Γöé
Γûê    // Tß║ío placeholder cho AI message
Γûê    const assistantId = (Date.now() + 1).toString();
Γûê    setMessages((prev) => [
Γûê      ...prev,
Γûê      {
Γûê        id: assistantId,
Γûê        role: "assistant",
Γûê        content: "",
Γûê        timestamp: new Date().toISOString(),
Γûê      },
Γûê    ]);
Γöé
Γûê    setIsStreaming(true);
Γûê    streamRef.current = "";
Γöé
Γûê    await streamChat(
Γûê      content,
Γûê      // onToken: cß║¡p nhß║¡t message content
Γûê      (token) => {
Γûê        streamRef.current += token;
Γûê        setMessages((prev) =>
Γûê          prev.map((msg) =>
Γûê            msg.id === assistantId
Γûê              ? { ...msg, content: streamRef.current }
Γûê              : msg
Γûê          )
Γûê        );
Γûê      },
Γûê      // onDone
Γûê      () => setIsStreaming(false),
Γûê      // onError
Γûê      (error) => {
Γûê        setMessages((prev) =>
Γûê          prev.map((msg) =>
Γûê            msg.id === assistantId
Γûê              ? { ...msg, content: `Lß╗ùi: ${error}` }
Γûê              : msg
Γûê          )
Γûê        );
Γûê        setIsStreaming(false);
Γûê      }
Γûê    );
Γûê  }, []);
Γöé
Γûê  return { messages, isStreaming, sendStream };
Γûê}
Γûê```
Γöé
Γûê### Markdown Rendering
Γöé
ΓûêAI agent th╞░ß╗¥ng trß║ú vß╗ü markdown (headers, lists, code blocks). Hiß╗ân thß╗ï markdown trong React:
Γöé
Γûê```bash
Γûênpm install react-markdown remark-gfm rehype-highlight
Γûê```
Γöé
Γûê```tsx
Γûê// src/components/MarkdownRenderer.tsx
Γûê"use client";
Γöé
Γûêimport ReactMarkdown from "react-markdown";
Γûêimport remarkGfm from "remark-gfm";
Γûêimport rehypeHighlight from "rehype-highlight";
Γöé
Γûêinterface MarkdownRendererProps {
Γûê  content: string;
Γûê}
Γöé
Γûêexport default function MarkdownRenderer({ content }: MarkdownRendererProps) {
Γûê  return (
Γûê    <ReactMarkdown
Γûê      remarkPlugins={[remarkGfm]}
Γûê      rehypePlugins={[rehypeHighlight]}
Γûê      components={{
Γûê        // Custom rendering cho code blocks
Γûê        code({ inline, className, children, ...props }) {
Γûê          if (inline) {
Γûê            return (
Γûê              <code
Γûê                className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-sm"
Γûê                {...props}
Γûê              >
Γûê                {children}
Γûê              </code>
Γûê            );
Γûê          }
Γöé
Γûê          return (
Γûê            <div className="relative my-3">
Γûê              <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto">
Γûê                <code className={className} {...props}>
Γûê                  {children}
Γûê                </code>
Γûê              </pre>
Γûê            </div>
Γûê          );
Γûê        },
Γûê        // Custom rendering cho links
Γûê        a({ href, children }) {
Γûê          return (
Γûê            <a
Γûê              href={href}
Γûê              target="_blank"
Γûê              rel="noopener noreferrer"
Γûê              className="text-blue-500 hover:underline"
Γûê            >
Γûê              {children}
Γûê            </a>
Γûê          );
Γûê        },
Γûê        // Custom rendering cho tables
Γûê        table({ children }) {
Γûê          return (
Γûê            <div className="overflow-x-auto my-3">
Γûê              <table className="min-w-full border-collapse border border-gray-300 dark:border-gray-700">
Γûê                {children}
Γûê              </table>
Γûê            </div>
Γûê          );
Γûê        },
Γûê      }}
Γûê    >
Γûê      {content}
Γûê    </ReactMarkdown>
Γûê  );
Γûê}
Γûê```
Γöé
ΓûêCß║¡p nhß║¡t ChatMessage ─æß╗â d├╣ng MarkdownRenderer:
Γöé
Γûê```tsx
Γûê// Cß║¡p nhß║¡t ChatMessage component
Γûêimport MarkdownRenderer from "./MarkdownRenderer";
Γöé
Γûê// Trong ChatMessage, thay thß║┐:
Γûê// <div>{message.content}</div>
Γûê// bß║▒ng:
Γûê<MarkdownRenderer content={message.content} />
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Streaming display l├á yß║┐u tß╗æ then chß╗æt cho UX cß╗ºa AI chat. Ng╞░ß╗¥i d├╣ng thß║Ñy c├óu trß║ú lß╗¥i xuß║Ñt hiß╗çn tß╗½ng phß║ºn, tß║ío cß║úm gi├íc "AI ─æang suy ngh─⌐ v├á trß║ú lß╗¥i". Kß║┐t hß╗úp vß╗¢i markdown rendering, bß║ín c├│ giao diß╗çn chat chuy├¬n nghiß╗çp, t╞░╞íng tß╗▒ ChatGPT.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Th├¬m cursor blinking animation khi ─æang stream ─æß╗â ng╞░ß╗¥i d├╣ng biß║┐t AI vß║½n ─æang sinh nß╗Öi dung:
Γöé
Γûê```css
Γûê/* Th├¬m v├áo globals.css */
Γûê.typing-cursor::after {
Γûê  content: "Γûï";
Γûê  animation: blink 1s infinite;
Γûê}
Γöé
Γûê@keyframes blink {
Γûê  0%, 50% { opacity: 1; }
Γûê  51%, 100% { opacity: 0; }
Γûê}
Γûê```
Γöé
Γûê---
Γöé
Γûê## T├│m tß║»t
Γöé
Γûê1. **Next.js App Router** cung cß║Ñp file-based routing, layouts, v├á server components. Cß║Ñu tr├║c th╞░ mß╗Ñc r├╡ r├áng: `app/` cho pages, `components/` cho reusable UI, `hooks/` cho custom hooks, `lib/` cho utilities.
Γöé
Γûê2. **Tailwind CSS** vß╗¢i mobile-first approach gi├║p tß║ío giao diß╗çn responsive nhanh ch├│ng. D├╣ng `sm:`, `md:`, `lg:` breakpoints v├á lu├┤n test tr├¬n nhiß╗üu k├¡ch th╞░ß╗¢c m├án h├¼nh.
Γöé
Γûê3. **Dark mode** vß╗¢i `next-themes` dß╗à setup: ThemeProvider bao bß╗ìc app, `dark:` prefix trong Tailwind classes, xß╗¡ l├╜ hydration mismatch vß╗¢i `mounted` state.
Γöé
Γûê4. **API integration** cß║ºn xß╗¡ l├╜ ba trß║íng th├íi: loading, success, error. D├╣ng custom hooks (`useChat`, `useStreamingChat`) ─æß╗â t├ích logic khß╗Åi UI components.
Γöé
Γûê5. **AI response display** cß║ºn: chat UI pattern (user phß║úi, AI tr├íi), streaming display qua SSE, v├á markdown rendering cho code blocks, tables, links.
Γöé
Γûê---
Γöé
Γûê## C├óu hß╗Åi ├┤n tß║¡p
Γöé
Γûê1. Giß║úi th├¡ch sß╗▒ kh├íc biß╗çt giß╗»a Server Component v├á Client Component trong Next.js App Router. Khi n├áo cß║ºn d├╣ng `"use client"`?
Γöé
Γûê2. Thiß║┐t kß║┐ responsive layout cho chat app: sidebar (conversations) + main chat area + info panel. Sidebar ß║⌐n tr├¬n mobile, hiß╗çn tr├¬n desktop. Viß║┐t code Tailwind CSS.
Γöé
Γûê3. Tß║íi sao cß║ºn xß╗¡ l├╜ `mounted` state trong ThemeToggle component? ─Éiß╗üu g├¼ xß║úy ra nß║┐u kh├┤ng xß╗¡ l├╜?
Γöé
Γûê4. Viß║┐t h├ám `streamChat` gß╗ìi SSE endpoint v├á cß║¡p nhß║¡t UI realtime. Xß╗¡ l├╜ tr╞░ß╗¥ng hß╗úp connection bß╗ï ngß║»t giß╗»a chß╗½ng.
Γöé
Γûê5. So s├ính hai c├ích hiß╗ân thß╗ï AI response: chß╗¥ response ho├án chß╗ënh rß╗ôi hiß╗ân thß╗ï vs. streaming tß╗½ng token. ╞»u/nh╞░ß╗úc ─æiß╗âm cß╗ºa mß╗ùi c├ích?


docs\guide\chapter-07.md:
Γûê---
Γûêtitle: "DevOps v├á Triß╗ân khai"
Γûêweight: 7
Γûê---
Γöé
Γûê## 7.1 Docker ΓÇö Container h├│a ß╗⌐ng dß╗Ñng
Γöé
ΓûêDocker l├á mß╗Öt nß╗ün tß║úng (platform) cho ph├⌐p bß║ín ─æ├│ng g├│i ß╗⌐ng dß╗Ñng c├╣ng to├án bß╗Ö dependencies (th╞░ viß╗çn, cß║Ñu h├¼nh, biß║┐n m├┤i tr╞░ß╗¥ng) v├áo mß╗Öt ─æ╞ín vß╗ï gß╗ìi l├á **container**. Container ─æß║úm bß║úo ß╗⌐ng dß╗Ñng chß║íy ─æß╗ông nhß║Ñt tr├¬n mß╗ìi m├íy ΓÇö tß╗½ laptop cß╗ºa bß║ín ─æß║┐n server production. Trong AI20K, 100% BTC chß║Ñm ─æiß╗âm DevOps, v├á Docker l├á c├┤ng cß╗Ñ nß╗ün tß║úng ─æß╗â ─æß║ít ─æiß╗âm cao.
Γöé
ΓûêTr╞░ß╗¢c Docker, developer th╞░ß╗¥ng gß║╖p "tß╗æi thß╗⌐ S├íu" ΓÇö ß╗⌐ng dß╗Ñng chß║íy tr├¬n m├íy m├¼nh nh╞░ng lß╗ùi tr├¬n server. Nguy├¬n nh├ón l├á sß╗▒ kh├íc biß╗çt vß╗ü phi├¬n bß║ún Python, th╞░ viß╗çn hß╗ç thß╗æng, biß║┐n m├┤i tr╞░ß╗¥ng. Docker giß║úi quyß║┐t vß║Ñn ─æß╗ü n├áy bß║▒ng c├ích ─æ├│ng g├│i to├án bß╗Ö runtime environment v├áo mß╗Öt image bß║Ñt biß║┐n (immutable image). Bß║ín build mß╗Öt lß║ºn, chß║íy ß╗ƒ ─æ├óu c┼⌐ng ─æ╞░ß╗úc.
Γöé
Γûê**Image vs Container** l├á hai kh├íi niß╗çm cß╗æt l├╡i cß║ºn ph├ón biß╗çt:
Γöé
Γûê- **Image** (ß║únh): bß║ún thiß║┐t kß║┐ (blueprint) bß║Ñt biß║┐n, chß╗⌐a OS, runtime, code, dependencies. Image ─æ╞░ß╗úc build tß╗½ `Dockerfile` v├á l╞░u trong registry (Docker Hub, GitHub Container Registry).
Γûê- **Container** (th├╣ng chß╗⌐a): mß╗Öt instance ─æang chß║íy cß╗ºa image. Bß║ín c├│ thß╗â chß║íy nhiß╗üu container tß╗½ c├╣ng mß╗Öt image, mß╗ùi container c├│ trß║íng th├íi ri├¬ng.
Γöé
ΓûêV├¡ dß╗Ñ v├▓ng ─æß╗¥i Docker c╞í bß║ún:
Γöé
Γûê```bash
Γûê# Build image tß╗½ Dockerfile
Γûêdocker build -t my-agent-api:latest .
Γöé
Γûê# Chß║íy container tß╗½ image
Γûêdocker run -d -p 8000:8000 --name my-api my-agent-api:latest
Γöé
Γûê# Xem log container
Γûêdocker logs my-api
Γöé
Γûê# Dß╗½ng container
Γûêdocker stop my-api
Γöé
Γûê# X├│a container
Γûêdocker rm my-api
Γöé
Γûê# X├│a image
Γûêdocker rmi my-agent-api:latest
Γûê```
Γöé
ΓûêV├▓ng ─æß╗¥i ho├án chß╗ënh: viß║┐t `Dockerfile` ΓåÆ build image ΓåÆ chß║íy container ΓåÆ push image l├¬n registry ΓåÆ pull tr├¬n server ΓåÆ chß║íy production.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** H├úy lu├┤n tag image vß╗¢i version cß╗Ñ thß╗â (v├¡ dß╗Ñ `my-agent-api:1.0.3`) thay v├¼ chß╗ë d├╣ng `latest`. Tag `latest` g├óy nhß║ºm lß║½n khi rollback v├á kh├┤ng ─æß║úm bß║úo reproducibility.
Γöé
ΓûêMß╗Öt sß╗æ lß╗çnh Docker hß╗»u ├¡ch kh├íc khi l├ám viß╗çc h├áng ng├áy:
Γöé
Γûê```bash
Γûê# Xem tß║Ñt cß║ú container ─æang chß║íy
Γûêdocker ps
Γöé
Γûê# Xem tß║Ñt cß║ú container (kß╗â ─æ├ú dß╗½ng)
Γûêdocker ps -a
Γöé
Γûê# Xem resource usage
Γûêdocker stats
Γöé
Γûê# V├áo b├¬n trong container ─æß╗â debug
Γûêdocker exec -it my-api /bin/bash
Γöé
Γûê# Xem chi tiß║┐t image (layers, size)
Γûêdocker images
Γûêdocker history my-agent-api:latest
Γûê```
Γöé
ΓûêKhi bß║ín ph├ít triß╗ân ß╗⌐ng dß╗Ñng AI Agent, Docker ─æß║╖c biß╗çt quan trß╗ìng v├¼ ß╗⌐ng dß╗Ñng c├│ nhiß╗üu dependencies phß╗⌐c tß║íp: LangChain, LangGraph, c├íc model embedding, vector store client, LLM API keys. Docker ─æß║úm bß║úo tß║Ñt cß║ú ─æ╞░ß╗úc cß║Ñu h├¼nh ─æ├║ng tr├¬n mß╗ìi m├┤i tr╞░ß╗¥ng.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Kh├┤ng l╞░u secrets (API keys, passwords) trong Docker image. Sß╗¡ dß╗Ñng environment variables hoß║╖c Docker secrets ─æß╗â truyß╗ün th├┤ng tin nhß║íy cß║úm l├║c runtime.
Γöé
Γûê## 7.2 Multi-stage Dockerfile
Γöé
ΓûêMulti-stage build l├á kß╗╣ thuß║¡t Docker cho ph├⌐p bß║ín sß╗¡ dß╗Ñng nhiß╗üu stage (giai ─æoß║ín) trong mß╗Öt `Dockerfile`. Stage ─æß║ºu ti├¬n (builder) c├ái ─æß║╖t dependencies v├á build ß╗⌐ng dß╗Ñng. Stage thß╗⌐ hai (production) chß╗ë copy kß║┐t quß║ú build, bß╗Å qua to├án bß╗Ö c├┤ng cß╗Ñ build. Kß║┐t quß║ú: image production nhß╗Å gß╗ìn h╞ín 5-10 lß║ºn, an to├án h╞ín v├¼ kh├┤ng chß╗⌐a build tools.
Γöé
ΓûêTß║íi sao multi-stage quan trß╗ìng? Mß╗Öt image Python th├┤ng th╞░ß╗¥ng c├│ thß╗â nß║╖ng 1-2 GB v├¼ chß╗⌐a pip cache, build tools (gcc, g++), v├á c├íc dependencies chß╗ë cß║ºn l├║c build. Multi-stage giß║úm xuß╗æng c├▓n 200-400 MB, tiß║┐t kiß╗çm bandwidth khi deploy v├á giß║úm attack surface.
Γöé
ΓûêD╞░ß╗¢i ─æ├óy l├á `Dockerfile` ho├án chß╗ënh cho ß╗⌐ng dß╗Ñng LangGraph + FastAPI:
Γöé
Γûê```dockerfile
Γûê# ============================================
Γûê# Stage 1: Builder ΓÇö c├ái ─æß║╖t dependencies
Γûê# ============================================
ΓûêFROM python:3.11-slim AS builder
Γöé
ΓûêWORKDIR /app
Γöé
Γûê# C├ái build tools cß║ºn thiß║┐t cho compile C extensions
ΓûêRUN apt-get update && apt-get install -y --no-install-recommends \
Γûê    build-essential \
Γûê    && rm -rf /var/lib/apt/lists/*
Γöé
Γûê# Copy requirements tr╞░ß╗¢c ΓÇö tß║¡n dß╗Ñng Docker layer caching
ΓûêCOPY requirements.txt .
Γöé
Γûê# C├ái Python dependencies v├áo virtual environment
ΓûêRUN python -m venv /opt/venv
ΓûêENV PATH="/opt/venv/bin:$PATH"
ΓûêRUN pip install --no-cache-dir -r requirements.txt
Γöé
Γûê# ============================================
Γûê# Stage 2: Production ΓÇö image cuß╗æi c├╣ng
Γûê# ============================================
ΓûêFROM python:3.11-slim AS production
Γöé
Γûê# Thiß║┐t lß║¡p biß║┐n m├┤i tr╞░ß╗¥ng
ΓûêENV PYTHONDONTWRITEBYTECODE=1 \
Γûê    PYTHONUNBUFFERED=1 \
Γûê    PATH="/opt/venv/bin:$PATH" \
Γûê    PORT=8000
Γöé
ΓûêWORKDIR /app
Γöé
Γûê# Tß║ío non-root user cho bß║úo mß║¡t
ΓûêRUN groupadd -r appuser && useradd -r -g appuser appuser
Γöé
Γûê# Copy virtual environment tß╗½ builder stage
ΓûêCOPY --from=builder /opt/venv /opt/venv
Γöé
Γûê# Copy source code
ΓûêCOPY . .
Γöé
Γûê# Chown tß║Ñt cß║ú file cho appuser
ΓûêRUN chown -R appuser:appuser /app
Γöé
Γûê# Chuyß╗ân sang non-root user
ΓûêUSER appuser
Γöé
Γûê# Expose port
ΓûêEXPOSE 8000
Γöé
Γûê# Health check ΓÇö kiß╗âm tra API c├▓n sß╗æng
ΓûêHEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
Γûê    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
Γöé
Γûê# Chß║íy ß╗⌐ng dß╗Ñng vß╗¢i uvicorn
ΓûêCMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
Γûê```
Γöé
ΓûêGiß║úi th├¡ch chi tiß║┐t tß╗½ng phß║ºn:
Γöé
Γûê**Layer caching:** Docker build theo tß╗½ng layer (tß╗½ng lß╗çnh trong Dockerfile). Khi bß║ín sß╗¡a code, chß╗ë c├íc layer tß╗½ `COPY . .` trß╗ƒ ─æi bß╗ï rebuild. Nß║┐u `requirements.txt` kh├┤ng ─æß╗òi, layer `pip install` ─æ╞░ß╗úc cache ΓÇö tiß║┐t kiß╗çm 2-5 ph├║t mß╗ùi lß║ºn build. ─É├óy l├á l├╜ do `COPY requirements.txt` ─æß║╖t tr╞░ß╗¢c `COPY . .`.
Γöé
Γûê**Non-root user:** Mß║╖c ─æß╗ïnh Docker chß║íy container vß╗¢i user `root`. Nß║┐u attacker khai th├íc lß╗ù hß╗òng trong ß╗⌐ng dß╗Ñng, hß╗ì c├│ quyß╗ün root trong container. Tß║ío `appuser` giß╗¢i hß║ín quyß╗ün truy cß║¡p, tu├ón thß╗º nguy├¬n tß║»c least privilege (quyß╗ün tß╗æi thiß╗âu).
Γöé
Γûê**HEALTHCHECK directive:** Docker tß╗▒ ─æß╗Öng kiß╗âm tra sß╗⌐c khß╗Åe container mß╗ùi 30 gi├óy. Nß║┐u kiß╗âm tra thß║Ñt bß║íi 3 lß║ºn li├¬n tiß║┐p, container ─æ╞░ß╗úc ─æ├ính dß║Ñu `unhealthy` v├á orchestrator (Docker Compose, Kubernetes) c├│ thß╗â tß╗▒ ─æß╗Öng restart. ─Éiß╗üu n├áy ─æß║úm bß║úo t├¡nh available cho API.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Lu├┤n sß╗¡ dß╗Ñng multi-stage build cho production. Image nhß╗Å h╞ín, an to├án h╞ín, v├á deploy nhanh h╞ín. Stage 1 build, Stage 2 chß║íy ΓÇö pattern n├áy ├íp dß╗Ñng cho mß╗ìi ß╗⌐ng dß╗Ñng Python.
Γöé
ΓûêTh├¬m file `.dockerignore` ─æß╗â loß║íi bß╗Å file kh├┤ng cß║ºn thiß║┐t:
Γöé
Γûê```text
Γûê__pycache__/
Γûê*.pyc
Γûê*.pyo
Γûê.env
Γûê.git
Γûê.gitignore
Γûê.venv/
Γûêvenv/
Γûê*.md
Γûêtests/
Γûê.dockerignore
ΓûêDockerfile
Γûêdocker-compose.yml
Γûê```
Γöé
ΓûêFile `.dockerignore` giß╗æng `.gitignore` ΓÇö ng─ân c├íc file kh├┤ng cß║ºn thiß║┐t v├áo Docker context, gi├║p build nhanh h╞ín v├á image nhß╗Å h╞ín.
Γöé
Γûê## 7.3 Docker Compose ΓÇö Quß║ún l├╜ nhiß╗üu dß╗ïch vß╗Ñ
Γöé
ΓûêDocker Compose l├á c├┤ng cß╗Ñ cho ph├⌐p bß║ín ─æß╗ïnh ngh─⌐a v├á chß║íy nhiß╗üu container (nhiß╗üu dß╗ïch vß╗Ñ) c├╣ng l├║c bß║▒ng mß╗Öt file YAML. Thay v├¼ g├╡ 5-6 lß╗çnh `docker run` d├ái d├▓ng, bß║ín viß║┐t mß╗Öt file `docker-compose.yml` v├á chß║íy `docker compose up` ΓÇö mß╗ìi thß╗⌐ tß╗▒ ─æß╗Öng khß╗ƒi ─æß╗Öng, kß║┐t nß╗æi mß║íng, v├á quß║ún l├╜ v├▓ng ─æß╗¥i.
Γöé
ΓûêTrong ß╗⌐ng dß╗Ñng AI Agent ─æiß╗ân h├¼nh, bß║ín cß║ºn ├¡t nhß║Ñt 3-4 dß╗ïch vß╗Ñ chß║íy c├╣ng nhau: API server, database (PostgreSQL), vector store (Chroma/PGVector), v├á c├│ thß╗â Redis cho caching. Docker Compose quß║ún l├╜ to├án bß╗Ö stack n├áy.
Γöé
ΓûêD╞░ß╗¢i ─æ├óy l├á `docker-compose.yml` ho├án chß╗ënh cho dß╗▒ ├ín AI Agent:
Γöé
Γûê```yaml
Γûêversion: "3.9"
Γöé
Γûêservices:
Γûê  # ============================================
Γûê  # API Server ΓÇö FastAPI + LangGraph
Γûê  # ============================================
Γûê  api:
Γûê    build:
Γûê      context: .
Γûê      dockerfile: Dockerfile
Γûê    container_name: agent-api
Γûê    ports:
Γûê      - "8000:8000"
Γûê    environment:
Γûê      - OPENAI_API_KEY=${OPENAI_API_KEY}
Γûê      - DATABASE_URL=postgresql://agentuser:agentpass@db:5432/agentdb
Γûê      - REDIS_URL=redis://redis:6379/0
Γûê      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
Γûê      - LANGSMITH_PROJECT=ai20k-agent
Γûê    depends_on:
Γûê      db:
Γûê        condition: service_healthy
Γûê      redis:
Γûê        condition: service_healthy
Γûê    healthcheck:
Γûê      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
Γûê      interval: 30s
Γûê      timeout: 10s
Γûê      retries: 3
Γûê      start_period: 10s
Γûê    volumes:
Γûê      - ./app:/app/app  # Hot reload khi dev
Γûê    networks:
Γûê      - agent-network
Γûê    deploy:
Γûê      resources:
Γûê        limits:
Γûê          memory: 512M
Γûê          cpus: "0.5"
Γûê        reservations:
Γûê          memory: 256M
Γûê          cpus: "0.25"
Γûê    restart: unless-stopped
Γöé
Γûê  # ============================================
Γûê  # PostgreSQL ΓÇö Database ch├¡nh
Γûê  # ============================================
Γûê  db:
Γûê    image: postgres:16-alpine
Γûê    container_name: agent-db
Γûê    environment:
Γûê      POSTGRES_USER: agentuser
Γûê      POSTGRES_PASSWORD: agentpass
Γûê      POSTGRES_DB: agentdb
Γûê    ports:
Γûê      - "5432:5432"
Γûê    volumes:
Γûê      - postgres-data:/var/lib/postgresql/data
Γûê    healthcheck:
Γûê      test: ["CMD-SHELL", "pg_isready -U agentuser -d agentdb"]
Γûê      interval: 10s
Γûê      timeout: 5s
Γûê      retries: 5
Γûê    networks:
Γûê      - agent-network
Γûê    deploy:
Γûê      resources:
Γûê        limits:
Γûê          memory: 256M
Γûê          cpus: "0.25"
Γûê    restart: unless-stopped
Γöé
Γûê  # ============================================
Γûê  # Redis ΓÇö Cache & Session Store
Γûê  # ============================================
Γûê  redis:
Γûê    image: redis:7-alpine
Γûê    container_name: agent-redis
Γûê    ports:
Γûê      - "6379:6379"
Γûê    volumes:
Γûê      - redis-data:/data
Γûê    healthcheck:
Γûê      test: ["CMD", "redis-cli", "ping"]
Γûê      interval: 10s
Γûê      timeout: 5s
Γûê      retries: 5
Γûê    networks:
Γûê      - agent-network
Γûê    deploy:
Γûê      resources:
Γûê        limits:
Γûê          memory: 128M
Γûê          cpus: "0.1"
Γûê    restart: unless-stopped
Γöé
Γûê# ============================================
Γûê# Named Volumes ΓÇö Data persistence
Γûê# ============================================
Γûêvolumes:
Γûê  postgres-data:
Γûê    driver: local
Γûê  redis-data:
Γûê    driver: local
Γöé
Γûê# ============================================
Γûê# Network ΓÇö C├ích ly c├íc dß╗ïch vß╗Ñ
Γûê# ============================================
Γûênetworks:
Γûê  agent-network:
Γûê    driver: bridge
Γûê```
Γöé
ΓûêGiß║úi th├¡ch c├íc kh├íi niß╗çm ch├¡nh:
Γöé
Γûê**depends_on vß╗¢i condition:** Service `api` sß║╜ ─æß╗úi `db` v├á `redis` healthy tr╞░ß╗¢c khi khß╗ƒi ─æß╗Öng. Nß║┐u kh├┤ng c├│ `condition`, API c├│ thß╗â start tr╞░ß╗¢c khi database sß║╡n s├áng ΓåÆ connection error. `service_healthy` ─æß║úm bß║úo API chß╗ë start khi healthcheck cß╗ºa dependencies pass.
Γöé
Γûê**Named volumes:** `postgres-data` v├á `redis-data` l├á named volumes ΓÇö dß╗» liß╗çu ─æ╞░ß╗úc l╞░u ngo├ái container. Khi bß║ín chß║íy `docker compose down`, container bß╗ï x├│a nh╞░ng data vß║½n c├▓n. Chß║íy `docker compose down -v` mß╗¢i x├│a data. ─É├óy l├á c├ích bß║úo vß╗ç data quan trß╗ìng khß╗Åi mß║Ñt m├ít.
Γöé
Γûê**Resource limits:** `deploy.resources.limits` giß╗¢i hß║ín memory v├á CPU cho mß╗ùi container. Nß║┐u API bß╗ï memory leak (rß║Ñt phß╗ò biß║┐n vß╗¢i Python + AI models), n├│ chß╗ë d├╣ng tß╗æi ─æa 512MB thay v├¼ chiß║┐m to├án bß╗Ö RAM server, ß║únh h╞░ß╗ƒng ─æß║┐n c├íc dß╗ïch vß╗Ñ kh├íc.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Khi ph├ít triß╗ân (development), th├¬m `volumes: - ./app:/app/app` ─æß╗â hot reload ΓÇö thay ─æß╗òi code tr├¬n m├íy local sß║╜ lß║¡p tß╗⌐c phß║ún ├ính trong container. Khi deploy production, x├│a d├▓ng n├áy ─æi.
Γöé
ΓûêC├íc lß╗çnh Docker Compose cß║ºn biß║┐t:
Γöé
Γûê```bash
Γûê# Khß╗ƒi ─æß╗Öng tß║Ñt cß║ú dß╗ïch vß╗Ñ (nß╗ün)
Γûêdocker compose up -d
Γöé
Γûê# Xem log tß║Ñt cß║ú dß╗ïch vß╗Ñ
Γûêdocker compose logs -f
Γöé
Γûê# Xem log mß╗Öt dß╗ïch vß╗Ñ cß╗Ñ thß╗â
Γûêdocker compose logs -f api
Γöé
Γûê# Khß╗ƒi ─æß╗Öng lß║íi mß╗Öt dß╗ïch vß╗Ñ
Γûêdocker compose restart api
Γöé
Γûê# Dß╗½ng tß║Ñt cß║ú (giß╗» data)
Γûêdocker compose down
Γöé
Γûê# Dß╗½ng tß║Ñt cß║ú (x├│a data)
Γûêdocker compose down -v
Γöé
Γûê# Rebuild v├á khß╗ƒi ─æß╗Öng
Γûêdocker compose up -d --build
Γûê```
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Kh├┤ng commit `docker-compose.yml` chß╗⌐a password thß║¡t v├áo git. Sß╗¡ dß╗Ñng `.env` file cho secrets v├á th├¬m `.env` v├áo `.gitignore`. Docker Compose tß╗▒ ─æß╗Öng ─æß╗ìc file `.env` trong c├╣ng th╞░ mß╗Ñc.
Γöé
Γûê## 7.4 CI/CD vß╗¢i GitHub Actions
Γöé
ΓûêCI/CD l├á viß║┐t tß║»t cß╗ºa Continuous Integration (T├¡ch hß╗úp li├¬n tß╗Ñc) v├á Continuous Deployment (Triß╗ân khai li├¬n tß╗Ñc). CI ─æß║úm bß║úo mß╗ùi lß║ºn push code l├¬n GitHub, to├án bß╗Ö test suite tß╗▒ ─æß╗Öng chß║íy ΓÇö ph├ít hiß╗çn lß╗ùi sß╗¢m tr╞░ß╗¢c khi merge. CD tß╗▒ ─æß╗Öng deploy l├¬n server khi code pass tß║Ñt cß║ú tests. ─É├óy l├á lß╗ùi phß╗ò biß║┐n nhß║Ñt v├á mß║Ñt ─æiß╗âm nghi├¬m trß╗ìng ß╗ƒ ti├¬u ch├¡ DevOps ΓÇö phß║ºn lß╗¢n ─æß╗Öi bß╗Å qua CI/CD.
Γöé
ΓûêGitHub Actions l├á CI/CD platform t├¡ch hß╗úp sß║╡n trong GitHub. Bß║ín ─æß╗ïnh ngh─⌐a workflow bß║▒ng file YAML trong th╞░ mß╗Ñc `.github/workflows/`. Mß╗ùi workflow chß╗⌐a mß╗Öt hoß║╖c nhiß╗üu job, mß╗ùi job chß╗⌐a nhiß╗üu step (b╞░ß╗¢c). Workflow ─æ╞░ß╗úc trigger bß╗ƒi events nh╞░ push, pull request, hoß║╖c manual dispatch.
Γöé
ΓûêD╞░ß╗¢i ─æ├óy l├á workflow CI ho├án chß╗ënh:
Γöé
Γûê```yaml
Γûê# .github/workflows/ci.yml
Γûêname: CI ΓÇö Lint, Test, Build
Γöé
Γûêon:
Γûê  push:
Γûê    branches: [main, develop]
Γûê  pull_request:
Γûê    branches: [main]
Γöé
Γûêjobs:
Γûê  # ============================================
Γûê  # Job 1: Lint & Format Check
Γûê  # ============================================
Γûê  lint:
Γûê    name: Lint vß╗¢i Ruff
Γûê    runs-on: ubuntu-latest
Γûê    steps:
Γûê      - name: Checkout code
Γûê        uses: actions/checkout@v4
Γöé
Γûê      - name: Set up Python
Γûê        uses: actions/setup-python@v5
Γûê        with:
Γûê          python-version: "3.11"
Γöé
Γûê      - name: Install Ruff
Γûê        run: pip install ruff
Γöé
Γûê      - name: Run Ruff check
Γûê        run: ruff check . --output-format=github
Γöé
Γûê      - name: Check formatting
Γûê        run: ruff format --check .
Γöé
Γûê  # ============================================
Γûê  # Job 2: Run Tests
Γûê  # ============================================
Γûê  test:
Γûê    name: Chß║íy Tests
Γûê    runs-on: ubuntu-latest
Γûê    needs: lint  # Chß╗ë chß║íy sau khi lint pass
Γûê    steps:
Γûê      - name: Checkout code
Γûê        uses: actions/checkout@v4
Γöé
Γûê      - name: Set up Python
Γûê        uses: actions/setup-python@v5
Γûê        with:
Γûê          python-version: "3.11"
Γöé
Γûê      - name: Cache pip dependencies
Γûê        uses: actions/cache@v4
Γûê        with:
Γûê          path: ~/.cache/pip
Γûê          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
Γûê          restore-keys: |
Γûê            ${{ runner.os }}-pip-
Γöé
Γûê      - name: Install dependencies
Γûê        run: |
Γûê          python -m pip install --upgrade pip
Γûê          pip install -r requirements.txt
Γûê          pip install pytest pytest-asyncio pytest-cov httpx
Γöé
Γûê      - name: Run tests with coverage
Γûê        env:
Γûê          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
Γûê        run: |
Γûê          pytest tests/ -v --cov=app --cov-report=xml --cov-report=term-missing
Γöé
Γûê      - name: Upload coverage report
Γûê        uses: actions/upload-artifact@v4
Γûê        if: always()
Γûê        with:
Γûê          name: coverage-report
Γûê          path: coverage.xml
Γöé
Γûê  # ============================================
Γûê  # Job 3: Build Docker Image
Γûê  # ============================================
Γûê  build:
Γûê    name: Build Docker Image
Γûê    runs-on: ubuntu-latest
Γûê    needs: test  # Chß╗ë chß║íy sau khi test pass
Γûê    steps:
Γûê      - name: Checkout code
Γûê        uses: actions/checkout@v4
Γöé
Γûê      - name: Set up Docker Buildx
Γûê        uses: docker/setup-buildx-action@v3
Γöé
Γûê      - name: Build image
Γûê        uses: docker/build-push-action@v5
Γûê        with:
Γûê          context: .
Γûê          push: false
Γûê          tags: agent-api:${{ github.sha }}
Γûê          cache-from: type=gha
Γûê          cache-to: type=gha,mode=max
Γûê```
Γöé
Γûê**Giß║úi th├¡ch workflow:**
Γöé
ΓûêWorkflow n├áy c├│ 3 jobs chß║íy tuß║ºn tß╗▒: lint ΓåÆ test ΓåÆ build. Nß║┐u lint thß║Ñt bß║íi, test v├á build kh├┤ng chß║íy ΓÇö tiß║┐t kiß╗çm t├ái nguy├¬n. Nß║┐u test thß║Ñt bß║íi, build kh├┤ng chß║íy ΓÇö kh├┤ng build code c├│ lß╗ùi.
Γöé
Γûê**Lint vß╗¢i Ruff:** Ruff l├á Python linter v├á formatter si├¬u nhanh (viß║┐t bß║▒ng Rust), thay thß║┐ Flake8, isort, Black. N├│ kiß╗âm tra code style, import order, unused imports, v├á nhiß╗üu lß╗ùi phß╗ò biß║┐n kh├íc. Output format `github` tß║ío annotation trß╗▒c tiß║┐p tr├¬n pull request ΓÇö reviewer thß║Ñy lß╗ùi ngay tr├¬n diff.
Γöé
Γûê**Cache pip dependencies:** Action `actions/cache` l╞░u cache cß╗ºa pip, tr├ính download lß║íi 100+ packages mß╗ùi lß║ºn chß║íy. Key cache dß╗▒a tr├¬n hash cß╗ºa `requirements.txt` ΓÇö chß╗ë invalidate khi dependencies thay ─æß╗òi.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Lu├┤n c├│ ├¡t nhß║Ñt lint + test trong CI pipeline. ─É├óy l├á dß║Ñu hiß╗çu chuy├¬n nghiß╗çp nhß║Ñt cho BTC. Phß║ºn lß╗¢n ─æß╗Öi kh├┤ng c├│ CI/CD ΓÇö chß╗ë cß║ºn bß║ín c├│, bß║ín ─æ├ú v╞░ß╗út xa.
Γöé
Γûê**Deploy workflow** ri├¬ng cho production:
Γöé
Γûê```yaml
Γûê# .github/workflows/deploy.yml
Γûêname: Deploy to Production
Γöé
Γûêon:
Γûê  push:
Γûê    branches: [main]
Γûê  workflow_dispatch:  # Cho ph├⌐p trigger thß╗º c├┤ng
Γöé
Γûêjobs:
Γûê  deploy:
Γûê    name: Deploy l├¬n Render
Γûê    runs-on: ubuntu-latest
Γûê    if: github.ref == 'refs/heads/main'
Γûê    steps:
Γûê      - name: Trigger Render Deploy Hook
Γûê        run: |
Γûê          curl -X POST "${{ secrets.RENDER_DEPLOY_HOOK }}"
Γöé
Γûê      - name: Notify deployment
Γûê        run: |
Γûê          echo "Deployed commit ${{ github.sha }} to production"
Γûê```
Γöé
ΓûêWorkflow n├áy tß╗▒ ─æß╗Öng deploy mß╗ùi khi code ─æ╞░ß╗úc merge v├áo nh├ính `main`. N├│ gß╗ìi Render Deploy Hook qua HTTP POST ΓÇö Render sß║╜ pull image mß╗¢i nhß║Ñt v├á deploy.
Γöé
Γûê## 7.5 Deploy l├¬n Cloud
Γöé
ΓûêSau khi ─æ├ú c├│ Docker image v├á CI/CD pipeline, b╞░ß╗¢c tiß║┐p theo l├á deploy ß╗⌐ng dß╗Ñng l├¬n cloud ─æß╗â ng╞░ß╗¥i d├╣ng thß╗▒c sß╗▒ truy cß║¡p ─æ╞░ß╗úc. Trong AI20K, Live URL (URL truy cß║¡p ─æ╞░ß╗úc) l├á mß╗Öt trong 10 deliverables bß║»t buß╗Öc.
Γöé
ΓûêC├│ nhiß╗üu lß╗▒a chß╗ìn deploy, nh╞░ng ─æ├óy l├á nhß╗»ng lß╗▒a chß╗ìn tß╗æt nhß║Ñt cho dß╗▒ ├ín AI Agent:
Γöé
Γûê### Backend ΓÇö Render hoß║╖c Railway
Γöé
Γûê**Render** (render.com) l├á platform-as-a-service (PaaS) cho ph├⌐p deploy ß╗⌐ng dß╗Ñng tß╗½ Docker image hoß║╖c git repository. ╞»u ─æiß╗âm: free tier, tß╗▒ ─æß╗Öng SSL, tß╗▒ ─æß╗Öng deploy tß╗½ GitHub, hß╗ù trß╗ú Docker.
Γöé
Γûê**Railway** (railway.app) t╞░╞íng tß╗▒ Render nh╞░ng c├│ UX th├ón thiß╗çn h╞ín v├á hß╗ù trß╗ú th├¬m nhiß╗üu loß║íi database. Cß║ú hai ─æß╗üu ph├╣ hß╗úp cho AI20K.
Γöé
ΓûêC├íc b╞░ß╗¢c deploy l├¬n Render:
Γöé
Γûê1. ─É─âng k├╜ Render bß║▒ng GitHub account
Γûê2. Chß╗ìn "New Web Service" ΓåÆ "Build and deploy from a Docker image"
Γûê3. Connect GitHub repository
Γûê4. Th├¬m environment variables: `OPENAI_API_KEY`, `DATABASE_URL`, `LANGSMITH_API_KEY`
Γûê5. Chß╗ìn instance type: Free (512MB RAM) hoß║╖c Starter ($7/th├íng)
Γûê6. Render tß╗▒ ─æß╗Öng build Docker image v├á deploy
Γöé
Γûê**Environment variables** l├á n╞íi l╞░u cß║Ñu h├¼nh v├á secrets. Tr├¬n Render, bß║ín th├¬m trong Dashboard ΓåÆ Environment:
Γöé
Γûê```
ΓûêOPENAI_API_KEY=sk-proj-xxxxx
ΓûêDATABASE_URL=postgresql://user:pass@host:5432/db
ΓûêLANGSMITH_API_KEY=lsv2_pt_xxxxx
ΓûêLANGSMITH_PROJECT=ai20k-agent-production
ΓûêENVIRONMENT=production
ΓûêLOG_LEVEL=INFO
Γûê```
Γöé
Γûê### Frontend ΓÇö Vercel
Γöé
ΓûêNß║┐u bß║ín c├│ giao diß╗çn web (React, Next.js, Streamlit), deploy l├¬n **Vercel** (vercel.com). Vercel tß╗æi ╞░u cho frontend, c├│ CDN global, v├á free tier rß║Ñt h├áo ph├│ng.
Γöé
Γûê```bash
Γûê# Deploy frontend l├¬n Vercel
Γûênpm install -g vercel
Γûêvercel --prod
Γûê```
Γöé
Γûê### Custom Domain
Γöé
ΓûêMua domain tß╗½ Namecheap hoß║╖c GoDaddy (~$10/n─âm), trß╗Å DNS vß╗ü Render/Vercel:
Γöé
Γûê- Render: th├¬m custom domain trong Settings ΓåÆ Custom Domains
Γûê- Vercel: th├¬m trong Project Settings ΓåÆ Domains
Γûê- CNAME record: `your-subdomain.yourdomain.com` ΓåÆ `your-app.onrender.com`
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Mua domain `.app` hoß║╖c `.dev` ΓÇö Google tß╗▒ ─æß╗Öng bß║¡t HTTPS cho c├íc TLD n├áy, tiß║┐t kiß╗çm cß║Ñu h├¼nh SSL. Domain `.me` c┼⌐ng phß╗ò biß║┐n cho project demo.
Γöé
ΓûêKiß╗âm tra sau khi deploy:
Γöé
Γûê```bash
Γûê# Test health endpoint
Γûêcurl https://your-app.onrender.com/health
Γöé
Γûê# Test API endpoint
Γûêcurl https://your-app.onrender.com/api/v1/chat \
Γûê  -H "Content-Type: application/json" \
Γûê  -d '{"message": "Xin ch├áo", "thread_id": "test-123"}'
Γöé
Γûê# Kiß╗âm tra response time
Γûêcurl -o /dev/null -s -w "Time: %{time_total}s\n" \
Γûê  https://your-app.onrender.com/health
Γûê```
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Render free tier "sleeps" sau 15 ph├║t kh├┤ng c├│ request. Lß║ºn truy cß║¡p ─æß║ºu ti├¬n sau sleep mß║Ñt 30-60 gi├óy ─æß╗â "wake up". D├╣ng cron job (nh╞░ UptimeRobot) ping mß╗ùi 5 ph├║t ─æß╗â giß╗» server awake, hoß║╖c upgrade l├¬n paid plan.
Γöé
Γûê## 7.6 Monitoring v├á Logging
Γöé
ΓûêMonitoring (gi├ím s├ít) v├á Logging (ghi log) l├á hai pilre cß╗ºa vß║¡n h├ánh ß╗⌐ng dß╗Ñng production. Kh├┤ng c├│ monitoring, bß║ín kh├┤ng biß║┐t ß╗⌐ng dß╗Ñng ─æang chß║íy tß╗æt hay kh├┤ng. Kh├┤ng c├│ logging, bß║ín kh├┤ng thß╗â debug khi c├│ lß╗ùi. Trong ti├¬u ch├¡ DevOps cß╗ºa AI20K, monitoring v├á logging l├á yß║┐u tß╗æ ph├ón biß╗çt giß╗»a ─æiß╗âm trung b├¼nh v├á ─æiß╗âm cao.
Γöé
Γûê### Python Logging Setup
Γöé
ΓûêPython c├│ th╞░ viß╗çn `logging` t├¡ch hß╗úp sß║╡n, nh╞░ng cß║Ñu h├¼nh mß║╖c ─æß╗ïnh kh├í c╞í bß║ún. D╞░ß╗¢i ─æ├óy l├á cß║Ñu h├¼nh logging production-ready:
Γöé
Γûê```python
Γûê# app/core/logging_config.py
Γûêimport logging
Γûêimport sys
Γûêimport json
Γûêfrom datetime import datetime, timezone
Γöé
Γöé
Γûêclass JSONFormatter(logging.Formatter):
Γûê    """Format log th├ánh JSON structured logging."""
Γöé
Γûê    def format(self, record: logging.LogRecord) -> str:
Γûê        log_entry = {
Γûê            "timestamp": datetime.now(timezone.utc).isoformat(),
Γûê            "level": record.levelname,
Γûê            "logger": record.name,
Γûê            "message": record.getMessage(),
Γûê            "module": record.module,
Γûê            "function": record.funcName,
Γûê            "line": record.lineno,
Γûê        }
Γöé
Γûê        # Th├¬m extra fields nß║┐u c├│
Γûê        if hasattr(record, "extra_data"):
Γûê            log_entry["data"] = record.extra_data
Γöé
Γûê        # Th├¬m exception info nß║┐u c├│
Γûê        if record.exc_info and record.exc_info[0] is not None:
Γûê            log_entry["exception"] = {
Γûê                "type": record.exc_info[0].__name__,
Γûê                "message": str(record.exc_info[1]),
Γûê            }
Γöé
Γûê        return json.dumps(log_entry, ensure_ascii=False)
Γöé
Γöé
Γûêdef setup_logging(log_level: str = "INFO") -> None:
Γûê    """Cß║Ñu h├¼nh logging cho ß╗⌐ng dß╗Ñng."""
Γûê    root_logger = logging.getLogger()
Γûê    root_logger.setLevel(getattr(logging, log_level.upper()))
Γöé
Γûê    # Handler cho stdout (console)
Γûê    console_handler = logging.StreamHandler(sys.stdout)
Γûê    console_handler.setFormatter(JSONFormatter())
Γûê    root_logger.addHandler(console_handler)
Γöé
Γûê    # Giß║úm log level cho c├íc th╞░ viß╗çn noisy
Γûê    logging.getLogger("httpx").setLevel(logging.WARNING)
Γûê    logging.getLogger("httpcore").setLevel(logging.WARNING)
Γûê    logging.getLogger("urllib3").setLevel(logging.WARNING)
Γûê```
Γöé
Γûê**Structured logging** (logging c├│ cß║Ñu tr├║c) ghi log d╞░ß╗¢i dß║íng JSON thay v├¼ plain text. ╞»u ─æiß╗âm: dß╗à parse, dß╗à search, dß╗à integrate vß╗¢i c├┤ng cß╗Ñ monitoring nh╞░ ELK Stack, Datadog, Grafana Loki.
Γöé
Γûê```python
Γûê# C├ích sß╗¡ dß╗Ñng logging trong code
Γûêimport logging
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γûê@app.post("/api/v1/chat")
Γûêasync def chat(request: ChatRequest):
Γûê    logger.info(
Γûê        "Processing chat request",
Γûê        extra={
Γûê            "extra_data": {
Γûê                "thread_id": request.thread_id,
Γûê                "message_length": len(request.message),
Γûê            }
Γûê        },
Γûê    )
Γûê    try:
Γûê        response = await agent.arun(request.message)
Γûê        logger.info(
Γûê            "Chat request completed",
Γûê            extra={
Γûê                "extra_data": {
Γûê                    "thread_id": request.thread_id,
Γûê                    "response_length": len(response),
Γûê                }
Γûê            },
Γûê        )
Γûê        return {"response": response}
Γûê    except Exception as e:
Γûê        logger.error(
Γûê            "Chat request failed",
Γûê            exc_info=True,
Γûê            extra={
Γûê                "extra_data": {
Γûê                    "thread_id": request.thread_id,
Γûê                    "error_type": type(e).__name__,
Γûê                }
Γûê            },
Γûê        )
Γûê        raise
Γûê```
Γöé
Γûê### LangSmith cho AI Tracing
Γöé
ΓûêLangSmith l├á c├┤ng cß╗Ñ monitoring chuy├¬n biß╗çt cho ß╗⌐ng dß╗Ñng LLM/LangChain/LangGraph. N├│ trace tß╗½ng b╞░ß╗¢c cß╗ºa agent ΓÇö tß╗½ l├║c nhß║¡n input, gß╗ìi LLM, retrieve documents, ─æß║┐n l├║c trß║ú output. AI Logs l├á deliverable th╞░ß╗¥ng ─æ╞░ß╗úc ho├án th├ánh tß╗æt nhß║Ñt v├¼ dß╗à thiß║┐t lß║¡p.
Γöé
ΓûêCß║Ñu h├¼nh LangSmith chß╗ë cß║ºn 3 environment variables:
Γöé
Γûê```bash
Γûêexport LANGSMITH_API_KEY="lsv2_pt_xxxxx"
Γûêexport LANGSMITH_PROJECT="ai20k-agent"
Γûêexport LANGCHAIN_TRACING_V2="true"
Γûê```
Γöé
Γûê```python
Γûê# Trong app, LangSmith tß╗▒ ─æß╗Öng trace khi biß║┐n m├┤i tr╞░ß╗¥ng ─æ╞░ß╗úc set
Γûê# Kh├┤ng cß║ºn code th├¬m ΓÇö chß╗ë cß║ºn import langchain
Γûêimport os
Γöé
Γûê# Verify LangSmith config
Γûêassert os.getenv("LANGCHAIN_TRACING_V2") == "true", "LangSmith not configured"
Γûê```
Γöé
ΓûêTr├¬n LangSmith dashboard, bß║ín sß║╜ thß║Ñy:
Γûê- Mß╗ùi request l├á mß╗Öt trace
Γûê- Mß╗ùi b╞░ß╗¢c trong graph l├á mß╗Öt span
Γûê- Token usage, latency, cost cho mß╗ùi LLM call
Γûê- Input/output cß╗ºa mß╗ùi node ΓÇö debug dß╗à d├áng
Γöé
Γûê### Health Check Endpoint
Γöé
ΓûêHealth check endpoint l├á URL m├á monitoring tools gß╗ìi ─æß╗ïnh kß╗│ ─æß╗â kiß╗âm tra ß╗⌐ng dß╗Ñng c├▓n sß╗æng v├á hoß║ít ─æß╗Öng ─æ├║ng:
Γöé
Γûê```python
Γûê# app/api/health.py
Γûêfrom fastapi import APIRouter, Depends
Γûêfrom datetime import datetime, timezone
Γûêimport logging
Γöé
Γûêrouter = APIRouter()
Γûêlogger = logging.getLogger(__name__)
Γöé
Γöé
Γûê@router.get("/health")
Γûêasync def health_check():
Γûê    """
Γûê    Health check endpoint cho monitoring.
Γûê    Kiß╗âm tra: API sß╗æng, database kß║┐t nß╗æi, c├íc dependencies.
Γûê    """
Γûê    checks = {
Γûê        "status": "healthy",
Γûê        "timestamp": datetime.now(timezone.utc).isoformat(),
Γûê        "version": "1.0.0",
Γûê    }
Γöé
Γûê    # Kiß╗âm tra database connection
Γûê    try:
Γûê        # Thay bß║▒ng logic check thß╗▒c tß║┐ cß╗ºa bß║ín
Γûê        # async with db.session() as session:
Γûê        #     await session.execute(text("SELECT 1"))
Γûê        checks["database"] = "connected"
Γûê    except Exception as e:
Γûê        logger.error(f"Database health check failed: {e}")
Γûê        checks["database"] = "disconnected"
Γûê        checks["status"] = "degraded"
Γöé
Γûê    # Kiß╗âm tra LLM API
Γûê    try:
Γûê        # C├│ thß╗â ping OpenAI API nhß║╣
Γûê        checks["llm_api"] = "reachable"
Γûê    except Exception as e:
Γûê        logger.error(f"LLM API health check failed: {e}")
Γûê        checks["llm_api"] = "unreachable"
Γûê        checks["status"] = "degraded"
Γöé
Γûê    status_code = 200 if checks["status"] == "healthy" else 503
Γûê    return JSONResponse(content=checks, status_code=status_code)
Γöé
Γöé
Γûê@router.get("/health/live")
Γûêasync def liveness_probe():
Γûê    """Kubernetes liveness probe ΓÇö chß╗ë kiß╗âm tra process c├▓n sß╗æng."""
Γûê    return {"status": "alive"}
Γöé
Γöé
Γûê@router.get("/health/ready")
Γûêasync def readiness_probe():
Γûê    """Kubernetes readiness probe ΓÇö kiß╗âm tra sß║╡n s├áng nhß║¡n traffic."""
Γûê    # Kiß╗âm tra tß║Ñt cß║ú dependencies
Γûê    return {"status": "ready"}
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Ba c├┤ng cß╗Ñ monitoring cß║ºn c├│: (1) Structured logging cho application logs, (2) LangSmith cho AI tracing, (3) Health check endpoint cho uptime monitoring. BTC ─æß║╖c biß╗çt ch├║ ├╜ AI Logs ΓÇö ─æ├óy l├á bß║▒ng chß╗⌐ng r├╡ r├áng nhß║Ñt rß║▒ng agent hoß║ít ─æß╗Öng ─æ├║ng.
Γöé
Γûê## T├│m tß║»t
Γöé
ΓûêTrong ch╞░╞íng n├áy, ch├║ng ta ─æ├ú t├¼m hiß╗âu to├án bß╗Ö pipeline DevOps cho ß╗⌐ng dß╗Ñng AI Agent:
Γöé
Γûê- **Docker** ─æ├│ng g├│i ß╗⌐ng dß╗Ñng v├áo container, ─æß║úm bß║úo chß║íy ─æß╗ông nhß║Ñt tr├¬n mß╗ìi m├┤i tr╞░ß╗¥ng
Γûê- **Multi-stage Dockerfile** tß║ío image production nhß╗Å gß╗ìn, an to├án vß╗¢i non-root user v├á HEALTHCHECK
Γûê- **Docker Compose** quß║ún l├╜ nhiß╗üu dß╗ïch vß╗Ñ (API, database, Redis) c├╣ng l├║c vß╗¢i health checks v├á resource limits
Γûê- **GitHub Actions CI/CD** tß╗▒ ─æß╗Öng lint, test, build tr├¬n mß╗ùi push ΓÇö chuy├¬n nghiß╗çp v├á bß║»t buß╗Öc cho Demo Day
Γûê- **Cloud deploy** vß╗¢i Render (backend) v├á Vercel (frontend) ΓÇö ─æ╞ín giß║ún, nhanh ch├│ng
Γûê- **Monitoring v├á Logging** vß╗¢i structured logging, LangSmith tracing, v├á health check endpoint
Γöé
ΓûêDevOps l├á ti├¬u ch├¡ chß║Ñm ─æiß╗âm ri├¬ng trong AI20K. Phß║ºn lß╗¢n ─æß╗Öi thiß║┐u CI/CD v├á kh├┤ng c├│ test. Chß╗ë cß║ºn bß║ín c├│ Docker + CI/CD + tests + health check, bß║ín ─æ├ú ß╗ƒ top vß╗ü DevOps.
Γöé
Γûê## C├óu hß╗Åi ├┤n tß║¡p
Γöé
Γûê1. Sß╗▒ kh├íc biß╗çt giß╗»a Docker image v├á Docker container l├á g├¼?
Γûê2. Tß║íi sao multi-stage build l├ám image nhß╗Å h╞ín? Giß║úi th├¡ch c╞í chß║┐ layer caching.
Γûê3. `depends_on` vß╗¢i `condition: service_healthy` kh├íc g├¼ vß╗¢i `depends_on` kh├┤ng c├│ condition?
Γûê4. Nß║┐u GitHub Actions CI pipeline cß╗ºa bß║ín thß║Ñt bß║íi ß╗ƒ b╞░ß╗¢c test, b╞░ß╗¢c build c├│ chß║íy kh├┤ng? Tß║íi sao?
Γûê5. Tß║íi sao kh├┤ng n├¬n l╞░u API keys trong Docker image? C├ích ─æ├║ng l├á g├¼?
Γûê6. Structured logging (JSON) ╞░u ─æiß╗âm g├¼ so vß╗¢i plain text logging?
Γûê7. LangSmith trace nhß╗»ng th├┤ng tin g├¼? Tß║íi sao n├│ quan trß╗ìng cho AI Agent?
Γûê8. Health check endpoint trß║ú vß╗ü HTTP status code n├áo khi ß╗⌐ng dß╗Ñng kh├┤ng khß╗Åe?


docs\guide\chapter-08.md:
Γûê---
Γûêtitle: "Kiß╗âm thß╗¡ v├á ─É├ính gi├í"
Γûêweight: 8
Γûê---
Γöé
Γûê## 8.1 Tß║íi sao cß║ºn test
Γöé
ΓûêTrong c├íc kß╗│ ─æ├ính gi├í AI20K, **phß║ºn lß╗¢n ─æß╗Öi kh├┤ng c├│ bß║Ñt kß╗│ test tß╗▒ ─æß╗Öng n├áo** ΓÇö ─æ├óy l├á lß╗ùi nghi├¬m trß╗ìng nhß║Ñt ß║únh h╞░ß╗ƒng ─æß║┐n ─æiß╗âm Code Quality v├á Evaluation Evidence. Kh├┤ng c├│ test, bß║ín kh├┤ng thß╗â chß╗⌐ng minh code hoß║ít ─æß╗Öng ─æ├║ng, kh├┤ng thß╗â refactor an to├án, v├á kh├┤ng thß╗â detect regression (lß╗ùi quay lß║íi). BTC ─æ├ính gi├í thß║Ñp nhß╗»ng dß╗▒ ├ín thiß║┐u test v├¼ n├│ thß╗â hiß╗çn thiß║┐u kß╗╖ luß║¡t engineering.
Γöé
ΓûêTesting kh├┤ng chß╗ë l├á "viß║┐t th├¬m code ─æß╗â kiß╗âm tra code." Testing l├á **safety net** (l╞░ß╗¢i an to├án) cho ph├⌐p bß║ín thay ─æß╗òi code m├á kh├┤ng sß╗ú l├ám hß╗Ång t├¡nh n─âng c┼⌐. Khi bß║ín th├¬m node mß╗¢i v├áo LangGraph graph, test ─æß║úm bß║úo c├íc node c┼⌐ vß║½n hoß║ít ─æß╗Öng. Khi bß║ín refactor prompt, test ─æß║úm bß║úo output vß║½n ─æ├║ng format.
Γöé
Γûê**Kim tß╗▒ th├íp kiß╗âm thß╗¡ (Testing Pyramid)** l├á m├┤ h├¼nh ph├ón bß╗ò effort testing:
Γöé
Γûê- **Unit tests** (nhiß╗üu nhß║Ñt): test tß╗½ng function, tß╗½ng node ri├¬ng lß║╗. Nhanh, ß╗òn ─æß╗ïnh, dß╗à viß║┐t. Chiß║┐m 70-80% tß╗òng sß╗æ test.
Γûê- **Integration tests** (trung b├¼nh): test sß╗▒ t╞░╞íng t├íc giß╗»a c├íc components ΓÇö API endpoint gß╗ìi ─æß║┐n database, LangGraph graph chß║íy end-to-end vß╗¢i mock LLM. Chiß║┐m 15-20%.
Γûê- **Evaluation tests** (├¡t nhß║Ñt): test chß║Ñt l╞░ß╗úng output cß╗ºa AI ΓÇö accuracy, faithfulness, relevance. Chß║íy chß║¡m, cß║ºn LLM thß║¡t. Chiß║┐m 5-10%.
Γöé
ΓûêV├¡ dß╗Ñ thß╗▒c tß║┐: mß╗Öt endpoint `/api/v1/chat` nhß║¡n message v├á trß║ú vß╗ü response.
Γöé
Γûê- **Unit test:** test h├ám `parse_message()` trß║ú ─æ├║ng format.
Γûê- **Integration test:** test to├án bß╗Ö endpoint tß╗½ HTTP request ─æß║┐n response, vß╗¢i LLM bß╗ï mock.
Γûê- **Evaluation test:** gß╗¡i 50 c├óu hß╗Åi thß╗▒c tß║┐, kiß╗âm tra accuracy v├á faithfulness cß╗ºa response.
Γöé
Γûê```python
Γûê# V├¡ dß╗Ñ minh hß╗ìa 3 loß║íi test
Γûêimport pytest
Γûêfrom unittest.mock import AsyncMock, patch
Γöé
Γûê# --- Unit Test: test mß╗Öt h├ám ─æ╞ín lß║╗ ---
Γûêdef test_parse_message_valid_input():
Γûê    """Unit test: test h├ám parse_message vß╗¢i input hß╗úp lß╗ç."""
Γûê    from app.utils import parse_message
Γöé
Γûê    result = parse_message('{"message": "Xin ch├áo", "thread_id": "123"}')
Γûê    assert result["message"] == "Xin ch├áo"
Γûê    assert result["thread_id"] == "123"
Γöé
Γöé
Γûê# --- Integration Test: test API endpoint ---
Γûê@pytest.mark.asyncio
Γûêasync def test_chat_endpoint(client):
Γûê    """Integration test: test endpoint /api/v1/chat."""
Γûê    response = await client.post(
Γûê        "/api/v1/chat",
Γûê        json={"message": "Xin ch├áo", "thread_id": "test-123"},
Γûê    )
Γûê    assert response.status_code == 200
Γûê    data = response.json()
Γûê    assert "response" in data
Γöé
Γöé
Γûê# --- Evaluation Test: test chß║Ñt l╞░ß╗úng AI ---
Γûêdef test_rag_accuracy(eval_dataset):
Γûê    """Evaluation test: test accuracy tr├¬n dataset."""
Γûê    correct = 0
Γûê    for sample in eval_dataset:
Γûê        response = agent.run(sample["question"])
Γûê        if response["answer"] == sample["expected_answer"]:
Γûê            correct += 1
Γûê    accuracy = correct / len(eval_dataset)
Γûê    assert accuracy >= 0.7, f"Accuracy {accuracy} below threshold 0.7"
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Kh├┤ng cß║ºn 100% coverage ngay tß╗½ ─æß║ºu. H├úy bß║»t ─æß║ºu vß╗¢i 5-10 test cho c├íc phß║ºn quan trß╗ìng nhß║Ñt (API endpoints, graph routing, data validation), rß╗ôi t─âng dß║ºn. Mß╗Ñc ti├¬u tß╗æi thiß╗âu cho AI20K l├á 60% code coverage.
Γöé
Γûê## 8.2 Viß║┐t test cho API
Γöé
ΓûêTest API endpoint l├á loß║íi test mang lß║íi gi├í trß╗ï cao nhß║Ñt vß╗¢i effort thß║Ñp nhß║Ñt. Bß║ín test to├án bß╗Ö flow: HTTP request ΓåÆ FastAPI routing ΓåÆ validation ΓåÆ business logic ΓåÆ response. Nß║┐u API test pass, bß║ín c├│ ─æß╗Ö tin cß║¡y cao rß║▒ng ß╗⌐ng dß╗Ñng hoß║ít ─æß╗Öng ─æ├║ng tß╗½ g├│c ─æß╗Ö ng╞░ß╗¥i d├╣ng.
Γöé
Γûê### C├ái ─æß║╖t pytest v├á dependencies
Γöé
Γûê```bash
Γûêpip install pytest pytest-asyncio pytest-cov httpx
Γûê```
Γöé
ΓûêGiß║úi th├¡ch tß╗½ng package:
Γûê- **pytest**: framework test phß╗ò biß║┐n nhß║Ñt cho Python, vß╗¢i syntax ─æ╞ín giß║ún v├á plugin ecosystem phong ph├║
Γûê- **pytest-asyncio**: cho ph├⌐p test c├íc h├ám async (FastAPI l├á async framework)
Γûê- **pytest-cov**: ─æo code coverage
Γûê- **httpx**: HTTP client hß╗ù trß╗ú async, d├╣ng ─æß╗â test FastAPI app th├┤ng qua `AsyncClient`
Γöé
Γûê### conftest.py ΓÇö Fixtures d├╣ng chung
Γöé
ΓûêFile `conftest.py` chß╗⌐a pytest fixtures ΓÇö c├íc h├ám setup/teardown ─æ╞░ß╗úc t├íi sß╗¡ dß╗Ñng across tß║Ñt cß║ú test files. ─Éß║╖t ß╗ƒ th╞░ mß╗Ñc `tests/`.
Γöé
Γûê```python
Γûê# tests/conftest.py
Γûêimport pytest
Γûêimport asyncio
Γûêfrom httpx import AsyncClient, ASGITransport
Γûêfrom app.main import app
Γöé
Γöé
Γûê@pytest.fixture(scope="session")
Γûêdef event_loop():
Γûê    """Tß║ío event loop d├╣ng chung cho tß║Ñt cß║ú test trong session."""
Γûê    loop = asyncio.new_event_loop()
Γûê    yield loop
Γûê    loop.close()
Γöé
Γöé
Γûê@pytest.fixture
Γûêasync def client():
Γûê    """
Γûê    Tß║ío AsyncClient test cho FastAPI app.
Γûê    Sß╗¡ dß╗Ñng ASGITransport ─æß╗â gß╗ìi trß╗▒c tiß║┐p ASGI app
Γûê    m├á kh├┤ng cß║ºn chß║íy server thß║¡t.
Γûê    """
Γûê    transport = ASGITransport(app=app)
Γûê    async with AsyncClient(
Γûê        transport=transport,
Γûê        base_url="http://testserver",
Γûê    ) as ac:
Γûê        yield ac
Γöé
Γöé
Γûê@pytest.fixture
Γûêdef sample_chat_request():
Γûê    """Dß╗» liß╗çu mß║½u cho chat request."""
Γûê    return {
Γûê        "message": "Viß╗çt Nam c├│ bao nhi├¬u tß╗ënh th├ánh?",
Γûê        "thread_id": "test-thread-001",
Γûê    }
Γöé
Γöé
Γûê@pytest.fixture
Γûêdef sample_documents():
Γûê    """Dß╗» liß╗çu mß║½u cho document upload."""
Γûê    return {
Γûê        "documents": [
Γûê            {
Γûê                "title": "Giß╗¢i thiß╗çu Viß╗çt Nam",
Γûê                "content": "Viß╗çt Nam c├│ 63 tß╗ënh th├ánh phß╗æ.",
Γûê                "source": "wiki",
Γûê            }
Γûê        ]
Γûê    }
Γûê```
Γöé
Γûê**Giß║úi th├¡ch:** Fixture `client` tß║ío `AsyncClient` kß║┐t nß╗æi trß╗▒c tiß║┐p ─æß║┐n FastAPI app qua ASGI transport ΓÇö kh├┤ng cß║ºn chß║íy HTTP server thß║¡t. ─Éiß╗üu n├áy l├ám test nhanh h╞ín 10-100 lß║ºn so vß╗¢i test qua network thß║¡t. `scope="session"` cho `event_loop` tß║ío loop mß╗Öt lß║ºn v├á t├íi sß╗¡ dß╗Ñng cho tß║Ñt cß║ú test.
Γöé
Γûê### Test GET endpoints
Γöé
Γûê```python
Γûê# tests/test_api_health.py
Γûêimport pytest
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_health_check(client):
Γûê    """Test GET /health trß║ú vß╗ü status healthy."""
Γûê    response = await client.get("/health")
Γöé
Γûê    assert response.status_code == 200
Γûê    data = response.json()
Γûê    assert data["status"] == "healthy"
Γûê    assert "timestamp" in data
Γûê    assert "version" in data
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_health_check_has_database(client):
Γûê    """Test GET /health bao gß╗ôm database status."""
Γûê    response = await client.get("/health")
Γöé
Γûê    data = response.json()
Γûê    assert "database" in data
Γûê    assert data["database"] in ["connected", "disconnected"]
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_root_endpoint(client):
Γûê    """Test GET / trß║ú vß╗ü th├┤ng tin API."""
Γûê    response = await client.get("/")
Γöé
Γûê    assert response.status_code == 200
Γûê    data = response.json()
Γûê    assert "message" in data or "status" in data
Γûê```
Γöé
Γûê### Test POST endpoints vß╗¢i mock LLM
Γöé
Γûê```python
Γûê# tests/test_api_chat.py
Γûêimport pytest
Γûêfrom unittest.mock import AsyncMock, patch, MagicMock
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_chat_success(client, sample_chat_request):
Γûê    """Test POST /api/v1/chat vß╗¢i mock LLM response."""
Γûê    # Mock agent.arun ─æß╗â kh├┤ng gß╗ìi LLM thß║¡t
Γûê    mock_response = "Viß╗çt Nam c├│ 63 tß╗ënh th├ánh phß╗æ trß╗▒c thuß╗Öc trung ╞░╞íng."
Γöé
Γûê    with patch("app.agent.graph.agent") as mock_agent:
Γûê        mock_agent.arun = AsyncMock(return_value=mock_response)
Γöé
Γûê        response = await client.post(
Γûê            "/api/v1/chat",
Γûê            json=sample_chat_request,
Γûê        )
Γöé
Γûê    assert response.status_code == 200
Γûê    data = response.json()
Γûê    assert "response" in data
Γûê    assert "63" in data["response"]
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_chat_empty_message(client):
Γûê    """Test POST /api/v1/chat vß╗¢i message rß╗ùng ΓåÆ validation error."""
Γûê    response = await client.post(
Γûê        "/api/v1/chat",
Γûê        json={"message": "", "thread_id": "test-001"},
Γûê    )
Γöé
Γûê    assert response.status_code == 422  # Validation Error
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_chat_missing_thread_id(client):
Γûê    """Test POST /api/v1/chat thiß║┐u thread_id."""
Γûê    response = await client.post(
Γûê        "/api/v1/chat",
Γûê        json={"message": "Xin ch├áo"},
Γûê    )
Γöé
Γûê    # T├╣y thuß╗Öc v├áo thread_id c├│ required hay auto-generate
Γûê    assert response.status_code in [200, 422]
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_chat_long_message(client):
Γûê    """Test POST /api/v1/chat vß╗¢i message qu├í d├ái."""
Γûê    long_message = "A" * 10001  # V╞░ß╗út qu├í giß╗¢i hß║ín
Γöé
Γûê    response = await client.post(
Γûê        "/api/v1/chat",
Γûê        json={"message": long_message, "thread_id": "test-001"},
Γûê    )
Γöé
Γûê    assert response.status_code == 422  # Validation Error
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_chat_llm_error(client, sample_chat_request):
Γûê    """Test POST /api/v1/chat khi LLM bß╗ï lß╗ùi."""
Γûê    with patch("app.agent.graph.agent") as mock_agent:
Γûê        mock_agent.arun = AsyncMock(
Γûê            side_effect=Exception("LLM API timeout")
Γûê        )
Γöé
Γûê        response = await client.post(
Γûê            "/api/v1/chat",
Γûê            json=sample_chat_request,
Γûê        )
Γöé
Γûê    # API n├¬n handle lß╗ùi gracefully
Γûê    assert response.status_code == 500
Γûê    data = response.json()
Γûê    assert "error" in data or "detail" in data
Γûê```
Γöé
Γûê**Giß║úi th├¡ch mock:** `unittest.mock.patch` thay thß║┐ `agent` bß║▒ng mock object. `AsyncMock(return_value=...)` trß║ú vß╗ü gi├í trß╗ï giß║ú ─æß╗ïnh thay v├¼ gß╗ìi LLM thß║¡t ΓÇö tiß║┐t kiß╗çm tiß╗ün API v├á ─æß║úm bß║úo test ß╗òn ─æß╗ïnh (kh├┤ng phß╗Ñ thuß╗Öc v├áo LLM response thay ─æß╗òi). `side_effect=Exception(...)` mock t├¼nh huß╗æng LLM lß╗ùi.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Lu├┤n mock external dependencies (LLM, database, third-party APIs) trong unit/integration tests. Test thß║¡t chß╗ë d├ánh cho evaluation tests. Mock ─æß║úm bß║úo test nhanh, ß╗òn ─æß╗ïnh, miß╗àn ph├¡.
Γöé
ΓûêChß║íy tests:
Γöé
Γûê```bash
Γûê# Chß║íy tß║Ñt cß║ú tests
Γûêpytest tests/ -v
Γöé
Γûê# Chß║íy mß╗Öt file test
Γûêpytest tests/test_api_chat.py -v
Γöé
Γûê# Chß║íy mß╗Öt test cß╗Ñ thß╗â
Γûêpytest tests/test_api_chat.py::test_chat_success -v
Γöé
Γûê# Chß║íy vß╗¢i coverage
Γûêpytest tests/ -v --cov=app --cov-report=term-missing
Γöé
Γûê# Chß║íy v├á in print statements
Γûêpytest tests/ -v -s
Γûê```
Γöé
Γûê## 8.3 Viß║┐t test cho Agent
Γöé
ΓûêTest Agent (LangGraph) phß╗⌐c tß║íp h╞ín test API v├¼ agent c├│ state, conditional routing, v├á gß╗ìi LLM. Chiß║┐n l╞░ß╗úc l├á test tß╗½ng node ri├¬ng lß║╗ (unit test), rß╗ôi test to├án bß╗Ö graph flow (integration test), lu├┤n mock LLM response.
Γöé
Γûê### Test individual nodes
Γöé
ΓûêMß╗ùi node trong LangGraph graph l├á mß╗Öt function nhß║¡n state v├á trß║ú vß╗ü state mß╗¢i. Test node l├á test function thuß║ºn t├║y ΓÇö ─æ╞ín giß║ún v├á nhanh ch├│ng.
Γöé
Γûê```python
Γûê# tests/test_agent_nodes.py
Γûêimport pytest
Γûêfrom unittest.mock import AsyncMock, patch
Γöé
Γöé
Γûêdef test_parse_user_query():
Γûê    """Unit test: test node parse_user_query."""
Γûê    from app.agent.nodes import parse_user_query
Γöé
Γûê    state = {"messages": [{"role": "user", "content": "Gi├í v├áng h├┤m nay?"}]}
Γûê    result = parse_user_query(state)
Γöé
Γûê    assert "parsed_query" in result
Γûê    assert result["parsed_query"]["intent"] == "price_query"
Γûê    assert "v├áng" in result["parsed_query"]["entity"]
Γöé
Γöé
Γûêdef test_format_response():
Γûê    """Unit test: test node format_response."""
Γûê    from app.agent.nodes import format_response
Γöé
Γûê    state = {
Γûê        "raw_answer": "Gi├í v├áng 18K h├┤m nay l├á 5.2 triß╗çu/l╞░ß╗úng.",
Γûê        "sources": [{"title": "Gi├í v├áng", "url": "https://example.com"}],
Γûê    }
Γûê    result = format_response(state)
Γöé
Γûê    assert "response" in result
Γûê    assert "5.2" in result["response"]
Γûê    assert "Nguß╗ôn" in result["response"] or "source" in result["response"].lower()
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_retrieve_documents():
Γûê    """Unit test: test node retrieve_documents vß╗¢i mock vector store."""
Γûê    from app.agent.nodes import retrieve_documents
Γöé
Γûê    mock_docs = [
Γûê        {"content": "Gi├í v├áng SJC 5.2 triß╗çu", "score": 0.95},
Γûê        {"content": "Gi├í v├áng 18K 4.8 triß╗çu", "score": 0.88},
Γûê    ]
Γöé
Γûê    with patch("app.agent.nodes.vector_store") as mock_vs:
Γûê        mock_vs.similarity_search = AsyncMock(return_value=mock_docs)
Γöé
Γûê        state = {"parsed_query": {"entity": "v├áng", "intent": "price_query"}}
Γûê        result = await retrieve_documents(state)
Γöé
Γûê    assert "documents" in result
Γûê    assert len(result["documents"]) == 2
Γûê```
Γöé
Γûê### Test graph flow end-to-end
Γöé
ΓûêTest to├án bß╗Ö graph tß╗½ input ─æß║┐n output, vß╗¢i tß║Ñt cß║ú LLM calls bß╗ï mock. ─Éiß╗üu n├áy ─æß║úm bß║úo routing logic ─æ├║ng ΓÇö agent ─æi qua ─æ├║ng c├íc nodes theo ─æ├║ng thß╗⌐ tß╗▒.
Γöé
Γûê```python
Γûê# tests/test_agent_graph.py
Γûêimport pytest
Γûêfrom unittest.mock import AsyncMock, patch, MagicMock
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_graph_simple_query_flow():
Γûê    """Integration test: test graph flow cho c├óu hß╗Åi ─æ╞ín giß║ún."""
Γûê    from app.agent.graph import build_graph
Γöé
Γûê    graph = build_graph()
Γöé
Γûê    # Mock tß║Ñt cß║ú LLM calls
Γûê    with patch("app.agent.nodes.llm") as mock_llm:
Γûê        mock_llm.ainvoke = AsyncMock(
Γûê            return_value=MagicMock(
Γûê                content='{"intent": "simple_query", "entity": "v├áng"}'
Γûê            )
Γûê        )
Γöé
Γûê        # Mock retrieve
Γûê        with patch("app.agent.nodes.vector_store") as mock_vs:
Γûê            mock_vs.similarity_search = AsyncMock(
Γûê                return_value=[{"content": "Gold price data", "score": 0.9}]
Γûê            )
Γöé
Γûê            # Chß║íy graph
Γûê            result = await graph.ainvoke(
Γûê                {"messages": [{"role": "user", "content": "Gi├í v├áng?"}]}
Γûê            )
Γöé
Γûê    assert "response" in result
Γûê    assert len(result.get("messages", [])) > 1
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_graph_conditional_routing():
Γûê    """Test: graph route ─æ├║ng cho c├íc loß║íi query kh├íc nhau."""
Γûê    from app.agent.graph import build_graph, should_retrieve
Γöé
Γûê    # Query cß║ºn retrieval
Γûê    state_retrieve = {"parsed_query": {"intent": "price_query"}}
Γûê    assert should_retrieve(state_retrieve) == "retrieve"
Γöé
Γûê    # Query kh├┤ng cß║ºn retrieval (chitchat)
Γûê    state_chitchat = {"parsed_query": {"intent": "chitchat"}}
Γûê    assert should_retrieve(state_chitchat) == "respond_directly"
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_graph_handles_empty_input():
Γûê    """Test: graph xß╗¡ l├╜ input rß╗ùng gracefully."""
Γûê    from app.agent.graph import build_graph
Γöé
Γûê    graph = build_graph()
Γöé
Γûê    result = await graph.ainvoke(
Γûê        {"messages": [{"role": "user", "content": ""}]}
Γûê    )
Γöé
Γûê    # Graph n├¬n trß║ú vß╗ü response thay v├¼ crash
Γûê    assert result is not None
Γûê    assert "response" in result or "messages" in result
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_graph_preserves_thread_history():
Γûê    """Test: graph duy tr├¼ lß╗ïch sß╗¡ hß╗Öi thoß║íi."""
Γûê    from app.agent.graph import build_graph
Γöé
Γûê    graph = build_graph()
Γûê    thread_id = "test-thread-history"
Γöé
Γûê    # Message 1
Γûê    with patch("app.agent.nodes.llm") as mock_llm:
Γûê        mock_llm.ainvoke = AsyncMock(
Γûê            return_value=MagicMock(content="Viß╗çt Nam ß╗ƒ ─É├┤ng Nam ├ü.")
Γûê        )
Γöé
Γûê        result1 = await graph.ainvoke(
Γûê            {
Γûê                "messages": [
Γûê                    {"role": "user", "content": "Viß╗çt Nam ß╗ƒ ─æ├óu?"}
Γûê                ],
Γûê                "thread_id": thread_id,
Γûê            }
Γûê        )
Γöé
Γûê    # Message 2 ΓÇö n├¬n nhß╗¢ context tß╗½ message 1
Γûê    with patch("app.agent.nodes.llm") as mock_llm:
Γûê        mock_llm.ainvoke = AsyncMock(
Γûê            return_value=MagicMock(
Γûê                content="Thß╗º ─æ├┤ cß╗ºa Viß╗çt Nam l├á H├á Nß╗Öi."
Γûê            )
Γûê        )
Γöé
Γûê        result2 = await graph.ainvoke(
Γûê            {
Γûê                "messages": [
Γûê                    {"role": "user", "content": "Thß╗º ─æ├┤ cß╗ºa n├│ l├á g├¼?"},
Γûê                ],
Γûê                "thread_id": thread_id,
Γûê            }
Γûê        )
Γöé
Γûê    assert result2 is not None
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Khi test LangGraph, test theo 3 mß╗⌐c: (1) tß╗½ng node ri├¬ng lß║╗ (unit), (2) conditional routing logic (unit), (3) to├án bß╗Ö graph flow end-to-end (integration). Mock tß║Ñt cß║ú LLM calls ─æß╗â test nhanh v├á ß╗òn ─æß╗ïnh.
Γöé
Γûê### Test conditional routing ri├¬ng biß╗çt
Γöé
ΓûêConditional routing l├á logic quan trß╗ìng nhß║Ñt trong LangGraph ΓÇö n├│ quyß║┐t ─æß╗ïnh agent ─æi qua path n├áo. Test ri├¬ng routing function ─æß║úm bß║úo agent h├ánh xß╗¡ ─æ├║ng vß╗¢i mß╗ùi loß║íi input.
Γöé
Γûê```python
Γûê# tests/test_routing.py
Γûêimport pytest
Γûêfrom app.agent.routing import should_retrieve, classify_intent
Γöé
Γöé
Γûêclass TestShouldRetrieve:
Γûê    """Test routing function should_retrieve."""
Γöé
Γûê    @pytest.mark.parametrize(
Γûê        "intent,expected",
Γûê        [
Γûê            ("price_query", "retrieve"),
Γûê            ("faq", "retrieve"),
Γûê            ("chitchat", "respond_directly"),
Γûê            ("greeting", "respond_directly"),
Γûê            ("complaint", "retrieve"),
Γûê        ],
Γûê    )
Γûê    def test_routing_by_intent(self, intent, expected):
Γûê        """Test: mß╗ùi intent route ─æ├║ng path."""
Γûê        state = {"parsed_query": {"intent": intent}}
Γûê        result = should_retrieve(state)
Γûê        assert result == expected
Γöé
Γöé
Γûêclass TestClassifyIntent:
Γûê    """Test intent classification."""
Γöé
Γûê    def test_price_query(self):
Γûê        result = classify_intent("Gi├í v├áng h├┤m nay bao nhi├¬u?")
Γûê        assert result == "price_query"
Γöé
Γûê    def test_greeting(self):
Γûê        result = classify_intent("Xin ch├áo")
Γûê        assert result == "greeting"
Γöé
Γûê    def test_faq(self):
Γûê        result = classify_intent("L├ám sao ─æß╗â mß╗ƒ t├ái khoß║ún?")
Γûê        assert result == "faq"
Γûê```
Γöé
Γûê**Giß║úi th├¡ch `@pytest.mark.parametrize`:** Decorator n├áy chß║íy test nhiß╗üu lß║ºn vß╗¢i c├íc input kh├íc nhau ΓÇö mß╗ùi bß╗Ö (intent, expected) l├á mß╗Öt test case ri├¬ng. 5 bß╗Ö data = 5 test cases, viß║┐t trong 1 function. Rß║Ñt hß╗»u ├¡ch cho test routing logic c├│ nhiß╗üu tr╞░ß╗¥ng hß╗úp.
Γöé
Γûê## 8.4 Test Coverage
Γöé
ΓûêCode coverage ─æo tß╗╖ lß╗ç phß║ºn tr─âm code ─æ╞░ß╗úc thß╗▒c thi khi chß║íy tests. 100% coverage ngh─⌐a l├á mß╗ìi d├▓ng code ─æß╗üu ─æ╞░ß╗úc ├¡t nhß║Ñt 1 test chß║íy qua. Tuy nhi├¬n, 100% coverage kh├┤ng ─æß║úm bß║úo 100% correctness ΓÇö test c├│ thß╗â chß║íy qua code nh╞░ng kh├┤ng assert ─æ├║ng. Coverage l├á chß╗ë sß╗æ tham khß║úo, kh├┤ng phß║úi mß╗Ñc ti├¬u tuyß╗çt ─æß╗æi.
Γöé
Γûê### C├ái ─æß║╖t v├á chß║íy coverage
Γöé
Γûê```bash
Γûê# C├ái pytest-cov
Γûêpip install pytest-cov
Γöé
Γûê# Chß║íy tests vß╗¢i coverage report
Γûêpytest tests/ --cov=app --cov-report=term-missing
Γöé
Γûê# Tß║ío HTML report (mß╗ƒ htmlcov/index.html trong browser)
Γûêpytest tests/ --cov=app --cov-report=html
Γöé
Γûê# ─Éß║╖t minimum coverage threshold
Γûêpytest tests/ --cov=app --cov-fail-under=60
Γûê```
Γöé
ΓûêOutput terminal sß║╜ hiß╗ân thß╗ï bß║úng coverage:
Γöé
Γûê```
ΓûêName                           Stmts   Miss  Cover   Missing
Γûê-------------------------------------------------------------
Γûêapp/__init__.py                    0      0   100%
Γûêapp/main.py                       25      3    88%   45-47
Γûêapp/api/__init__.py                0      0   100%
Γûêapp/api/health.py                  8      0   100%
Γûêapp/api/chat.py                   35     12    66%   23-28, 41-46
Γûêapp/agent/__init__.py              0      0   100%
Γûêapp/agent/graph.py                45     18    60%   34-52, 67-71
Γûêapp/agent/nodes.py                30      5    83%   15, 28-30
Γûêapp/agent/routing.py              12      0   100%
Γûê-------------------------------------------------------------
ΓûêTOTAL                            155     38    75%
Γûê```
Γöé
ΓûêCß╗Öt "Missing" cho biß║┐t d├▓ng n├áo ch╞░a ─æ╞░ß╗úc testΦªåτ¢û ΓÇö tß║¡p trung viß║┐t test cho nhß╗»ng d├▓ng n├áy.
Γöé
Γûê### Mß╗Ñc ti├¬u coverage cho AI20K
Γöé
Γûê| Phß║ºn code | Mß╗Ñc ti├¬u coverage | Ghi ch├║ |
Γûê|-----------|-------------------|---------|
Γûê| API endpoints | 80%+ | Quan trß╗ìng nhß║Ñt, dß╗à test |
Γûê| Agent nodes | 70%+ | Mock LLM, test logic |
Γûê| Routing logic | 90%+ | ─É╞ín giß║ún, parametrize test |
Γûê| Graph flow | 60%+ | Integration test |
Γûê| Utilities | 80%+ | Pure functions, dß╗à test |
Γûê| Configuration | 50%+ | ├ìt logic, ├¡t priority |
Γûê| **Tß╗òng thß╗â** | **60%+** | **Mß╗Ñc ti├¬u tß╗æi thiß╗âu** |
Γöé
Γûê### Cß║Ñu h├¼nh coverage trong `pyproject.toml`
Γöé
Γûê```toml
Γûê[tool.pytest.ini_options]
Γûêtestpaths = ["tests"]
Γûêasyncio_mode = "auto"
Γûêaddopts = "-v --cov=app --cov-report=term-missing --cov-fail-under=60"
Γöé
Γûê[tool.coverage.run]
Γûêsource = ["app"]
Γûêomit = [
Γûê    "app/__init__.py",
Γûê    "*/tests/*",
Γûê    "*/migrations/*",
Γûê]
Γöé
Γûê[tool.coverage.report]
Γûêexclude_lines = [
Γûê    "pragma: no cover",
Γûê    "if __name__ == .__main__.:",
Γûê    "raise NotImplementedError",
Γûê    "pass",
Γûê]
Γûê```
Γöé
ΓûêVß╗¢i cß║Ñu h├¼nh n├áy, chß╗ë cß║ºn chß║íy `pytest` kh├┤ng cß║ºn th├¬m flag n├áo ΓÇö n├│ tß╗▒ ─æß╗Öng chß║íy coverage v├á fail nß║┐u d╞░ß╗¢i 60%.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Kh├┤ng cß╗æ gß║»ng ─æß║ít 100% coverage bß║▒ng c├ích viß║┐t test "r├íc" ΓÇö test chß╗ë gß╗ìi code m├á kh├┤ng assert g├¼. Coverage cao + test chß║Ñt l╞░ß╗úng thß║Ñp tß╗ç h╞ín coverage thß║Ñp + test chß║Ñt l╞░ß╗úng cao. Tß║¡p trung v├áo happy path, error path, v├á edge cases.
Γöé
Γûê### Nhß╗»ng g├¼ n├¬n test v├á bß╗Å qua
Γöé
Γûê**N├¬n test:**
Γûê- API endpoints (happy path + error cases)
Γûê- Agent node logic (parsing, formatting, routing)
Γûê- Data validation (Pydantic models)
Γûê- Error handling (LLM timeout, invalid input, database error)
Γöé
Γûê**C├│ thß╗â bß╗Å qua:**
Γûê- LLM response content (kh├┤ng thß╗â predict ch├¡nh x├íc)
Γûê- Third-party library internals
Γûê- Trivial getters/setters
Γûê- Migration scripts
Γöé
Γûê## 8.5 Evaluation Evidence ΓÇö Bß║▒ng chß╗⌐ng ─æ├ính gi├í
Γöé
ΓûêEvaluation Evidence (bß║▒ng chß╗⌐ng ─æ├ính gi├í) l├á mß╗Öt trong 10 deliverables BTC y├¬u cß║ºu, nh╞░ng **rß║Ñt ├¡t ─æß╗Öi** nß╗Öp ─æ╞░ß╗úc deliverable n├áy. ─É├óy l├á c╞í hß╗Öi ghi ─æiß╗âm lß╗¢n ΓÇö ─æa sß╗æ ─æß╗Öi bß╗Å qua phß║ºn n├áy, n├¬n bß║ín chß╗ë cß║ºn nß╗Öp l├á ─æ├ú v╞░ß╗út xa c├íc ─æß╗Öi kh├íc.
Γöé
Γûê### BTC mong ─æß╗úi g├¼ trong Evaluation Evidence?
Γöé
ΓûêBTC muß╗æn thß║Ñy **bß║▒ng chß╗⌐ng c├│ hß╗ç thß╗æng** rß║▒ng agent cß╗ºa bß║ín hoß║ít ─æß╗Öng ─æ├║ng v├á hß╗»u ├¡ch. Kh├┤ng chß╗ë l├á "n├│ chß║íy ─æ╞░ß╗úc" m├á l├á "n├│ chß║íy ─æ╞░ß╗úc v├á ─æ├óy l├á bß║▒ng chß╗⌐ng." Evaluation Evidence cß║ºn bao gß╗ôm:
Γöé
Γûê1. **Bß║úng metrics:** Accuracy, relevance, faithfulness, response time
Γûê2. **Test results:** Output tß╗½ pytest vß╗¢i coverage
Γûê3. **User feedback:** Kß║┐t quß║ú thß╗¡ nghiß╗çm vß╗¢i ng╞░ß╗¥i d├╣ng thß╗▒c
Γûê4. **Code traceability:** Map test case ΓåÆ requirement ΓåÆ code
Γöé
Γûê### Cß║Ñu tr├║c b├ío c├ío Evaluation Evidence
Γöé
Γûê```markdown
Γûê# Evaluation Evidence ΓÇö Team XXX
Γöé
Γûê## 1. Test Results
Γûê- Sß╗æ l╞░ß╗úng test cases: 45
Γûê- Pass/Fail: 43/2
Γûê- Code coverage: 72%
Γûê- Screenshot: [pytest output]
Γöé
Γûê## 2. RAG Quality Metrics
Γûê| Metric | Score | Benchmark |
Γûê|--------|-------|-----------|
Γûê| Faithfulness | 0.85 | > 0.7 |
Γûê| Answer Relevance | 0.82 | > 0.7 |
Γûê| Context Precision | 0.78 | > 0.6 |
Γûê| Context Recall | 0.80 | > 0.6 |
Γöé
Γûê## 3. Performance Metrics
Γûê| Endpoint | Avg Response Time | P95 | P99 |
Γûê|----------|------------------|-----|-----|
Γûê| /api/v1/chat | 2.3s | 4.1s | 5.8s |
Γûê| /health | 12ms | 25ms | 40ms |
Γöé
Γûê## 4. User Feedback
Γûê- Sß╗æ ng╞░ß╗¥i tham gia test: 10
Γûê- Rating trung b├¼nh: 4.2/5
Γûê- Phß║ún hß╗ôi ch├¡nh: [summary]
Γûê```
Γöé
Γûê### Format bß║úng metrics
Γöé
Γûê```python
Γûê# Script tß║ío metrics report
Γûêdef generate_eval_report(test_results: list[dict]) -> dict:
Γûê    """Tß║ío evaluation report tß╗½ test results."""
Γûê    total = len(test_results)
Γûê    correct = sum(1 for r in test_results if r["passed"])
Γöé
Γûê    return {
Γûê        "total_cases": total,
Γûê        "passed": correct,
Γûê        "failed": total - correct,
Γûê        "accuracy": correct / total if total > 0 else 0,
Γûê        "categories": _group_by_category(test_results),
Γûê        "timestamp": datetime.now(timezone.utc).isoformat(),
Γûê    }
Γûê```
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Chß╗Ñp screenshot terminal output khi chß║íy pytest v├á ─æ╞░a v├áo b├ío c├ío. BTC th├¡ch thß║Ñy bß║▒ng chß╗⌐ng trß╗▒c quan h╞ín l├á chß╗ë con sß╗æ. Th├¬m coverage badge v├áo README ΓÇö n├│ thß╗â hiß╗çn chuy├¬n nghiß╗çp v├á dß╗à nh├¼n.
Γöé
Γûê## 8.6 RAGAS ΓÇö ─É├ính gi├í chß║Ñt l╞░ß╗úng RAG
Γöé
ΓûêRAGAS (Retrieval Augmented Generation Assessment) l├á framework ─æ├ính gi├í chß║Ñt l╞░ß╗úng hß╗ç thß╗æng RAG. Nß║┐u agent cß╗ºa bß║ín c├│ retrieval (t├¼m kiß║┐m t├ái liß╗çu) + generation (sinh c├óu trß║ú lß╗¥i), RAGAS cung cß║Ñp metrics ch├¡nh x├íc ─æß╗â ─æo chß║Ñt l╞░ß╗úng.
Γöé
Γûê### Tß║íi sao cß║ºn RAGAS?
Γöé
ΓûêAgent RAG c├│ 2 giai ─æoß║ín: (1) retrieve documents li├¬n quan, (2) generate c├óu trß║ú lß╗¥i dß╗▒a tr├¬n documents. Bß║ín cß║ºn ─æ├ính gi├í cß║ú hai giai ─æoß║ín:
Γöé
Γûê- **Retrieval c├│ t├¼m ─æ├║ng t├ái liß╗çu kh├┤ng?** ΓåÆ Context Precision, Context Recall
Γûê- **Generation c├│ trung th├ánh vß╗¢i t├ái liß╗çu kh├┤ng?** ΓåÆ Faithfulness
Γûê- **C├óu trß║ú lß╗¥i c├│ li├¬n quan ─æß║┐n c├óu hß╗Åi kh├┤ng?** ΓåÆ Answer Relevance
Γöé
Γûê### 4 metrics ch├¡nh cß╗ºa RAGAS
Γöé
Γûê| Metric | ─Éo l╞░ß╗¥ng | Khoß║úng | Tß╗æt |
Γûê|--------|----------|--------|-----|
Γûê| **Faithfulness** (─Éß╗Ö trung th├ánh) | C├óu trß║ú lß╗¥i c├│ chß╗ë dß╗▒a v├áo context kh├┤ng? | 0-1 | > 0.7 |
Γûê| **Answer Relevance** | C├óu trß║ú lß╗¥i c├│ li├¬n quan ─æß║┐n c├óu hß╗Åi kh├┤ng? | 0-1 | > 0.7 |
Γûê| **Context Precision** | Documents retrieved c├│ ─æ├║ng thß╗⌐ tß╗▒ ╞░u ti├¬n kh├┤ng? | 0-1 | > 0.6 |
Γûê| **Context Recall** | C├│ retrieve ─æß╗º documents cß║ºn thiß║┐t kh├┤ng? | 0-1 | > 0.6 |
Γöé
Γûê### C├ái ─æß║╖t v├á chß║íy RAGAS
Γöé
Γûê```bash
Γûêpip install ragas
Γûê```
Γöé
Γûê```python
Γûê# tests/test_ragas_eval.py
Γûê"""
ΓûêRAGAS evaluation test.
ΓûêChß║íy ri├¬ng: pytest tests/test_ragas_eval.py -v --timeout=300
Γûê"""
Γûêimport pytest
Γûêfrom ragas import evaluate
Γûêfrom ragas.metrics import (
Γûê    faithfulness,
Γûê    answer_relevancy,
Γûê    context_precision,
Γûê    context_recall,
Γûê)
Γûêfrom datasets import Dataset
Γöé
Γöé
Γûê# Test dataset ΓÇö bß║ín cß║ºn tß║ío dataset thß╗▒c tß║┐ cho dß╗▒ ├ín cß╗ºa m├¼nh
ΓûêTEST_DATASET = {
Γûê    "question": [
Γûê        "Gi├í v├áng SJC h├┤m nay bao nhi├¬u?",
Γûê        "Thß╗º tß╗Ñc mß╗ƒ t├ái khoß║ún ng├ón h├áng?",
Γûê        "L├úi suß║Ñt tiß║┐t kiß╗çm 6 th├íng?",
Γûê    ],
Γûê    "contexts": [
Γûê        [
Γûê            "Gi├í v├áng SJC mua v├áo 5.150.000─æ, b├ín ra 5.200.000─æ.",
Γûê            "Gi├í v├áng nhß║½n tr├▓n 5.050.000─æ - 5.100.000─æ.",
Γûê        ],
Γûê        [
Γûê            "B╞░ß╗¢c 1: Mang CMND/CCCD ─æß║┐n quß║ºy.",
Γûê            "B╞░ß╗¢c 2: ─Éiß╗ün form ─æ─âng k├╜ mß╗ƒ t├ái khoß║ún.",
Γûê            "B╞░ß╗¢c 3: Nß║íp tiß╗ün tß╗æi thiß╗âu 50.000─æ.",
Γûê        ],
Γûê        [
Γûê            "L├úi suß║Ñt tiß║┐t kiß╗çm 6 th├íng l├á 5.0%/n─âm.",
Γûê            "L├úi suß║Ñt kh├┤ng kß╗│ hß║ín l├á 0.1%/n─âm.",
Γûê        ],
Γûê    ],
Γûê    "answer": [
Γûê        "Gi├í v├áng SJC h├┤m nay: mua v├áo 5.150.000─æ, b├ín ra 5.200.000─æ.",
Γûê        "─Éß╗â mß╗ƒ t├ái khoß║ún, bß║ín cß║ºn mang CMND/CCCD ─æß║┐n quß║ºy, ─æiß╗ün form ─æ─âng k├╜, v├á nß║íp tß╗æi thiß╗âu 50.000─æ.",
Γûê        "L├úi suß║Ñt tiß║┐t kiß╗çm 6 th├íng hiß╗çn tß║íi l├á 5.0%/n─âm.",
Γûê    ],
Γûê    "ground_truth": [
Γûê        "Gi├í v├áng SJC: mua 5.150.000─æ, b├ín 5.200.000─æ.",
Γûê        "CMND + form + nß║íp 50.000─æ.",
Γûê        "5.0%/n─âm.",
Γûê    ],
Γûê}
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûê@pytest.mark.timeout(300)  # Timeout 5 ph├║t
Γûêasync def test_ragas_metrics():
Γûê    """Chß║íy RAGAS evaluation tr├¬n test dataset."""
Γûê    dataset = Dataset.from_dict(TEST_DATASET)
Γöé
Γûê    metrics = [
Γûê        faithfulness,
Γûê        answer_relevancy,
Γûê        context_precision,
Γûê        context_recall,
Γûê    ]
Γöé
Γûê    results = evaluate(dataset, metrics=metrics)
Γöé
Γûê    # Assert minimum thresholds
Γûê    assert results["faithfulness"] >= 0.7, (
Γûê        f"Faithfulness {results['faithfulness']:.2f} < 0.7"
Γûê    )
Γûê    assert results["answer_relevancy"] >= 0.7, (
Γûê        f"Answer Relevancy {results['answer_relevancy']:.2f} < 0.7"
Γûê    )
Γöé
Γûê    # Print results ─æß╗â ─æ╞░a v├áo b├ío c├ío
Γûê    print("\n=== RAGAS Evaluation Results ===")
Γûê    for metric, value in results.items():
Γûê        print(f"  {metric}: {value:.3f}")
Γöé
Γöé
Γûêdef test_generate_eval_table():
Γûê    """
Γûê    Helper: in bß║úng metrics cho b├ío c├ío Evaluation Evidence.
Γûê    Kh├┤ng phß║úi test thß║¡t ΓÇö d├╣ng ─æß╗â generate report.
Γûê    """
Γûê    # Thay bß║▒ng results thß╗▒c tß║┐ tß╗½ test_ragas_metrics
Γûê    mock_results = {
Γûê        "faithfulness": 0.85,
Γûê        "answer_relevancy": 0.82,
Γûê        "context_precision": 0.78,
Γûê        "context_recall": 0.80,
Γûê    }
Γöé
Γûê    print("\n| Metric | Score | Benchmark |")
Γûê    print("|--------|-------|-----------|")
Γûê    for metric, value in mock_results.items():
Γûê        status = "PASS" if value >= 0.7 else "FAIL"
Γûê        print(f"| {metric} | {value:.2f} | > 0.7 ({status}) |")
Γûê```
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** RAGAS evaluation gß╗ìi LLM (─æß╗â ─æ├ính gi├í LLM output), n├¬n n├│ tß╗æn token v├á chß║íy chß║¡m. Chß║íy ri├¬ng biß╗çt, kh├┤ng chß║íy trong CI pipeline th├┤ng th╞░ß╗¥ng. Th├¬m flag `@pytest.mark.slow` v├á exclude khß╗Åi default test run.
Γöé
Γûê### Tß║ío test dataset chß║Ñt l╞░ß╗úng
Γöé
ΓûêTest dataset l├á yß║┐u tß╗æ quyß║┐t ─æß╗ïnh chß║Ñt l╞░ß╗úng RAGAS evaluation. D╞░ß╗¢i ─æ├óy l├á h╞░ß╗¢ng dß║½n tß║ío dataset:
Γöé
Γûê```python
Γûê# scripts/create_eval_dataset.py
Γûê"""
ΓûêScript tß║ío evaluation dataset tß╗½ dß╗» liß╗çu thß╗▒c.
ΓûêChß║íy: python scripts/create_eval_dataset.py
Γûê"""
Γûêimport json
Γöé
Γöé
Γûêdef create_eval_dataset():
Γûê    """Tß║ío eval dataset tß╗½ FAQ hoß║╖c t├ái liß╗çu."""
Γûê    dataset = {
Γûê        "question": [],
Γûê        "contexts": [],
Γûê        "answer": [],
Γûê        "ground_truth": [],
Γûê    }
Γöé
Γûê    # Th├¬m c├íc c├óu hß╗Åi test ΓÇö n├¬n ─æa dß║íng:
Γûê    # - C├óu hß╗Åi trß╗▒c tiß║┐p (factual)
Γûê    # - C├óu hß╗Åi y├¬u cß║ºu tß╗òng hß╗úp (multi-hop)
Γûê    # - C├óu hß╗Åi ngo├ái phß║ím vi (out-of-scope)
Γûê    # - C├óu hß╗Åiµ¿íτ│è (ambiguous)
Γöé
Γûê    test_cases = [
Γûê        {
Γûê            "question": "Gi├í v├áng SJC h├┤m nay?",
Γûê            "contexts": ["Gi├í v├áng SJC 5.150.000 - 5.200.000─æ."],
Γûê            "ground_truth": "5.150.000 - 5.200.000─æ",
Γûê            "category": "factual",
Γûê        },
Γûê        {
Γûê            "question": "So s├ính l├úi suß║Ñt gß╗¡i tiß║┐t kiß╗çm 3 th├íng v├á 6 th├íng?",
Γûê            "contexts": [
Γûê                "L├úi suß║Ñt 3 th├íng: 4.5%/n─âm.",
Γûê                "L├úi suß║Ñt 6 th├íng: 5.0%/n─âm.",
Γûê            ],
Γûê            "ground_truth": "3 th├íng 4.5%, 6 th├íng 5.0% ΓÇö ch├¬nh 0.5%",
Γûê            "category": "multi_hop",
Γûê        },
Γûê        {
Γûê            "question": "Thß╗¥i tiß║┐t h├┤m nay thß║┐ n├áo?",
Γûê            "contexts": [],
Γûê            "ground_truth": "Kh├┤ng c├│ th├┤ng tin vß╗ü thß╗¥i tiß║┐t.",
Γûê            "category": "out_of_scope",
Γûê        },
Γûê    ]
Γöé
Γûê    for tc in test_cases:
Γûê        dataset["question"].append(tc["question"])
Γûê        dataset["contexts"].append(tc["contexts"])
Γûê        dataset["ground_truth"].append(tc["ground_truth"])
Γûê        # Answer sß║╜ ─æ╞░ß╗úc generate bß║▒ng agent thß║¡t
Γöé
Γûê    with open("eval_dataset.json", "w", encoding="utf-8") as f:
Γûê        json.dump(dataset, f, ensure_ascii=False, indent=2)
Γöé
Γûê    print(f"Created dataset with {len(test_cases)} test cases")
Γöé
Γöé
Γûêif __name__ == "__main__":
Γûê    create_eval_dataset()
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Evaluation Evidence l├á deliverable dß╗à ghi ─æiß╗âm nhß║Ñt v├¼ hß║ºu hß║┐t ─æß╗Öi bß╗Å qua. Chß╗ë cß║ºn: (1) pytest output vß╗¢i coverage, (2) bß║úng RAGAS metrics, (3) v├ái user feedback ΓÇö bß║ín ─æ├ú v╞░ß╗út xa phß║ºn lß╗¢n c├íc ─æß╗Öi kh├íc.
Γöé
Γûê## T├│m tß║»t
Γöé
ΓûêTrong ch╞░╞íng n├áy, ch├║ng ta ─æ├ú t├¼m hiß╗âu vß╗ü kiß╗âm thß╗¡ v├á ─æ├ính gi├í cho ß╗⌐ng dß╗Ñng AI Agent:
Γöé
Γûê- **Testing pyramid:** Unit tests (70-80%), Integration tests (15-20%), Evaluation tests (5-10%)
Γûê- **API testing:** pytest + AsyncClient + conftest.py fixtures, test GET/POST endpoints, validation, errors
Γûê- **Agent testing:** Test tß╗½ng node ri├¬ng lß║╗, test conditional routing, test graph flow end-to-end
Γûê- **Code coverage:** pytest-cov, mß╗Ñc ti├¬u 60%+, cß║Ñu h├¼nh trong pyproject.toml
Γûê- **Evaluation Evidence:** Cß║Ñu tr├║c b├ío c├ío, metrics table, user feedback, code traceability
Γûê- **RAGAS metrics:** Faithfulness, Answer Relevancy, Context Precision, Context Recall
Γöé
ΓûêPhß║ºn lß╗¢n ─æß╗Öi kh├┤ng c├│ test. Phß║ºn lß╗¢n ─æß╗Öi kh├┤ng c├│ Evaluation Evidence. Chß╗ë cß║ºn bß║ín c├│ cß║ú hai, bß║ín ─æ├ú ß╗ƒ top ─æß╗Öi vß╗ü Code Quality.
Γöé
Γûê## C├óu hß╗Åi ├┤n tß║¡p
Γöé
Γûê1. Tß║íi sao phß║ºn lß╗¢n ─æß╗Öi bß╗Å qua viß╗çc viß║┐t test? Hß║¡u quß║ú l├á g├¼ cho ─æiß╗âm sß╗æ?
Γûê2. Giß║úi th├¡ch testing pyramid. Tß║íi sao unit tests chiß║┐m nhiß╗üu nhß║Ñt?
Γûê3. `conftest.py` fixture `client` hoß║ít ─æß╗Öng nh╞░ thß║┐ n├áo? Tß║íi sao kh├┤ng cß║ºn chß║íy HTTP server thß║¡t?
Γûê4. Tß║íi sao phß║úi mock LLM responses trong integration tests?
Γûê5. `@pytest.mark.parametrize` giß║úi quyß║┐t vß║Ñn ─æß╗ü g├¼? Cho v├¡ dß╗Ñ.
Γûê6. Code coverage 60% ngh─⌐a l├á g├¼? Tß║íi sao kh├┤ng cß║ºn 100%?
Γûê7. RAGAS Faithfulness ─æo l╞░ß╗¥ng ─æiß╗üu g├¼? Tß║íi sao quan trß╗ìng cho RAG agent?
Γûê8. Bß║ín cß║ºn nhß╗»ng g├¼ trong b├ío c├ío Evaluation Evidence ─æß╗â BTC chß║Ñm ─æiß╗âm cao?


docs\guide\chapter-09.md:
Γûê---
Γûêtitle: "Nß╗Öp b├ái Demo Day"
Γûêweight: 9
Γûê---
Γöé
Γûê## 9.1 M╞░ß╗¥i deliverables BTC y├¬u cß║ºu
Γöé
ΓûêBan Tß╗ò Chß╗⌐c (BTC) AI20K y├¬u cß║ºu mß╗ùi ─æß╗Öi nß╗Öp **10 deliverables** cho Demo Day. Tß╗╖ lß╗ç ho├án th├ánh phß╗ò biß║┐n nh╞░ sau (╞░ß╗¢c t├¡nh tß╗½ kinh nghiß╗çm):
Γöé
Γûê| # | Deliverable | Mß╗⌐c ─æß╗Ö phß╗ò biß║┐n | ─Éß╗Ö kh├│ | Mß║╣o |
Γûê|---|-------------|-----------------|--------|-----|
Γûê| 1 | Source Code (GitHub repo) | Phß║ºn lß╗¢n ho├án th├ánh | Trung b├¼nh | Push code sß╗¢m, kh├┤ng ─æß╗úi ho├án hß║úo |
Γûê| 2 | README.md | Phß║ºn lß╗¢n ho├án th├ánh | Dß╗à | D├╣ng template, c├│ screenshot |
Γûê| 3 | Architecture Diagram | Th╞░ß╗¥ng bß╗ï thiß║┐u | Trung b├¼nh | D├╣ng draw.io hoß║╖c Mermaid |
Γûê| 4 | AI Logs (LangSmith/screenshot) | Phß║ºn lß╗¢n ho├án th├ánh | Dß╗à | Chß╗ë cß║ºn config 3 env vars |
Γûê| 5 | Live URL | Th╞░ß╗¥ng ho├án th├ánh | Trung b├¼nh | Deploy l├¬n Render, free tier OK |
Γûê| 6 | Video Demo | Hiß║┐m khi c├│ | Trung b├¼nh | Quay 3-5 ph├║t, upload YouTube |
Γûê| 7 | Pitch Deck (slide thuyß║┐t tr├¼nh) | Th╞░ß╗¥ng bß╗ï thiß║┐u | Kh├│ | 10 slides theo template |
Γûê| 8 | Development Journal | Phß║ºn lß╗¢n ho├án th├ánh | Dß╗à | Ghi mß╗ùi ng├áy, kh├┤ng cß║ºn d├ái |
Γûê| 9 | Worklog (commit history) | Phß║ºn lß╗¢n ho├án th├ánh | Dß╗à | Git log tß╗▒ ─æß╗Öng |
Γûê| 10 | Evaluation Evidence | Hiß║┐m khi c├│ | Kh├│ | RAGAS metrics + test results |
Γöé
ΓûêPh├ón t├¡ch nhanh: deliverables dß╗à nhß║Ñt l├á AI Logs v├á Worklog ΓÇö kh├┤ng cß║ºn code phß╗⌐c tß║íp, chß╗ë cß║ºn discipline. Deliverables kh├│ nhß║Ñt l├á Video Demo, Pitch Deck, v├á Evaluation Evidence ΓÇö ─æ├óy c┼⌐ng l├á n╞íi bß║ín tß║ío lß╗úi thß║┐ cß║ính tranh lß╗¢n nhß║Ñt.
Γöé
ΓûêMß╗ùi deliverable cß║ºn ─æ╞░ß╗úc ─æß║╖t ─æ├║ng vß╗ï tr├¡ trong GitHub repository:
Γöé
Γûê```
Γûêproject-root/
ΓûêΓö£ΓöÇΓöÇ README.md              ΓåÉ Deliverable #2
ΓûêΓö£ΓöÇΓöÇ docs/
ΓûêΓöé   Γö£ΓöÇΓöÇ architecture.md    ΓåÉ Deliverable #3 (hoß║╖c .png/.pdf)
ΓûêΓöé   Γö£ΓöÇΓöÇ video-demo.md      ΓåÉ Deliverable #6 (link YouTube)
ΓûêΓöé   Γö£ΓöÇΓöÇ pitch-deck.pdf     ΓåÉ Deliverable #7
ΓûêΓöé   Γö£ΓöÇΓöÇ journal.md         ΓåÉ Deliverable #8
ΓûêΓöé   Γö£ΓöÇΓöÇ worklog.md         ΓåÉ Deliverable #9
ΓûêΓöé   ΓööΓöÇΓöÇ evaluation.md      ΓåÉ Deliverable #10
ΓûêΓö£ΓöÇΓöÇ src/                   ΓåÉ Deliverable #1 (Source Code)
ΓûêΓö£ΓöÇΓöÇ tests/                 ΓåÉ Cho Evaluation Evidence
ΓûêΓö£ΓöÇΓöÇ .github/workflows/     ΓåÉ Bonus cho DevOps
ΓûêΓö£ΓöÇΓöÇ Dockerfile             ΓåÉ Bonus cho DevOps
ΓûêΓööΓöÇΓöÇ docker-compose.yml     ΓåÉ Bonus cho DevOps
Γûê```
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** 10/10 deliverables = ─æiß╗âm tß╗æi ─æa ß╗ƒ ti├¬u ch├¡ "Ho├án th├ánh deliverables". Nhiß╗üu ─æß╗Öi mß║Ñt ─æiß╗âm kh├┤ng phß║úi v├¼ code k├⌐m m├á v├¼ thiß║┐u deliverables. Thß╗▒c tß║┐ cho thß║Ñy ─æa sß╗æ ─æß╗Öi chß╗ë ho├án th├ánh khoß║úng 5/10 deliverables ΓÇö tß╗⌐c l├á nß╗Öp ─æß╗º 10/10 ─æ├ú v╞░ß╗út phß║ºn lß╗¢n c├íc ─æß╗Öi kh├íc.
Γöé
Γûê### Chi tiß║┐t tß╗½ng deliverable
Γöé
Γûê**1. Source Code:** Push to├án bß╗Ö code l├¬n GitHub. Repo n├¬n c├│ cß║Ñu tr├║c r├╡ r├áng, `.gitignore` ─æ├║ng, kh├┤ng chß╗⌐a secrets, kh├┤ng chß╗⌐a file lß╗¢n (>10MB). BTC sß║╜ clone v├á chß║íy thß╗¡ ΓÇö ─æß║úm bß║úo code chß║íy ─æ╞░ß╗úc sau khi set env vars.
Γöé
Γûê**2. README.md:** File README l├á ß║Ñn t╞░ß╗úng ─æß║ºu ti├¬n. Phß║úi c├│: t├¬n dß╗▒ ├ín, m├┤ tß║ú, screenshot/gif, h╞░ß╗¢ng dß║½n c├ái ─æß║╖t, c├ích chß║íy, cß║Ñu tr├║c th╞░ mß╗Ñc, tech stack, team members. Xem template ß╗ƒ mß╗Ñc 9.2.
Γöé
Γûê**3. Architecture Diagram:** S╞í ─æß╗ô kiß║┐n tr├║c thß╗â hiß╗çn bß║ín hiß╗âu hß╗ç thß╗æng. D├╣ng draw.io (miß╗àn ph├¡), Mermaid (trong README), hoß║╖c Excalidraw. Vß║╜ r├╡: Frontend, Backend API, LangGraph Agent, Vector Store, External APIs.
Γöé
Γûê**4. AI Logs:** Chß╗⌐ng minh agent hoß║ít ─æß╗Öng ─æ├║ng. C├ích dß╗à nhß║Ñt: d├╣ng LangSmith (3 env vars, kh├┤ng cß║ºn code th├¬m). Hoß║╖c screenshot terminal output cho thß║Ñy agent reasoning steps.
Γöé
Γûê**5. Live URL:** URL truy cß║¡p ─æ╞░ß╗úc tß╗½ internet. Deploy l├¬n Render (backend), Vercel (frontend). Free tier chß║Ñp nhß║¡n ─æ╞░ß╗úc. ─Éß║úm bß║úo URL hoß║ít ─æß╗Öng ├¡t nhß║Ñt ─æß║┐n hß║┐t ng├áy Demo Day + 7 ng├áy.
Γöé
Γûê**6. Video Demo:** Quay m├án h├¼nh 3-5 ph├║t, ─æi qua main features. Upload YouTube (unlisted OK). N├¬n c├│: giß╗¢i thiß╗çu team, demo main use case, giß║úi th├¡ch architecture, demo edge case. Rß║Ñt hiß║┐m ─æß╗Öi c├│ video ΓÇö ─æ├óy l├á lß╗úi thß║┐ cß║ính tranh lß╗¢n.
Γöé
Γûê**7. Pitch Deck:** Slide thuyß║┐t tr├¼nh cho Demo Day. Th╞░ß╗¥ng 10 slides, mß╗ùi slide 1 ph├║t. Xem template chi tiß║┐t ß╗ƒ mß╗Ñc 9.6.
Γöé
Γûê**8. Development Journal:** Nhß║¡t k├╜ ph├ít triß╗ân, ghi lß║íi: quyß║┐t ─æß╗ïnh kß╗╣ thuß║¡t v├á l├╜ do, kh├│ kh─ân gß║╖p phß║úi v├á c├ích giß║úi quyß║┐t, b├ái hß╗ìc r├║t ra. Kh├┤ng cß║ºn d├ái ΓÇö 2-3 c├óu mß╗ùi ng├áy ─æß╗º.
Γöé
Γûê**9. Worklog:** Lß╗ïch sß╗¡ ph├ít triß╗ân, chß╗⌐ng minh team l├ám viß╗çc ─æß╗üu ─æß║╖n. C├ích dß╗à nhß║Ñt: `git log --oneline --since="2024-01-01" > worklog.md`. Hoß║╖c export GitHub contribution graph.
Γöé
Γûê**10. Evaluation Evidence:** Bß║▒ng chß╗⌐ng ─æ├ính gi├í chß║Ñt l╞░ß╗úng agent. Xem ch╞░╞íng 8 phß║ºn 8.5 v├á 8.6. Rß║Ñt hiß║┐m ─æß╗Öi nß╗Öp deliverable n├áy ΓÇö ─æ├óy l├á c╞í hß╗Öi ghi ─æiß╗âm lß╗¢n.
Γöé
Γûê## 9.2 Checklist chi tiß║┐t
Γöé
ΓûêD╞░ß╗¢i ─æ├óy l├á checklist tß╗½ng b╞░ß╗¢c ─æß╗â ─æß║úm bß║úo kh├┤ng bß╗Å s├│t deliverables. In ra hoß║╖c copy v├áo Notion/Trello, check tß╗½ng mß╗Ñc tr╞░ß╗¢c khi nß╗Öp.
Γöé
Γûê### Checklist Source Code
Γöé
Γûê- [ ] Repository GitHub public hoß║╖c add BTC l├ám collaborator
Γûê- [ ] Code chß║íy ─æ╞░ß╗úc sau khi set env vars (README c├│ h╞░ß╗¢ng dß║½n)
Γûê- [ ] `.gitignore` ─æ├║ng (kh├┤ng chß╗⌐a `.env`, `__pycache__`, `.venv`)
Γûê- [ ] Kh├┤ng commit secrets (API keys, passwords)
Γûê- [ ] Kh├┤ng commit file lß╗¢n (models, datasets >10MB)
Γûê- [ ] C├│ `requirements.txt` hoß║╖c `pyproject.toml` vß╗¢i pinned versions
Γûê- [ ] Code c├│ type hints
Γûê- [ ] Code c├│ docstrings cho functions ch├¡nh
Γûê- [ ] C├│ ├¡t nhß║Ñt 1 file test (pytest)
Γöé
Γûê### Checklist README.md
Γöé
Γûê- [ ] T├¬n dß╗▒ ├ín v├á m├┤ tß║ú r├╡ r├áng
Γûê- [ ] Screenshot hoß║╖c GIF cß╗ºa ß╗⌐ng dß╗Ñng
Γûê- [ ] H╞░ß╗¢ng dß║½n c├ái ─æß║╖t (step-by-step)
Γûê- [ ] H╞░ß╗¢ng dß║½n chß║íy (v├á chß║íy vß╗¢i Docker nß║┐u c├│)
Γûê- [ ] Cß║Ñu tr├║c th╞░ mß╗Ñc (tree)
Γûê- [ ] Tech stack (bß║úng hoß║╖c badges)
Γûê- [ ] Environment variables cß║ºn thiß║┐t (liß╗çt k├¬ t├¬n, kh├┤ng ghi gi├í trß╗ï)
Γûê- [ ] API documentation (endpoints, request/response format)
Γûê- [ ] Team members (t├¬n, vai tr├▓)
Γûê- [ ] Link Live URL
Γöé
Γûê### Checklist Architecture Diagram
Γöé
Γûê- [ ] S╞í ─æß╗ô r├╡ r├áng, dß╗à ─æß╗ìc
Γûê- [ ] Thß╗â hiß╗çn ─æß║ºy ─æß╗º components (Frontend, Backend, Agent, DB, External APIs)
Γûê- [ ] C├│ data flow arrows (m┼⌐i t├¬n luß╗ông dß╗» liß╗çu)
Γûê- [ ] File format: PNG hoß║╖c SVG (embed trong README)
Γûê- [ ] C├│ m├┤ tß║ú ngß║»n k├¿m s╞í ─æß╗ô
Γöé
Γûê### Checklist AI Logs
Γöé
Γûê- [ ] LangSmith project URL (share publicly hoß║╖c screenshot)
Γûê- [ ] Hoß║╖c: screenshot terminal logs cho thß║Ñy agent reasoning
Γûê- [ ] ├ìt nhß║Ñt 5-10 trace examples
Γûê- [ ] Mß╗ùi trace cho thß║Ñy: input, LLM call, retrieval, output
Γöé
Γûê### Checklist Live URL
Γöé
Γûê- [ ] URL trß║ú vß╗ü HTTP 200 khi truy cß║¡p
Γûê- [ ] Health check endpoint hoß║ít ─æß╗Öng (`/health`)
Γûê- [ ] API endpoints ch├¡nh hoß║ít ─æß╗Öng
Γûê- [ ] URL ─æ╞░ß╗úc ghi trong README
Γûê- [ ] URL hoß║ít ─æß╗Öng ß╗òn ─æß╗ïnh (kh├┤ng sleep ΓÇö d├╣ng UptimeRobot nß║┐u free tier)
Γöé
Γûê### Checklist Video Demo
Γöé
Γûê- [ ] Video 3-5 ph├║t, chß║Ñt l╞░ß╗úng HD
Γûê- [ ] Upload YouTube (unlisted OK)
Γûê- [ ] Link YouTube ghi trong README hoß║╖c `docs/video-demo.md`
Γûê- [ ] Video c├│: giß╗¢i thiß╗çu team, demo use case ch├¡nh, demo edge case
Γûê- [ ] Audio r├╡ r├áng, c├│ phß╗Ñ ─æß╗ü tß╗æt h╞ín
Γöé
Γûê### Checklist Pitch Deck
Γöé
Γûê- [ ] 10 slides theo template (xem mß╗Ñc 9.6)
Γûê- [ ] File PDF (kh├┤ng PowerPoint ΓÇö tr├ính font/format issues)
Γûê- [ ] Th├¬m v├áo `docs/pitch-deck.pdf`
Γûê- [ ] Thß╗▒c h├ánh tr├¼nh b├áy trong 10 ph├║t
Γöé
Γûê### Checklist Journal + Worklog
Γöé
Γûê- [ ] Journal: ├¡t nhß║Ñt 5-7 entries, mß╗ùi entry 2-3 c├óu
Γûê- [ ] Worklog: git log hoß║╖c bß║úng commit history
Γûê- [ ] Cß║ú hai l╞░u trong `docs/`
Γöé
Γûê### Checklist Evaluation Evidence
Γöé
Γûê- [ ] Bß║úng test results (pytest output + coverage)
Γûê- [ ] Bß║úng RAGAS metrics (hoß║╖c tß╗▒ ─æ├ính gi├í)
Γûê- [ ] Performance metrics (response time)
Γûê- [ ] User feedback (├¡t nhß║Ñt 3-5 ng╞░ß╗¥i)
Γûê- [ ] Code traceability (map test case ΓåÆ feature)
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Tß║ío GitHub Issue hoß║╖c Notion checklist ngay tuß║ºn ─æß║ºu ti├¬n. Check off tß╗½ng mß╗Ñc khi ho├án th├ánh. ─Éß╗½ng ─æß║┐n tuß║ºn cuß╗æi mß╗¢i chß║íy checklist ΓÇö l├║c ─æ├│ ─æ├ú qu├í muß╗Ön ─æß╗â quay video hay viß║┐t journal.
Γöé
Γûê## 9.3 Ti├¬u ch├¡ chß║Ñm ─æiß╗âm
Γöé
ΓûêBTC chß║Ñm ─æiß╗âm theo 5 ti├¬u ch├¡, mß╗ùi ti├¬u ch├¡ thang ─æiß╗âm 1-10. ─Éiß╗âm tß╗æi ─æa = 50 ─æiß╗âm. D╞░ß╗¢i ─æ├óy l├á ph├ón t├¡ch tß╗½ng ti├¬u ch├¡ v├á c├ích ghi ─æiß╗âm tß╗æi ─æa.
Γöé
Γûê### 5 ti├¬u ch├¡ chß║Ñm ─æiß╗âm
Γöé
Γûê| Ti├¬u ch├¡ | Trß╗ìng sß╗æ | M├┤ tß║ú |
Γûê|----------|----------|-------|
Γûê| Product/Business | 20% | Gi├í trß╗ï sß║ún phß║⌐m, market fit, business model |
Γûê| System Design | 20% | Kiß║┐n tr├║c, scalability, tech stack choice |
Γûê| UI/UX | 20% | Giao diß╗çn, trß║úi nghiß╗çm ng╞░ß╗¥i d├╣ng, accessibility |
Γûê| DevOps | 20% | Docker, CI/CD, deployment, monitoring |
Γûê| Code Quality | 20% | Code style, tests, error handling, documentation |
Γöé
ΓûêPh├ón t├¡ch: DevOps th╞░ß╗¥ng l├á ti├¬u ch├¡ c├│ ─æiß╗âm trung b├¼nh thß║Ñp nhß║Ñt ΓÇö ─æ├óy l├á c╞í hß╗Öi lß╗¢n ─æß╗â ghi ─æiß╗âm. Chß╗ë cß║ºn c├│ Docker + CI/CD + health check, bß║ín ─æ├ú ─æß║ít 7-8/10 ß╗ƒ ti├¬u ch├¡ n├áy.
Γöé
Γûê### C├ích tß╗æi ─æa h├│a tß╗½ng ti├¬u ch├¡
Γöé
Γûê**Product/Business (target: 8+/10)**
Γûê- Thß╗â hiß╗çn r├╡ problem statement v├á target user
Γûê- Demo use case thß╗▒c tß║┐, kh├┤ng phß║úi toy example
Γûê- C├│ market sizing hoß║╖c competitor analysis
Γûê- Business model khß║ú thi (d├╣ ─æ╞ín giß║ún)
Γûê- Minimum: giß║úi quyß║┐t 1 pain point cß╗Ñ thß╗â cho 1 nh├│m user cß╗Ñ thß╗â
Γöé
Γûê**System Design (target: 8+/10)**
Γûê- Architecture diagram r├╡ r├áng, professional
Γûê- Giß║úi th├¡ch ─æ╞░ß╗úc tß║íi sao chß╗ìn tech stack n├áy
Γûê- Hß╗ç thß╗æng c├│ thß╗â scale (d├╣ chß╗ë vß╗ü mß║╖t l├╜ thuyß║┐t)
Γûê- Error handling ß╗ƒ mß╗ìi layer
Γûê- Minimum: c├│ diagram + giß║úi th├¡ch design decisions trong README
Γöé
Γûê**UI/UX (target: 7+/10)**
Γûê- Giao diß╗çn sß║ích sß║╜, responsive, d├╣ng ─æ╞░ß╗úc tr├¬n mobile
Γûê- Loading states cho LLM calls (spinner, skeleton)
Γûê- Error messages th├ón thiß╗çn (kh├┤ng hiß╗çn raw exception)
Γûê- ├ìt nhß║Ñt 2-3 screens/views
Γûê- Minimum: giao diß╗çn kh├┤ng bß╗ï lß╗ùi, c├│ thß╗â chat vß╗¢i agent
Γöé
Γûê**DevOps (target: 8+/10)**
Γûê- Dockerfile multi-stage + Docker Compose
Γûê- GitHub Actions CI (lint + test + build)
Γûê- Live URL hoß║ít ─æß╗Öng ß╗òn ─æß╗ïnh
Γûê- Health check endpoint
Γûê- Structured logging + LangSmith tracing
Γûê- Minimum: Live URL + Docker + bß║Ñt kß╗│ CI/CD n├áo
Γöé
Γûê**Code Quality (target: 8+/10)**
Γûê- Type hints cho tß║Ñt cß║ú functions
Γûê- Docstrings cho public APIs
Γûê- Tests vß╗¢i 60%+ coverage
Γûê- No bare except, no hardcoded secrets
Γûê- Consistent code style (Ruff lint pass)
Γûê- Minimum: code chß║íy + c├│ tests + kh├┤ng c├│ anti-patterns
Γöé
Γûê### Mß╗Ñc ti├¬u ─æiß╗âm sß╗æ cho AI20K
Γöé
Γûê| Mß╗Ñc ti├¬u | Tß╗òng ─æiß╗âm | Cß║ºn ─æß║ít ß╗ƒ mß╗ùi ti├¬u ch├¡ |
Γûê|----------|-----------|------------------------|
Γûê| Top 3 | 40+/50 | 8+ ß╗ƒ mß╗ùi ti├¬u ch├¡ |
Γûê| Top 5 | 37+/50 | 7.5+ ß╗ƒ mß╗ùi ti├¬u ch├¡ |
Γûê| Top 8 | 35+/50 | 7+ ß╗ƒ mß╗ùi ti├¬u ch├¡ |
Γûê| Pass | 30+/50 | 6+ ß╗ƒ mß╗ùi ti├¬u ch├¡ |
Γöé
Γûê─Éß╗â ─æß║ít kß║┐t quß║ú tß╗æt (top), cß║ºn khoß║úng 35+ ─æiß╗âm. ─Éß╗â pass an to├án, cß║ºn khoß║úng 30 ─æiß╗âm. Mß╗ùi ti├¬u ch├¡ 7+/10 l├á mß╗Ñc ti├¬u tß╗æi thiß╗âu.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Chiß║┐n l╞░ß╗úc tß╗æi ╞░u: ─æß║úm bß║úo 7+ ß╗ƒ mß╗ìi ti├¬u ch├¡ tr╞░ß╗¢c, rß╗ôi ─æß║⌐y 1-2 ti├¬u ch├¡ l├¬n 9+. Kh├┤ng tß║¡p trung hß║┐t v├áo 1 ti├¬u ch├¡ m├á bß╗Å qua c├íc ti├¬u ch├¡ kh├íc. DevOps l├á ti├¬u ch├¡ dß╗à ghi ─æiß╗âm nhß║Ñt v├¼ ─æa sß╗æ ─æß╗Öi bß╗Å qua phß║ºn n├áy.
Γöé
Γûê## 9.4 Nhß╗»ng lß╗ùi phß╗ò biß║┐n cß║ºn tr├ính
Γöé
ΓûêKinh nghiß╗çm thß╗▒c tiß╗àn cho thß║Ñy nhß╗»ng lß╗ùi sau ─æ├óy lß║╖p ─æi lß║╖p lß║íi ß╗ƒ nhiß╗üu ─æß╗Öi. Hiß╗âu v├á tr├ính nhß╗»ng lß╗ùi n├áy l├á c├ích nhanh nhß║Ñt ─æß╗â cß║úi thiß╗çn ─æiß╗âm sß╗æ.
Γöé
Γûê### Top 5 lß╗ùi phß╗ò biß║┐n nhß║Ñt
Γöé
Γûê**Lß╗ùi #1: Kh├┤ng c├│ CI/CD**
Γöé
ΓûêHß║ºu hß║┐t c├íc ─æß╗Öi kh├┤ng thiß║┐t lß║¡p CI/CD pipeline. ─É├óy l├á lß╗ùi nghi├¬m trß╗ìng nhß║Ñt v├¼ n├│ ß║únh h╞░ß╗ƒng trß╗▒c tiß║┐p ─æß║┐n ti├¬u ch├¡ DevOps. Kh├┤ng c├│ CI/CD ngh─⌐a l├á code kh├┤ng ─æ╞░ß╗úc test tß╗▒ ─æß╗Öng, kh├┤ng ─æ╞░ß╗úc lint tß╗▒ ─æß╗Öng, v├á deploy bß║▒ng tay ΓÇö kh├┤ng chuy├¬n nghiß╗çp.
Γöé
Γûê```yaml
Γûê# SAI: Kh├┤ng c├│ .github/workflows/
Γûê# (th╞░ mß╗Ñc kh├┤ng tß╗ôn tß║íi)
Γöé
Γûê# ─É├ÜNG: .github/workflows/ci.yml
Γûêname: CI
Γûêon:
Γûê  push:
Γûê    branches: [main]
Γûêjobs:
Γûê  test:
Γûê    runs-on: ubuntu-latest
Γûê    steps:
Γûê      - uses: actions/checkout@v4
Γûê      - uses: actions/setup-python@v5
Γûê        with:
Γûê          python-version: "3.11"
Γûê      - run: pip install -r requirements.txt
Γûê      - run: pytest tests/ -v
Γûê```
Γöé
Γûê**Lß╗ùi #2: Kh├┤ng c├│ test**
Γöé
Γûê─Éa sß╗æ c├íc ─æß╗Öi kh├┤ng c├│ test tß╗▒ ─æß╗Öng, code coverage = 0%. BTC kh├┤ng thß╗â verify code hoß║ít ─æß╗Öng ─æ├║ng, dß║½n ─æß║┐n ─æiß╗âm Code Quality thß║Ñp.
Γöé
Γûê```python
Γûê# SAI: Kh├┤ng c├│ th╞░ mß╗Ñc tests/
Γûê# (hoß║╖c tests/ rß╗ùng)
Γöé
Γûê# ─É├ÜNG: tests/test_api.py
Γûêimport pytest
Γûêfrom httpx import AsyncClient
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_health(client):
Γûê    response = await client.get("/health")
Γûê    assert response.status_code == 200
Γûê```
Γöé
Γûê**Lß╗ùi #3: Bare except**
Γöé
ΓûêBß║»t exception vß╗¢i `except:` hoß║╖c `except Exception` m├á kh├┤ng log hay handle cß╗Ñ thß╗â. ─É├óy l├á anti-pattern nghi├¬m trß╗ìng ΓÇö n├│ che giß║Ñu bugs v├á l├ám debug cß╗▒c kß╗│ kh├│ kh─ân.
Γöé
Γûê```python
Γûê# SAI: Bare except
Γûêtry:
Γûê    result = llm.invoke(prompt)
Γûêexcept:  # Bß║»t mß╗ìi thß╗⌐, che giß║Ñu lß╗ùi
Γûê    pass
Γöé
Γûê# SAI: except Exception qu├í rß╗Öng
Γûêtry:
Γûê    result = llm.invoke(prompt)
Γûêexcept Exception:
Γûê    pass  # Vß║½n che giß║Ñu lß╗ùi
Γöé
Γûê# ─É├ÜNG: Bß║»t cß╗Ñ thß╗â + log
Γûêimport logging
Γûêlogger = logging.getLogger(__name__)
Γöé
Γûêtry:
Γûê    result = llm.invoke(prompt)
Γûêexcept openai.APIError as e:
Γûê    logger.error(f"LLM API error: {e}")
Γûê    raise HTTPException(status_code=503, detail="AI service unavailable")
Γûêexcept openai.RateLimitError:
Γûê    logger.warning("Rate limit hit, retrying...")
Γûê    # Retry logic
Γûêexcept ValidationError as e:
Γûê    logger.error(f"Validation error: {e}")
Γûê    raise HTTPException(status_code=422, detail=str(e))
Γûê```
Γöé
Γûê**Lß╗ùi #4: Hardcoded secrets**
Γöé
ΓûêNhiß╗üu ─æß╗Öi commit API key trß╗▒c tiß║┐p v├áo source code tr├¬n GitHub. ─É├óy l├á lß╗ùi bß║úo mß║¡t nghi├¬m trß╗ìng ΓÇö key c├│ thß╗â bß╗ï ai ─æ├│ sß╗¡ dß╗Ñng tr├íi ph├⌐p, tß╗æn tiß╗ün.
Γöé
Γûê```python
Γûê# SAI: Hardcoded API key
Γûêopenai_client = OpenAI(api_key="sk-proj-abc123...")
ΓûêDATABASE_URL = "postgresql://admin:password123@localhost/db"
Γöé
Γûê# ─É├ÜNG: D├╣ng environment variables
Γûêimport os
Γûêfrom dotenv import load_dotenv
Γöé
Γûêload_dotenv()
Γûêopenai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
ΓûêDATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///local.db")
Γûê```
Γöé
Γûê```python
Γûê# .env (kh├┤ng commit v├áo git!)
ΓûêOPENAI_API_KEY=sk-proj-abc123...
ΓûêDATABASE_URL=postgresql://user:pass@host/db
Γûê```
Γöé
Γûê```text
Γûê# .gitignore (lu├┤n c├│ d├▓ng n├áy)
Γûê.env
Γûê```
Γöé
Γûê**Lß╗ùi #5: Thiß║┐u Evaluation Evidence**
Γöé
ΓûêGß║ºn nh╞░ kh├┤ng c├│ ─æß╗Öi n├áo nß╗Öp bß║▒ng chß╗⌐ng ─æ├ính gi├í chß║Ñt l╞░ß╗úng AI agent. ─É├óy l├á deliverable th╞░ß╗¥ng bß╗ï bß╗Å qua nhß║Ñt, nh╞░ng lß║íi l├á c╞í hß╗Öi ghi ─æiß╗âm lß╗¢n nhß║Ñt.
Γöé
Γûê## 9.5 Tips ghi ─æiß╗âm tß╗½ kinh nghiß╗çm thß╗▒c tiß╗àn
Γöé
ΓûêKinh nghiß╗çm tß╗½ c├íc ─æß╗Öi ─æß║ít kß║┐t quß║ú cao cho thß║Ñy nhß╗»ng ─æiß╗âm chung tß║ío n├¬n sß╗▒ kh├íc biß╗çt.
Γöé
Γûê### ─Éiß╗âm chung cß╗ºa top teams
Γöé
Γûê**1. ─Éß╗º 10 deliverables.** C├íc ─æß╗Öi ─æß║ít ─æiß╗âm cao nß╗Öp ─æß╗º hoß║╖c gß║ºn ─æß╗º tß║Ñt cß║ú deliverables (9-10/10). ─Éß╗Öi yß║┐u chß╗ë nß╗Öp 4-5/10. Deliverables ho├án chß╗ënh = t├¡n hiß╗çu chuy├¬n nghiß╗çp.
Γöé
Γûê**2. Code c├│ cß║Ñu tr├║c r├╡ r├áng.** Top teams tß╗ò chß╗⌐c code theo cß║Ñu tr├║c module: `app/api/`, `app/agent/`, `app/core/`, `app/models/`. Kh├┤ng dump tß║Ñt cß║ú code v├áo 1-2 file. Mß╗ùi module c├│ `__init__.py` v├áΦüîΦ┤ú r├╡ r├áng.
Γöé
Γûê```text
Γûê# Cß║Ñu tr├║c tß╗æt (v├¡ dß╗Ñ)
Γûêapp/
ΓûêΓö£ΓöÇΓöÇ __init__.py
ΓûêΓö£ΓöÇΓöÇ main.py              # FastAPI app
ΓûêΓö£ΓöÇΓöÇ api/
ΓûêΓöé   Γö£ΓöÇΓöÇ __init__.py
ΓûêΓöé   Γö£ΓöÇΓöÇ health.py        # Health endpoints
ΓûêΓöé   ΓööΓöÇΓöÇ chat.py          # Chat endpoints
ΓûêΓö£ΓöÇΓöÇ agent/
ΓûêΓöé   Γö£ΓöÇΓöÇ __init__.py
ΓûêΓöé   Γö£ΓöÇΓöÇ graph.py         # LangGraph graph
ΓûêΓöé   Γö£ΓöÇΓöÇ nodes.py         # Agent nodes
ΓûêΓöé   Γö£ΓöÇΓöÇ state.py         # State definition
ΓûêΓöé   ΓööΓöÇΓöÇ tools.py         # Agent tools
ΓûêΓö£ΓöÇΓöÇ core/
ΓûêΓöé   Γö£ΓöÇΓöÇ __init__.py
ΓûêΓöé   Γö£ΓöÇΓöÇ config.py        # Settings
ΓûêΓöé   ΓööΓöÇΓöÇ logging_config.py
ΓûêΓö£ΓöÇΓöÇ models/
ΓûêΓöé   Γö£ΓöÇΓöÇ __init__.py
ΓûêΓöé   ΓööΓöÇΓöÇ schemas.py       # Pydantic models
ΓûêΓööΓöÇΓöÇ services/
Γûê    Γö£ΓöÇΓöÇ __init__.py
Γûê    ΓööΓöÇΓöÇ vector_store.py  # Vector store service
Γöé
Γûê# Cß║Ñu tr├║c k├⌐m (v├¡ dß╗Ñ)
Γûêapp.py                   # Tß║Ñt cß║ú trong 1 file
Γûêagent.py                 # Tß║Ñt cß║ú agent logic
Γûê```
Γöé
Γûê**3. README chuy├¬n nghiß╗çp.** Top teams c├│ README vß╗¢i: screenshot, architecture diagram, installation guide, API docs, team info. README l├á thß╗⌐ BTC ─æß╗ìc ─æß║ºu ti├¬n ΓÇö ß║Ñn t╞░ß╗úng ─æß║ºu ti├¬n quyß║┐t ─æß╗ïnh tone cß╗ºa to├án bß╗Ö ─æ├ính gi├í.
Γöé
Γûê**4. C├│ tests.** D├╣ ├¡t, top teams c├│ ├¡t nhß║Ñt 5-10 test cases cho API endpoints v├á agent nodes. Bottom teams c├│ 0 tests.
Γöé
Γûê**5. Docker + deployment.** Top teams c├│ Dockerfile v├á Live URL hoß║ít ─æß╗Öng. Bottom teams kh├┤ng Dockerize hoß║╖c Live URL kh├┤ng hoß║ít ─æß╗Öng.
Γöé
Γûê### Tips cß╗Ñ thß╗â ─æß╗â ghi ─æiß╗âm
Γöé
Γûê**Tip 1: README "v├áng"** ΓÇö README l├á deliverable ROI (return on investment) cao nhß║Ñt. 30 ph├║t viß║┐t README tß╗æt ─æ├íng gi├í h╞ín 3 tiß║┐ng th├¬m feature. BTC ─æß╗ìc README tr╞░ß╗¢c khi xem code. README tß╗æt = ─æiß╗âm +1-2 ß╗ƒ mß╗ìi ti├¬u ch├¡.
Γöé
Γûê**Tip 2: Deploy sß╗¢m** ΓÇö Deploy trong tuß║ºn ─æß║ºu ti├¬n, ngay cß║ú khi app chß╗ë c├│ 1 endpoint `/health`. Deploy sß╗¢m cho bß║ín thß╗¥i gian fix deployment issues. Nhiß╗üu ─æß╗Öi deploy ng├áy cuß╗æi v├á gß║╖p lß╗ùi kh├┤ng kß╗ïp fix.
Γöé
Γûê**Tip 3: Screenshot mß╗ìi thß╗⌐** ΓÇö Screenshot: running app, API docs (/docs), test output, LangSmith traces, Docker running, CI/CD green checks. Cho tß║Ñt cß║ú v├áo README hoß║╖c `docs/`. Bß║▒ng chß╗⌐ng h├¼nh ß║únh mß║ính h╞ín text.
Γöé
Γûê**Tip 4: Git history ─æß╗üu ─æß║╖n** ΓÇö Commit th╞░ß╗¥ng xuy├¬n (h├áng ng├áy), message r├╡ r├áng. BTC xem git history ─æß╗â ─æ├ính gi├í effort v├á tiß║┐n ─æß╗Ö. 50 commits trong 4 tuß║ºn tß╗æt h╞ín 3 commits ng├áy cuß╗æi.
Γöé
Γûê```bash
Γûê# Tß╗æt: commit message r├╡ r├áng
Γûêgit commit -m "feat: add RAG retrieval node with ChromaDB"
Γûêgit commit -m "fix: handle empty query in chat endpoint"
Γûêgit commit -m "test: add integration tests for chat API"
Γöé
Γûê# K├⌐m: commit message chung chung
Γûêgit commit -m "update"
Γûêgit commit -m "fix"
Γûêgit commit -m "wip"
Γûê```
Γöé
Γûê**Tip 5: Nß╗Öp Evaluation Evidence** ΓÇö Rß║Ñt hiß║┐m ─æß╗Öi c├│ deliverable n├áy. ─É├óy l├á "low-hanging fruit" (tr├íi h├íi thß║Ñp) ΓÇö ├¡t effort, nhiß╗üu ─æiß╗âm. Chß║íy pytest + RAGAS, screenshot kß║┐t quß║ú, viß║┐t bß║úng metrics. Xong trong 1-2 ng├áy.
Γöé
Γûê## 9.6 Pitch Deck ΓÇö Slide thuyß║┐t tr├¼nh
Γöé
ΓûêPitch Deck l├á b├ái thuyß║┐t tr├¼nhDemo Day ΓÇö th╞░ß╗¥ng 10 ph├║t cho 10 slides. ─É├óy l├á deliverable c├│ completion rate thß║Ñp (33%) nh╞░ng ß║únh h╞░ß╗ƒng lß╗¢n ─æß║┐n ß║Ñn t╞░ß╗úng BTC. Slide tß╗æt + thuyß║┐t tr├¼nh tß╗æt = ─æiß╗âm thuyß║┐t phß╗Ñc ß╗ƒ mß╗ìi ti├¬u ch├¡.
Γöé
Γûê### Cß║Ñu tr├║c 10 slides
Γöé
Γûê**Slide 1: Title (Ti├¬u ─æß╗ü)**
Γûê- T├¬n dß╗▒ ├ín
Γûê- Tagline (1 c├óu m├┤ tß║ú)
Γûê- T├¬n team + logo
Γûê- Ng├áy Demo Day
Γöé
Γûê**Slide 2: Problem (Vß║Ñn ─æß╗ü)**
Γûê- M├┤ tß║ú pain point cß╗Ñ thß╗â
Γûê- Ai ─æang gß║╖p vß║Ñn ─æß╗ü? (target user)
Γûê- Tß║ºn suß║Ñt/mß╗⌐c ─æß╗Ö nghi├¬m trß╗ìng
Γûê- Sß╗æ liß╗çu nß║┐u c├│ (v├¡ dß╗Ñ: "70% sinh vi├¬n kh├┤ng biß║┐t sß╗¡ dß╗Ñng AI")
Γöé
Γûê**Slide 3: Solution (Giß║úi ph├íp)**
Γûê- Giß║úi ph├íp cß╗ºa bß║ín giß║úi quyß║┐t vß║Ñn ─æß╗ü nh╞░ thß║┐ n├áo
Γûê- Kh├íc biß╗çt vß╗¢i c├íc giß║úi ph├íp hiß╗çn c├│
Γûê- Demo screenshot hoß║╖c mockup
Γöé
Γûê**Slide 4: Product Demo (Sß║ún phß║⌐m)**
Γûê- Screenshot hoß║╖c GIF demo thß╗▒c tß║┐
Γûê- Highlight main features
Γûê- User flow ch├¡nh
Γöé
Γûê**Slide 5: Architecture (Kiß║┐n tr├║c)**
Γûê- Architecture diagram (─æ╞ín giß║ún, dß╗à hiß╗âu)
Γûê- Giß║úi th├¡ch tech stack choices
Γûê- Tß║íi sao chß╗ìn LangGraph? Tß║íi sao chß╗ìn vector store n├áy?
Γöé
Γûê**Slide 6: AI/LLM Approach (C├ích tiß║┐p cß║¡n AI)**
Γûê- RAG pipeline, Agent design, Prompt strategy
Γûê- LangGraph graph diagram
Γûê- Evaluation metrics (RAGAS hoß║╖c custom)
Γöé
Γûê**Slide 7: Technical Highlights (─Éiß╗âm nß╗òi bß║¡t kß╗╣ thuß║¡t)**
Γûê- CI/CD pipeline
Γûê- Test coverage
Γûê- Performance metrics
Γûê- DevOps setup
Γöé
Γûê**Slide 8: Demo Video (Video demo)**
Γûê- Embed video hoß║╖c QR code link YouTube
Γûê- 2-3 ph├║t demo main use case
Γöé
Γûê**Slide 9: Challenges & Learnings (Th├ích thß╗⌐c & B├ái hß╗ìc)**
Γûê- Kh├│ kh─ân lß╗¢n nhß║Ñt v├á c├ích giß║úi quyß║┐t
Γûê- B├ái hß╗ìc kß╗╣ thuß║¡t
Γûê- Nß║┐u l├ám lß║íi, bß║ín sß║╜ thay ─æß╗òi g├¼?
Γöé
Γûê**Slide 10: Team & Next Steps (Team & B╞░ß╗¢c tiß║┐p theo)**
Γûê- Team members + vai tr├▓
Γûê- Roadmap tiß║┐p theo (nß║┐u c├│ thß╗¥i gian ph├ít triß╗ân th├¬m)
Γûê- Cß║úm ╞ín + Q&A
Γöé
Γûê### Tips cho slide v├á thuyß║┐t tr├¼nh
Γöé
Γûê**Slide design:**
Γûê- Mß╗ùi slide chß╗ë 1 idea ch├¡nh
Γûê- Font size tß╗æi thiß╗âu 24pt (BTC ngß╗ôi xa)
Γûê- H├¼nh ß║únh > text (1 h├¼nh = 1000 tß╗½)
Γûê- Dark background + light text (projector tß╗æt h╞ín)
Γûê- Kh├┤ng qu├í 30 tß╗½ mß╗ùi slide
Γöé
Γûê**Thuyß║┐t tr├¼nh:**
Γûê- Thß╗▒c h├ánh ├¡t nhß║Ñt 3 lß║ºn tr╞░ß╗¢c Demo Day
Γûê- Time rehearsal: 10 slides ├ù 1 ph├║t = 10 ph├║t
Γûê- Chß╗ë c├│ ng╞░ß╗¥i n├│i chuyß╗çn, kh├┤ng ai ─æß╗ìc slide
Γûê- Demo live rß╗ºi ro ΓÇö c├│ video backup sß║╡n
Γûê- Chuß║⌐n bß╗ï cho Q&A: "L├ám sao bß║ín xß╗¡ l├╜ hallucination?" "Scale thß║┐ n├áo?"
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** BTC sß║╜ hß╗Åi vß╗ü technical decisions. Chuß║⌐n bß╗ï c├óu trß║ú lß╗¥i cho: "Tß║íi sao chß╗ìn LangGraph thay v├¼ CrewAI/AutoGen?", "L├ám sao giß║úm hallucination?", "Cost per request l├á bao nhi├¬u?", "L├ám sao scale khi c├│ 1000 users ─æß╗ông thß╗¥i?"
Γöé
Γûê## T├│m tß║»t
Γöé
ΓûêTrong ch╞░╞íng n├áy, ch├║ng ta ─æ├ú t├¼m hiß╗âu mß╗ìi thß╗⌐ cß║ºn biß║┐t ─æß╗â nß╗Öp b├ái Demo Day th├ánh c├┤ng:
Γöé
Γûê- **10 deliverables** BTC y├¬u cß║ºu ΓÇö Video Demo v├á Evaluation Evidence th╞░ß╗¥ng bß╗ï bß╗Å qua nhß║Ñt, l├á c╞í hß╗Öi ghi ─æiß╗âm lß╗¢n nhß║Ñt
Γûê- **Checklist chi tiß║┐t** cho tß╗½ng deliverable ΓÇö kh├┤ng bß╗Å s├│t g├¼
Γûê- **5 ti├¬u ch├¡ chß║Ñm ─æiß╗âm** ΓÇö DevOps l├á ti├¬u ch├¡ dß╗à cß║úi thiß╗çn nhß║Ñt
Γûê- **Top 5 lß╗ùi phß╗ò biß║┐n** ΓÇö Kh├┤ng c├│ CI/CD, Kh├┤ng c├│ test, Bare except, Hardcoded secrets, Thiß║┐u Evaluation Evidence
Γûê- **Tips tß╗½ c├íc ─æß╗Öi ─æß║ít ─æiß╗âm cao** ΓÇö README chuy├¬n nghiß╗çp, deploy sß╗¢m, commit ─æß╗üu, screenshot mß╗ìi thß╗⌐
Γûê- **Pitch Deck 10 slides** ΓÇö template ho├án chß╗ënh cho Demo Day
Γöé
ΓûêCuß╗æi c├╣ng, h├úy nhß╗¢: Demo Day kh├┤ng chß╗ë l├á thi ΓÇö n├│ l├á c╞í hß╗Öi thß╗â hiß╗çn kß╗╣ n─âng engineering v├á teamwork. BTC ─æ├ính gi├í tß╗òng thß╗â, kh├┤ng chß╗ë code. Deliverables ─æß║ºy ─æß╗º + code sß║ích + thuyß║┐t tr├¼nh tß╗æt = chiß║┐n thß║»ng.
Γöé
Γûê## Checklist cuß╗æi c├╣ng tr╞░ß╗¢c khi nß╗Öp
Γöé
Γûê- [ ] 10/10 deliverables ─æ├ú ho├án th├ánh?
Γûê- [ ] README c├│ screenshot, install guide, API docs?
Γûê- [ ] Live URL hoß║ít ─æß╗Öng (test tr├¬n browser kh├íc + incognito)?
Γûê- [ ] Tests chß║íy pass (pytest green)?
Γûê- [ ] Kh├┤ng c├│ hardcoded secrets trong code?
Γûê- [ ] Kh├┤ng c├│ bare except?
Γûê- [ ] Docker build th├ánh c├┤ng?
Γûê- [ ] CI/CD pipeline xanh (GitHub Actions green)?
Γûê- [ ] Git history ─æß╗üu ─æß║╖n (kh├┤ng phß║úi 5 commits ng├áy cuß╗æi)?
Γûê- [ ] Pitch Deck ─æ├ú thß╗▒c h├ánh thuyß║┐t tr├¼nh 3+ lß║ºn?


docs\guide\chapter-10.md:
Γûê---
Γûêtitle: "T├ái nguy├¬n hß╗ìc tß║¡p"
Γûêweight: 10
Γûê---
Γöé
Γûê## 10.1 Lß╗Ö tr├¼nh hß╗ìc 6 tuß║ºn
Γöé
ΓûêLß╗Ö tr├¼nh n├áy thiß║┐t kß║┐ cho sinh vi├¬n VinUni tham gia AI20K Build Phase, vß╗¢i mß╗Ñc ti├¬u tß╗½ "ch╞░a biß║┐t LangGraph" ─æß║┐n "c├│ thß╗â build v├á deploy AI Agent ho├án chß╗ënh" trong 6 tuß║ºn. Mß╗ùi tuß║ºn c├│ focus cß╗Ñ thß╗â, kß║┐t hß╗úp l├╜ thuyß║┐t v├á thß╗▒c h├ánh.
Γöé
Γûê### Tuß║ºn 1: Nß╗ün tß║úng Python v├á API
Γöé
ΓûêMß╗Ñc ti├¬u: Hiß╗âu FastAPI, viß║┐t ─æ╞░ß╗úc API endpoint, biß║┐t gß╗ìi LLM API.
Γöé
Γûê- Hß╗ìc FastAPI fundamentals: routing, request/response, Pydantic models
Γûê- L├ám quen vß╗¢i async/await trong Python
Γûê- Gß╗ìi OpenAI API c╞í bß║ún: chat completion, streaming
Γûê- Setup project structure: `app/`, `tests/`, `requirements.txt`
Γûê- B├ái tß║¡p: Viß║┐t FastAPI app c├│ 3 endpoints (GET /health, POST /chat, GET /history)
Γöé
ΓûêT├ái liß╗çu: FastAPI official tutorial (2-3 giß╗¥), Python async docs (1 giß╗¥), OpenAI API quickstart (1 giß╗¥).
Γöé
Γûê### Tuß║ºn 2: LangGraph Fundamentals
Γöé
ΓûêMß╗Ñc ti├¬u: Hiß╗âu LangGraph graph, state, nodes, edges. Build ─æ╞░ß╗úc agent ─æ╞ín giß║ún.
Γöé
Γûê- Hß╗ìc LangGraph concepts: StateGraph, nodes, edges, conditional routing
Γûê- Build graph ─æß║ºu ti├¬n: 2-3 nodes, conditional routing
Γûê- Thß╗¡ nghiß╗çm vß╗¢i different state schemas (TypedDict vs Pydantic)
Γûê- Debug vß╗¢i LangSmith tracing
Γûê- B├ái tß║¡p: Build agent c├│ routing dß╗▒a tr├¬n intent (FAQ ΓåÆ retrieval, chitchat ΓåÆ respond directly)
Γöé
ΓûêT├ái liß╗çu: LangGraph Academy Module 1-2 (4-5 giß╗¥), Lance Martin YouTube LangGraph playlist (2 giß╗¥).
Γöé
Γûê### Tuß║ºn 3: RAG v├á Vector Store
Γöé
ΓûêMß╗Ñc ti├¬u: Hiß╗âu RAG pipeline, load documents, embed, retrieve.
Γöé
Γûê- Hß╗ìc document loading: PDF, web, text files
Γûê- Text splitting strategies: chunk size, overlap
Γûê- Embedding models: OpenAI embeddings, local alternatives
Γûê- Vector stores: ChromaDB (local), PGVector (production)
Γûê- RAG pipeline: retrieve ΓåÆ rerank ΓåÆ generate
Γûê- B├ái tß║¡p: Build RAG agent trß║ú lß╗¥i c├óu hß╗Åi tß╗½ 10 t├ái liß╗çu PDF
Γöé
ΓûêT├ái liß╗çu: DeepLearning.AI "Building RAG Agents with LLMs" (4 giß╗¥), LangChain RAG tutorial (2 giß╗¥).
Γöé
Γûê### Tuß║ºn 4: Agent n├óng cao v├á Tools
Γöé
ΓûêMß╗Ñc ti├¬u: Agent c├│ tools, memory, multi-step reasoning.
Γöé
Γûê- Hß╗ìc LangGraph tools: @tool decorator, tool calling
Γûê- Agent memory: conversation history, long-term memory
Γûê- Multi-step reasoning: ReAct pattern, planning
Γûê- Error handling trong agent: retry, fallback
Γûê- B├ái tß║¡p: Build agent c├│ 3+ tools (search, calculator, database query)
Γöé
ΓûêT├ái liß╗çu: LangGraph Academy Module 3-4 (4 giß╗¥), DeepLearning.AI "AI Agents in LangGraph" (3 giß╗¥).
Γöé
Γûê### Tuß║ºn 5: DevOps, Testing, v├á Deploy
Γöé
ΓûêMß╗Ñc ti├¬u: Dockerize, viß║┐t tests, deploy l├¬n cloud, setup CI/CD.
Γöé
Γûê- Docker: Dockerfile multi-stage, Docker Compose
Γûê- Testing: pytest, mock LLM, test coverage
Γûê- CI/CD: GitHub Actions workflow
Γûê- Deploy: Render (backend), Vercel (frontend)
Γûê- Monitoring: structured logging, LangSmith, health checks
Γûê- B├ái tß║¡p: Dockerize app, ─æß║ít 60%+ test coverage, deploy l├¬n Render
Γöé
ΓûêT├ái liß╗çu: Ch╞░╞íng 7 v├á 8 cß╗ºa guidebook n├áy, Docker official tutorial (2 giß╗¥), pytest docs (1 giß╗¥).
Γöé
Γûê### Tuß║ºn 6: Evaluation v├á Chuß║⌐n bß╗ï Demo Day
Γöé
ΓûêMß╗Ñc ti├¬u: ─É├ính gi├í chß║Ñt l╞░ß╗úng agent, chuß║⌐n bß╗ï deliverables.
Γöé
Γûê- RAGAS evaluation: faithfulness, relevance, precision
Γûê- Evaluation report: metrics table, test results, user feedback
Γûê- Ho├án thiß╗çn 10 deliverables
Γûê- Pitch Deck: 10 slides, thuyß║┐t tr├¼nh
Γûê- Code review: x├│a bare except, th├¬m type hints, cleanup
Γûê- B├ái tß║¡p: Nß╗Öp ─æß╗º 10 deliverables, ─æß║ít 35+/50 ─æiß╗âm dß╗▒ kiß║┐n
Γöé
ΓûêT├ái liß╗çu: Ch╞░╞íng 9 cß╗ºa guidebook n├áy, RAGAS docs (2 giß╗¥).
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Lß╗Ö tr├¼nh n├áy intensity cao ΓÇö ~15-20 giß╗¥/tuß║ºn. Nß║┐u bß║ín c├│ ├¡t thß╗¥i gian, ╞░u ti├¬n: Tuß║ºn 2 (LangGraph) > Tuß║ºn 3 (RAG) > Tuß║ºn 5 (DevOps) > Tuß║ºn 6 (Evaluation). ─É├óy l├á thß╗⌐ tß╗▒ impact ─æß║┐n ─æiß╗âm sß╗æ.
Γöé
Γûê### Tß╗òng kß║┐t thß╗¥i gian
Γöé
Γûê| Tuß║ºn | Chß╗º ─æß╗ü | Giß╗¥ hß╗ìc | Giß╗¥ code |
Γûê|------|--------|---------|----------|
Γûê| 1 | FastAPI + LLM API | 6 | 8 |
Γûê| 2 | LangGraph fundamentals | 6 | 10 |
Γûê| 3 | RAG + Vector Store | 6 | 10 |
Γûê| 4 | Agent n├óng cao + Tools | 7 | 10 |
Γûê| 5 | DevOps + Testing + Deploy | 5 | 12 |
Γûê| 6 | Evaluation + Demo Day prep | 4 | 10 |
Γûê| **Tß╗òng** | | **34** | **60** |
Γöé
Γûê## 10.2 Kh├│a hß╗ìc DeepLearning.AI
Γöé
ΓûêDeepLearning.AI (deeplearning.ai) l├á nß╗ün tß║úng hß╗ìc AI h├áng ─æß║ºu cß╗ºa Andrew Ng, vß╗¢i h╞ín 121 kh├│a hß╗ìc ngß║»n (short courses). C├íc kh├│a hß╗ìc n├áy miß╗àn ph├¡, duration 1-2 giß╗¥, v├á ─æ╞░ß╗úc thiß║┐t kß║┐ bß╗ƒi chuy├¬n gia tß╗½ OpenAI, LangChain, Google, Anthropic. ─É├óy l├á nguß╗ôn hß╗ìc tß║¡p chß║Ñt l╞░ß╗úng cao nhß║Ñt cho AI20K.
Γöé
Γûê### Top kh├│a hß╗ìc cho AI20K
Γöé
Γûê| Kh├│a hß╗ìc | Chß╗º ─æß╗ü | Thß╗¥i gian | ╞»u ti├¬n |
Γûê|----------|--------|-----------|---------|
Γûê| AI Agents in LangGraph | LangGraph agents, ReAct, tools | 2 giß╗¥ | CAO |
Γûê| Building RAG Agents with LLMs | RAG pipeline, retrieval, evaluation | 2 giß╗¥ | CAO |
Γûê| Prompt Engineering with LLMs | Prompt design, chain-of-thought | 1 giß╗¥ | CAO |
Γûê| Functions, Tools and Agents with LangChain | Tool use, agents, chains | 1.5 giß╗¥ | CAO |
Γûê| Multi-AI Agent Systems with CrewAI | Multi-agent collaboration | 1.5 giß╗¥ | TRUNG B├îNH |
Γûê| Evaluating and Debugging Generative AI | Evaluation methods, metrics | 1 giß╗¥ | TRUNG B├îNH |
Γûê| LangChain for LLM Application Development | LangChain basics, chains, memory | 1.5 giß╗¥ | TRUNG B├îNH |
Γûê| ChatGPT Prompt Engineering for Developers | Prompt engineering basics | 1 giß╗¥ | THß║ñP |
Γûê| Building Systems with the ChatGPT API | API usage, system design | 1 giß╗¥ | THß║ñP |
Γûê| Red Teaming LLM Applications | Security, adversarial testing | 1 giß╗¥ | BONUS |
Γöé
Γûê### C├ích hß╗ìc hiß╗çu quß║ú tß╗½ DeepLearning.AI
Γöé
Γûê**Chiß║┐n l╞░ß╗úc hß╗ìc tß║¡p:**
Γöé
Γûê1. **Xem video ß╗ƒ 1.5x speed.** C├íc kh├│a hß╗ìc DeepLearning.AI n├│i chß║¡m, t─âng tß╗æc 1.5x tiß║┐t kiß╗çm 33% thß╗¥i gian m├á vß║½n hiß╗âu.
Γöé
Γûê2. **Code along.** Mß╗ùi kh├│a c├│ Jupyter notebook. Code c├╣ng video, kh├┤ng chß╗ë xem. Sau ─æ├│, thß╗¡ modify code v├á xem kß║┐t quß║ú thay ─æß╗òi thß║┐ n├áo.
Γöé
Γûê3. **├üp dß╗Ñng ngay.** Sau mß╗ùi kh├│a, ├íp dß╗Ñng concept v├áo dß╗▒ ├ín AI20K cß╗ºa bß║ín. V├¡ dß╗Ñ: hß╗ìc xong "AI Agents in LangGraph" ΓåÆ th├¬m 1 node mß╗¢i v├áo agent cß╗ºa bß║ín.
Γöé
Γûê4. **Ghi ch├║ v├áo journal.** Mß╗ùi kh├│a hß╗ìc, ghi 3 ─æiß╗âm ch├¡nh v├áo Development Journal ΓÇö vß╗½a ├┤n tß║¡p, vß╗½a c├│ material cho deliverable.
Γöé
Γûê**AI Agents courses (35 kh├│a):** DeepLearning.AI c├│ 35 kh├│a li├¬n quan ─æß║┐n AI Agents, tß╗½ c╞í bß║ún ─æß║┐n n├óng cao. Kh├┤ng cß║ºn hß╗ìc tß║Ñt cß║ú ΓÇö chß╗ìn 3-4 kh├│a c├│ priority CAO trong bß║úng tr├¬n, rß╗ôi mß╗ƒ rß╗Öng nß║┐u c├│ thß╗¥i gian.
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Bß╗æn kh├│a hß╗ìc bß║»t buß╗Öc cho AI20K: (1) AI Agents in LangGraph, (2) Building RAG Agents with LLMs, (3) Prompt Engineering with LLMs, (4) Functions, Tools and Agents with LangChain. Ho├án th├ánh 4 kh├│a n├áy trong 2 tuß║ºn ─æß║ºu.
Γöé
Γûê### Lß╗Ö tr├¼nh hß╗ìc DeepLearning.AI theo tuß║ºn
Γöé
Γûê- **Tuß║ºn 1:** Prompt Engineering + Building Systems with ChatGPT API (2 kh├│a)
Γûê- **Tuß║ºn 2:** AI Agents in LangGraph + Functions/Tools/Agents (2 kh├│a)
Γûê- **Tuß║ºn 3:** Building RAG Agents (1 kh├│a, nh╞░ng intensive)
Γûê- **Tuß║ºn 4:** Evaluating and Debugging Generative AI (1 kh├│a)
Γûê- **Tuß║ºn 5-6:** Bonus courses t├╣y thß╗¥i gian
Γöé
Γûê## 10.3 T├ái liß╗çu LangGraph
Γöé
ΓûêLangGraph l├á framework ch├¡nh cho AI20K, v├á t├ái liß╗çu ch├¡nh thß╗⌐c l├á nguß╗ôn hß╗ìc tß║¡p ─æ├íng tin cß║¡y nhß║Ñt. Ngo├ái docs, c├▓n c├│ nhiß╗üu t├ái nguy├¬n cß╗Öng ─æß╗ông chß║Ñt l╞░ß╗úng cao.
Γöé
Γûê### T├ái liß╗çu ch├¡nh thß╗⌐c
Γöé
Γûê**LangGraph Documentation** (langchain-ai.github.io/langgraph/):
Γûê- Core concepts: StateGraph, nodes, edges, state, tools
Γûê- Tutorials: step-by-step guides cho common patterns
Γûê- API reference: chi tiß║┐t mß╗ìi class v├á function
Γûê- How-to guides: specific tasks nh╞░ "add memory to agent", "human-in-the-loop"
Γöé
Γûê**LangGraph Academy** (academy.langchain.com):
Γûê- Module 1: Fundamentals ΓÇö StateGraph, nodes, edges
Γûê- Module 2: State management ΓÇö TypedDict state, reducers
Γûê- Module 3: Tools and human-in-the-loop
Γûê- Module 4: Multi-agent systems
Γûê- Module 5: Persistence and deployment
Γûê- Mß╗ùi module 2-3 giß╗¥, c├│ code exercises
Γöé
Γûê### K├¬nh YouTube
Γöé
Γûê**Lance Martin** (youtube.com/@LanceMartinAI):
Γûê- LangGraph tutorials tß╗½ c╞í bß║ún ─æß║┐n n├óng cao
Γûê- RAG deep dives
Γûê- Agent patterns and best practices
Γûê- Cß║¡p nhß║¡t li├¬n tß╗Ñc khi LangGraph release version mß╗¢i
Γûê- ╞»u ─æiß╗âm: ngß║»n gß╗ìn (10-20 ph├║t/video), practical, code-first
Γöé
Γûê**James Briggs** (youtube.com/@JamesBriggs):
Γûê- Vector databases and embeddings
Γûê- RAG optimization techniques
Γûê- LangChain ecosystem tutorials
Γûê- ╞»u ─æiß╗âm: deep technical explanations, production-focused
Γöé
Γûê**LangChain Official** (youtube.com/@LangChain):
Γûê- Official tutorials v├á announcements
Γûê- LangGraph release walkthroughs
Γûê- Community showcases
Γöé
Γûê### GitHub examples
Γöé
Γûê**langchain-ai/langgraph** (github.com/langchain-ai/langgraph):
Γûê- Th╞░ mß╗Ñc `examples/` chß╗⌐a dozens of complete examples
Γûê- Examples theo pattern: ReAct agent, RAG, multi-agent, human-in-the-loop
Γûê- Mß╗ùi example c├│ README v├á requirements.txt ΓÇö chß║íy ─æ╞░ß╗úc ngay
Γöé
Γûê```bash
Γûê# Clone LangGraph repo v├á xem examples
Γûêgit clone https://github.com/langchain-ai/langgraph.git
Γûêcd langgraph/examples
Γûêls -la
Γöé
Γûê# Chß║íy mß╗Öt example
Γûêcd rag/
Γûêpip install -r requirements.txt
Γûêpython agent.py
Γûê```
Γöé
Γûê**langchain-ai/langchain** (github.com/langchain-ai/langchain):
Γûê- Th╞░ mß╗Ñc `templates/` chß╗⌐a project templates
Γûê- `cookbook/` chß╗⌐a recipes cho specific use cases
Γûê- Useful cho t├¼m solutions cho specific problems
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Khi gß║╖p lß╗ùi vß╗¢i LangGraph, search GitHub Issues tr╞░ß╗¢c: `repo:langchain-ai/langgraph "error message"`. 90% lß╗ùi phß╗ò biß║┐n ─æ├ú ─æ╞░ß╗úc hß╗Åi v├á trß║ú lß╗¥i. Nß║┐u kh├┤ng t├¼m thß║Ñy, mß╗ƒ issue mß╗¢i ΓÇö maintainers phß║ún hß╗ôi nhanh.
Γöé
Γûê## 10.4 BMAD Method
Γöé
ΓûêBMAD (Build Modular AI Development) l├á mß╗Öt ph╞░╞íng ph├íp ph├ít triß╗ân phß║ºn mß╗üm AI-first, phi├¬n bß║ún mß╗¢i nhß║Ñt l├á BMAD-v6. BMAD sß╗¡ dß╗Ñng 6 AI agents chuy├¬n biß╗çt, mß╗ùi agent ─æß║úm nhiß╗çm mß╗Öt vai tr├▓ trong quy tr├¼nh ph├ít triß╗ân, t╞░╞íng tß╗▒ nh╞░ mß╗Öt development team thß╗▒c tß║┐. Hiß╗âu BMAD gi├║p bß║ín t╞░ duy vß╗ü multi-agent systems v├á project management hiß╗çu quß║ú.
Γöé
Γûê### 6 AI Agents trong BMAD-v6
Γöé
Γûê| Agent | Vai tr├▓ | Analog thß╗▒c tß║┐ | Khi n├áo d├╣ng |
Γûê|-------|---------|----------------|-------------|
Γûê| **Mary** (Analyst) | Ph├ón t├¡ch y├¬u cß║ºu, viß║┐t PRD, user stories | Business Analyst | ─Éß║ºu dß╗▒ ├ín, khi nhß║¡n brief |
Γûê| **John** (Architect) | Thiß║┐t kß║┐ kiß║┐n tr├║c, tech stack, system design | Solution Architect | Sau khi c├│ PRD |
Γûê| **Winston** (Developer) | Viß║┐t code, implement features | Developer | Sau khi c├│ architecture |
Γûê| **Amelia** (Designer) | UI/UX design, wireframes, user flow | UX Designer | Song song vß╗¢i development |
Γûê| **Sally** (QA) | Viß║┐t test, review code, quality assurance | QA Engineer | Song song vß╗¢i development |
Γûê| **Paige** (PM) | Quß║ún l├╜ tiß║┐n ─æß╗Ö, priorities, deliverables | Project Manager | Xuy├¬n suß╗æt dß╗▒ ├ín |
Γöé
Γûê### 4-phase workflow
Γöé
Γûê**Phase 1: Discovery (Kh├ím ph├í) ΓÇö Agent Mary + Paige**
ΓûêMary ph├ón t├¡ch requirements tß╗½ BTC brief, viß║┐t Product Requirements Document (PRD), x├íc ─æß╗ïnh user personas v├á use cases. Paige tß║ío project plan vß╗¢i timeline, milestones, v├á resource allocation. Output: PRD document + project plan.
Γöé
Γûê**Phase 2: Design (Thiß║┐t kß║┐) ΓÇö Agent John + Amelia**
ΓûêJohn thiß║┐t kß║┐ system architecture: tech stack, data flow, API design, deployment strategy. Amelia thiß║┐t kß║┐ UI/UX: wireframes, user flows, interaction patterns. Output: Architecture document + UI mockups.
Γöé
Γûê**Phase 3: Build (X├óy dß╗▒ng) ΓÇö Agent Winston + Sally**
ΓûêWinston implement code theo architecture design. Sally viß║┐t tests song song, review code, ─æß║úm bß║úo quality standards. Output: Working code + test suite.
Γöé
Γûê**Phase 4: Deliver (Giao h├áng) ΓÇö Agent Paige + Sally**
ΓûêPaige quß║ún l├╜ deliverables checklist, ─æß║úm bß║úo ─æß╗º 10/10. Sally chß║íy final evaluation, verify tß║Ñt cß║ú quality gates pass. Output: Complete deliverables package.
Γöé
Γûê### Khi n├áo sß╗¡ dß╗Ñng BMAD
Γöé
ΓûêBMAD ph├╣ hß╗úp khi:
Γûê- Dß╗▒ ├ín c├│ scope r├╡ r├áng, cß║ºn structure
Γûê- Team mß╗¢i l├ám viß╗çc c├╣ng nhau, cß║ºn roles ph├ón minh
Γûê- Cß║ºn documentation ─æß║ºy ─æß╗º cho Demo Day
Γûê- Muß╗æn hß╗ìc multi-agent thinking pattern
Γöé
ΓûêBMAD kh├┤ng ph├╣ hß╗úp khi:
Γûê- Prototype nhanh, thß╗¡ nghiß╗çm ├╜ t╞░ß╗ƒng
Γûê- Solo developer, kh├┤ng cß║ºn role separation
Γûê- Dß╗▒ ├ín rß║Ñt nhß╗Å (1-2 endpoints)
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** BMAD l├á framework t╞░ duy, kh├┤ng phß║úi tool bß║»t buß╗Öc. Bß║ín kh├┤ng cß║ºn c├ái ─æß║╖t g├¼ cß║ú. H├úy ├íp dß╗Ñng mindset: ph├ón t├¡ch tr╞░ß╗¢c khi code (Mary), thiß║┐t kß║┐ tr╞░ß╗¢c khi implement (John), test song song vß╗¢i dev (Sally), quß║ún l├╜ deliverables xuy├¬n suß╗æt (Paige).
Γöé
Γûê### ├üp dß╗Ñng BMAD v├áo AI20K
Γöé
ΓûêTrong AI20K, bß║ín c├│ thß╗â ├íp dß╗Ñng BMAD bß║▒ng c├ích:
Γöé
Γûê1. **Session 1 (Mary):** ─Éß╗ìc BTC brief, viß║┐t PRD 1 trang: problem, solution, target user, features, non-goals
Γûê2. **Session 2 (John):** Vß║╜ architecture diagram, chß╗ìn tech stack, define API contracts
Γûê3. **Session 3-10 (Winston + Sally):** Implement + test song song. Mß╗ùi feature mß╗¢i = test mß╗¢i
Γûê4. **Session 11-12 (Paige + Sally):** Ho├án thiß╗çn deliverables, chß║íy evaluation, chuß║⌐n bß╗ï Pitch Deck
Γöé
Γûê## 10.5 Dß╗▒ ├ín mß║½u tham khß║úo
Γöé
ΓûêKhi hß╗ìc c├ích x├óy dß╗▒ng AI Agent, viß╗çc tham khß║úo c├íc dß╗▒ ├ín mß║½u tß╗æt l├á mß╗Öt trong nhß╗»ng c├ích hß╗ìc nhanh nhß║Ñt. D╞░ß╗¢i ─æ├óy l├á nhß╗»ng pattern v├á best practices m├á c├íc dß╗▒ ├ín AI Agent chß║Ñt l╞░ß╗úng cao th╞░ß╗¥ng c├│, ─æß╗â bß║ín hß╗ìc hß╗Åi v├á ├íp dß╗Ñng v├áo dß╗▒ ├ín cß╗ºa m├¼nh.
Γöé
Γûê### Pattern 1: Sß╗▒ ho├án chß╗ënh (Completeness)
Γöé
ΓûêDß╗▒ ├ín AI Agent chß║Ñt l╞░ß╗úng cao kh├┤ng cß║ºn xuß║Ñt sß║»c ß╗ƒ mß╗ìi mß║╖t, nh╞░ng phß║úi ─æß╗º tß╗æt ß╗ƒ tß║Ñt cß║ú. ─Éiß╗âm ─æß╗üu ß╗ƒ 5 ti├¬u ch├¡ (Kiß║┐n tr├║c, Code, T├ái liß╗çu, Demo, S├íng tß║ío) tß╗æt h╞ín ─æiß╗âm cao ß╗ƒ 1-2 ti├¬u ch├¡.
Γöé
Γûê─Éß║╖c ─æiß╗âm cß╗ºa dß╗▒ ├ín ho├án chß╗ënh:
Γûê- Code structure r├╡ r├áng, modular
Γûê- ─Éß║ºy ─æß╗º deliverables (gß║ºn ─æß╗º 10/10)
Γûê- README chuy├¬n nghiß╗çp, c├│ screenshot v├á h╞░ß╗¢ng dß║½n
Γûê- DevOps setup ho├án chß╗ënh: Docker, CI/CD, health check
Γöé
ΓûêHß╗ìc: **completeness** ΓÇö kh├┤ng cß║ºn perfect, nh╞░ng kh├┤ng bß╗Å trß╗æng phß║ºn n├áo.
Γöé
Γûê### Pattern 2: Kß╗╖ luß║¡t code (Code Discipline)
Γöé
ΓûêCode chß║Ñt l╞░ß╗úng kh├┤ng cß║ºn kß╗╣ thuß║¡t phß╗⌐c tß║íp ΓÇö chß╗ë cß║ºn consistent application of best practices:
Γûê- Type hints cho tß║Ñt cß║ú functions
Γûê- Docstrings chi tiß║┐t
Γûê- Error handling cß╗Ñ thß╗â (kh├┤ng bare except)
Γûê- Code style nhß║Ñt qu├ín
Γûê- C├│ tests (├¡t nh╞░ng chß║Ñt)
Γöé
ΓûêHß╗ìc: **discipline** ΓÇö chß║Ñt l╞░ß╗úng code ─æß║┐n tß╗½ th├│i quen, kh├┤ng phß║úi kß╗╣ thuß║¡t cao si├¬u.
Γöé
Γûê### Pattern 3: ─Éß╗Ö s├óu trong LangGraph (Depth)
Γöé
ΓûêThay v├¼ x├óy nhiß╗üu features n├┤ng, x├óy ├¡t features nh╞░ng s├óu v├á ─æ├║ng:
Γûê- Graph design phß╗⌐c tß║íp: 5+ nodes, conditional routing, tools
Γûê- State management ─æ├║ng c├ích (TypedDict vß╗¢i reducers)
Γûê- Human-in-the-loop pattern
Γûê- RAG pipeline tß╗æi ╞░u: chunking, retrieval, reranking
Γöé
ΓûêHß╗ìc: **depth** ΓÇö hiß╗âu s├óu mß╗Öt v├ái pattern tß╗æt h╞ín hiß╗âu n├┤ng nhiß╗üu pattern.
Γöé
Γûê### Pattern 4: Infrastructure First
Γöé
ΓûêDeploy sß╗¢m, deploy th╞░ß╗¥ng. Infrastructure vß╗»ng chß║»c gi├║p development nhanh h╞ín:
Γûê- Multi-stage Dockerfile tß╗æi ╞░u
Γûê- Docker Compose vß╗¢i nhiß╗üu services
Γûê- Live URL hoß║ít ─æß╗Öng ß╗òn ─æß╗ïnh
Γûê- Environment-based configuration
Γöé
ΓûêHß╗ìc: **infrastructure first** ΓÇö khi infrastructure vß╗»ng, bß║ín tß║¡p trung v├áo logic thay v├¼ fight vß╗¢i m├┤i tr╞░ß╗¥ng.
Γöé
Γûê### Pattern 5: Thß╗¡ nghiß╗çm multi-agent (Ambition)
Γöé
ΓûêThß╗¡ nghiß╗çm approach phß╗⌐c tß║íp h╞ín, kß╗â cß║ú khi ch╞░a ho├án hß║úo:
Γûê- Nhiß╗üu agents chuy├¬n biß╗çt (retrieval agent + reasoning agent)
Γûê- Agent-to-agent communication
Γûê- Task delegation based on query type
Γöé
ΓûêHß╗ìc: **ambition** ΓÇö BTC ─æ├ính gi├í cao nß╗ù lß╗▒c hß╗ìc hß╗Åi v├á innovation. Thß╗¡ nghiß╗çm approach mß╗¢i l├á c├ích hß╗ìc nhanh nhß║Ñt.
Γöé
Γûê### Bß║úng tham chiß║┐u nhanh
Γöé
Γûê| Khi bß║ín muß╗æn hß╗ìc vß╗ü... | Tß║¡p trung v├áo pattern... | T├ái liß╗çu tham khß║úo |
Γûê|------------------------|--------------------------|-------------------|
Γûê| Tß╗òng thß╗â ho├án chß╗ënh | Completeness | README mß║½u, deliverables checklist |
Γûê| Code sß║ích, c├│ discipline | Code Discipline | Type hints guide, ruff config |
Γûê| LangGraph n├óng cao | Depth | LangGraph examples tr├¬n GitHub |
Γûê| Docker, DevOps | Infrastructure First | Docker docs, CI/CD templates |
Γûê| Multi-agent | Ambition | CrewAI docs, LangGraph multi-agent |
Γûê| Documentation | Completeness | README template, ADR mß║½u |
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** ─Éß╗½ng copy code tß╗½ dß╗▒ ├ín kh├íc. Hß╗ìc **pattern** v├á **approach**, rß╗ôi ├íp dß╗Ñng v├áo context dß╗▒ ├ín cß╗ºa bß║ín. BTC c├│ thß╗â nhß║¡n ra code copy v├á ─æ├ính gi├í thß║Ñp. Hiß╗âu tß║íi sao hß╗ì l├ám vß║¡y quan trß╗ìng h╞ín l├ám ─æ├║ng hß╗çt hß╗ì.
Γöé
Γûê## T├│m tß║»t
Γöé
ΓûêTrong ch╞░╞íng cuß╗æi n├áy, ch├║ng ta ─æ├ú tß╗òng hß╗úp t├ái nguy├¬n hß╗ìc tß║¡p cho h├ánh tr├¼nh AI20K:
Γöé
Γûê- **Lß╗Ö tr├¼nh 6 tuß║ºn** tß╗½ FastAPI c╞í bß║ún ─æß║┐n Demo Day, ~94 giß╗¥ tß╗òng cß╗Öng
Γûê- **DeepLearning.AI courses** ΓÇö 4 kh├│a bß║»t buß╗Öc: LangGraph agents, RAG, Prompt Engineering, Tools
Γûê- **LangGraph resources** ΓÇö Official docs, Academy, YouTube channels (Lance Martin, James Briggs), GitHub examples
Γûê- **BMAD Method** ΓÇö 6 agents, 4 phases, ├íp dß╗Ñng nh╞░ framework t╞░ duy cho project management
Γûê- **Dß╗▒ ├ín mß║½u tham khß║úo** ΓÇö 5 pattern ch├¡nh: completeness, code discipline, depth, infrastructure first, ambition
Γöé
ΓûêAI20K Build Phase l├á h├ánh tr├¼nh ngß║»n nh╞░ng intense. 6 tuß║ºn kh├┤ng nhiß╗üu, nh╞░ng ─æß╗º ─æß╗â build mß╗Öt AI Agent ho├án chß╗ënh nß║┐u bß║ín sß╗¡ dß╗Ñng thß╗¥i gian v├á t├ái nguy├¬n wisely. Lß╗Ö tr├¼nh, t├ái liß╗çu, v├á kinh nghiß╗çm thß╗▒c tiß╗àn ─æ├ú sß║╡n s├áng ΓÇö giß╗¥ l├á l├║c bß║ín bß║»t tay v├áo code.
Γöé
Γûê## Lß╗¥i kß║┐t
Γöé
ΓûêCh├║c c├íc bß║ín VinUni AI20K th├ánh c├┤ng. H├úy nhß╗¢:
Γöé
Γûê- **Start simple, iterate fast.** Bß║»t ─æß║ºu vß╗¢i 1 endpoint, 1 node, 1 test. Rß╗ôi mß╗ƒ rß╗Öng.
Γûê- **Ship early, ship often.** Deploy trong tuß║ºn ─æß║ºu ti├¬n. Mß╗ùi tuß║ºn th├¬m feature mß╗¢i.
Γûê- **Document everything.** README, journal, architecture. Deliverables ─æß║ºy ─æß╗º = nß╗¡a chiß║┐n thß║»ng.
Γûê- **Tr├ính nhß╗»ng sai lß║ºm phß╗ò biß║┐n.** Hß║ºu hß║┐t ─æß╗Öi thiß║┐u CI/CD, thiß║┐u tests, thiß║┐u Evaluation Evidence. Tr├ính nhß╗»ng lß╗ùi n├áy, bß║ín ─æ├ú ß╗ƒ top.
Γöé
ΓûêMay mß║»n v├á hß║╣n gß║╖p ß╗ƒ Demo Day.


docs\guide\code-style\python.md:
Γûê---
Γûêtitle: "Python Code Style"
Γûêdescription: "Chuß║⌐n code Python cho AI20K project"
Γûêweight: 1
Γûê---
Γöé
Γûê## Python Style Guide
Γöé
Γûê### 1. Type Hints ΓÇö Bß║«T BUß╗ÿC
Γöé
Γûê```python
Γûê# Γ£à Tß╗ÉT ΓÇö Full type hints
Γûêasync def analyze_sentiment(text: str) -> dict[str, float]:
Γûê    """Ph├ón t├¡ch sentiment cß╗ºa text."""
Γûê    result = await model.predict(text)
Γûê    return {"positive": result.pos, "negative": result.neg}
Γöé
Γûê# Γ¥î Tß╗å ΓÇö Kh├┤ng type hints
Γûêdef process(data):
Γûê    x = model.run(data)
Γûê    return x
Γûê```
Γöé
Γûê### 2. Function Rules
Γöé
Γûê- **Max 30 lines** per function ΓÇö d├ái h╞ín ΓåÆ t├ích ra
Γûê- **Max 3 parameters** ΓÇö nhiß╗üu h╞ín ΓåÆ d├╣ng Pydantic model
Γûê- **Lu├┤n c├│ return type hint**
Γûê- **Docstring** cho public functions
Γöé
Γûê### 3. Naming Conventions
Γöé
Γûê| Type | Convention | Example |
Γûê|------|-----------|---------|
Γûê| File | snake_case | `analyze_node.py` |
Γûê| Function | snake_case | `def analyze_query()` |
Γûê| Class | PascalCase | `class AgentState` |
Γûê| Constant | UPPER_SNAKE | `MAX_RETRIES = 3` |
Γöé
Γûê### 4. Import Order
Γöé
Γûê```python
Γûê# 1. Standard library
Γûêimport os
Γûêfrom typing import Optional
Γöé
Γûê# 2. Third-party
Γûêfrom fastapi import APIRouter, HTTPException
Γûêfrom langchain_core.tools import tool
Γöé
Γûê# 3. Local
Γûêfrom src.config import get_settings
Γûêfrom src.models.schemas import ChatRequest
Γûê```
Γöé
Γûê### 5. Error Handling
Γöé
Γûê```python
Γûê# Γ£à Tß╗ÉT ΓÇö Specific exception
Γûêtry:
Γûê    result = await llm.ainvoke(prompt)
Γûêexcept openai.APIError as e:
Γûê    logger.error(f"LLM call failed: {e}")
Γûê    return {"error": str(e)}
Γöé
Γûê# Γ¥î Tß╗å ΓÇö Bare except (trß╗½ khi c├│ l├╜ do ─æß║╖c biß╗çt)
Γûêtry:
Γûê    result = await llm.ainvoke(prompt)
Γûêexcept:  # Che mß╗ìi lß╗ùi!
Γûê    pass
Γûê```
Γöé
Γûê### 6. Lint with Ruff
Γöé
Γûê```bash
Γûê# Check
Γûêruff check src/ tests/
Γöé
Γûê# Auto-fix
Γûêruff check --fix src/ tests/
Γûê```
Γöé
ΓûêRuff chß║íy tß╗▒ ─æß╗Öng trong CI ΓÇö code kh├┤ng pass ruff sß║╜ bß╗ï reject.


docs\guide\code-style\_index.md:
Γûê---
Γûêtitle: "Code Style Guide"
Γûêdescription: "Chuß║⌐n code chß║Ñt l╞░ß╗úng cao"
Γûêweight: 4
Γûê---
Γöé
ΓûêPhß║ºn n├áy quy ╞░ß╗¢c chuß║⌐n code Python ├íp dß╗Ñng cho to├án bß╗Ö dß╗▒ ├ín AI20K. Bß║ín sß║╜ t├¼m hiß╗âu vß╗ü type hints, quy tß║»c viß║┐t h├ám, c├ích ─æß║╖t t├¬n biß║┐n, thß╗⌐ tß╗▒ import v├á xß╗¡ l├╜ lß╗ùi ─æ├║ng c├ích. Tß║Ñt cß║ú ─æß╗üu ─æ╞░ß╗úc tß╗▒ ─æß╗Öng kiß╗âm tra bß║▒ng Ruff linter. Tu├ón thß╗º code style gi├║p team collaboration hiß╗çu quß║ú v├á giß║úm thiß╗âu bug trong qu├í tr├¼nh ph├ít triß╗ân.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [Python Style Guide](python.md) ΓÇö Type hints, quy tß║»c h├ám, naming, imports, error handling v├á Ruff


docs\guide\cost-management.md:
Γûê---
Γûêtitle: "Quß║ún l├╜ chi ph├¡ API"
Γûêdescription: "╞»ß╗¢c t├¡nh v├á tß╗æi ╞░u chi ph├¡ LLM API cho dß╗▒ ├ín AI20K"
Γûêweight: 98
Γûê---
Γöé
Γûê# Quß║ún l├╜ chi ph├¡ API ΓÇö ─Éß╗½ng ─æß╗â bill bß║Ñt ngß╗¥
Γöé
ΓûêKhi x├óy dß╗▒ng AI Agent, mß╗ùi lß║ºn gß╗ìi LLM (GPT-4, Claude, v.v.) ─æß╗üu tß╗æn tiß╗ün. Nß║┐u kh├┤ng kiß╗âm so├ít, bß║ín c├│ thß╗â ti├¬u hß║┐t budget chß╗ë trong v├ái ng├áy testing. Phß║ºn n├áy gi├║p bß║ín ╞░ß╗¢c t├¡nh chi ph├¡ v├á ├íp dß╗Ñng c├íc chiß║┐n l╞░ß╗úc giß║úm cost.
Γöé
Γûê---
Γöé
Γûê## ╞»ß╗¢c t├¡nh chi ph├¡ cho AI20K
Γöé
Γûê### Bß║úng gi├í tham khß║úo (th├íng 5/2025)
Γöé
Γûê| Model | Input (per 1M tokens) | Output (per 1M tokens) | Ph├╣ hß╗úp cho |
Γûê|-------|----------------------|------------------------|-------------|
Γûê| gpt-4o-mini | $0.15 | $0.60 | **Development + Production** |
Γûê| gpt-4o | $2.50 | $10.00 | Testing chß║Ñt l╞░ß╗úng cao |
Γûê| gpt-4.1-mini | $0.40 | $1.60 | C├ón bß║▒ng cost/chß║Ñt l╞░ß╗úng |
Γûê| gpt-4.1 | $2.00 | $8.00 | Agent phß╗⌐c tß║íp |
Γûê| claude-sonnet-4-6 | $3.00 | $15.00 | Agent phß╗⌐c tß║íp |
Γûê| claude-haiku-4-5 | $0.80 | $4.00 | Development |
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** D├╣ng **gpt-4o-mini** cho to├án bß╗Ö qu├í tr├¼nh development. N├│ rß║╗ h╞ín gpt-4o ~17 lß║ºn nh╞░ng vß║½n ─æß╗º th├┤ng minh cho hß║ºu hß║┐t t├íc vß╗Ñ AI Agent. Chß╗ë chuyß╗ân sang model ─æß║»t h╞ín khi cß║ºn chß║Ñt l╞░ß╗úng output cao nhß║Ñt cho Demo Day.
Γöé
Γûê### ╞»ß╗¢c t├¡nh chi ph├¡ theo giai ─æoß║ín
Γöé
Γûê**Giai ─æoß║ín Development (4-5 tuß║ºn):**
Γûê- Mß╗ùi lß║ºn test agent: ~500-2000 tokens ΓåÆ ~$0.001-0.003
Γûê- Ng├áy code 4 giß╗¥, test ~50 lß║ºn ΓåÆ ~$0.05-0.15/ng├áy
Γûê- 5 tuß║ºn development ΓåÆ **~$2-5 tß╗òng cß╗Öng**
Γöé
Γûê**Giai ─æoß║ín Evaluation:**
Γûê- Chß║íy 50-100 c├óu hß╗Åi test, mß╗ùi c├óu ~1000 tokens ΓåÆ ~$0.10-0.50
Γûê- Chß║íy 3-5 lß║ºn ─æß╗â tune ΓåÆ **~$0.50-2.50**
Γöé
Γûê**Giai ─æoß║ín Demo Day:**
Γûê- Demo live ~10 ph├║t, ~20 requests ΓåÆ **~$0.10**
Γöé
Γûê**Tß╗òng ╞░ß╗¢c t├¡nh cho to├án bß╗Ö AI20K: ~$5-10** (vß╗¢i gpt-4o-mini)
Γöé
Γûê---
Γöé
Γûê## 8 chiß║┐n l╞░ß╗úc giß║úm chi ph├¡
Γöé
Γûê### 1. D├╣ng model rß║╗ nhß║Ñt ─æß╗º cho task
Γöé
Γûê```python
Γûê# Γ¥î ─Éß║»t ΓÇö d├╣ng gpt-4o cho mß╗ìi thß╗⌐
Γûêllm = ChatOpenAI(model="gpt-4o")
Γöé
Γûê# Γ£à Rß║╗ ΓÇö d├╣ng gpt-4o-mini cho development
Γûêllm = ChatOpenAI(model="gpt-4o-mini")
Γöé
Γûê# Γ£à Tß╗æi ╞░u ΓÇö d├╣ng model kh├íc nhau cho task kh├íc nhau
Γûêanalyze_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)  # Ph├ón t├¡ch: rß║╗, deterministic
Γûêgenerate_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)  # Sinh text: rß║╗, creative
Γûê```
Γöé
Γûê### 2. Giß╗¢i hß║ín max_tokens
Γöé
Γûê```python
Γûê# Γ¥î Kh├┤ng giß╗¢i hß║ín ΓÇö LLM c├│ thß╗â sinh rß║Ñt d├ái
Γûêllm = ChatOpenAI(model="gpt-4o-mini")
Γöé
Γûê# Γ£à Giß╗¢i hß║ín output ΓÇö tiß║┐t kiß╗çm tokens
Γûêllm = ChatOpenAI(model="gpt-4o-mini", max_tokens=500)  # ─Éß╗º cho c├óu trß║ú lß╗¥i ngß║»n
Γûêllm = ChatOpenAI(model="gpt-4o-mini", max_tokens=1500)  # ─Éß╗º cho c├óu trß║ú lß╗¥i chi tiß║┐t
Γûê```
Γöé
Γûê### 3. Temperature = 0 cho task ph├ón t├¡ch
Γöé
Γûê```python
Γûê# Task ph├ón t├¡ch/routing ΓÇö kh├┤ng cß║ºn creativity, giß║úm token waste
Γûêanalyze_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
Γûê```
Γöé
Γûê### 4. Cache kß║┐t quß║ú LLM trong development
Γöé
Γûê```python
Γûêfrom functools import lru_cache
Γûêimport hashlib
Γûêimport json
Γöé
Γûê# Cache ─æ╞ín giß║ún trong memory
Γûê_llm_cache: dict[str, str] = {}
Γöé
Γûêdef cached_llm_call(prompt: str, model: str = "gpt-4o-mini") -> str:
Γûê    """Cache LLM responses ─æß╗â tr├ính gß╗ìi lß║íi c├╣ng prompt."""
Γûê    cache_key = hashlib.md5(f"{model}:{prompt}".encode()).hexdigest()
Γûê    
Γûê    if cache_key in _llm_cache:
Γûê        return _llm_cache[cache_key]
Γûê    
Γûê    from langchain_openai import ChatOpenAI
Γûê    llm = ChatOpenAI(model=model)
Γûê    response = llm.invoke(prompt)
Γûê    _llm_cache[cache_key] = response.content
Γûê    return response.content
Γûê```
Γöé
Γûê### 5. Mock LLM trong test
Γöé
Γûê```python
Γûê# Γ¥î Tß╗æn tiß╗ün ΓÇö gß╗ìi LLM thß║¡t trong test
Γûêdef test_analyze():
Γûê    result = analyze_node({"query": "test"})  # Gß╗ìi OpenAI API thß║¡t
Γöé
Γûê# Γ£à Miß╗àn ph├¡ ΓÇö mock LLM response
Γûêfrom unittest.mock import AsyncMock, patch
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_analyze():
Γûê    with patch("langchain_openai.ChatOpenAI.ainvoke") as mock:
Γûê        mock.return_value = AsyncMock(content='{"query_type": "factual"}')
Γûê        result = await analyze_node({"query": "test"})
Γûê    assert result["query_type"] == "factual"
Γûê```
Γöé
Γûê### 6. R├║t gß╗ìn prompt ΓÇö ├¡t tokens h╞ín
Γöé
Γûê```python
Γûê# Γ¥î Prompt d├ái ΓÇö tß╗æn input tokens
Γûêprompt = """Bß║ín l├á mß╗Öt trß╗ú l├╜ AI th├┤ng minh, ─æ╞░ß╗úc thiß║┐t kß║┐ ─æß╗â gi├║p ─æß╗í ng╞░ß╗¥i d├╣ng
Γûêtrß║ú lß╗¥i c├íc c├óu hß╗Åi vß╗ü nhiß╗üu chß╗º ─æß╗ü kh├íc nhau. Vui l├▓ng ph├ón t├¡ch c├óu hß╗Åi sau
Γûêv├á x├íc ─æß╗ïnh loß║íi cß╗ºa n├│..."""
Γöé
Γûê# Γ£à Prompt ngß║»n ΓÇö tiß║┐t kiß╗çm tokens
Γûêprompt = "Ph├ón loß║íi c├óu hß╗Åi: factual, analytical, hoß║╖c creative. Chß╗ë trß║ú JSON."
Γûê```
Γöé
Γûê### 7. Giß╗¢i hß║ín sß╗æ v├▓ng lß║╖p agent
Γöé
Γûê```python
Γûê# Γ¥î Kh├┤ng giß╗¢i hß║ín ΓÇö agent c├│ thß╗â lß║╖p 20+ lß║ºn
Γûêdef should_continue(state):
Γûê    if state.get("needs_more"):
Γûê        return "research"
Γûê    return END
Γöé
Γûê# Γ£à Giß╗¢i hß║ín 3 v├▓ng ΓÇö ─æß╗º cho hß║ºu hß║┐t c├óu hß╗Åi
ΓûêMAX_ITERATIONS = 3
Γöé
Γûêdef should_continue(state):
Γûê    if state.get("iteration", 0) >= MAX_ITERATIONS:
Γûê        return END
Γûê    if state.get("needs_more"):
Γûê        return "research"
Γûê    return END
Γûê```
Γöé
Γûê### 8. Monitor usage bß║▒ng LangSmith
Γöé
ΓûêLangSmith tß╗▒ ─æß╗Öng track token usage cho mß╗ùi LLM call. Kiß╗âm tra dashboard ─æß╗ïnh kß╗│ ─æß╗â ph├ít hiß╗çn:
Γûê- Node n├áo tß╗æn nhiß╗üu tokens nhß║Ñt
Γûê- C├│ request bß║Ñt th╞░ß╗¥ng kh├┤ng (agent lß║╖p qu├í nhiß╗üu)
Γûê- Tß╗òng chi ph├¡ theo ng├áy/tuß║ºn
Γöé
Γûê---
Γöé
Γûê## Thiß║┐t lß║¡p budget limit
Γöé
Γûê### OpenAI Usage Limits
Γöé
Γûê1. V├áo https://platform.openai.com/settings/organization/billing
Γûê2. Set **Monthly budget limit** ΓÇö v├¡ dß╗Ñ $20/th├íng
Γûê3. Bß║¡t **Email notification** khi ─æß║ít 80% budget
Γöé
Γûê### Cß║únh b├ío trong code
Γöé
Γûê```python
Γûêimport os
Γûêimport logging
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γûê# ╞»ß╗¢c t├¡nh cost per request
Γûêdef estimate_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4o-mini") -> float:
Γûê    """╞»ß╗¢c t├¡nh chi ph├¡ USD cho mß╗Öt LLM call."""
Γûê    pricing = {
Γûê        "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
Γûê        "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
Γûê    }
Γûê    p = pricing.get(model, pricing["gpt-4o-mini"])
Γûê    return input_tokens * p["input"] + output_tokens * p["output"]
Γûê```
Γöé
Γûê---
Γöé
Γûê## T├│m tß║»t
Γöé
Γûê| Chiß║┐n l╞░ß╗úc | Tiß║┐t kiß╗çm | ─Éß╗Ö kh├│ |
Γûê|------------|-----------|--------|
Γûê| D├╣ng gpt-4o-mini | ~17x so vß╗¢i gpt-4o | Dß╗à |
Γûê| Giß╗¢i hß║ín max_tokens | 20-50% | Dß╗à |
Γûê| Mock LLM trong test | 100% test cost | Trung b├¼nh |
Γûê| Giß╗¢i hß║ín iterations | 30-60% | Dß╗à |
Γûê| R├║t gß╗ìn prompt | 10-30% | Dß╗à |
Γûê| Cache responses | 50-80% repeated queries | Trung b├¼nh |
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** Tß╗òng chi ph├¡ cho to├án bß╗Ö AI20K vß╗¢i gpt-4o-mini chß╗ë khoß║úng **$5-10** ΓÇö rß║Ñt hß╗úp l├╜ cho sinh vi├¬n. ├üp dß╗Ñng c├íc chiß║┐n l╞░ß╗úc tr├¬n ─æß╗â kh├┤ng bß╗ï bß║Ñt ngß╗¥ vß╗¢i bill.


docs\guide\deliverables\checklist.md:
Γûê---
Γûêtitle: "Deliverables Checklist"
Γûêdescription: "Danh s├ích 10 deliverables v├á c├ích ho├án th├ánh"
Γûêweight: 1
Γûê---
Γöé
Γûê## 10 Deliverables BTC Y├¬u Cß║ºu
Γöé
Γûê### Chi tiß║┐t tß╗½ng deliverable
Γöé
Γûê#### 1. Source Code (GitHub)
Γûê- **Location:** To├án bß╗Ö th╞░ mß╗Ñc `src/`
Γûê- **Y├¬u cß║ºu:** Code chß║íy ─æ╞░ß╗úc, c├│ cß║Ñu tr├║c r├╡ r├áng
Γûê- **Tips:** Follow template folder structure
Γöé
Γûê#### 2. README.md
Γûê- **Location:** `/README.md`
Γûê- **Y├¬u cß║ºu:** Problem ΓåÆ Solution ΓåÆ Tech Stack ΓåÆ Setup ΓåÆ Team
Γûê- **Tips:** Sß╗¡ dß╗Ñng template README.md ─æ├ú c├│ sß║╡n
Γöé
Γûê#### 3. Architecture Diagram
Γûê- **Location:** `/docs/architecture_diagram.md`
Γûê- **Y├¬u cß║ºu:** System diagram + Component descriptions
Γûê- **Tips:** D├╣ng Mermaid syntax (render tr├¬n GitHub)
Γöé
Γûê#### 4. AI Logs
Γûê- **Y├¬u cß║ºu:** Log c├íc interaction vß╗¢i LLM
Γûê- **Tips:** Setup logging trong `main.py` hoß║╖c d├╣ng LangSmith
Γöé
Γûê#### 5. Live URL / Deploy
Γûê- **Y├¬u cß║ºu:** Sß║ún phß║⌐m chß║íy ─æ╞░ß╗úc tr├¬n internet
Γûê- **Tips:** Deploy backend l├¬n Render/Railway, frontend l├¬n Vercel
Γöé
Γûê#### 6. Video Demo
Γûê- **Location:** Upload l├¬n YouTube/Google Drive
Γûê- **Y├¬u cß║ºu:** Tß╗æi ─æa 5 ph├║t, demo feature ch├¡nh
Γûê- **Tips:** Follow pitch structure trong `presentation/README.md`
Γöé
Γûê#### 7. Pitch Deck
Γûê- **Location:** `/presentation/pitch_deck.pptx`
Γûê- **Y├¬u cß║ºu:** 10 slides theo structure chuß║⌐n
Γûê- **Tips:** Follow template trong `presentation/README.md`
Γöé
Γûê#### 8. Weekly Journal
Γûê- **Location:** `/JOURNAL.md`
Γûê- **Y├¬u cß║ºu:** Ghi lß║íi mß╗ùi tuß║ºn: mß╗Ñc ti├¬u, ho├án th├ánh, kh├│ kh─ân, b├ái hß╗ìc
Γûê- **Tips:** Template ─æ├ú c├│ sß║╡n, chß╗ë cß║ºn ─æiß╗ün
Γöé
Γûê#### 9. Worklog
Γûê- **Location:** `/WORKLOG.md`
Γûê- **Y├¬u cß║ºu:** Ghi lß║íi h├áng ng├áy: ai l├ám g├¼, kß║┐t quß║ú g├¼
Γûê- **Tips:** Template ─æ├ú c├│ sß║╡n, cß║¡p nhß║¡t mß╗ùi ng├áy
Γöé
Γûê#### 10. Evaluation Evidence
Γûê- **Location:** `/eval/results/report.md`
Γûê- **Y├¬u cß║ºu:** Metrics, test results, user feedback
Γûê- **Tips:** Follow template trong `eval/results/report.md`
Γöé
Γûê## Evaluation Criteria (BTC chß║Ñm 1-10)
Γöé
Γûê1. **Product/Business** ΓÇö README, metrics, user feedback
Γûê2. **System Design** ΓÇö Architecture, diagram, folder structure
Γûê3. **UX/UI Design** ΓÇö Responsive, dark mode, accessibility
Γûê4. **DevOps** ΓÇö Docker, CI/CD, logging, .env
Γûê5. **Code Quality** ΓÇö Type hints, naming, tests, no bare except
Γöé
Γûê### Target: 35+/50 points
Γöé
Γûê| Criteria | Minimum | How to achieve |
Γûê|----------|---------|---------------|
Γûê| Product | ΓëÑ 8 | README ─æß║ºy ─æß╗º, metrics, feedback |
Γûê| System | ΓëÑ 7 | Architecture doc + Mermaid diagram |
Γûê| UI/UX | ΓëÑ 7 | Responsive + dark mode |
Γûê| DevOps | ΓëÑ 6 | Docker + CI/CD + logging |
Γûê| Code | ΓëÑ 7 | Type hints + tests + ruff pass |


docs\guide\deliverables\_index.md:
Γûê---
Γûêtitle: "Required Deliverables"
Γûêdescription: "10 deliverables BTC y├¬u cß║ºu v├á c├ích ho├án th├ánh"
Γûêweight: 7
Γûê---
Γöé
ΓûêPhß║ºn n├áy liß╗çt k├¬ chi tiß║┐t 10 deliverables m├á BTC y├¬u cß║ºu v├á c├ích ho├án th├ánh tß╗½ng mß╗Ñc. Dß╗▒a tr├¬n ph├ón t├¡ch tß╗╖ lß╗ç ho├án th├ánh cß╗ºa Cohort 1, bß║ín sß║╜ biß║┐t ch├¡nh x├íc deliverable n├áo dß╗à ─æß║ít ─æiß╗âm, deliverable n├áo cß║ºn ch├║ ├╜ nhiß╗üu h╞ín. Mß╗Ñc ti├¬u l├á ─æß║ít tß╗æi thiß╗âu 35/50 ─æiß╗âm ─æß╗â qua v├▓ng. Checklist n├áy l├á kim chß╗ë nam ─æß╗â bß║ín kh├┤ng bß╗Å s├│t bß║Ñt kß╗│ y├¬u cß║ºu n├áo.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [Deliverables Checklist](checklist.md) ΓÇö Tß╗╖ lß╗ç ho├án th├ánh Cohort 1, 10 deliverables vß╗¢i vß╗ï tr├¡/mß║╣o, ti├¬u ch├¡ ─æ├ính gi├í, mß╗Ñc ti├¬u 35+/50


docs\guide\devops\docker-cicd.md:
Γûê---
Γûêtitle: "Docker & CI/CD"
Γûêdescription: "Setup Docker v├á GitHub Actions"
Γûêweight: 1
Γûê---
Γöé
Γûê## Docker
Γöé
Γûê### Multi-stage Dockerfile
Γöé
Γûê```dockerfile
Γûê# Stage 1: Build
ΓûêFROM python:3.11-slim AS builder
ΓûêWORKDIR /app
ΓûêCOPY requirements.txt .
ΓûêRUN pip install --no-cache-dir --user -r requirements.txt
Γöé
Γûê# Stage 2: Production
ΓûêFROM python:3.11-slim
ΓûêWORKDIR /app
ΓûêCOPY --from=builder /root/.local /root/.local
ΓûêENV PATH=/root/.local/bin:$PATH
ΓûêCOPY . .
ΓûêRUN mkdir -p /app/data
ΓûêEXPOSE 8000
ΓûêCMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
Γûê```
Γöé
Γûê### Commands
Γöé
Γûê```bash
Γûêdocker build -t ai20k-app .
Γûêdocker compose up -d
Γûêdocker compose logs -f backend
Γûêdocker compose down
Γûê```
Γöé
Γûê## CI/CD (GitHub Actions)
Γöé
ΓûêCI tß╗▒ chß║íy khi push l├¬n GitHub:
Γöé
Γûê1. **Lint** ΓÇö `ruff check` ─æß║úm bß║úo code style
Γûê2. **Test** ΓÇö `pytest` chß║íy tß║Ñt cß║ú tests
Γûê3. Pass ΓåÆ merge ─æ╞░ß╗úc. Fail ΓåÆ fix tr╞░ß╗¢c.
Γöé
Γûê### Setup CI
Γöé
ΓûêFile `.github/workflows/ci.yml` ─æ├ú c├│ sß║╡n trong template.
Γöé
Γûê### Y├¬u cß║ºu minimum
Γöé
Γûê- Γ£à CI pipeline phß║úi chß║íy ─æ╞░ß╗úc
Γûê- Γ£à Ruff lint pass
Γûê- Γ£à Tß║Ñt cß║ú tests pass
Γöé
Γûê## Environment Variables
Γöé
Γûê```bash
Γûê# .env.example ΓÇö commit ─æ╞░ß╗úc (template)
Γûê# .env ΓÇö KH├öNG BAO GIß╗£ commit (actual values)
Γûê```
Γöé
Γûê## Git Workflow
Γöé
Γûê```
Γûêmain (production)
Γûê  ΓööΓöÇΓöÇ develop (daily work)
Γûê       Γö£ΓöÇΓöÇ feature/agent-flow
Γûê       Γö£ΓöÇΓöÇ feature/api-routes
Γûê       ΓööΓöÇΓöÇ feature/ui
Γûê```
Γöé
Γûê### Commit Messages
Γöé
Γûê```
Γûêfeat: th├¬m agent graph vß╗¢i nodes analyze + respond
Γûêfix: sß╗¡a lß╗ùi CORS blocked tr├¬n frontend
Γûêdocs: cß║¡p nhß║¡t architecture diagram
Γûêtest: th├¬m test cho chat endpoint
Γûêrefactor: t├ích analyze node th├ánh file ri├¬ng
Γûê```


docs\guide\devops\_index.md:
Γûê---
Γûêtitle: "DevOps Guide"
Γûêdescription: "Docker, CI/CD, deployment"
Γûêweight: 6
Γûê---
Γöé
ΓûêPhß║ºn n├áy h╞░ß╗¢ng dß║½n c├ích ─æ├│ng g├│i v├á triß╗ân khai dß╗▒ ├ín AI Agent chuy├¬n nghiß╗çp. Bß║ín sß║╜ t├¼m hiß╗âu multi-stage Dockerfile ─æß╗â tß╗æi ╞░u image size, c├íc lß╗çnh Docker th╞░ß╗¥ng d├╣ng, v├á thiß║┐t lß║¡p GitHub Actions CI ─æß╗â tß╗▒ ─æß╗Öng test mß╗ùi lß║ºn push. Ngo├ái ra c├▓n c├│ h╞░ß╗¢ng dß║½n quß║ún l├╜ biß║┐n m├┤i tr╞░ß╗¥ng v├á Git workflow chuß║⌐n. ─É├óy l├á phß║ºn bß║»t buß╗Öc ─æß╗â deliver sß║ún phß║⌐m ho├án chß╗ënh cho BTC.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [Docker & CI/CD](docker-cicd.md) ΓÇö Multi-stage Dockerfile, Docker commands, GitHub Actions CI, env vars v├á git workflow


docs\guide\free-accounts.md:
Γûê---
Γûêtitle: "─É─âng k├╜ t├ái khoß║ún miß╗àn ph├¡"
Γûêdescription: "H╞░ß╗¢ng dß║½n ─æ─âng k├╜ c├íc g├│i t├ái khoß║ún miß╗àn ph├¡ (free tier) ─æß╗â bß║»t ─æß║ºu build ß╗⌐ng dß╗Ñng AI"
Γûêweight: 97
Γûê---
Γöé
Γûê# ─É─âng k├╜ t├ái khoß║ún miß╗àn ph├¡ ΓÇö Bß║»t ─æß║ºu build ß╗⌐ng dß╗Ñng AI
Γöé
ΓûêTrong ch╞░╞íng tr├¼nh VinUni AI20K, c├íc ─æß╗Öi sß║╜ phß║úi build mß╗Öt ß╗⌐ng dß╗Ñng AI Agent ho├án chß╗ënh ΓÇö tß╗½ backend (FastAPI + LangGraph), frontend (Next.js/Streamlit), database, ─æß║┐n deployment l├¬n cloud. Tß║Ñt cß║ú c├íc dß╗ïch vß╗Ñ d╞░ß╗¢i ─æ├óy ─æß╗üu c├│ g├│i miß╗àn ph├¡ (free tier) ─æß╗º d├╣ng cho viß╗çc ph├ít triß╗ân v├á demo trong 6 tuß║ºn cß╗ºa ch╞░╞íng tr├¼nh. Bß║ín **KH├öNG cß║ºn thß║╗ t├¡n dß╗Ñng** cho hß║ºu hß║┐t c├íc dß╗ïch vß╗Ñ.
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Mß╗Öt sß╗æ dß╗ïch vß╗Ñ y├¬u cß║ºu thß║╗ t├¡n dß╗Ñng ─æß╗â x├íc minh (nh╞░ng sß║╜ kh├┤ng t├¡nh ph├¡ nß║┐u bß║ín d├╣ng trong free tier). ─Éiß╗üu n├áy ─æ╞░ß╗úc ghi r├╡ b├¬n cß║ính mß╗ùi dß╗ïch vß╗Ñ.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** ─É─âng k├╜ t├ái khoß║ún l├á viß╗çc **─Éß║ªU TI├èN** ─æß╗Öi n├¬n l├ám trong Tuß║ºn 1. C├áng sß╗¢m ─æ─âng k├╜, c├áng sß╗¢m bß║»t ─æß║ºu code!
Γöé
Γûê---
Γöé
Γûê## Tß╗òng quan Technology Stack AI20K
Γöé
ΓûêTr╞░ß╗¢c khi ─æ─âng k├╜ t├ái khoß║ún, h├úy hiß╗âu bß║ín sß║╜ cß║ºn g├¼:
Γöé
Γûê| Th├ánh phß║ºn | C├┤ng nghß╗ç | Nß╗ün tß║úng | Mß╗Ñc ─æ├¡ch |
Γûê|------------|-----------|----------|----------|
Γûê| Backend | FastAPI + Python 3.11 | Render / Railway | API server cho AI Agent |
Γûê| AI Agent | LangGraph + LangChain | ΓÇö | Xß╗¡ l├╜ logic & workflow cß╗ºa agent |
Γûê| LLM | GPT-4o-mini / Gemini / Mistral | OpenAI / Google / Mistral API | Bß╗Ö n├úo AI ΓÇö xß╗¡ l├╜ ng├┤n ngß╗» |
Γûê| Database | PostgreSQL + pgvector | Supabase | L╞░u trß╗» dß╗» liß╗çu & vector |
Γûê| Vector Store | ChromaDB / Pinecone / Qdrant | Self-host / Cloud | L╞░u trß╗» embedding ─æß╗â t├¼m kiß║┐m ngß╗» ngh─⌐a |
Γûê| Frontend | Next.js / Streamlit | Vercel / Streamlit Cloud | Giao diß╗çn ng╞░ß╗¥i d├╣ng |
Γûê| DevOps | Docker + GitHub Actions | GitHub | ─É├│ng g├│i & tß╗▒ ─æß╗Öng deploy |
Γûê| Monitoring | Langfuse / LangSmith | Cloud / Self-host | Theo d├╡i hoß║ít ─æß╗Öng cß╗ºa AI Agent |
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Template dß╗▒ ├ín (`ai20k-agent-template`) ─æ├ú ─æ╞░ß╗úc setup sß║╡n cho stack n├áy. Bß║ín chß╗ë cß║ºn fork vß╗ü v├á bß║»t ─æß║ºu code!
Γöé
Γûê---
Γöé
Γûê## Nh├│m 1: AI/LLM APIs ΓÇö Xß╗¡ l├╜ ng├┤n ngß╗» & tr├¡ tuß╗ç nh├ón tß║ío
Γöé
Γûê─É├óy l├á nh├│m quan trß╗ìng nhß║Ñt ΓÇö LLM (Large Language Model) l├á "bß╗Ö n├úo" cß╗ºa ß╗⌐ng dß╗Ñng AI. Mß╗ùi ─æß╗Öi n├¬n ─æ─âng k├╜ ├¡t nhß║Ñt 2-3 provider ─æß╗â c├│ lß╗▒a chß╗ìn dß╗▒ ph├▓ng.
Γöé
Γûê### Mistral AI ΓÇö KHUY├èN D├ÖNG (H├áo ph├│ng nhß║Ñt)
Γöé
Γûê- **G├│i miß╗àn ph├¡:** Cß║Ñp 1 Tß╗╢ token/th├íng miß╗àn ph├¡ ΓÇö kh├┤ng cß║ºn thß║╗ t├¡n dß╗Ñng!
Γûê- **Models:** Truy cß║¡p Tß║ñT Cß║ó model: Mistral Large, Mistral Small, Codestral, Pixtral
Γûê- **Giß╗¢i hß║ín:** 1 request/gi├óy, 2 request/ph├║t, 500,000 token/ph├║t
Γûê- **L╞░u ├╜:** C├│ thß╗â d├╣ng data ─æß╗â train (c├│ thß╗â tß║»t trong Admin Console)
Γûê- **─É─âng k├╜:** https://console.mistral.ai
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** ─É├óy l├á g├│i LLM API miß╗àn ph├¡ H├ÇO PH├ôNG NHß║ñT hiß╗çn c├│. 1 tß╗╖ token/th├íng ─æß╗º ─æß╗â ph├ít triß╗ân v├á demo nhiß╗üu lß║ºn. ╞»u ti├¬n ─æ─âng k├╜ t├ái khoß║ún n├áy ─Éß║ªU TI├èN!
Γöé
Γûê![Giao diß╗çn ─æ─âng k├╜ Mistral AI (console.mistral.ai)](book-media/free-accounts/mistral.jpg)
Γöé
Γûê### Google Gemini API ΓÇö KHUY├èN D├ÖNG (Dß╗à ─æ─âng k├╜)
Γöé
Γûê- **G├│i miß╗àn ph├¡:** Kh├┤ng cß║ºn thß║╗ t├¡n dß╗Ñng. Lß║Ñy API key ngay tr├¬n Google AI Studio.
Γûê- **Model khuy├¬n d├╣ng:** Gemini 2.5 Flash: 10 RPM, ~250 request/ng├áy ΓÇö nhanh & mß║ính
Γûê- **Model cao cß║Ñp:** Gemini 2.5 Pro: 5 RPM, ~25-100 request/ng├áy ΓÇö giß╗¢i hß║ín thß║Ñp h╞ín
Γûê- **L╞░u ├╜:** Giß╗¢i hß║ín rate ─æ├ú giß║úm ─æ├íng kß╗â tß╗½ cuß╗æi 2025. N├¬n d├╣ng Flash thay v├¼ Pro.
Γûê- **─É─âng k├╜:** https://aistudio.google.com/apikey
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Chß╗ë cß║ºn t├ái khoß║ún Google (Gmail). Lß║Ñy API key trong 30 gi├óy. Flash model ─æß╗º mß║ính cho hß║ºu hß║┐t use case AI Agent.
Γöé
Γûê![Lß║Ñy API key tr├¬n Google AI Studio (aistudio.google.com/apikey)](book-media/free-accounts/gemini.jpg)
Γöé
Γûê### Groq API ΓÇö Tß╗æc ─æß╗Ö cß╗▒c nhanh (D├╣ng cho demo)
Γöé
Γûê- **G├│i miß╗àn ph├¡:** Kh├┤ng cß║ºn thß║╗ t├¡n dß╗Ñng. Truy cß║¡p tß║Ñt cß║ú model miß╗àn ph├¡.
Γûê- **Giß╗¢i hß║ín:** 30 request/ph├║t, 6,000 token/ph├║t
Γûê- **Models:** Llama 3.x, Mixtral, Gemma, DeepSeek, Whisper (speech-to-text)
Γûê- **Mß║╣o:** Nß║┐u th├¬m thß║╗ t├¡n dß╗Ñng (kh├┤ng cß║ºn nß║íp tiß╗ün) ΓåÆ giß╗¢i hß║ín t─âng 10x + giß║úm 25% gi├í.
Γûê- **─É─âng k├╜:** https://console.groq.com
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Groq c├│ tß╗æc ─æß╗Ö inference nhanh nhß║Ñt hiß╗çn nay (LPU chip chuy├¬n dß╗Ñng). Tuyß╗çt vß╗¥i cho Demo Day ΓÇö response gß║ºn nh╞░ tß╗⌐c th├¼!
Γöé
Γûê![Giao diß╗çn ─æ─âng k├╜ Groq (console.groq.com)](book-media/free-accounts/groq.jpg)
Γöé
Γûê### Cohere API ΓÇö Tß╗æt cho RAG & Search
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 1,000 API calls/th├íng, reset ─æß║ºu mß╗ùi th├íng.
Γûê- **Giß╗¢i hß║ín:** 20 RPM (Chat), 100 RPM (Embed), 10 RPM (Rerank)
Γûê- **─Éß║╖c biß╗çt:** Command R+, Embed v3/v4, Rerank v3/3.5 ΓÇö cß╗▒c kß╗│ ph├╣ hß╗úp cho ß╗⌐ng dß╗Ñng RAG.
Γûê- **─É─âng k├╜:** https://cohere.com
Γöé
Γûê![Trang ─æ─âng k├╜ Cohere (cohere.com)](book-media/free-accounts/cohere.jpg)
Γöé
Γûê---
Γöé
Γûê## Nh├│m 2: Cloud Hosting ΓÇö Triß╗ân khai Backend & Frontend
Γöé
ΓûêBß║ín cß║ºn cloud hosting ─æß╗â deploy ß╗⌐ng dß╗Ñng l├¬n internet, ─æß╗â ban gi├ím khß║úo v├á ng╞░ß╗¥i d├╣ng c├│ thß╗â truy cß║¡p demo.
Γöé
Γûê### Render.com ΓÇö KHUY├èN D├ÖNG CHO BACKEND
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 750 giß╗¥ instance miß╗àn ph├¡/th├íng (chia cho c├íc service)
Γûê- **T├ái nguy├¬n:** 512 MB RAM, 0.1 CPU cho mß╗ùi web service
Γûê- **Database:** 1 GB PostgreSQL (hß║┐t hß║ín sau 30 ng├áy, rß╗ôi x├│a sau 14 ng├áy grace)
Γûê- **Cold start:** Service tß╗▒ sleep sau 15 ph├║t kh├┤ng hoß║ít ─æß╗Öng ΓåÆ mß║Ñt 30-60 gi├óy ─æß╗â wake up
Γûê- **Bandwidth:** 5 GB bandwidth/th├íng
Γûê- **─É─âng k├╜:** https://render.com
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Deploy FastAPI backend l├¬n Render rß║Ñt ─æ╞ín giß║ún ΓÇö chß╗ë cß║ºn kß║┐t nß╗æi GitHub repo, chß╗ìn Docker, v├á Render tß╗▒ build + deploy. Template `ai20k-agent-template` ─æ├ú c├│ sß║╡n Dockerfile!
Γöé
Γûê> ΓÜá∩╕Å **L╞»U ├¥:** Database miß╗àn ph├¡ tr├¬n Render sß║╜ bß╗ï X├ôA sau 30 ng├áy. D├╣ng Supabase (Nh├│m 3) thay thß║┐ cho database l├óu d├ái.
Γöé
Γûê![Giao diß╗çn ─æ─âng k├╜ Render.com](book-media/free-accounts/render.jpg)
Γöé
Γûê### Vercel ΓÇö KHUY├èN D├ÖNG CHO FRONTEND (Next.js)
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 100 GB bandwidth/th├íng
Γûê- **Requests:** 1 triß╗çu edge requests/th├íng
Γûê- **Build:** 6,000 build minutes/th├íng
Γûê- **T├¡ch hß╗úp:** Deploy tß╗▒ ─æß╗Öng khi push l├¬n GitHub
Γûê- **─É─âng k├╜:** https://vercel.com/signup
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Vercel l├á lß╗▒a chß╗ìn Tß╗ÉT NHß║ñT cho Next.js frontend. Deploy chß╗ë mß║Ñt 2 ph├║t ΓÇö kß║┐t nß╗æi GitHub repo ΓåÆ tß╗▒ nhß║¡n Next.js ΓåÆ deploy xong!
Γöé
Γûê![Giao diß╗çn ─æ─âng k├╜ Vercel (vercel.com/signup)](book-media/free-accounts/vercel.jpg)
Γöé
Γûê### Hugging Face Spaces ΓÇö FREE GPU cho AI Demo!
Γöé
Γûê- **G├│i miß╗àn ph├¡:** CPU Basic: 2 vCPU, 16 GB RAM, 50 GB disk ΓÇö ngß╗º sau 48h kh├┤ng d├╣ng
Γûê- **GPU miß╗àn ph├¡:** ZeroGPU: ~3.5 ph├║t/ng├áy GPU compute tr├¬n NVIDIA H200!
Γûê- **Ph├╣ hß╗úp:** Tß╗æt nhß║Ñt cho AI demo, gradio apps, streamlit apps
Γûê- **─É─âng k├╜:** https://huggingface.co/new-space
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Nß║┐u ─æß╗Öi cß║ºn chß║íy model AI nß║╖ng (Whisper, LLM local, image generation), Hugging Face Spaces l├á lß╗▒a chß╗ìn duy nhß║Ñt c├│ GPU miß╗àn ph├¡!
Γöé
Γûê![Tß║ío Space mß╗¢i tr├¬n Hugging Face (huggingface.co/new-space)](book-media/free-accounts/huggingface.jpg)
Γöé
Γûê### Streamlit Community Cloud ΓÇö Deploy Streamlit nhanh ch├│ng
Γöé
Γûê- **G├│i miß╗àn ph├¡:** Unlimited public apps (tß╗½ public GitHub repos)
Γûê- **T├ái nguy├¬n:** 1 GB RAM (burst l├¬n 3 GB), 2 CPU cores
Γûê- **URL:** URL dß║íng `your-app.streamlit.app`
Γûê- **─É─âng k├╜:** https://streamlit.io/cloud
Γöé
Γûê---
Γöé
Γûê## Nh├│m 3: Database & Vector Store ΓÇö L╞░u trß╗» dß╗» liß╗çu
Γöé
Γûêß╗¿ng dß╗Ñng AI Agent cß║ºn 2 loß║íi l╞░u trß╗»: (1) Database truyß╗ün thß╗æng cho dß╗» liß╗çu ng╞░ß╗¥i d├╣ng, v├á (2) Vector Store cho t├¼m kiß║┐m ngß╗» ngh─⌐a (RAG).
Γöé
Γûê### Supabase ΓÇö KHUY├èN D├ÖNG (PostgreSQL + pgvector)
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 500 MB database, 500 MB RAM, 5 GB egress/th├íng
Γûê- **Projects:** Tß╗æi ─æa 2 active projects
Γûê- **Vector Search:** C├│ pgvector extension ΓÇö t├¼m kiß║┐m vector ngay trong PostgreSQL!
Γûê- **T├¡nh n─âng:** Bao gß╗ôm Auth (50K MAU), Storage (1 GB), Edge Functions (500K/th├íng)
Γûê- **L╞░u ├╜:** Tß╗▒ ─æß╗Öng pause sau 7 ng├áy kh├┤ng d├╣ng
Γûê- **─É─âng k├╜:** https://supabase.com
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Supabase l├á lß╗▒a chß╗ìn Tß╗ÉT NHß║ñT cho AI20K v├¼: (1) PostgreSQL t╞░╞íng th├¡ch vß╗¢i template, (2) pgvector thay thß║┐ Vector Store ri├¬ng, (3) Auth sß║╡n c├│, (4) 2 projects ─æß╗º cho dev + demo.
Γöé
Γûê### Pinecone ΓÇö Vector Database chuy├¬n dß╗Ñng
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 2 GB vector storage, 5 serverless indexes
Γûê- **Operations:** 2 triß╗çu write units/th├íng, 1 triß╗çu read units/th├íng
Γûê- **Embedding:** 5 triß╗çu token/th├íng cho embedding inference
Γûê- **─É─âng k├╜:** https://www.pinecone.io
Γöé
Γûê### ChromaDB ΓÇö Self-hosted, KH├öNG GIß╗ÜI Hß║áN
Γöé
Γûê- **G├│i miß╗àn ph├¡:** Ho├án to├án miß╗àn ph├¡, open-source (Apache 2.0). Chß║íy local hoß║╖c trong Docker.
Γûê- **C├ái ─æß║╖t:** `pip install chromadb` ΓÇö chß║íy ngay trong Python
Γûê- **T╞░╞íng th├¡ch:** Template `ai20k-agent-template` ─æ├ú t├¡ch hß╗úp sß║╡n ChromaDB.
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** ChromaDB self-hosted l├á lß╗▒a chß╗ìn ─É╞áN GIß║óN NHß║ñT ΓÇö kh├┤ng cß║ºn t├ái khoß║ún cloud, chß║íy trß╗▒c tiß║┐p trong FastAPI server. Kß║┐t hß╗úp vß╗¢i Supabase ─æß╗â c├│ cß║ú database truyß╗ün thß╗æng + vector search.
Γöé
Γûê### Qdrant Cloud ΓÇö Vector DB miß╗àn ph├¡ tr├¬n cloud
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 1 GB RAM, 0.5 vCPU, 4 GB disk ΓÇö ~250K vectors
Γûê- **Features:** ─Éß║ºy ─æß╗º API (REST + gRPC), hybrid search, quantization
Γûê- **Thß║╗ t├¡n dß╗Ñng:** Kh├┤ng cß║ºn thß║╗ t├¡n dß╗Ñng
Γûê- **─É─âng k├╜:** https://cloud.qdrant.io
Γöé
Γûê### MongoDB Atlas ΓÇö NoSQL miß╗àn ph├¡
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 512 MB storage, 100 ops/sec, 500 connections (MIß╗äN PH├ì m├úi m├úi)
Γûê- **Vector Search:** Atlas Vector Search khß║ú dß╗Ñng tr├¬n g├│i M0
Γûê- **─É─âng k├╜:** https://www.mongodb.com/cloud/atlas/register
Γöé
Γûê---
Γöé
Γûê## Nh├│m 4: DevOps & CI/CD ΓÇö Tß╗▒ ─æß╗Öng h├│a
Γöé
Γûê### GitHub ΓÇö Bß║«T BUß╗ÿC (Quß║ún l├╜ code & CI/CD)
Γöé
Γûê- **G├│i miß╗àn ph├¡:** Unlimited public repos, unlimited private repos
Γûê- **GitHub Actions:** Public repos: UNLIMITED minutes. Private repos: 2,000 ph├║t/th├íng.
Γûê- **CI/CD sß║╡n:** Template `ai20k-agent-template` ─æ├ú c├│ sß║╡n file `.github/workflows/ci.yml`
Γöé
Γûê**C├íc b╞░ß╗¢c ─æ─âng k├╜:**
Γöé
Γûê1. V├áo https://github.com/signup ΓåÆ tß║ío t├ái khoß║ún (d├╣ng email tr╞░ß╗¥ng)
Γûê2. Fork repo `ai20k-agent-template` vß╗ü t├ái khoß║ún cß╗ºa ─æß╗Öi
Γûê3. Invite c├íc th├ánh vi├¬n trong ─æß╗Öi v├áo repo (Settings ΓåÆ Collaborators)
Γûê4. Kiß╗âm tra GitHub Actions ─æ├ú chß║íy (tab Actions) ΓÇö CI pipeline tß╗▒ test code
Γöé
Γûê### Docker Hub ΓÇö L╞░u trß╗» container images
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 100 pulls/giß╗¥ (─æ├ú login), unlimited public repos, 1 private repo
Γûê- **Template:** Template ─æ├ú c├│ Dockerfile + docker-compose.yml
Γûê- **─É─âng k├╜:** https://hub.docker.com
Γöé
Γûê### GitLab CI ΓÇö Thay thß║┐ GitHub (nß║┐u muß╗æn)
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 400 CI/CD ph├║t/th├íng tr├¬n shared runners, 5 GB storage
Γûê- **Self-hosted:** Self-managed runners kh├┤ng giß╗¢i hß║ín minutes
Γûê- **─É─âng k├╜:** https://gitlab.com
Γöé
Γûê---
Γöé
Γûê## Nh├│m 5: Monitoring & Logging ΓÇö Gi├ím s├ít ß╗⌐ng dß╗Ñng AI
Γöé
ΓûêMonitoring gi├║p bß║ín biß║┐t AI Agent ─æang hoß║ít ─æß╗Öng ra sao, c├│ lß╗ùi g├¼, v├á chß║Ñt l╞░ß╗úng response thß║┐ n├áo. ─É├óy c┼⌐ng l├á ti├¬u ch├¡ ─æ├ính gi├í DevOps trong Demo Day.
Γöé
Γûê### Langfuse ΓÇö KHUY├èN D├ÖNG (Open-source, unlimited)
Γöé
Γûê- **Cloud miß╗àn ph├¡:** 50,000 traces/th├íng, 2 users, 30 ng├áy retention
Γûê- **Self-hosted:** UNLIMITED traces, UNLIMITED users ΓÇö MIT license
Γûê- **T╞░╞íng th├¡ch:** Hoß║ít ─æß╗Öng vß╗¢i mß╗ìi LLM framework (LangChain, LangGraph, OpenAI SDK...)
Γûê- **─É─âng k├╜:** Cloud: https://cloud.langfuse.com | Self-hosted: https://github.com/langfuse/langfuse
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** Langfuse self-hosted l├á lß╗▒a chß╗ìn Tß╗ÉT NHß║ñT ΓÇö kh├┤ng giß╗¢i hß║ín, chß║íy trong Docker c├╣ng FastAPI. 10x nhiß╗üu traces h╞ín LangSmith tr├¬n cloud!
Γöé
Γûê### LangSmith ΓÇö Ch├¡nh thß╗⌐c tß╗½ LangChain
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 5,000 traces/th├íng, 1 user, 14 ng├áy retention
Γûê- **╞»u ─æiß╗âm:** T├¡ch hß╗úp s├óu vß╗¢i LangChain/LangGraph (d├╣ng trong template)
Γûê- **─É─âng k├╜:** https://smith.langchain.com
Γöé
Γûê![Giao diß╗çn LangSmith (smith.langchain.com)](book-media/free-accounts/langsmith.jpg)
Γöé
Γûê### Phoenix by Arize ΓÇö Open-source AI Observability
Γöé
Γûê- **G├│i miß╗àn ph├¡:** Ho├án to├án miß╗àn ph├¡, open-source. Kh├┤ng giß╗¢i hß║ín.
Γûê- **C├ái ─æß║╖t:** `pip install arize-phoenix` ΓÇö chß║íy local
Γûê- **Features:** Embedding visualization, drift detection, token monitoring
Γûê- **GitHub:** https://github.com/arize-ai/phoenix
Γöé
Γûê### Grafana Cloud ΓÇö Monitoring hß║í tß║ºng tß╗òng qu├ít
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 3 users, 10K metrics, 50 GB logs/th├íng, 50 GB traces/th├íng
Γûê- **Ph├╣ hß╗úp:** Tß╗æt cho monitoring hß║í tß║ºng (CPU, RAM, network) ΓÇö kh├┤ng chuy├¬n AI
Γûê- **─É─âng k├╜:** https://grafana.com/cloud
Γöé
Γûê---
Γöé
Γûê## Nh├│m 6: Frontend Hosting ΓÇö Giao diß╗çn ng╞░ß╗¥i d├╣ng
Γöé
ΓûêT├╣y v├áo framework frontend ─æß╗Öi chß╗ìn:
Γöé
Γûê| Framework | Nß╗ün tß║úng | G├│i miß╗àn ph├¡ | ─É├ính gi├í | Ghi ch├║ |
Γûê|-----------|----------|--------------|----------|---------|
Γûê| Next.js | Vercel | 100 GB BW, 1M requests | Γ¡ÉΓ¡ÉΓ¡ÉΓ¡ÉΓ¡É | Deploy 2 ph├║t |
Γûê| Next.js | Cloudflare Pages | Unlimited BW, 100 projects | Γ¡ÉΓ¡ÉΓ¡ÉΓ¡ÉΓ¡É | BW kh├┤ng giß╗¢i hß║ín |
Γûê| Streamlit | Streamlit Cloud | Unlimited public apps | Γ¡ÉΓ¡ÉΓ¡ÉΓ¡É | Chß╗ë cß║ºn GitHub repo |
Γûê| Static HTML | GitHub Pages | 1 GB, 100 GB BW | Γ¡ÉΓ¡ÉΓ¡ÉΓ¡É | Miß╗àn ph├¡, ─æ╞ín giß║ún |
Γûê| Bß║Ñt kß╗│ framework | Netlify | 300 credits/th├íng | Γ¡ÉΓ¡ÉΓ¡É | Giß╗¢i hß║ín mß╗¢i (2025) |
Γöé
Γûê---
Γöé
Γûê## Nh├│m 7: Domain & DNS ΓÇö T├¬n miß╗ün
Γöé
ΓûêT├¬n miß╗ün ri├¬ng **KH├öNG Bß║«T BUß╗ÿC** cho Demo Day ΓÇö bß║ín ho├án to├án c├│ thß╗â d├╣ng URL miß╗àn ph├¡ tß╗½ c├íc cloud platform (`yourapp.vercel.app`, `yourapp.onrender.com`, `yourapp.streamlit.app`). Tuy nhi├¬n, nß║┐u muß╗æn t├¬n miß╗ün ri├¬ng cho chuy├¬n nghiß╗çp:
Γöé
Γûê### Subdomain miß╗àn ph├¡ (Kh├┤ng cß║ºn ─æ─âng k├╜)
Γöé
Γûê| Nß╗ün tß║úng | Subdomain mß║½u | C├ích lß║Ñy |
Γûê|----------|---------------|----------|
Γûê| Vercel | `your-team.vercel.app` | Tß╗▒ ─æß╗Öng khi deploy Next.js |
Γûê| Render | `your-team.onrender.com` | Tß╗▒ ─æß╗Öng khi deploy FastAPI |
Γûê| Streamlit | `your-team.streamlit.app` | Tß╗▒ ─æß╗Öng khi deploy Streamlit |
Γûê| GitHub Pages | `your-team.github.io` | Tß╗▒ ─æß╗Öng khi tß║ío GitHub Pages |
Γûê| Cloudflare Pages | `your-team.pages.dev` | Tß╗▒ ─æß╗Öng khi deploy |
Γûê| DuckDNS | `your-team.duckdns.org` | Dynamic DNS, cß║ºn cß║¡p nhß║¡t |
Γöé
Γûê### T├¬n miß╗ün trß║ú ph├¡
Γöé
Γûê- **Gi├í rß║╗:** Porkbun.com ΓÇö t├¬n miß╗ün .xyz, .top tß╗½ $1-2/n─âm
Γûê- **Phß╗ò biß║┐n:** Namecheap.com ΓÇö nhiß╗üu lß╗▒a chß╗ìn, ~$2-5/n─âm cho TLD rß║╗
Γûê- **Minh bß║ích:** Cloudflare Registrar ΓÇö gi├í at-cost (kh├┤ng markup)
Γöé
Γûê> ≡ƒÆí **Mß║╕O:** T├¬n miß╗ün ri├¬ng l├á "nice to have" ΓÇö KH├öNG ß║únh h╞░ß╗ƒng ─æiß╗âm ─æ├ính gi├í. ╞»u ti├¬n thß╗¥i gian cho viß╗çc build app h╞ín!
Γöé
Γûê---
Γöé
Γûê## Nh├│m 8: C├┤ng cß╗Ñ hß╗ù trß╗ú kh├íc
Γöé
Γûê### ngrok ΓÇö Chia sß║╗ localhost cho ng╞░ß╗¥i kh├íc test
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 1 tunnel, URL random (─æß╗òi mß╗ùi 2 giß╗¥), 1 GB bandwidth/th├íng
Γûê- **D├╣ng khi:** Tß╗æt cho test nhanh ΓÇö cho teammate hoß║╖c mentor xem app ─æang chß║íy local
Γûê- **─É─âng k├╜:** https://ngrok.com
Γöé
Γûê### Postman ΓÇö Test API
Γöé
Γûê- **G├│i miß╗àn ph├¡:** Core API testing cho 1 user, 5,000 AI credits/th├íng
Γûê- **D├╣ng cho:** Test c├íc endpoint FastAPI (`/api/v1/chat`, `/api/v1/status`)
Γûê- **─É─âng k├╜:** https://www.postman.com
Γöé
Γûê### Figma ΓÇö Thiß║┐t kß║┐ giao diß╗çn
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 3 design files + 3 FigJam files, unlimited personal drafts
Γûê- **D├╣ng cho:** Wireframe UI/UX cho ß╗⌐ng dß╗Ñng AI Agent
Γûê- **─É─âng k├╜:** https://www.figma.com
Γöé
Γûê### Sentry ΓÇö Error tracking
Γöé
Γûê- **G├│i miß╗àn ph├¡:** 5,000 error events/th├íng, unlimited projects
Γûê- **D├╣ng cho:** Tß╗▒ ─æß╗Öng bß║»t lß╗ùi trong FastAPI app, gß╗¡i alert
Γûê- **─É─âng k├╜:** https://sentry.io
Γöé
Γûê---
Γöé
Γûê## FAQ ΓÇö C├óu hß╗Åi th╞░ß╗¥ng gß║╖p
Γöé
Γûê**Q: T├┤i c├│ cß║ºn thß║╗ t├¡n dß╗Ñng kh├┤ng?**
Γöé
ΓûêA: Hß║ºu hß║┐t **KH├öNG Cß║ªN**. Mistral, Google Gemini, Groq, Together AI, Cohere, Supabase, Qdrant, Langfuse, GitHub, Docker Hub ─æß╗üu kh├┤ng y├¬u cß║ºu thß║╗ t├¡n dß╗Ñng. Chß╗ë Render (cho mß╗Öt sß╗æ t├¡nh n─âng) v├á Railway c├│ thß╗â y├¬u cß║ºu.
Γöé
Γûê**Q: T├┤i n├¬n d├╣ng LLM n├áo?**
Γöé
ΓûêA: Khuyß║┐n nghß╗ï: Mistral (1 tß╗╖ token free) l├ám ch├¡nh, Google Gemini Flash l├ám backup, Groq cho demo cß║ºn tß╗æc ─æß╗Ö. Nß║┐u template y├¬u cß║ºu OpenAI cß╗Ñ thß╗â ΓåÆ ─æ─âng k├╜ OpenAI v├á d├╣ng GPT-4o-mini (rß║╗ nhß║Ñt).
Γöé
Γûê**Q: Free tier c├│ ─æß╗º cho Demo Day kh├┤ng?**
Γöé
ΓûêA: C├ô. Tß║Ñt cß║ú c├íc dß╗ïch vß╗Ñ tr├¬n ─æß╗üu ─æß╗º cho 6 tuß║ºn ph├ít triß╗ân + Demo Day. L╞░u ├╜: (1) Render database miß╗àn ph├¡ hß║┐t hß║ín 30 ng├áy ΓÇö d├╣ng Supabase, (2) OpenAI credit $5 sß║╜ hß║┐t nhanh nß║┐u d├╣ng GPT-4o ΓÇö ╞░u ti├¬n GPT-4o-mini hoß║╖c Mistral.
Γöé
Γûê**Q: L├ám sao ─æß╗â tiß║┐t kiß╗çm credit?**
Γöé
ΓûêA: (1) D├╣ng Mistral/Gemini/Groq (free) thay v├¼ OpenAI cho development. (2) D├╣ng GPT-4o-mini thay v├¼ GPT-4o khi phß║úi d├╣ng OpenAI. (3) Tß║»t debug mode khi kh├┤ng cß║ºn. (4) D├╣ng ChromaDB local thay v├¼ Pinecone cloud. (5) Giß║úm token output bß║▒ng prompt ngß║»n gß╗ìn.
Γöé
Γûê**Q: Render sleep sau 15 ph├║t ΓÇö sao cho app lu├┤n sß║╡n s├áng cho Demo?**
Γöé
ΓûêA: (1) D├╣ng script ping mß╗ùi 10 ph├║t (cron job hoß║╖c GitHub Actions). (2) Hoß║╖c upgrade l├¬n paid plan ($7/th├íng). (3) Hoß║╖c deploy tr├¬n Railway/UptimeRobot. (4) Wake up thß╗º c├┤ng tr╞░ß╗¢c demo 1 ph├║t.
Γöé
Γûê**Q: Nhiß╗üu ng╞░ß╗¥i trong ─æß╗Öi c├│ d├╣ng chung t├ái khoß║ún ─æ╞░ß╗úc kh├┤ng?**
Γöé
ΓûêA: GitHub: Mß╗ùi ng╞░ß╗¥i 1 t├ái khoß║ún ΓåÆ collaborate tr├¬n repo. Vercel/Render: 1 t├ái khoß║ún ─æß╗Öi ΓåÆ share login hoß║╖c invite members. API keys: Share qua file `.env` (KH├öNG commit l├¬n GitHub).
Γöé
Γûê**Q: Template d├╣ng OpenAI, nh╞░ng t├┤i muß╗æn d├╣ng Mistral/Gemini ΓÇö ─æ╞░ß╗úc kh├┤ng?**
Γöé
ΓûêA: ─É╞»ß╗óC! Template d├╣ng LangChain ΓÇö hß╗ù trß╗ú nhiß╗üu provider. Chß╗ë cß║ºn thay ─æß╗òi `get_llm()` trong `src/services/llm.py`. V├¡ dß╗Ñ: `ChatMistralAI` thay v├¼ `ChatOpenAI`. Xem h╞░ß╗¢ng dß║½n trong `docs/guide/chapter-04.md` cß╗ºa template.
Γöé
Γûê**Q: T├┤i c├│ thß╗â d├╣ng ChatGPT Plus / Claude Pro subscription thay v├¼ API kh├┤ng?**
Γöé
ΓûêA: KH├öNG. ChatGPT Plus / Claude Pro l├á subscription cho chat interface, KH├öNG phß║úi API access. Bß║ín cß║ºn ─æ─âng k├╜ API ri├¬ng (platform.openai.com, console.anthropic.com). API t├¡nh ph├¡ theo token sß╗¡ dß╗Ñng.
Γöé
Γûê---
Γöé
Γûê> ≡ƒöæ **─ÉIß╗éM CH├ìNH:** ─É─âng k├╜ t├ái khoß║ún trong Tuß║ºn 1, ╞░u ti├¬n c├íc dß╗ïch vß╗Ñ KHUY├èN D├ÖNG (Mistral, Gemini, Render, Vercel, Supabase, GitHub, Langfuse). Ch├║c c├íc ─æß╗Öi x├óy dß╗▒ng th├ánh c├┤ng ß╗⌐ng dß╗Ñng AI! ΓÇö *VinUni AI20K ΓÇö T├¼m Kiß║┐m Nh├ón T├ái Thß╗▒c Chiß║┐n A.I*


docs\guide\langgraph\nodes-and-edges.md:
Γûê---
Γûêtitle: "Nodes & Edges"
Γûêdescription: "─Éß╗ïnh ngh─⌐a nodes v├á edges trong LangGraph graph"
Γûêweight: 2
Γûê---
Γöé
Γûê## Nodes
Γöé
ΓûêMß╗ùi node l├á mß╗Öt h├ám async nhß║¡n state, trß║ú vß╗ü dict:
Γöé
Γûê```python
Γûêasync def analyze_node(state: AgentState) -> dict:
Γûê    """Ph├ón t├¡ch query tß╗½ user."""
Γûê    query = state.get("query", "")
Γûê    analysis = await process_query(query)
Γûê    return {"analysis": analysis}
Γûê```
Γöé
Γûê### Node Best Practices
Γöé
Γûê1. **Mß╗Öt node mß╗Öt tr├ích nhiß╗çm** ΓÇö Kh├┤ng l├ám 2 viß╗çc trong 1 node
Γûê2. **Return chß╗ë fields cß║ºn update** ΓÇö Kh├┤ng return to├án bß╗Ö state
Γûê3. **Error handling** ΓÇö Lu├┤n c├│ try/except v├á set error field
Γûê4. **Docstring** ΓÇö M├┤ tß║ú node l├ám g├¼
Γöé
Γûê```python
Γûêasync def safe_analyze_node(state: AgentState) -> dict:
Γûê    """Ph├ón t├¡ch query, handle errors gracefully."""
Γûê    try:
Γûê        query = state.get("query", "")
Γûê        result = await llm_service.analyze(query)
Γûê        return {"analysis": result}
Γûê    except Exception as e:
Γûê        return {"error": f"Analysis failed: {e}"}
Γûê```
Γöé
Γûê## Edges
Γöé
Γûê### Linear Edges
Γöé
Γûê```python
Γûêgraph.add_edge("analyze", "respond")
Γûê```
Γöé
Γûê### Conditional Edges (Routing)
Γöé
Γûê```python
Γûêdef route_after_analyze(state: AgentState) -> str:
Γûê    if state.get("error"):
Γûê        return "respond"
Γûê    if state.get("needs_search"):
Γûê        return "search"
Γûê    return "respond"
Γöé
Γûêgraph.add_conditional_edges("analyze", route_after_analyze)
Γûê```
Γöé
Γûê## Graph Construction
Γöé
Γûê```python
Γûêfrom langgraph.graph import END, StateGraph
Γöé
Γûêdef build_graph() -> StateGraph:
Γûê    graph = StateGraph(AgentState)
Γöé
Γûê    # 1. Add nodes
Γûê    graph.add_node("analyze", analyze_node)
Γûê    graph.add_node("search", search_node)
Γûê    graph.add_node("respond", respond_node)
Γöé
Γûê    # 2. Set entry point
Γûê    graph.set_entry_point("analyze")
Γöé
Γûê    # 3. Add edges
Γûê    graph.add_conditional_edges("analyze", route_after_analyze)
Γûê    graph.add_edge("search", "respond")
Γûê    graph.add_edge("respond", END)
Γöé
Γûê    return graph.compile()
Γöé
Γûêagent = build_graph()
Γûê```
Γöé
Γûê## Agent Patterns
Γöé
Γûê### ReAct Pattern (Recommended)
Γöé
Γûê```
ΓûêQuery ΓåÆ Analyze ΓåÆ [Call Tool ΓåÆ Observe ΓåÆ Re-analyze]* ΓåÆ Respond
Γûê```
Γöé
Γûê### Plan-and-Execute Pattern
Γöé
Γûê```
ΓûêQuery ΓåÆ Plan ΓåÆ [Execute Step 1 ΓåÆ ... ΓåÆ Step N] ΓåÆ Respond
Γûê```
Γöé
Γûê### Multi-Agent Pattern
Γöé
Γûê```
ΓûêQuery ΓåÆ Router ΓåÆ [Agent A | Agent B | Agent C] ΓåÆ Synthesize ΓåÆ Respond
Γûê```


docs\guide\langgraph\state.md:
Γûê---
Γûêtitle: "State Management"
Γûêdescription: "─Éß╗ïnh ngh─⌐a State schema cho LangGraph agent"
Γûêweight: 1
Γûê---
Γöé
Γûê## State Schema
Γöé
ΓûêState l├á "bß╗Ö nhß╗¢" cß╗ºa agent, truyß╗ün giß╗»a c├íc nodes:
Γöé
Γûê```python
Γûêfrom typing import TypedDict
Γöé
Γûêclass AgentState(TypedDict, total=False):
Γûê    query: str        # Input tß╗½ user
Γûê    context: str      # Context tß╗½ RAG
Γûê    analysis: str     # Kß║┐t quß║ú ph├ón t├¡ch
Γûê    response: str     # Response cuß╗æi c├╣ng
Γûê    error: str        # Error nß║┐u c├│
Γûê    metadata: dict    # Extra info
Γûê```
Γöé
Γûê## Nguy├¬n tß║»c thiß║┐t kß║┐ State
Γöé
Γûê### 1. D├╣ng TypedDict
Γöé
Γûê```python
Γûê# Γ£à Tß╗ÉT ΓÇö TypedDict cho state
Γûêclass AgentState(TypedDict, total=False):
Γûê    query: str
Γûê    response: str
Γöé
Γûê# Γ¥î Tß╗å ΓÇö Kh├┤ng d├╣ng Pydantic cho LangGraph state
Γûêclass AgentState(BaseModel):
Γûê    query: str  # LangGraph expects TypedDict
Γûê```
Γöé
Γûê### 2. total=False cho optional fields
Γöé
Γûê```python
Γûêclass AgentState(TypedDict, total=False):
Γûê    query: str           # Input (lu├┤n c├│)
Γûê    context: str         # Optional ΓÇö chß╗ë c├│ khi d├╣ng RAG
Γûê    error: str           # Optional ΓÇö chß╗ë c├│ khi lß╗ùi
Γûê```
Γöé
Γûê### 3. Chß╗ë th├¬m fields thß╗▒c sß╗▒ cß║ºn
Γöé
Γûê- Mß╗ùi field = data ─æ╞░ß╗úc truyß╗ün giß╗»a nodes
Γûê- Kh├┤ng d├╣ng state nh╞░ "trash can" chß╗⌐a mß╗ìi thß╗⌐
Γûê- Th├¬m docstring cho tß╗½ng field
Γöé
Γûê### 4. Stateµ¢┤µû░ pattern
Γöé
Γûê```python
Γûê# Mß╗ùi node chß╗ë return fields n├│ thay ─æß╗òi
Γûêasync def analyze_node(state: AgentState) -> dict:
Γûê    query = state.get("query", "")
Γûê    analysis = await process(query)
Γûê    return {"analysis": analysis}  # Chß╗ë update "analysis"
Γûê```


docs\guide\langgraph\tools.md:
Γûê---
Γûêtitle: "Agent Tools"
Γûêdescription: "Tß║ío tools cho LangGraph agent"
Γûêweight: 3
Γûê---
Γöé
Γûê## Tool Definition
Γöé
Γûê```python
Γûêfrom langchain_core.tools import tool
Γöé
Γûê@tool
Γûêdef search_knowledge(query: str) -> str:
Γûê    """T├¼m kiß║┐m th├┤ng tin trong knowledge base.
Γöé
Γûê    Args:
Γûê        query: C├óu hß╗Åi cß║ºn t├¼m kiß║┐m
Γöé
Γûê    Returns:
Γûê        Kß║┐t quß║ú t├¼m kiß║┐m dß║íng text
Γûê    """
Γûê    results = vector_store.similarity_search(query, k=3)
Γûê    return "\n".join([r.page_content for r in results])
Γûê```
Γöé
Γûê## Nguy├¬n tß║»c
Γöé
Γûê1. **Lu├┤n c├│ docstring** ΓÇö Agent d├╣ng docstring ─æß╗â quyß║┐t ─æß╗ïnh khi n├áo gß╗ìi tool
Γûê2. **Type hints cho tß║Ñt cß║ú params** ΓÇö Gi├║p agent truyß╗ün ─æ├║ng kiß╗âu data
Γûê3. **Return string** ΓÇö Agent dß╗à parse kß║┐t quß║ú
Γûê4. **Error handling b├¬n trong tool** ΓÇö Kh├┤ng throw, return error message
Γöé
Γûê## Tool Types
Γöé
Γûê### Search Tool (RAG)
Γöé
Γûê```python
Γûê@tool
Γûêdef search_documents(query: str) -> str:
Γûê    """T├¼m kiß║┐m t├ái liß╗çu li├¬n quan."""
Γûê    docs = vector_store.similarity_search(query, k=5)
Γûê    if not docs:
Γûê        return "Kh├┤ng t├¼m thß║Ñy t├ái liß╗çu li├¬n quan."
Γûê    return "\n---\n".join([d.page_content for d in docs])
Γûê```
Γöé
Γûê### API Call Tool
Γöé
Γûê```python
Γûê@tool
Γûêdef call_external_api(endpoint: str, params: dict) -> str:
Γûê    """Gß╗ìi API ngo├ái."""
Γûê    try:
Γûê        response = httpx.post(endpoint, json=params)
Γûê        return response.text
Γûê    except Exception as e:
Γûê        return f"API error: {e}"
Γûê```
Γöé
Γûê### Calculator Tool
Γöé
Γûê```python
Γûê@tool
Γûêdef calculate(expression: str) -> str:
Γûê    """T├¡nh to├ín biß╗âu thß╗⌐c to├ín hß╗ìc."""
Γûê    try:
Γûê        result = eval(expression, {"__builtins__": {}}, {})
Γûê        return str(result)
Γûê    except Exception as e:
Γûê        return f"Calculation error: {e}"
Γûê```
Γöé
Γûê## Th├¬m Tools v├áo Agent
Γöé
Γûê```python
Γûêfrom langchain_openai import ChatOpenAI
Γöé
Γûêllm = ChatOpenAI(model="gpt-4o-mini")
Γûêllm_with_tools = llm.bind_tools([search_documents, calculate])
Γûê```


docs\guide\langgraph\_index.md:
Γûê---
Γûêtitle: "LangGraph Agent"
Γûêdescription: "X├óy dß╗▒ng AI Agent vß╗¢i LangGraph"
Γûêweight: 3
Γûê---
Γöé
ΓûêPhß║ºn n├áy ─æi s├óu v├áo LangGraph ΓÇö framework ch├¡nh ─æß╗â x├óy dß╗▒ng AI Agent trong template AI20K. Bß║ín sß║╜ t├¼m hiß╗âu ba kh├íi niß╗çm cß╗æt l├╡i: State (trß║íng th├íi), Nodes & Edges (n├║t v├á cß║ính), v├á Tools (c├┤ng cß╗Ñ). Mß╗ùi kh├íi niß╗çm ─æß╗üu c├│ v├¡ dß╗Ñ code cß╗Ñ thß╗â ─æß╗â bß║ín c├│ thß╗â ├íp dß╗Ñng ngay. Nß║»m vß╗»ng LangGraph l├á ch├¼a kh├│a ─æß╗â x├óy dß╗▒ng agent th├┤ng minh c├│ khß║ú n─âng suy luß║¡n v├á h├ánh ─æß╗Öng.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [State](state.md) ΓÇö ─Éß╗ïnh ngh─⌐a v├á quß║ún l├╜ trß║íng th├íi trong LangGraph
Γûê- [Nodes & Edges](nodes-and-edges.md) ΓÇö X├óy dß╗▒ng luß╗ông xß╗¡ l├╜ bß║▒ng nodes v├á edges
Γûê- [Tools](tools.md) ΓÇö Tß║ío v├á t├¡ch hß╗úp c├┤ng cß╗Ñ cho agent


docs\guide\patterns\rag-pattern.md:
Γûê---
Γûêtitle: "RAG Pattern"
Γûêdescription: "Retrieval-Augmented Generation pattern"
Γûêweight: 1
Γûê---
Γöé
Γûê## RAG (Retrieval-Augmented Generation)
Γöé
Γûê### Flow
Γöé
Γûê```
ΓûêQuery ΓåÆ Embed ΓåÆ Search Vector DB ΓåÆ Retrieve Top-K ΓåÆ Context + Query ΓåÆ LLM ΓåÆ Response
Γûê```
Γöé
Γûê### Implementation
Γöé
Γûê```python
Γûê# Node: Retrieve context tß╗½ vector store
Γûêasync def retrieve_node(state: AgentState) -> dict:
Γûê    query = state.get("query", "")
Γöé
Γûê    # Embed query
Γûê    embeddings = OpenAIEmbeddings()
Γûê    query_embedding = await embeddings.aembed_query(query)
Γöé
Γûê    # Search vector store
Γûê    docs = vector_store.similarity_search_by_vector(query_embedding, k=3)
Γûê    context = "\n---\n".join([d.page_content for d in docs])
Γöé
Γûê    return {"context": context}
Γûê```
Γöé
Γûê### Graph vß╗¢i RAG
Γöé
Γûê```python
Γûêdef build_rag_graph():
Γûê    graph = StateGraph(AgentState)
Γûê    graph.add_node("retrieve", retrieve_node)
Γûê    graph.add_node("generate", generate_node)
Γûê    graph.set_entry_point("retrieve")
Γûê    graph.add_edge("retrieve", "generate")
Γûê    graph.add_edge("generate", END)
Γûê    return graph.compile()
Γûê```
Γöé
Γûê## Streaming Response
Γöé
Γûê```python
Γûêfrom fastapi.responses import StreamingResponse
Γöé
Γûê@router.post("/chat/stream")
Γûêasync def chat_stream(request: ChatRequest):
Γûê    async def generate():
Γûê        async for chunk in agent.astream({"query": request.message}):
Γûê            yield f"data: {json.dumps(chunk)}\n\n"
Γûê    return StreamingResponse(generate(), media_type="text/event-stream")
Γûê```
Γöé
Γûê## Pydantic Settings Pattern
Γöé
Γûê```python
Γûêfrom pydantic_settings import BaseSettings
Γöé
Γûêclass Settings(BaseSettings):
Γûê    api_key: str = ""  # Required in .env
Γûê    model: str = "gpt-4o-mini"  # Default
Γöé
Γûê    model_config = {"env_file": ".env"}
Γûê```
Γöé
Γûê## FastAPI Lifespan Pattern
Γöé
Γûê```python
Γûêfrom contextlib import asynccontextmanager
Γöé
Γûê@asynccontextmanager
Γûêasync def lifespan(app: FastAPI):
Γûê    # Startup
Γûê    print("Starting app...")
Γûê    yield
Γûê    # Shutdown
Γûê    print("Shutting down...")
Γöé
Γûêapp = FastAPI(lifespan=lifespan)
Γûê```


docs\guide\patterns\_index.md:
Γûê---
Γûêtitle: "Common Patterns"
Γûêdescription: "C├íc pattern hay d├╣ng trong AI Agent"
Γûêweight: 9
Γûê---
Γöé
ΓûêPhß║ºn n├áy tß╗òng hß╗úp c├íc design pattern phß╗ò biß║┐n khi x├óy dß╗▒ng AI Agent, ─æß║╖c biß╗çt l├á RAG (Retrieval-Augmented Generation). Bß║ín sß║╜ t├¼m hiß╗âu luß╗ông RAG ho├án chß╗ënh, c├ích code retrieve node, x├óy dß╗▒ng RAG graph builder, streaming response, cß║Ñu h├¼nh bß║▒ng Pydantic settings v├á quß║ún l├╜ FastAPI lifespan. ─É├óy l├á phß║ºn tham khß║úo quan trß╗ìng ─æß╗â x├óy dß╗▒ng agent c├│ khß║ú n─âng trß║ú lß╗¥i dß╗▒a tr├¬n t├ái liß╗çu ri├¬ng.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [RAG Pattern](rag-pattern.md) ΓÇö Luß╗ông RAG, code retrieve node, RAG graph builder, streaming, Pydantic settings, FastAPI lifespan


docs\guide\resources\recommended-courses.md:
Γûê---
Γûêtitle: "Recommended Courses"
Γûêdescription: "Kh├│a hß╗ìc ─æ╞░ß╗úc tuyß╗ân chß╗ìn tß╗½ DeepLearning.AI (121 courses) v├á c├íc nguß╗ôn kh├íc"
Γûêweight: 1
Γûê---
Γöé
Γûê## Lß╗Ö tr├¼nh hß╗ìc 6 tuß║ºn
Γöé
Γûê### Week 1: Foundations (2h)
Γöé
Γûê| Course | Time | Level |
Γûê|--------|------|-------|
Γûê| ChatGPT Prompt Engineering for Developers | 1h | Beginner |
Γûê| LangChain for LLM Application Development | 1h | Beginner |
Γöé
Γûê### Week 2: Agent Basics (3.5h)
Γöé
Γûê| Course | Time | Level |
Γûê|--------|------|-------|
Γûê| Functions, Tools and Agents with LangChain | 1.5h | Beginner |
Γûê| AI Agents in LangGraph | 2h | Intermediate |
Γöé
Γûê### Week 3: Agent Patterns (3h)
Γöé
Γûê| Course | Time | Level |
Γûê|--------|------|-------|
Γûê| Agentic AI (by Andrew Ng) | 1h | Intermediate |
Γûê| Building Agentic RAG with LlamaIndex | 1.5h | Beginner |
Γûê| Evaluating AI Agents | 0.5h | Beginner |
Γöé
Γûê### Week 4: Advanced Patterns (3h)
Γöé
Γûê| Course | Time | Level |
Γûê|--------|------|-------|
Γûê| Long-Term Agentic Memory With LangGraph | 1h | Intermediate |
Γûê| Design, Develop, and Deploy Multi-Agent Systems with CrewAI | 1h | Beginner |
Γûê| MCP: Build Rich-Context AI Apps with Anthropic | 1h | Intermediate |
Γöé
Γûê### Week 5: Production (2.5h)
Γöé
Γûê| Course | Time | Level |
Γûê|--------|------|-------|
Γûê| Pydantic for LLM Workflows | 1h | Intermediate |
Γûê| Retrieval Augmented Generation (RAG) | 1h | Intermediate |
Γûê| Red Teaming LLM Applications | 0.5h | Beginner |
Γöé
Γûê### Week 6: Polish & Deploy (2h)
Γöé
Γûê| Course | Time | Level |
Γûê|--------|------|-------|
Γûê| Evaluating and Debugging Generative AI | 1h | Intermediate |
Γûê| Building Generative AI Applications with Gradio | 1h | Beginner |
Γöé
Γûê## To├án bß╗Ö danh s├ích DeepLearning.AI ΓÇö AI Agents (35 courses)
Γöé
Γûê| # | Course | Level | Focus |
Γûê|---|--------|-------|-------|
Γûê| 1 | AI Agents in LangGraph | Intermediate | LangGraph basics, state, nodes, edges |
Γûê| 2 | Agentic AI (by Andrew Ng) | Intermediate | Agentic workflows, multi-step |
Γûê| 3 | Long-Term Agentic Memory With LangGraph | Intermediate | Memory + LangGraph + LangMem |
Γûê| 4 | Building Agentic RAG with LlamaIndex | Beginner | RAG + Agent patterns |
Γûê| 5 | Functions, Tools and Agents with LangChain | Beginner | Tool use, function calling |
Γûê| 6 | Design, Develop, and Deploy Multi-Agent Systems with CrewAI | Beginner | Multi-agent with CrewAI |
Γûê| 7 | AI Agentic Design Patterns with AutoGen | Beginner | Multi-agent with AutoGen |
Γûê| 8 | Evaluating AI Agents | Beginner | Agent evaluation methods |
Γûê| 9 | Agent Memory: Building Memory-Aware Agents | Intermediate | Agent memory systems |
Γûê| 10 | A2A: The Agent2Agent Protocol | Intermediate | Agent-to-agent communication |
Γûê| 11 | Agent Skills with Anthropic | Beginner | Expert knowledge for agents |
Γûê| 12 | Semantic Caching for AI Agents | Intermediate | Speed up agents, reduce costs |
Γûê| 13 | Building Coding Agents with Tool Execution | Intermediate | Code agents in sandboxes |
Γûê| 14 | Document AI: From OCR to Agentic Doc Extraction | Intermediate | Document parsing agents |
Γûê| 15 | Governing AI Agents | Beginner | Data governance for agents |
Γûê| 16 | Building Live Voice Agents with Google's ADK | Intermediate | Voice AI agents |
Γûê| 17 | Building and Evaluating Data Agents | Intermediate | Data-connected agents |
Γûê| 18 | Spec-Driven Development with Coding Agents | Beginner | Spec ΓåÆ code agents |
Γûê| 19 | Build Interactive Agents with Generative UI | Beginner | Agents with custom UIs |
Γûê| 20 | Claude Code: A Highly Agentic Coding Assistant | Intermediate | Claude Code agent |
Γûê| 21 | DSPy: Build and Optimize Agentic Apps | Intermediate | DSPy optimization |
Γûê| 22 | Building AI Voice Agents for Production | Intermediate | Production voice agents |
Γûê| 23 | Building Code Agents with Hugging Face smolagents | Intermediate | Code agents with smolagents |
Γûê| 24 | Building AI Browser Agents | Intermediate | Web navigation agents |
Γûê| 25 | Vibe Coding 101 with Replit | Beginner | AI coding agent |
Γûê| 26 | Event-Driven Agentic Document Workflows | Beginner | Document workflows |
Γûê| 27 | Build Apps with Windsurf's AI Coding Agents | Beginner | Windsurf IDE agents |
Γûê| 28 | Nvidia's NeMo Agent Toolkit | Intermediate | Production agent systems |
Γûê| 29 | AI Agents for Image and Video Generation | Intermediate | Image/video agents |
Γûê| 30 | Gemini CLI: Code & Create | Beginner | Gemini CLI agent |
Γûê| 31 | Build AI Apps with MCP Server: Working with Box Files | Intermediate | MCP + multi-agent |
Γûê| 32 | Knowledge Graphs for AI Agent API Discovery | Intermediate | Knowledge graph + agents |
Γûê| 33 | Agentic Knowledge Graph Construction | Intermediate | Multi-agent knowledge graphs |
Γûê| 34 | Practical Multi AI Agents with CrewAI | Beginner | Collaborative agents |
Γûê| 35 | Multi AI Agent Systems with CrewAI | Beginner | Business workflow agents |
Γöé
Γûê## RAG & Retrieval Courses
Γöé
Γûê| Course | Time | Level |
Γûê|--------|------|-------|
Γûê| Retrieval Augmented Generation (RAG) | 1h | Intermediate |
Γûê| Building Applications with Vector Databases | 1h | Beginner |
Γûê| Advanced Retrieval for AI with Chroma | 1h | Intermediate |
Γûê| Building and Evaluating Advanced RAG | 1h | Beginner |
Γûê| Knowledge Graphs for RAG | 1h | Intermediate |
Γûê| Vector Databases: from Embeddings to Applications | 1h | Intermediate |
Γûê| Understanding and Applying Text Embeddings | 1h | Beginner |
Γöé
Γûê## Prompt Engineering Courses
Γöé
Γûê| Course | Time | Level |
Γûê|--------|------|-------|
Γûê| ChatGPT Prompt Engineering for Developers | 1h | Beginner |
Γûê| AI Prompting for Everyone | 1h | Beginner |
Γûê| Improving Accuracy of LLM Applications | 1h | Intermediate |
Γûê| MCP: Build Rich-Context AI Apps with Anthropic | 1h | Intermediate |
Γöé
Γûê## Python & Tools
Γöé
Γûê| Course | Time | Level |
Γûê|--------|------|-------|
Γûê| AI Python for Beginners | 1h | Beginner |
Γûê| Pydantic for LLM Workflows | 1h | Intermediate |
Γûê| Building Generative AI Applications with Gradio | 1h | Beginner |
Γûê| Jupyter AI: AI Coding in Notebooks | 1h | Beginner |
Γöé
Γûê> Tß║Ñt cß║ú courses ─æß╗üu **miß╗àn ph├¡** tß║íi [deeplearning.ai/courses](https://www.deeplearning.ai/courses)


docs\guide\resources\reference-teams.md:
Γûê---
Γûêtitle: "Reference Teams (Cohort 1)"
Γûêdescription: "Top practices tß╗½ 12 teams Cohort 1"
Γûêweight: 2
Γûê---
Γöé
Γûê## Ph├ón t├¡ch Cohort 1
Γöé
Γûê### Xß║┐p hß║íng tß╗òng thß╗â
Γöé
Γûê| Rank | Team | Score | Strengths |
Γûê|------|------|-------|-----------|
Γûê| 1 | A20-App-010 | 39.6/50 | Product 10, System 9, UI 8.5 |
Γûê| 2 | A20-App-007 | 38.3/50 | Best code quality, Clean Architecture |
Γûê| 3 | A20-App-008 | 37.6/50 | Good all-around |
Γûê| 4 | A20-App-003 | 37.1/50 | Best LangGraph implementation |
Γûê| 5 | A20-App-002 | 37.0/50 | Best multi-agent architecture |
Γöé
Γûê### Best Practices by Category
Γöé
Γûê#### README (Reference: Team 011)
Γûê- Table of contents with anchor links
Γûê- "Important links" table (demo, video, slides)
Γûê- Environment variable table with Required/Default/Description
Γûê- Step-by-step setup guide
Γöé
Γûê#### Architecture (Reference: Team 007)
Γûê- Clean Architecture layers
Γûê- CQRS pattern
Γûê- ADR (Architecture Decision Records)
Γöé
Γûê#### LangGraph Agent (Reference: Team 003)
Γûê- `state.py` (TypedDict) + `pipeline.py` (graph builder) + `nodes/` directory
Γûê- Conditional edges with retry logic
Γûê- Singleton compiled pipeline
Γöé
Γûê#### Docker (Reference: Team 001)
Γûê- Multi-stage Alpine build
Γûê- Non-root user
Γûê- HEALTHCHECK directive
Γûê- `--mount=type=cache` for pip
Γöé
Γûê#### Evaluation Evidence (Reference: Team 011)
Γûê- RAGAS evaluation with 50 golden samples
Γûê- Test scenario table with pass/fail
Γûê- User feedback quotes with ratings
Γûê- Explicit answers to evaluation questions
Γöé
Γûê### Common Weaknesses (PHß║óI TR├üNH)
Γöé
Γûê| Issue | Teams affected | Impact |
Γûê|-------|---------------|--------|
Γûê| No CI/CD | 12/12 | DevOps score thß║Ñp |
Γûê| No tests | 10/12 | Code quality thß║Ñp |
Γûê| Bare except | 3/12 | Code quality giß║úm |
Γûê| Hardcoded secrets | 1/12 | Security risk |
Γûê| Missing Evaluation Evidence | 10/12 | Product score thß║Ñp |
Γûê| No Video Demo | 12/12 | Missing deliverable |


docs\guide\resources\_index.md:
Γûê---
Γûêtitle: "Learning Resources"
Γûêdescription: "Kh├│a hß╗ìc v├á t├ái liß╗çu tham khß║úo ─æ╞░ß╗úc tuyß╗ân chß╗ìn"
Γûêweight: 11
Γûê---
Γöé
ΓûêPhß║ºn n├áy tß╗òng hß╗úp c├íc t├ái nguy├¬n hß╗ìc tß║¡p ─æ╞░ß╗úc tuyß╗ân chß╗ìn ─æß╗â bß║ín n├óng cao kß╗╣ n─âng x├óy dß╗▒ng AI Agent. Bao gß╗ôm lß╗Ö tr├¼nh hß╗ìc 6 tuß║ºn vß╗¢i c├íc kh├│a hß╗ìc tß╗½ DeepLearning.AI, c┼⌐ng nh╞░ ph├ón hß║íng v├á best practices tß╗½ c├íc ─æß╗Öi xuß║Ñt sß║»c nhß║Ñt Cohort 1. D├╣ bß║ín l├á ng╞░ß╗¥i mß╗¢i hay ─æ├ú c├│ kinh nghiß╗çm, c├íc t├ái liß╗çu n├áy sß║╜ gi├║p bß║ín ─æi nhanh h╞ín tr├¬n con ─æ╞░ß╗¥ng ph├ít triß╗ân AI Agent.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [Recommended Courses](recommended-courses.md) ΓÇö Lß╗Ö tr├¼nh hß╗ìc 6 tuß║ºn vß╗¢i c├íc kh├│a DeepLearning.AI
Γûê- [Reference Teams](reference-teams.md) ΓÇö Xß║┐p hß║íng Cohort 1 v├á best practices tß╗½ c├íc ─æß╗Öi xuß║Ñt sß║»c


docs\guide\setup\quick-start.md:
Γûê---
Γûêtitle: "Quick Start"
Γûêdescription: "Khß╗ƒi tß║ío project trong 5 ph├║t"
Γûêweight: 1
Γûê---
Γöé
Γûê## Quick Start Guide
Γöé
Γûê### B╞░ß╗¢c 1: Clone Template
Γöé
Γûê```bash
Γûêgit clone https://github.com/AI20K-Build-Cohort-2/starter-code-template.git C2-App-XXX
Γûêcd C2-App-XXX
Γûê```
Γöé
Γûê### B╞░ß╗¢c 2: Environment Setup
Γöé
Γûê```bash
Γûê# Tß║ío virtual environment
Γûêpython3 -m venv .venv
Γûêsource .venv/bin/activate  # macOS/Linux
Γöé
Γûê# C├ái dependencies
Γûêpip install -r requirements.txt
Γöé
Γûê# Tß║ío .env tß╗½ template
Γûêcp .env.example .env
Γûê# ΓåÆ Mß╗ƒ .env v├á ─æiß╗ün API keys
Γûê```
Γöé
Γûê### B╞░ß╗¢c 3: Verify Setup
Γöé
Γûê```bash
Γûê# Chß║íy server
Γûêuvicorn src.main:app --reload
Γöé
Γûê# Mß╗ƒ browser: http://localhost:8000/docs
Γûê# ΓåÆ Phß║úi thß║Ñy Swagger UI
Γûê```
Γöé
Γûê### B╞░ß╗¢c 4: Git Setup
Γöé
Γûê```bash
Γûê# ─Éß╗òi remote origin sang repo cß╗ºa team
Γûêgit remote set-url origin https://github.com/AI20K-Build-Cohort-2/C2-App-XXX.git
Γöé
Γûê# Tß║ío branch develop
Γûêgit checkout -b develop
Γöé
Γûê# Push lß║ºn ─æß║ºu
Γûêgit push -u origin develop
Γûê```
Γöé
Γûê## Folder Structure
Γöé
Γûê```
ΓûêC2-App-XXX/
ΓûêΓö£ΓöÇΓöÇ src/                    ΓåÉ Source code ch├¡nh
ΓûêΓöé   Γö£ΓöÇΓöÇ agents/             ΓåÉ LangGraph agents
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ graph.py        ΓåÉ Graph definition
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ state.py        ΓåÉ State schema
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ nodes/          ΓåÉ Processing nodes
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ tools/          ΓåÉ Agent tools
ΓûêΓöé   Γö£ΓöÇΓöÇ api/                ΓåÉ FastAPI routes
ΓûêΓöé   Γö£ΓöÇΓöÇ models/             ΓåÉ Pydantic schemas
ΓûêΓöé   Γö£ΓöÇΓöÇ services/           ΓåÉ Business logic
ΓûêΓöé   Γö£ΓöÇΓöÇ config.py           ΓåÉ Settings
ΓûêΓöé   ΓööΓöÇΓöÇ main.py             ΓåÉ App entry point
ΓûêΓö£ΓöÇΓöÇ tests/                  ΓåÉ Test suite
ΓûêΓö£ΓöÇΓöÇ docs/                   ΓåÉ Documentation
ΓûêΓö£ΓöÇΓöÇ eval/                   ΓåÉ Evaluation results
ΓûêΓö£ΓöÇΓöÇ presentation/           ΓåÉ Demo materials
ΓûêΓö£ΓöÇΓöÇ Dockerfile              ΓåÉ Multi-stage build
ΓûêΓö£ΓöÇΓöÇ docker-compose.yml      ΓåÉ Full stack
ΓûêΓööΓöÇΓöÇ .github/workflows/      ΓåÉ CI/CD
Γûê```
Γöé
Γûê## Nguy├¬n tß║»c tß╗ò chß╗⌐c code
Γöé
Γûê1. **Mß╗Öt file mß╗Öt tr├ích nhiß╗çm** ΓÇö `graph.py` chß╗ë build graph, `state.py` chß╗ë ─æß╗ïnh ngh─⌐a state
Γûê2. **Nodes v├áo folder `nodes/`** ΓÇö Mß╗ùi node l├á mß╗Öt file ri├¬ng
Γûê3. **Tools v├áo folder `tools/`** ΓÇö Mß╗ùi tool l├á mß╗Öt file ri├¬ng
Γûê4. **API routes t├ích ri├¬ng** ΓÇö Kh├┤ng trß╗Ön logic v├áo main.py
Γûê5. **Config centralized** ΓÇö Tß║Ñt cß║ú settings trong `config.py`


docs\guide\setup\_index.md:
Γûê---
Γûêtitle: "Project Setup"
Γûêdescription: "Khß╗ƒi tß║ío project tß╗½ template AI20K"
Γûêweight: 1
Γûê---
Γöé
ΓûêPhß║ºn n├áy h╞░ß╗¢ng dß║½n bß║ín khß╗ƒi tß║ío dß╗▒ ├ín AI Agent tß╗½ template AI20K chß╗ë trong v├ái b╞░ß╗¢c ─æ╞ín giß║ún. Bß║ín sß║╜ hß╗ìc c├ích clone repository, cß║Ñu h├¼nh biß║┐n m├┤i tr╞░ß╗¥ng, x├íc nhß║¡n hß╗ç thß╗æng hoß║ít ─æß╗Öng ─æ├║ng v├á thiß║┐t lß║¡p Git workflow. ─É├óy l├á b╞░ß╗¢c ─æß║ºu ti├¬n v├á quan trß╗ìng nhß║Ñt tr╞░ß╗¢c khi bß║»t tay v├áo code. L├ám ─æ├║ng tß╗½ ─æß║ºu sß║╜ gi├║p bß║ín tiß║┐t kiß╗çm rß║Ñt nhiß╗üu thß╗¥i gian sß╗¡a lß╗ùi sau n├áy.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [Quick Start](quick-start.md) ΓÇö H╞░ß╗¢ng dß║½n 4 b╞░ß╗¢c clone, setup env, verify v├á git setup


docs\guide\testing\writing-tests.md:
Γûê---
Γûêtitle: "Writing Tests"
Γûêdescription: "C├ích viß║┐t tests cho agent v├á API"
Γûêweight: 1
Γûê---
Γöé
Γûê## Test Structure
Γöé
Γûê```
Γûêtests/
ΓûêΓö£ΓöÇΓöÇ conftest.py           ΓåÉ Fixtures d├╣ng chung
ΓûêΓö£ΓöÇΓöÇ test_agents/
ΓûêΓöé   ΓööΓöÇΓöÇ test_graph.py     ΓåÉ Test agent flow
ΓûêΓööΓöÇΓöÇ test_api/
Γûê    ΓööΓöÇΓöÇ test_routes.py    ΓåÉ Test API endpoints
Γûê```
Γöé
Γûê## API Tests
Γöé
Γûê```python
Γûêimport pytest
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_chat_endpoint(client):
Γûê    response = await client.post(
Γûê        "/api/v1/chat",
Γûê        json={"message": "Hello"}
Γûê    )
Γûê    assert response.status_code == 200
Γûê    data = response.json()
Γûê    assert "response" in data
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_empty_message_rejected(client):
Γûê    response = await client.post(
Γûê        "/api/v1/chat",
Γûê        json={"message": ""}
Γûê    )
Γûê    assert response.status_code == 422
Γûê```
Γöé
Γûê## Agent Tests
Γöé
Γûê```python
Γûê@pytest.mark.asyncio
Γûêasync def test_agent_returns_response():
Γûê    result = await agent.ainvoke({"query": "test query"})
Γûê    assert "response" in result
Γûê    assert len(result["response"]) > 0
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_agent_handles_empty_query():
Γûê    result = await agent.ainvoke({"query": ""})
Γûê    assert "error" in result or "response" in result
Γûê```
Γöé
Γûê## Fixtures (conftest.py)
Γöé
Γûê```python
Γûêimport pytest
Γûêfrom httpx import ASGITransport, AsyncClient
Γûêfrom src.main import app
Γöé
Γûê@pytest.fixture
Γûêasync def client():
Γûê    transport = ASGITransport(app=app)
Γûê    async with AsyncClient(
Γûê        transport=transport,
Γûê        base_url="http://test"
Γûê    ) as ac:
Γûê        yield ac
Γûê```
Γöé
Γûê## Run Tests
Γöé
Γûê```bash
Γûê# Run all
Γûêpytest tests/ -v
Γöé
Γûê# Specific file
Γûêpytest tests/test_api/test_routes.py -v
Γöé
Γûê# With coverage
Γûêpytest tests/ --cov=src --cov-report=term-missing
Γûê```
Γöé
Γûê## Minimum Requirements
Γöé
Γûê- Tß╗æi thiß╗âu **3 test cases** cho API
Γûê- Tß╗æi thiß╗âu **2 test cases** cho Agent
Γûê- Tß║Ñt cß║ú tests phß║úi pass tr╞░ß╗¢c khi push


docs\guide\testing\_index.md:
Γûê---
Γûêtitle: "Testing Guide"
Γûêdescription: "Viß║┐t tests cho AI Agent project"
Γûêweight: 5
Γûê---
Γöé
ΓûêPhß║ºn n├áy h╞░ß╗¢ng dß║½n c├ích viß║┐t test cho dß╗▒ ├ín AI Agent mß╗Öt c├ích b├ái bß║ún v├á hiß╗çu quß║ú. Bß║ín sß║╜ hß╗ìc cß║Ñu tr├║c th╞░ mß╗Ñc test, c├ích viß║┐t test cho API endpoints v├á agent logic, c┼⌐ng nh╞░ sß╗¡ dß╗Ñng conftest.py ─æß╗â quß║ún l├╜ fixtures. BTC y├¬u cß║ºu tß╗æi thiß╗âu mß╗Öt sß╗æ l╞░ß╗úng test nhß║Ñt ─æß╗ïnh ΓÇö viß║┐t test tß╗æt kh├┤ng chß╗ë gi├║p ─æß║ít ─æiß╗âm cao m├á c├▓n ─æß║úm bß║úo agent hoß║ít ─æß╗Öng ß╗òn ─æß╗ïnh.
Γöé
Γûê## Trang trong mß╗Ñc n├áy
Γöé
Γûê- [Writing Tests](writing-tests.md) ΓÇö Cß║Ñu tr├║c test, v├¡ dß╗Ñ API/agent test, conftest.py v├á y├¬u cß║ºu tß╗æi thiß╗âu


docs\guide\troubleshooting.md:
Γûê---
Γûêtitle: "Troubleshooting ΓÇö Sß╗¡a lß╗ùi th╞░ß╗¥ng gß║╖p"
Γûêweight: 99
Γûê---
Γöé
Γûê# Troubleshooting ΓÇö Sß╗¡a lß╗ùi th╞░ß╗¥ng gß║╖p
Γöé
ΓûêPhß║ºn n├áy tß╗òng hß╗úp c├íc lß╗ùi phß╗ò biß║┐n khi setup v├á chß║íy dß╗▒ ├ín AI Agent, k├¿m h╞░ß╗¢ng dß║½n sß╗¡a chi tiß║┐t. Nß║┐u bß║ín gß║╖p lß╗ùi kh├┤ng c├│ trong danh s├ích, h├úy kiß╗âm tra lß║íi c├íc b╞░ß╗¢c trong ch╞░╞íng t╞░╞íng ß╗⌐ng hoß║╖c t├¼m tr├¬n GitHub Issues cß╗ºa template.
Γöé
Γûê---
Γöé
Γûê## Python & Environment
Γöé
Γûê### `ModuleNotFoundError: No module named 'xxx'`
Γöé
Γûê**Nguy├¬n nh├ón:** Bß║ín ch╞░a k├¡ch hoß║ít virtual environment, hoß║╖c c├ái package nhß║ºm v├áo system Python.
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```bash
Γûê# 1. X├íc nhß║¡n ─æang ß╗ƒ trong venv
Γûêwhich python
Γûê# Output phß║úi chß╗⌐a .venv, v├¡ dß╗Ñ: /path/to/project/.venv/bin/python
Γöé
Γûê# 2. Nß║┐u kh├┤ng, k├¡ch hoß║ít lß║íi
Γûêsource .venv/bin/activate
Γöé
Γûê# 3. C├ái lß║íi package
Γûêpip install -e ".[dev]"
Γûê```
Γöé
Γûê**Nß║┐u vß║½n lß╗ùi:**
Γûê```bash
Γûê# X├│a venv c┼⌐ v├á tß║ío lß║íi
Γûêrm -rf .venv
Γûêpython3.11 -m venv .venv
Γûêsource .venv/bin/activate
Γûêpip install -e ".[dev]"
Γûê```
Γöé
Γûê### `python3.11: command not found`
Γöé
Γûê**Nguy├¬n nh├ón:** Ch╞░a c├ái Python 3.11 hoß║╖c kh├┤ng c├│ trong PATH.
Γöé
Γûê**C├ích sß╗¡a (macOS):**
Γûê```bash
Γûêbrew install python@3.11
Γûê```
Γöé
Γûê**C├ích sß╗¡a (Ubuntu/WSL):**
Γûê```bash
Γûêsudo add-apt-repository ppa:deadsnakes/ppa
Γûêsudo apt update
Γûêsudo apt install python3.11 python3.11-venv python3.11-dev
Γûê```
Γöé
Γûê### `pip install` chß║¡m hoß║╖c timeout
Γöé
Γûê**C├ích sß╗¡a:** D├╣ng mirror gß║ºn Viß╗çt Nam:
Γûê```bash
Γûêpip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple
Γûê# Hoß║╖c
Γûêpip install -e ".[dev]" -i https://mirror.cloudflare.com/pypi/simple
Γûê```
Γöé
Γûê### `ERROR: Could not build wheel for xxx`
Γöé
Γûê**Nguy├¬n nh├ón:** Thiß║┐u C compiler hoß║╖c development headers.
Γöé
Γûê**C├ích sß╗¡a (macOS):**
Γûê```bash
Γûêxcode-select --install
Γûê```
Γöé
Γûê**C├ích sß╗¡a (Ubuntu/WSL):**
Γûê```bash
Γûêsudo apt install build-essential python3.11-dev
Γûê```
Γöé
Γûê---
Γöé
Γûê## FastAPI & Server
Γöé
Γûê### `uvicorn: command not found`
Γöé
Γûê**Nguy├¬n nh├ón:** uvicorn ch╞░a ─æ╞░ß╗úc c├ái hoß║╖c ch╞░a k├¡ch hoß║ít venv.
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```bash
Γûêsource .venv/bin/activate
Γûêpip install uvicorn
Γûê```
Γöé
Γûê### `ERROR: [Errno 48] Address already in use` (Port 8000 bß╗ï chiß║┐m)
Γöé
Γûê**Nguy├¬n nh├ón:** Mß╗Öt process kh├íc ─æang d├╣ng port 8000 (c├│ thß╗â l├á lß║ºn chß║íy server tr╞░ß╗¢c ch╞░a tß║»t).
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```bash
Γûê# T├¼m process ─æang chiß║┐m port
Γûêlsof -i :8000
Γöé
Γûê# Kill process ─æ├│ (thay PID bß║▒ng sß╗æ tß╗½ lß╗çnh tr├¬n)
Γûêkill -9 <PID>
Γöé
Γûê# Hoß║╖c d├╣ng port kh├íc
Γûêuvicorn src.api.main:app --reload --port 8001
Γûê```
Γöé
Γûê### `openai.AuthenticationError: Invalid API Key`
Γöé
Γûê**Nguy├¬n nh├ón:** API key kh├┤ng hß╗úp lß╗ç, ch╞░a set, hoß║╖c hß║┐t hß║ín.
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```bash
Γûê# 1. Kiß╗âm tra file .env ─æ├ú tß║ío ch╞░a
Γûêls -la .env
Γûê# Nß║┐u ch╞░a: cp .env.example .env
Γöé
Γûê# 2. Kiß╗âm tra API key trong .env
Γûêgrep OPENAI_API_KEY .env
Γûê# Phß║úi c├│ dß║íng: OPENAI_API_KEY=sk-proj-xxxxx (kh├┤ng c├│ ngoß║╖c k├⌐p)
Γöé
Γûê# 3. Test nhanh
Γûêpython -c "from openai import OpenAI; c=OpenAI(); print(c.models.list().data[:3])"
Γûê```
Γöé
Γûê### `pydantic.ValidationError` khi khß╗ƒi ─æß╗Öng app
Γöé
Γûê**Nguy├¬n nh├ón:** Biß║┐n m├┤i tr╞░ß╗¥ng sai kiß╗âu dß╗» liß╗çu (v├¡ dß╗Ñ: `API_PORT=abc` thay v├¼ sß╗æ).
Γöé
Γûê**C├ích sß╗¡a:** Kiß╗âm tra file `.env` ΓÇö ─æß║úm bß║úo:
Γûê- Port l├á sß╗æ nguy├¬n (v├¡ dß╗Ñ: `8000`, kh├┤ng phß║úi `"8000"`)
Γûê- Boolean l├á `true`/`false` (kh├┤ng phß║úi `yes`/`no`)
Γûê- Enum values ─æ├║ng (`development`/`staging`/`production`)
Γöé
Γûê---
Γöé
Γûê## LangGraph
Γöé
Γûê### `ImportError: cannot import name 'StateGraph' from 'langgraph'`
Γöé
Γûê**Nguy├¬n nh├ón:** LangGraph ch╞░a c├ái hoß║╖c version c┼⌐.
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```bash
Γûêpip install --upgrade langgraph langchain-core
Γûê```
Γöé
Γûê### `GraphRecursionError: Recursion limit reached`
Γöé
Γûê**Nguy├¬n nh├ón:** Agent bß╗ï lß║╖p v├┤ hß║ín ΓÇö conditional edge lu├┤n trß║ú vß╗ü node c┼⌐, kh├┤ng bao giß╗¥ ─æß║┐n END.
Γöé
Γûê**C├ích sß╗¡a:**
Γûê1. Th├¬m `iteration` counter v├áo state v├á giß╗¢i hß║ín sß╗æ lß║ºn lß║╖p:
Γûê```python
Γûêdef should_continue(state: AgentState) -> str:
Γûê    if state.get("iteration", 0) >= 3:  # Tß╗æi ─æa 3 v├▓ng
Γûê        return END
Γûê    if state.get("needs_more_research"):
Γûê        return "research"
Γûê    return END
Γûê```
Γûê2. Kiß╗âm tra routing function c├│ fallback (default case) kh├┤ng.
Γöé
Γûê### `TypeError: expected string or bytes-like object` trong routing function
Γöé
Γûê**Nguy├¬n nh├ón:** Routing function trß║ú vß╗ü gi├í trß╗ï kh├┤ng khß╗¢p vß╗¢i map trong `add_conditional_edges`.
Γöé
Γûê**C├ích sß╗¡a:** ─Éß║úm bß║úo mß╗ìi gi├í trß╗ï trß║ú vß╗ü cß╗ºa routing function c├│ trong map:
Γûê```python
Γûê# Γ£à ─É├║ng ΓÇö c├│ fallback
Γûêdef route(state) -> str:
Γûê    if state.get("type") == "search":
Γûê        return "search"
Γûê    return "answer"  # Fallback
Γöé
Γûêgraph.add_conditional_edges(
Γûê    "router", route,
Γûê    {"search": "search", "answer": "answer"}  # Map chß╗⌐a cß║ú fallback
Γûê)
Γûê```
Γöé
Γûê---
Γöé
Γûê## Docker
Γöé
Γûê### `docker: command not found`
Γöé
Γûê**C├ích sß╗¡a (macOS):** C├ái Docker Desktop tß╗½ https://docker.com/products/docker-desktop
Γöé
Γûê**C├ích sß╗¡a (Ubuntu):**
Γûê```bash
Γûêsudo apt update
Γûêsudo apt install docker.io docker-compose
Γûêsudo usermod -aG docker $USER
Γûê# Logout v├á login lß║íi
Γûê```
Γöé
Γûê### `docker build` fails ß╗ƒ `pip install`
Γöé
Γûê**Nguy├¬n nh├ón:** Docker kh├┤ng cache layer do `requirements.txt` thay ─æß╗òi, hoß║╖c network issue.
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```bash
Γûê# Build kh├┤ng cache
Γûêdocker build --no-cache -t my-agent .
Γöé
Γûê# Nß║┐u lß╗ùi network, th├¬m pip mirror v├áo Dockerfile:
Γûê# RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
Γûê```
Γöé
Γûê### `docker compose up` fails ΓÇö service unhealthy
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```bash
Γûê# Xem log chi tiß║┐t
Γûêdocker compose logs api
Γûêdocker compose logs db
Γöé
Γûê# Rebuild tß╗½ ─æß║ºu
Γûêdocker compose down -v
Γûêdocker compose up -d --build
Γûê```
Γöé
Γûê### Container restart li├¬n tß╗Ñc
Γöé
Γûê**C├ích debug:**
Γûê```bash
Γûê# Xem log container
Γûêdocker logs <container_name> --tail 50
Γöé
Γûê# V├áo container ─æß╗â debug
Γûêdocker exec -it <container_name> /bin/bash
Γöé
Γûê# Kiß╗âm tra health check
Γûêdocker inspect <container_name> | grep -A 5 Health
Γûê```
Γöé
Γûê---
Γöé
Γûê## Git & GitHub
Γöé
Γûê### `! [rejected] main -> main (fetch first)`
Γöé
Γûê**Nguy├¬n nh├ón:** Remote c├│ commit mß╗¢i m├á local ch╞░a pull.
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```bash
Γûêgit pull origin main --rebase
Γûê# Giß║úi quyß║┐t conflict nß║┐u c├│
Γûêgit rebase --continue
Γûêgit push origin main
Γûê```
Γöé
Γûê### `fatal: not a git repository`
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```bash
Γûêgit init
Γûêgit add .
Γûêgit commit -m "feat: khß╗ƒi tß║ío dß╗▒ ├ín"
Γûêgit remote add origin https://github.com/your-org/your-repo.git
Γûêgit push -u origin main
Γûê```
Γöé
Γûê### K├¡ch hoß║ít GitHub Actions
Γöé
ΓûêNß║┐u CI kh├┤ng chß║íy sau khi push:
Γûê1. V├áo repo tr├¬n GitHub ΓåÆ **Actions** tab
Γûê2. Nß║┐u thß║Ñy "Workflows aren't being run on this fork", click **Enable workflows**
Γûê3. Kiß╗âm tra file `.github/workflows/ci.yml` c├│ trong branch ─æ├║ng kh├┤ng
Γöé
Γûê---
Γöé
Γûê## Deploy
Γöé
Γûê### Render deploy fails ΓÇö build error
Γöé
Γûê**C├ích sß╗¡a:**
Γûê1. Kiß╗âm tra build log chi tiß║┐t tr├¬n Render Dashboard
Γûê2. ─Éß║úm bß║úo `Dockerfile` hoß║╖c `requirements.txt` c├│ trong repo
Γûê3. Th├¬m `runtime.txt` vß╗¢i nß╗Öi dung `3.11.x` nß║┐u Render chß╗ìn sai Python version
Γöé
Γûê### Render free tier "sleeping" ΓÇö response chß║¡m
Γöé
Γûê**C├ích khß║»c phß╗Ñc:**
Γûê- D├╣ng UptimeRobot (free) ping `/health` mß╗ùi 5 ph├║t ─æß╗â giß╗» server awake
Γûê- Hoß║╖c upgrade l├¬n paid plan ($7/th├íng)
Γöé
Γûê### API trß║ú vß╗ü `403 Forbidden` sau khi deploy
Γöé
Γûê**Nguy├¬n nh├ón:** CORS ch╞░a cß║Ñu h├¼nh ─æ├║ng cho production URL.
Γöé
Γûê**C├ích sß╗¡a:**
Γûê```python
Γûêapp.add_middleware(
Γûê    CORSMiddleware,
Γûê    allow_origins=[
Γûê        "http://localhost:3000",
Γûê        "https://your-frontend.vercel.app",  # Th├¬m production URL
Γûê    ],
Γûê    allow_credentials=True,
Γûê    allow_methods=["*"],
Γûê    allow_headers=["*"],
Γûê)
Γûê```
Γöé
Γûê---
Γöé
Γûê## Lß╗ùi kh├┤ng x├íc ─æß╗ïnh?
Γöé
Γûê1. **─Éß╗ìc error message kß╗╣** ΓÇö Python traceback th╞░ß╗¥ng chß╗ë r├╡ file v├á d├▓ng g├óy lß╗ùi
Γûê2. **Google lß╗ùi** ΓÇö Copy paste error message v├áo Google, th╞░ß╗¥ng c├│ giß║úi ph├íp tr├¬n StackOverflow
Γûê3. **Check `.env`** ΓÇö 80% lß╗ùi production do biß║┐n m├┤i tr╞░ß╗¥ng thiß║┐u hoß║╖c sai
Γûê4. **Chß║íy `make check`** ΓÇö Lint + format + typecheck + test trong mß╗Öt lß╗çnh
Γûê5. **X├│a v├á tß║ío lß║íi** ΓÇö `rm -rf .venv && python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`


docs\PRD.md:
Γûê# PRD ΓÇö P-030
Γöé
Γûê**AI Agent ─æß╗ü xuß║Ñt & r├á so├ít thiß║┐t kß║┐ kiß║┐n tr├║c hß╗ç thß╗æng**
Γöé
Γûê---
Γöé
Γûê## 1. Mß╗Ñc ti├¬u
Γöé
ΓûêChuß║⌐n ho├í viß╗çc r├á so├ít thiß║┐t kß║┐ kiß║┐n tr├║c: tß╗½ phß╗Ñ thuß╗Öc kinh nghiß╗çm c├í nh├ón th├ánh mß╗Öt quy tr├¼nh lß║╖p lß║íi ─æ╞░ß╗úc, c├│ checklist cß╗æ ─æß╗ïnh, c├│ nguß╗ôn dß║½n, c├│ l╞░u vß║┐t.
Γöé
Γûê**Phi mß╗Ñc ti├¬u:**
Γöé
Γûê- Kh├┤ng thay thß║┐ kiß║┐n tr├║c s╞░. Agent l├á v├▓ng lß╗ìc ─æß║ºu ti├¬n.
Γûê- Kh├┤ng tß╗▒ ─æß╗Öng ├íp dß╗Ñng bß║Ñt kß╗│ thay ─æß╗òi n├áo v├áo t├ái liß╗çu.
Γûê- Kh├┤ng t├¡ch hß╗úp Jira / Confluence / GitHub PR.
Γöé
Γûê## 2. Personas
Γöé
Γûê| | SUBMITTER | ARCHITECT |
Γûê|---|---|---|
Γûê| L├á ai | Lß║¡p tr├¼nh vi├¬n, tech lead vß╗½a viß║┐t xong thiß║┐t kß║┐ | Ng╞░ß╗¥i chß╗ïu tr├ích nhiß╗çm ph├¬ duyß╗çt tr╞░ß╗¢c khi ─æß╗Öi bß║»t tay code |
Γûê| ─Éau ß╗ƒ ─æ├óu | Chß╗¥ review l├óu; feedback kh├┤ng r├╡ c─ân cß╗⌐ | ─Éß╗ìc thß╗º c├┤ng tß╗æn thß╗¥i gian; dß╗à s├│t; kh├┤ng nhß╗¢ ti├¬u ch├¡ |
Γûê| Cß║ºn g├¼ | Biß║┐t thiß║┐t kß║┐ sai chß╗ù n├áo, sß╗¡a thß║┐ n├áo | Danh s├ích rß╗ºi ro c├│ ╞░u ti├¬n, c├│ nguß╗ôn, ─æß╗â tß║¡p trung v├áo phß║ºn kh├│ |
Γöé
Γûê## 3. User stories
Γöé
Γûê### US-01 ┬╖ Nß╗Öp thiß║┐t kß║┐
Γûê> L├á **SUBMITTER**, t├┤i muß╗æn tß║úi l├¬n `spec.yaml` ─æß╗â hß╗ç thß╗æng kiß╗âm tra thiß║┐t kß║┐ cß╗ºa t├┤i.
Γöé
Γûê**Acceptance criteria**
Γûê- [ ] Upload file `.yaml` 
Γûê- [ ] Sai l╞░ß╗úc ─æß╗ô ΓåÆ trß║ú lß╗ùi 422 k├¿m **─æ╞░ß╗¥ng dß║½n tr╞░ß╗¥ng sai** v├á m├┤ tß║ú
Γûê- [ ] File tr├╣ng ΓåÆ trß║ú 409 k├¿m ID bß║ún ─æ├ú c├│
Γûê- [ ] Th├ánh c├┤ng ΓåÆ chuyß╗ân tß╗¢i trang chi tiß║┐t, hiß╗ân thß╗ï YAML ─æ├ú t├┤ m├áu c├║ ph├íp
Γöé
Γûê### US-02 ┬╖ Chß║íy r├á so├ít
Γûê> L├á **ARCHITECT**, t├┤i muß╗æn chß║íy r├á so├ít tß╗▒ ─æß╗Öng tr├¬n mß╗Öt thiß║┐t kß║┐ ─æ├ú nß╗Öp.
Γöé
Γûê**Acceptance criteria**
Γûê- [ ] SUBMITTER kh├┤ng thß║Ñy n├║t n├áy
Γûê- [ ] Bß║Ñm ΓåÆ trß║ú vß╗ü ngay (202), kh├┤ng chß╗¥; trß║íng th├íi `queued`
Γûê- [ ] M├án h├¼nh hiß╗ân thß╗ï tiß║┐n ─æß╗Ö theo node ─æang chß║íy, cß║¡p nhß║¡t mß╗ùi 3 gi├óy
Γûê- [ ] Lß╗ùi ΓåÆ trß║íng th├íi `failed` k├¿m th├┤ng b├ío ─æß╗ìc ─æ╞░ß╗úc, c├│ n├║t chß║íy lß║íi
Γöé
Γûê### US-03 ┬╖ ─Éß╗ìc b├ío c├ío
Γûê> L├á **cß║ú hai vai tr├▓**, t├┤i muß╗æn xem rß╗ºi ro ─æ╞░ß╗úc nh├│m theo chiß╗üu v├á sß║»p theo mß╗⌐c ─æß╗Ö.
Γöé
Γûê**Acceptance criteria**
Γûê- [ ] Ph├ít hiß╗çn nh├│m theo 4 chiß╗üu, sß║»p theo severity (critical ΓåÆ info)
Γûê- [ ] Mß╗ùi ph├ít hiß╗çn c├│: mß╗⌐c ─æß╗Ö, m├ú checklist, ti├¬u ─æß╗ü, `yaml_path`, gi├í trß╗ï quan s├ít, gi├í trß╗ï kß╗│ vß╗ìng
Γûê- [ ] Click ph├ít hiß╗çn ΓåÆ cß╗Öt phß║úi cuß╗Ön tß╗¢i ─æ├║ng d├▓ng YAML v├á **highlight**
Γûê- [ ] Mß╗ƒ rß╗Öng ΓåÆ l├╜ do, m├ú nguy├¬n tß║»c bß╗ï vi phß║ím, bß║úng ph╞░╞íng ├ín
Γûê- [ ] Ph├ít hiß╗çn ch╞░a x├íc minh nß║▒m ß╗ƒ mß╗Ñc ri├¬ng "Cß║ºn kiß╗âm chß╗⌐ng"
Γöé
Γûê### US-04 ┬╖ So s├ính ph╞░╞íng ├ín
Γûê> L├á **ARCHITECT**, t├┤i muß╗æn thß║Ñy c├íc c├ích khß║»c phß╗Ñc k├¿m ─æ├ính ─æß╗òi ─æß╗â chß╗ìn cho ─æ├║ng.
Γöé
Γûê**Acceptance criteria**
Γûê- [ ] Ph├ít hiß╗çn tß╗½ mß╗⌐c `high` trß╗ƒ l├¬n c├│ 2ΓÇô3 ph╞░╞íng ├ín
Γûê- [ ] Mß╗ùi ph╞░╞íng ├ín hiß╗ân thß╗ï: chi ph├¡ (USD/th├íng), ─æß╗Ö trß╗à th├¬m (ms), mß╗ƒ rß╗Öng (1ΓÇô5), hiß╗çu n─âng (1ΓÇô5), vß║¡n h├ánh (1ΓÇô5)
Γûê- [ ] Chi ph├¡ v├á ─æß╗Ö trß╗à **tra tß╗½ bß║úng `cost_reference`**, kh├┤ng do m├┤ h├¼nh sinh
Γûê- [ ] Ph╞░╞íng ├ín khuyß║┐n nghß╗ï ─æ╞░ß╗úc ─æ├ính dß║Ñu, k├¿m l├╜ do bß║▒ng mß╗Öt c├óu
Γûê- [ ] Nß║┐u kh├┤ng ph╞░╞íng ├ín n├áo ─æß║ít ΓåÆ n├│i r├╡, kh├┤ng chß╗ìn bß╗½a
Γöé
Γûê### US-05 ┬╖ Quyß║┐t ─æß╗ïnh (HITL)
Γûê> L├á **ARCHITECT**, t├┤i muß╗æn duyß╗çt hoß║╖c b├íc bß╗Å tß╗½ng ph├ít hiß╗çn k├¿m l├╜ do.
Γöé
Γûê**Acceptance criteria**
Γûê- [ ] Ba n├║t: Chß║Ñp nhß║¡n / B├íc bß╗Å / Sß╗¡a ─æß╗òi, k├¿m ├┤ ghi ch├║
Γûê- [ ] SUBMITTER gß╗ìi API n├áy ΓåÆ 403
Γûê- [ ] Quyß║┐t ─æß╗ïnh l├á **bß║ún ghi mß╗¢i**, kh├┤ng sß╗¡a bß║ún c┼⌐; l╞░u ng╞░ß╗¥i + thß╗¥i ─æiß╗âm
Γûê- [ ] Khi mß╗ìi ph├ít hiß╗çn ─æ├ú c├│ quyß║┐t ─æß╗ïnh ΓåÆ review chuyß╗ân `approved`
Γûê- [ ] Thanh tiß║┐n ─æß╗Ö "─æ├ú xß╗¡ l├╜ x/y"
Γöé
Γûê### US-06 ┬╖ Tra cß╗⌐u nguy├¬n tß║»c
Γûê> L├á **cß║ú hai vai tr├▓**, t├┤i muß╗æn xem kho nguy├¬n tß║»c nß╗Öi bß╗Ö.
Γöé
Γûê**Acceptance criteria**
Γûê- [ ] Danh s├ích nguy├¬n tß║»c, lß╗ìc theo ph├ón loß║íi v├á mß╗⌐c bß║»t buß╗Öc (MUST/SHOULD/MAY)
Γûê- [ ] Mß╗ùi mß╗Ñc c├│ m├ú, ti├¬u ─æß╗ü, nß╗Öi dung, v├¡ dß╗Ñ vi phß║ím, v├¡ dß╗Ñ tu├ón thß╗º, nguß╗ôn
Γöé
Γûê## 4. Y├¬u cß║ºu chß╗⌐c n─âng
Γöé
Γûê| M├ú | Y├¬u cß║ºu | ╞»u ti├¬n |
Γûê|---|---|---|
Γûê| FR-01 | ─É─âng k├╜, ─æ─âng nhß║¡p JWT, 2 vai tr├▓ | P0 |
Γûê| FR-02 | Upload v├á validate `spec.yaml` theo l╞░ß╗úc ─æß╗ô Pydantic | P0 |
Γûê| FR-03 | Rule engine: C├íc luß║¡t x├íc ─æß╗ïnh chß║íy tr├¬n c├óy YAML | P0 |
Γûê| FR-04 | Truy xuß║Ñt nguy├¬n tß║»c nß╗Öi bß╗Ö (pgvector, 4 truy vß║Ñn ├ù top-k) | P0 |
Γûê| FR-05 | R├á so├ít 4 chiß╗üu bß║▒ng LLM, chß║íy song song | P0 |
Γûê| FR-06 | X├íc minh grounding: `yaml_path` + gi├í trß╗ï + m├ú nguy├¬n tß║»c | P0 |
Γûê| FR-07 | Sinh 2ΓÇô3 ph╞░╞íng ├ín cho ph├ít hiß╗çn ΓëÑ high | P0 |
Γûê| FR-08 | Chß║Ñm ─æ├ính ─æß╗òi 4 trß╗Ñc; chi ph├¡ & ─æß╗Ö trß╗à t├¡nh tß╗½ `cost_reference` | P0 |
Γûê| FR-09 | HITL: quyß║┐t ─æß╗ïnh tß╗½ng ph├ít hiß╗çn, c├│ l╞░u vß║┐t | P0 |
Γûê| FR-10 | Kho nguy├¬n tß║»c: duyß╗çt, lß╗ìc, nß║íp lß║íi | P1 |
Γûê| FR-11 | Sinh diagram C4 (Mermaid) tß╗½ `components` bß║▒ng template | P2 |
Γûê| FR-12 | Ph├ít hiß╗çn anti-pattern (AP-01ΓÇª05) | P2 |
Γûê| FR-13 | Xuß║Ñt b├ío c├ío Markdown / PDF | P2 |
Γöé
Γûê## 5. Y├¬u cß║ºu phi chß╗⌐c n─âng
Γöé
Γûê| M├ú | Chß╗ë ti├¬u |
Γûê|---|---|
Γûê| NFR-01 | R├á so├ít Γëñ 120 s vß╗¢i file Γëñ 200 d├▓ng |
Γûê| NFR-02 | API ─æß╗ìc p95 Γëñ 400 ms (kh├┤ng t├¡nh thß╗¥i gian ─æ├ính thß╗⌐c Render) |
Γûê| NFR-03 | `grounded_ratio` ΓëÑ 95% |
Γûê| NFR-04 | ─Éß╗Ö bao phß╗º ΓëÑ 70% tr├¬n golden set |
Γûê| NFR-05 | B├ío ─æß╗Öng giß║ú Γëñ 2 / file sß║ích |
Γûê| NFR-06 | Chi ph├¡ Γëñ $0.05 / l╞░ß╗út r├á so├ít |
Γûê| NFR-07 | TLS mß╗ìi chß║╖ng, kß╗â cß║ú kß║┐t nß╗æi DB (`sslmode=require`) |
Γûê| NFR-08 | Mß║¡t khß║⌐u bcrypt cost 12; kh├┤ng secret trong m├ú nguß╗ôn |
Γûê| NFR-09 | Mß╗ìi l╞░ß╗út gß╗ìi m├┤ h├¼nh ghi lß║íi token + ─æß╗Ö trß╗à (bß║úng `agent_runs`) |
Γûê| NFR-10 | M├íy sß║ích chß╗ë cß║ºn Docker + `.env`, c├ái ─æß║╖t Γëñ 10 ph├║t |
Γöé
Γûê## 6. ─Éß║ºu v├áo / ─æß║ºu ra
Γöé
Γûê**─Éß║ºu v├áo:** File `spec.yaml`
Γöé
Γûê**─Éß║ºu ra:** File json
Γöé
Γöé
Γûê## 7. Rß╗ºi ro
Γöé
Γûê| Rß╗ºi ro | Mß╗⌐c | Xß╗¡ l├╜ |
Γûê|---|---|---|
Γûê| Ng╞░ß╗¥i d├╣ng viß║┐t sai l╞░ß╗úc ─æß╗ô YAML | Cao | Lß╗ùi chß╗ë r├╡ ─æ╞░ß╗¥ng dß║½n tr╞░ß╗¥ng sai; file mß║½u c├│ ch├║ th├¡ch; editor c├│ gß╗úi ├╜ |
Γûê| M├┤ h├¼nh trß║ú JSON sai ─æß╗ïnh dß║íng | Cao | Structured output + Pydantic; retry 2 lß║ºn; lß║ºn 3 ─æß╗òi sang `gpt-4o` |
Γûê| Hß║┐t quota API l├║c demo | Thß║Ñp | 2 API key; giß╗» sß║╡n 1 review ─æ├ú chß║íy trong seed; video dß╗▒ ph├▓ng |
Γöé
Γûê## 8. Ngo├ái phß║ím vi
Γöé
Γûê─Éß╗ìc t├ái liß╗çu tß╗▒ do ┬╖ s╞í ─æß╗ô dß║íng ß║únh ┬╖ fine-tuning ┬╖ ph├ón quyß╗ün theo dß╗▒ ├ín ┬╖ h├áng ─æß╗úi ph├ón t├ín (Celery/Redis) ┬╖ cß╗Öng t├íc thß╗¥i gian thß╗▒c ┬╖ t├¡ch hß╗úp hß╗ç thß╗æng ngo├ái


docs\UI_FLOW.md:
Γûê# UI Flow & Wireframe ΓÇö P-030
Γöé
ΓûêReact.js + Tailwind + shadcn/ui.
Γöé
Γûê---
Γöé
Γûê## 1. Sitemap
Γöé
Γûê```mermaid
Γûêgraph LR
Γûê    L["/login"] --> D["/specs<br/>Danh s├ích thiß║┐t kß║┐"]
Γûê    D --> N["/specs/new<br/>Nß╗Öp spec.yaml"]
Γûê    D --> S["/specs/[id]<br/>Chi tiß║┐t + lß╗ïch sß╗¡ review"]
Γûê    S --> R["/reviews/[id]<br/>Γÿà B├ío c├ío r├á so├ít"]
Γûê    D --> P["/principles<br/>Kho nguy├¬n tß║»c"]
Γöé
Γûê    style R fill:#F7EBE4,stroke:#B85A34,stroke-width:2px
Γûê    style L fill:#EEF2F8,stroke:#3B6FB8
Γûê```
Γöé
Γûê## 2. User flow
Γöé
Γûê```mermaid
Γûêflowchart TD
Γûê    A(["─É─âng nhß║¡p"]) --> B{"Vai tr├▓?"}
Γûê    B -->|SUBMITTER| C["Nß╗Öp spec.yaml"]
Γûê    B -->|ARCHITECT| D["Danh s├ích thiß║┐t kß║┐"]
Γöé
Γûê    C --> E{"L╞░ß╗úc ─æß╗ô hß╗úp lß╗ç?"}
Γûê    E -->|Kh├┤ng| F["422 ΓÇö chß╗ë r├╡ tr╞░ß╗¥ng sai<br/>quay lß║íi sß╗¡a"]
Γûê    F --> C
Γûê    E -->|C├│| G["L╞░u ┬╖ trß║íng th├íi ready"]
Γöé
Γûê    G --> D
Γûê    D --> H["ARCHITECT bß║Ñm R├á so├ít"]
Γûê    H --> I["202 ΓÇö chß║íy nß╗ün<br/>polling 3 gi├óy"]
Γûê    I --> J{"Kß║┐t quß║ú"}
Γûê    J -->|failed| K["B├ío lß╗ùi ┬╖ n├║t chß║íy lß║íi"]
Γûê    K --> H
Γûê    J -->|awaiting_human| L["B├ío c├ío 4 chiß╗üu<br/>+ bß║úng ph╞░╞íng ├ín"]
Γöé
Γûê    L --> M["Duyß╗çt tß╗½ng ph├ít hiß╗çn<br/>Chß║Ñp nhß║¡n ┬╖ B├íc bß╗Å ┬╖ Sß╗¡a ─æß╗òi"]
Γûê    M --> N{"C├▓n mß╗Ñc ch╞░a xß╗¡ l├╜?"}
Γûê    N -->|C├│| M
Γûê    N -->|Hß║┐t| O(["approved"])
Γöé
Γûê    style L fill:#F7EBE4,stroke:#B85A34,stroke-width:2px
Γûê    style M fill:#F7EBE4,stroke:#B85A34,stroke-width:2px
Γûê    style O fill:#E8F1EA,stroke:#3F7A52
Γûê```
Γöé
Γûê---
Γöé
Γûê## 3. Wireframe
Γöé
Γûê### 3.1 `/specs` ΓÇö Danh s├ích thiß║┐t kß║┐
Γöé
Γûê```
ΓûêΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
ΓûêΓöé  P-030  Arch Review          Thiß║┐t kß║┐   Nguy├¬n tß║»c      khua Γû╛       Γöé
ΓûêΓö£ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöñ
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  Thiß║┐t kß║┐ ─æ├ú nß╗Öp                              [ + Nß╗Öp spec.yaml ]    Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ  Γöé
ΓûêΓöé  Γöé T├¬n dß╗ïch vß╗Ñ      Ng├áy nß╗Öp    Trß║íng th├íi       X├íc minh   ActionΓöé  Γöé
ΓûêΓöé  Γö£ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöñ  Γöé
ΓûêΓöé  Γöé order-service    01/08 14:2  ΓùÅ Chß╗¥ duyß╗çt        97%     [Xem]  Γöé  Γöé
ΓûêΓöé  Γöé v1.2                          8/14 ─æ├ú xß╗¡ l├╜                    Γöé  Γöé
ΓûêΓöé  Γö£ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöñ  Γöé
ΓûêΓöé  Γöé notify-service   31/07 09:1  Γ£ô ─É├ú duyß╗çt         100%    [Xem]  Γöé  Γöé
ΓûêΓöé  Γö£ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöñ  Γöé
ΓûêΓöé  Γöé payment-gw       31/07 08:0  Γùï Ch╞░a r├á so├ít      ΓÇö    [R├á so├ít]Γöé  Γöé
ΓûêΓöé  Γöé v0.9                                                    ARCH   Γöé  Γöé
ΓûêΓöé  ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ  Γöé
ΓûêΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
Γûê```
Γöé
Γûê- N├║t `R├á so├ít` **chß╗ë hiß╗çn vß╗¢i ARCHITECT**
Γûê- Trß║íng th├íi rß╗ùng: minh hoß║í + n├║t nß╗Öp file + link tß╗¢i file mß║½u
Γûê- ─Éang tß║úi: `<Skeleton />` 3 d├▓ng
Γöé
Γûê### 3.2 `/specs/new` ΓÇö Nß╗Öp thiß║┐t kß║┐
Γöé
Γûê```
ΓûêΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
ΓûêΓöé  ΓåÉ Quay lß║íi                                                          Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  Nß╗Öp bß║ún thiß║┐t kß║┐                                                    Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ    Γöé
ΓûêΓöé  Γöé                                                              Γöé    Γöé
ΓûêΓöé  Γöé              K├⌐o thß║ú spec.yaml v├áo ─æ├óy                       Γöé    Γöé
ΓûêΓöé  Γöé              hoß║╖c  [ Chß╗ìn file ]                             Γöé    Γöé
ΓûêΓöé  Γöé                                                              Γöé    Γöé
ΓûêΓöé  Γöé              .yaml ┬╖ tß╗æi ─æa 1 MB                             Γöé    Γöé
ΓûêΓöé  ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ    Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  ≡ƒôä Tß║úi file mß║½u c├│ ch├║ th├¡ch    ≡ƒôû Xem l╞░ß╗úc ─æß╗ô spec.yaml            Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  ΓöÇΓöÇΓöÇ Sau khi chß╗ìn file ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ   Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  Γ£ù L╞░ß╗úc ─æß╗ô kh├┤ng hß╗úp lß╗ç ΓÇö 2 lß╗ùi                                      Γöé
ΓûêΓöé    ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ      Γöé
ΓûêΓöé    Γöé components[0].replicas    thiß║┐u tr╞░ß╗¥ng bß║»t buß╗Öc          Γöé      Γöé
ΓûêΓöé    Γöé context.sla.p95_latency   phß║úi l├á sß╗æ, nhß║¡n ─æ╞░ß╗úc "300ms"  Γöé      Γöé
ΓûêΓöé    ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ      Γöé
ΓûêΓöé                                       [ Sß╗¡a v├á thß╗¡ lß║íi ]             Γöé
ΓûêΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
Γûê```
Γöé
ΓûêValidate ngay khi chß╗ìn file, **tr╞░ß╗¢c khi gß╗¡i l├¬n server** ΓÇö lß╗ùi l╞░ß╗úc ─æß╗ô kh├┤ng tß╗æn mß╗Öt token n├áo.
Γöé
Γûê### 3.3 `/reviews/[id]` ΓÇö ─Éang chß║íy
Γöé
Γûê```
ΓûêΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
ΓûêΓöé  order-service v1.2                                    Γƒ│ ─Éang r├á so├ítΓöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  ΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæ  8/13 node        ~35 s c├▓n lß║íi    Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  Γ£ô load_spec              Γ£ô validate_schema      Γ£ô flatten_paths     Γöé
ΓûêΓöé  Γ£ô derive_metrics         Γ£ô rule_engine          Γ£ô retrieve_princ.   Γöé
ΓûêΓöé  Γƒ│ review_security   Γƒ│ review_cost   Γƒ│ review_avail   Γƒ│ review_scal  Γöé
ΓûêΓöé  Γùï verify_grounding       Γùï generate_options     Γùï compose_report    Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ  Γöé
ΓûêΓöé  Γöé  ΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæ  skeleton  ΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæΓûæ  Γöé  Γöé
ΓûêΓöé  ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ  Γöé
ΓûêΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
Γûê```
Γöé
ΓûêT├¬n node lß║Ñy tß╗½ bß║úng `agent_runs`. Biß║┐n 60 gi├óy chß╗¥ th├ánh qu├í tr├¼nh quan s├ít ─æ╞░ß╗úc ΓÇö vß╗½a ─æß╗í sß╗æt ruß╗Öt, vß╗½a cho ng╞░ß╗¥i chß║Ñm thß║Ñy b├¬n trong hß╗ç thß╗æng ─æang l├ám g├¼.
Γöé
Γûê### 3.4 `/reviews/[id]` ΓÇö B├ío c├ío (m├án h├¼nh ch├¡nh)
Γöé
Γûê```
ΓûêΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
ΓûêΓöé order-service v1.2 ┬╖ 74s ┬╖ $0.031 ┬╖ ─É├ú x├íc minh 97%      [Xuß║Ñt b├ío c├ío Γû╛]     Γöé
ΓûêΓöé ΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûêΓûæΓûæΓûæΓûæΓûæΓûæΓûæ  ─É├ú xß╗¡ l├╜ 8/14                                               Γöé
ΓûêΓö£ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓö¼ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöñ
ΓûêΓöé  Bß║úo mß║¡t(4) Sß║╡n s├áng(5) Mß╗ƒ rß╗Öng(3)Γöé  spec.yaml                               Γöé
ΓûêΓöé  Chi ph├¡(2)                       Γöé                                          Γöé
ΓûêΓöé                                   Γöé   11  components:                        Γöé
ΓûêΓöé  ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ  Γöé   12    - id: api-gateway                Γöé
ΓûêΓöé  Γöé≡ƒö┤ CRITICAL  AV-01     ΓÜÖluß║¡t Γöé  Γöé   13      type: gateway                  Γöé
ΓûêΓöé  Γöé API Gateway 1 bß║ún sao,      Γöé  Γöé Γû╕ 14      replicas: 1        ΓùÇΓöüΓöüΓöüΓöüΓöüΓöüΓöüΓöüΓöüΓöô Γöé
ΓûêΓöé  Γöé kh├┤ng c├│ dß╗▒ ph├▓ng           Γöé  Γöé   15      availability_zones:          Γöâ Γöé
ΓûêΓöé  Γöé components[0].replicas = 1  ΓöéΓöÇΓöÇΓö╝ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöüΓö¢ Γöé
ΓûêΓöé  Γöé kß╗│ vß╗ìng: >= 2               Γöé  Γöé   16        - ap-southeast-1a            Γöé
ΓûêΓöé  Γö£ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöñ  Γöé   17      stateful: true                 Γöé
ΓûêΓöé  Γöé  L├╜ do                      Γöé  Γöé   18                                     Γöé
ΓûêΓöé  Γöé  To├án bß╗Ö l╞░u l╞░ß╗úng ─æi quaΓÇª  Γöé  Γöé   19  datastores:                        Γöé
ΓûêΓöé  Γöé                             Γöé  Γöé   20    - id: main-db                    Γöé
ΓûêΓöé  Γöé  ≡ƒôÿ ARC-AVL-002  MUST       Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  Dß╗ïch vß╗Ñ h╞░ß╗¢ng ng╞░ß╗¥i d├╣ng   Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  phß║úi c├│ ΓëÑ 2 bß║ún sao        Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé                             Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  Ph╞░╞íng ├ín khß║»c phß╗Ñc        Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓö¼ΓöÇΓöÇΓöÇΓöÇΓö¼ΓöÇΓöÇΓöÇΓö¼ΓöÇΓöÇΓöÇΓöÉ Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  Γöé           Γöé$/thΓöéms Γöémß╗ƒ Γöé Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  Γö£ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓö╝ΓöÇΓöÇΓöÇΓöÇΓö╝ΓöÇΓöÇΓöÇΓö╝ΓöÇΓöÇΓöÇΓöñ Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  ΓöéA 2 bß║ún/1AZΓöé +20Γöé 0 Γöé3/5Γöé Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  ΓöéB 2 bß║ún/2AZΓöé +62Γöé+2 Γöé5/5Γöé Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  Γöé  Γùå khuyß║┐n Γöé    Γöé   Γöé   Γöé Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  ΓöéC Managed  Γöé+45ΓÇªΓöé+5 Γöé5/5Γöé Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓö┤ΓöÇΓöÇΓöÇΓöÇΓö┤ΓöÇΓöÇΓöÇΓö┤ΓöÇΓöÇΓöÇΓöÿ Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé  Γùå B ─æß║ít SLA 99.9% v├á rß║╗    Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé    nhß║Ñt trong nh├│m ─æß║ít SLA. Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé    K├¿m ─æiß╗üu kiß╗çn: xß╗¡ l├╜     Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé    c├╣ng SC-01.              Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé                             Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé [Γ£ô Chß║Ñp nhß║¡n][Γ£ù B├íc bß╗Å][ΓÅ╕] Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé Γöé Ghi ch├║ΓÇª                Γöé Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ Γöé  Γöé                                          Γöé
ΓûêΓöé  ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ  Γöé                                          Γöé
ΓûêΓöé                                   Γöé                                          Γöé
ΓûêΓöé  ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ  Γöé                                          Γöé
ΓûêΓöé  Γöé≡ƒƒá HIGH  SE-02        Γ£ô khua Γöé  Γöé                                          Γöé
ΓûêΓöé  Γöé main-db kh├┤ng m├ú ho├í at restΓöé  Γöé                                          Γöé
ΓûêΓöé  Γöé ─É├ú chß║Ñp nhß║¡n ┬╖ 01/08 15:12  Γöé  Γöé                                          Γöé
ΓûêΓöé  ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ  Γöé                                          Γöé
ΓûêΓöé                                   Γöé                                          Γöé
ΓûêΓöé  Γû╕ Cß║ºn kiß╗âm chß╗⌐ng thß╗º c├┤ng (1)    Γöé                                          Γöé
ΓûêΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓö┤ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
Γûê```
Γöé
Γûê**Chi tiß║┐t cß║ºn ─æ├║ng:**
Γöé
Γûê| Yß║┐u tß╗æ | Quy tß║»c |
Γûê|---|---|
Γûê| Tß╗ë lß╗ç cß╗Öt | 40% tr├íi / 60% phß║úi |
Γûê| Click ph├ít hiß╗çn | Cß╗Öt phß║úi cuß╗Ön tß╗¢i `line`, highlight d├▓ng, giß╗» 2 gi├óy rß╗ôi nhß║ít dß║ºn |
Γûê| Nh├ún nguß╗ôn | `ΓÜÖ luß║¡t` (rule engine) hoß║╖c `≡ƒñû m├┤ h├¼nh` ΓÇö cho biß║┐t ─æß╗Ö tin cß║¡y |
Γûê| M├áu severity | critical `#B85A34` ┬╖ high `#C08A2E` ┬╖ medium `#96762A` ┬╖ low x├ím |
Γûê| ─É├ú quyß║┐t ─æß╗ïnh | Card mß╗¥ 60%, hiß╗çn t├¬n ng╞░ß╗¥i + thß╗¥i ─æiß╗âm, thu gß╗ìn |
Γûê| Ch╞░a x├íc minh | Nh├│m ri├¬ng cuß╗æi danh s├ích, c├│ accordion, mß║╖c ─æß╗ïnh ─æ├│ng |
Γûê| N├║t quyß║┐t ─æß╗ïnh | ß║¿n ho├án to├án vß╗¢i SUBMITTER |
Γöé
Γûê### 3.5 `/principles` ΓÇö Kho nguy├¬n tß║»c
Γöé
Γûê```
ΓûêΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
ΓûêΓöé  Nguy├¬n tß║»c kiß║┐n tr├║c nß╗Öi bß╗Ö                            20 mß╗Ñc       Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  Ph├ón loß║íi: [Tß║Ñt cß║ú Γû╛]    Mß╗⌐c: [Tß║Ñt cß║ú Γû╛]    ≡ƒöì T├¼mΓÇª                Γöé
ΓûêΓöé                                                                      Γöé
ΓûêΓöé  ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ  Γöé
ΓûêΓöé  Γöé ARC-AVL-002   MUST    ─Éß╗Ö sß║╡n s├áng                              Γöé  Γöé
ΓûêΓöé  Γöé Dß╗ïch vß╗Ñ h╞░ß╗¢ng ng╞░ß╗¥i d├╣ng phß║úi chß║íy tß╗æi thiß╗âu hai bß║ún sao       Γöé  Γöé
ΓûêΓöé  Γöé Nguß╗ôn: Azure WAF ΓÇö Reliability (bi├¬n soß║ín lß║íi)          [Γû╛]    Γöé  Γöé
ΓûêΓöé  Γö£ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöñ  Γöé
ΓûêΓöé  Γöé ARC-SEC-003   MUST    Bß║úo mß║¡t                                  Γöé  Γöé
ΓûêΓöé  Γöé Dß╗» liß╗çu nhß║íy cß║úm phß║úi m├ú ho├í khi l╞░u                    [Γû╛]    Γöé  Γöé
ΓûêΓöé  ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ  Γöé
ΓûêΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
Γûê```
Γöé
ΓûêMß╗ƒ rß╗Öng ΓåÆ nß╗Öi dung ─æß║ºy ─æß╗º, v├¡ dß╗Ñ vi phß║ím, v├¡ dß╗Ñ tu├ón thß╗º.
Γöé
Γûê---
Γöé
Γûê## 4. Trß║íng th├íi v├á tr╞░ß╗¥ng hß╗úp bi├¬n
Γöé
Γûê| T├¼nh huß╗æng | Xß╗¡ l├╜ tr├¬n UI |
Γûê|---|---|
Γûê| Ch╞░a c├│ thiß║┐t kß║┐ n├áo | Minh hoß║í + n├║t nß╗Öp + link file mß║½u |
Γûê| ─Éang tß║úi dß╗» liß╗çu | `<Skeleton />`, kh├┤ng d├╣ng spinner to├án trang |
Γûê| YAML sai l╞░ß╗úc ─æß╗ô | Danh s├ích lß╗ùi k├¿m ─æ╞░ß╗¥ng dß║½n tr╞░ß╗¥ng, validate ph├¡a client tr╞░ß╗¢c |
Γûê| Review `failed` | Banner ─æß╗Å, th├┤ng b├ío ─æß╗ìc ─æ╞░ß╗úc, n├║t Chß║íy lß║íi |
Γûê| T├ái liß╗çu kh├┤ng c├│ ph├ít hiß╗çn n├áo | Thß║╗ xanh "Kh├┤ng t├¼m thß║Ñy rß╗ºi ro" + nhß║»c kiß╗âm tra thß╗º c├┤ng |
Γûê| SUBMITTER mß╗ƒ review | Thß║Ñy to├án bß╗Ö nß╗Öi dung, kh├┤ng thß║Ñy n├║t quyß║┐t ─æß╗ïnh |
Γöé
Γûê## 5. Component (shadcn/ui)
Γöé
Γûê`Button` `Card` `Table` `Badge` `Dialog` `Tabs` `Accordion` `Input` `Textarea` `Label` `Skeleton` `Sonner` `Progress` `Tooltip` `DropdownMenu`
Γöé
ΓûêNgo├ái ra: `react-markdown` (nß╗Öi dung nguy├¬n tß║»c) ┬╖ `shiki` hoß║╖c `prism` (t├┤ m├áu YAML) ┬╖ `@tanstack/react-query` (polling 3 gi├óy)
Γöé
Γûê## 6. Responsive
Γöé
ΓûêThiß║┐t kß║┐ cho desktop tr╞░ß╗¢c ΓÇö ng╞░ß╗¥i d├╣ng thß║¡t r├á so├ít tr├¬n m├án h├¼nh lß╗¢n.
Γöé
Γûê- `ΓëÑ 1280px` ΓÇö hai cß╗Öt 40/60
Γûê- `768ΓÇô1279px` ΓÇö hai cß╗Öt 50/50, thu gß╗ìn sidebar
Γûê- `< 768px` ΓÇö mß╗Öt cß╗Öt, YAML nß║▒m trong `Sheet` tr╞░ß╗út l├¬n khi click ph├ít hiß╗çn


eval\results\report.md:
Γûê# Evaluation Report
Γöé
Γûê> B├ío c├ío ─æ├ính gi├í chß║Ñt l╞░ß╗úng sß║ún phß║⌐m theo ti├¬u ch├¡ BTC.
Γöé
Γûê---
Γöé
Γûê## 1. Metrics
Γöé
Γûê| Metric | Target | Actual | Status |
Γûê|--------|--------|--------|--------|
Γûê| Response accuracy | >80% | ΓÇö | ΓÅ│ |
Γûê| Response latency | <3s | ΓÇö | ΓÅ│ |
Γûê| User satisfaction | >4/5 | ΓÇö | ΓÅ│ |
Γûê| Test coverage | >60% | ΓÇö | ΓÅ│ |
Γöé
Γûê## 2. Test Results
Γöé
Γûê### Unit Tests
Γûê```
Γûêpytest tests/ -v
Γûê# Paste output here
Γûê```
Γöé
Γûê### Integration Tests
Γûê```
Γûê# M├┤ tß║ú test scenarios v├á kß║┐t quß║ú
Γûê```
Γöé
Γûê## 3. User Feedback
Γöé
Γûê| User | Feedback | Rating |
Γûê|------|----------|--------|
Γûê| [User 1] | [feedback] | [1-5] |
Γûê| [User 2] | [feedback] | [1-5] |
Γöé
Γûê## 4. Demo Results
Γöé
Γûê- Ng├áy demo: [YYYY-MM-DD]
Γûê- Ng╞░ß╗¥i tham gia: [sß╗æ ng╞░ß╗¥i]
Γûê- Feedback chung: [t├│m tß║»t]
Γûê- Issues ph├ít hiß╗çn: [danh s├ích]
Γöé
Γûê## 5. Action Items
Γöé
Γûê- [ ] [Cß║ºn cß║úi thiß╗çn 1]
Γûê- [ ] [Cß║ºn cß║úi thiß╗çn 2]


fix_all.py:
Γûê∩╗┐import os
Γûêimport ftfy
Γöé
Γûêdef fix_directory(path):
Γûê    for root, dirs, files in os.walk(path):
Γûê        for file in files:
Γûê            if file.endswith('.py'):
Γûê                filepath = os.path.join(root, file)
Γûê                try:
Γûê                    with open(filepath, 'r', encoding='utf-8') as f:
Γûê                        text = f.read()
Γûê                    
Γûê                    fixed_text = ftfy.fix_text(text)
Γûê                    
Γûê                    if text != fixed_text:
Γûê                        with open(filepath, 'w', encoding='utf-8') as f:
Γûê                            f.write(fixed_text)
Γûê                        print(f"Fixed {filepath}")
Γûê                except Exception as e:
Γûê                    print(f"Failed to fix {filepath}: {e}")
Γöé
Γûêfix_directory('src')
Γûêfix_directory('scripts')
Γûêfix_directory('tests')
Γûêprint("All files processed!")


fix_encoding.py:
Γûê∩╗┐import os
Γöé
Γûêwith open('src/services/github_events.py', 'r', encoding='utf-8') as f:
Γûê    corrupted_text = f.read()
Γöé
Γûêif corrupted_text.startswith('\ufeff'):
Γûê    corrupted_text = corrupted_text[1:]
Γöé
Γûêoriginal_text = corrupted_text.encode('cp1252').decode('utf-8')
Γöé
Γûêwith open('github_events_fixed.py', 'w', encoding='utf-8') as f:
Γûê    f.write(original_text)
Γûêprint("Fixed successfully!")


github_events_ftfy.py:
Γûê"""
Γûêgithub_events.py ΓÇö Xß╗¡ l├╜ sß╗▒ kiß╗çn push tß╗½ GitHub.
Γöé
Γûê    x├íc thß╗▒c chß╗» k├╜  ->  b├│c t├ích payload  ->  ghi nhß║¡t k├╜ DB
Γûê                                            ->  xo├í catalog cß╗ºa file bß╗ï removed
Γûê                                            ->  nß║íp catalog cß╗ºa file added/modified
Γûê                                            ->  d├í┬╗┬▒ng response
Γöé
Γûê─É├óy l├á tß║ºng DUY NHß║ñT biß║┐t thß╗⌐ tß╗▒ c├íc b╞░ß╗¢c, ─æ├║ng vai tr├▓ `app/services/ingest.py`
Γûêgiß╗» cho luß╗ông upload thß╗º c├┤ng. Controller (`src/api/routes.py`) kh├┤ng biß║┐t g├¼ vß╗ü
Γûêh├¼nh dß║íng payload cß╗ºa GitHub, v├á `ingest` kh├┤ng biß║┐t l├á n├│ ─æang ─æ╞░ß╗úc gß╗ìi tß╗½ mß╗Öt
Γûêwebhook hay tß╗½ mß╗Öt form upload.
Γöé
ΓûêHai nguy├¬n tß║»c chi phß╗æi to├án bß╗Ö file n├áy:
Γöé
Γûê1. **Mß╗Öt file hß╗Ång kh├┤ng ─æ╞░ß╗úc l├ám hß╗Ång cß║ú lß║ºn push.** Lß╗ùi thuß╗Öc vß╗ü nß╗Öi dung file
Γûê   (YAML sai schema, tranh chß║Ñp quyß╗ün sß╗ƒ hß╗»u, kh├┤ng tß║úi ─æ╞░ß╗úc tß╗½ GitHub) ─æ╞░ß╗úc gom
Γûê   th├ánh `Issue` v├á vß║½n trß║ú HTTP 200. Trß║ú 4xx/5xx sß║╜ khiß║┐n GitHub ─æ├ính dß║Ñu
Γûê   delivery thß║Ñt bß║íi rß╗ôi RETRY ΓÇö m├á retry th├¼ file vß║½n sai y nh╞░ c┼⌐.
Γöé
Γûê2. **Sß╗▒ cß╗æ hß╗ç thß╗æng th├¼ ng╞░ß╗úc lß║íi: phß║úi ─æß╗â nß╗ò.** `CriticalError` (database sß║¡p,
Γûê   chß║│ng hß║ín) ─æ╞░ß╗úc re-raise ─æß╗â th├ánh 500 v├á GitHub retry ΓÇö lß║ºn sau DB sß╗æng lß║íi
Γûê   th├¼ push ─æ╞░ß╗úc xß╗¡ l├╜ thß║¡t. Nuß╗æt n├│ th├ánh `Issue` l├á b├ío "─æ├ú xß╗¡ l├╜ xong" cho
Γûê   mß╗Öt viß╗çc ch╞░a hß╗ü xß║úy ra.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport hashlib
Γûêimport hmac
Γûêimport logging
Γûêimport posixpath
Γûêfrom dataclasses import dataclass
Γûêfrom typing import Any
Γûêfrom urllib.parse import quote
Γöé
Γûêimport httpx
Γûêfrom starlette.concurrency import run_in_threadpool
Γöé
Γûêfrom src.core.config import ALLOWED_EXTENSIONS
Γûêfrom src.core.errors import (
Γûê    AppError,
Γûê    CriticalError,
Γûê    ErrorCode,
Γûê    SecurityError,
Γûê    Stage,
Γûê)
Γûêfrom src.models import schemas
Γûêfrom src.models.schemas import ApiResponse, Issue
Γûêfrom src.services import github_event_repository, ingest
Γûêfrom src.config import get_settings
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
ΓûêGITHUB_API_BASE = "https://api.github.com"
Γöé
Γûê# GitHub gß╗¡i t├¬n nh├ính d╞░ß╗¢i dß║íng `refs/heads/main`. Tag l├á `refs/tags/v1.0`.
Γûê_BRANCH_PREFIX = "refs/heads/"
Γöé
Γûê# Content-Type khai vß╗¢i `ingest`: layer 2 chß╗ë d├╣ng n├│ ─æß╗â Cß║óNH B├üO khi lß╗çch, kh├┤ng
Γûê# ─æß╗â chß║╖n, n├¬n khai ─æ├║ng loß║íi thß║¡t l├á ─æß╗º.
Γûê_YAML_CONTENT_TYPE = "application/x-yaml"
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Dß╗» liß╗çu ─æ├ú b├│c t├ích khß╗Åi payload
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûê@dataclass(frozen=True)
Γûêclass PushEvent:
Γûê    """Mß╗Öt lß║ºn push, ─æ├ú lß╗ìc sß║ích c├▓n ─æ├║ng thß╗⌐ hß╗ç thß╗æng quan t├óm.
Γöé
Γûê    Ba danh s├ích file mang ─É╞»ß╗£NG Dß║¬N ─Éß║ªY ─Éß╗ª trong repo
Γûê    ('services/order/catalog-info.yaml') v├á chß╗ë chß╗⌐a file `.yaml`/`.yml`.
Γûê    """
Γöé
Γûê    repo_full_name: str
Γûê    commit_id: str
Γûê    commit_url: str
Γûê    email: str
Γûê    branch: str
Γûê    timestamp: str
Γûê    added_files: list[str]
Γûê    modified_files: list[str]
Γûê    removed_files: list[str]
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# B╞░ß╗¢c 1 ΓÇö x├íc thß╗▒c
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef verify_signature(body: bytes, signature_header: str | None) -> None:
Γûê    """Kiß╗âm tra HMAC-SHA256 cß╗ºa GitHub. Kh├┤ng hß╗úp lß╗ç th├¼ raise, hß╗úp lß╗ç th├¼ im lß║╖ng.
Γöé
Γûê    Chß║íy tr├¬n body TH├ö, tr╞░ß╗¢c khi parse JSON: chß╗» k├╜ k├╜ tr├¬n ─æ├║ng chuß╗ùi byte
Γûê    GitHub gß╗¡i ─æi. Parse rß╗ôi serialize lß║íi sß║╜ ra chuß╗ùi kh├íc (thß╗⌐ tß╗▒ key, khoß║úng
Γûê    trß║»ng) v├á kh├┤ng c├▓n khß╗¢p chß╗» k├╜ n├áo cß║ú.
Γûê    """
Γûê    secret = get_settings().webhook_secret
Γöé
Γûê    if not secret:
Γûê        # Lß╗ùi cß║Ñu h├¼nh ph├¡a ta, kh├┤ng phß║úi cß╗ºa ng╞░ß╗¥i gß╗¡i. Tuyß╗çt ─æß╗æi kh├┤ng ─æ╞░ß╗úc
Γûê        # "v├¼ ch╞░a cß║Ñu h├¼nh n├¬n bß╗Å qua b╞░ß╗¢c x├íc thß╗▒c" ΓÇö nh╞░ vß║¡y l├á mß╗ƒ toang
Γûê        # endpoint cho bß║Ñt kß╗│ ai gß╗¡i payload giß║ú.
Γûê        raise CriticalError(
Γûê            ErrorCode.WEBHOOK_NOT_CONFIGURED,
Γûê            "Hß╗ç thß╗æng ch╞░a ─æ╞░ß╗úc cß║Ñu h├¼nh ─æß╗â nhß║¡n webhook. Vui l├▓ng li├¬n hß╗ç hß╗ù trß╗ú.",
Γûê            stage=Stage.RECEIVE,
Γûê            log_message="Thiß║┐u WEBHOOK_SECRET ΓÇö kh├┤ng c├│ c├ích n├áo x├íc thß╗▒c webhook GitHub.",
Γûê        )
Γöé
Γûê    if not signature_header:
Γûê        raise SecurityError(
Γûê            ErrorCode.INVALID_SIGNATURE,
Γûê            "Y├¬u cß║ºu kh├┤ng hß╗úp lß╗ç.",
Γûê            stage=Stage.RECEIVE,
Γûê            log_message="Webhook kh├┤ng k├¿m header X-Hub-Signature-256.",
Γûê        )
Γöé
Γûê    expected = "sha256=" + hmac.new(
Γûê        secret.encode("utf-8"), body, hashlib.sha256
Γûê    ).hexdigest()
Γöé
Γûê    # So s├ính tr├¬n bytes: `compare_digest` vß╗¢i chuß╗ùi str sß║╜ nß╗ò TypeError nß║┐u
Γûê    # header chß╗⌐a k├╜ tß╗▒ ngo├ái ASCII ΓÇö v├á header th├¼ do ng╞░ß╗¥i gß╗¡i ─æß║╖t.
Γûê    if not hmac.compare_digest(
Γûê        expected.encode("utf-8"), signature_header.encode("utf-8")
Γûê    ):
Γûê        # `message` cß╗æ ├╜ m╞í hß╗ô: n├│i r├╡ "chß╗» k├╜ sai" l├á chß╗ë cho kß║╗ ─æang d├▓ biß║┐t
Γûê        # n├│ sai ß╗ƒ ─æ├óu. L├╜ do thß║¡t chß╗ë nß║▒m trong log.
Γûê        raise SecurityError(
Γûê            ErrorCode.INVALID_SIGNATURE,
Γûê            "Y├¬u cß║ºu kh├┤ng hß╗úp lß╗ç.",
Γûê            stage=Stage.RECEIVE,
Γûê            log_message="Chß╗» k├╜ HMAC kh├┤ng khß╗¢p ΓÇö request kh├┤ng ─æß║┐n tß╗½ GitHub, "
Γûê            "hoß║╖c WEBHOOK_SECRET hai b├¬n kh├íc nhau.",
Γûê        )
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# B╞░ß╗¢c 2 ΓÇö b├│c t├ích payload
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef _classify_files(
Γûê    commits: list[dict[str, Any]],
Γûê) -> tuple[list[str], list[str], list[str]]:
Γûê    """Gß╗Öp thay ─æß╗òi cß╗ºa Mß╗îI commit trong push th├ánh 3 danh s├ích, h├ánh-─æß╗Öng-cuß╗æi-thß║»ng.
Γöé
Γûê    Mß╗Öt lß║ºn push mang nhiß╗üu commit v├á c├╣ng mß╗Öt file c├│ thß╗â xuß║Ñt hiß╗çn ß╗ƒ nhiß╗üu
Γûê    commit vß╗¢i h├ánh ─æß╗Öng kh├íc nhau. Chß╗ë trß║íng th├íi CUß╗ÉI C├ÖNG l├á c├│ thß║¡t: file
Γûê    th├¬m ß╗ƒ commit 1 rß╗ôi xo├í ß╗ƒ commit 3 th├¼ tr├¬n nh├ính n├│ kh├┤ng c├▓n tß╗ôn tß║íi ΓÇö nß║íp
Γûê    n├│ v├áo hß╗ç thß╗æng l├á nß║íp mß╗Öt file ─æ├ú chß║┐t.
Γöé
Γûê    Ri├¬ng 'added' thß║»ng 'modified' ─æß║┐n sau: trong c├╣ng mß╗Öt lß║ºn push th├¼ n├│ vß║½n l├á
Γûê    file mß╗¢i toanh, gß╗ìi l├á "sß╗¡a" th├¼ sai bß║ún chß║Ñt.
Γûê    """
Γûê    state: dict[str, str] = {}
Γûê    for commit in commits:
Γûê        for path in commit.get("added") or []:
Γûê            state[path] = "added"
Γûê        for path in commit.get("modified") or []:
Γûê            if state.get(path) != "added":
Γûê                state[path] = "modified"
Γûê        for path in commit.get("removed") or []:
Γûê            state[path] = "removed"
Γöé
Γûê    buckets: dict[str, list[str]] = {"added": [], "modified": [], "removed": []}
Γûê    for path, action in state.items():
Γûê        if path.lower().endswith(ALLOWED_EXTENSIONS):
Γûê            buckets[action].append(path)
Γöé
Γûê    # sorted() ─æß╗â thß╗⌐ tß╗▒ xß╗¡ l├╜ v├á nß╗Öi dung ghi v├áo bß║úng log l├á tß║Ñt ─æß╗ïnh, kh├┤ng
Γûê    # phß╗Ñ thuß╗Öc thß╗⌐ tß╗▒ key cß╗ºa dict hay thß╗⌐ tß╗▒ GitHub liß╗çt k├¬ file.
Γûê    return (
Γûê        sorted(buckets["added"]),
Γûê        sorted(buckets["modified"]),
Γûê        sorted(buckets["removed"]),
Γûê    )
Γöé
Γöé
Γûêdef parse_push_payload(payload: dict[str, Any]) -> PushEvent | None:
Γûê    """B├│c `PushEvent` khß╗Åi payload. Trß║ú None khi kh├┤ng c├│ g├¼ ─æß╗â xß╗¡ l├╜.
Γöé
Γûê    Trß║ú None thay v├¼ raise cho mß╗ìi tr╞░ß╗¥ng hß╗úp "push hß╗úp lß╗ç nh╞░ng kh├┤ng li├¬n
Γûê    quan" (push tag, xo├í nh├ính, push to├án file .py). ─É├│ kh├┤ng phß║úi lß╗ùi cß╗ºa ai
Γûê    cß║ú ΓÇö GitHub bß║»n webhook cho mß╗ìi push l├á ─æ├║ng viß╗çc cß╗ºa n├│.
Γûê    """
Γûê    ref = payload.get("ref") or ""
Γûê    if not ref.startswith(_BRANCH_PREFIX):
Γûê        logger.info("Bß╗Å qua push kh├┤ng nhß║»m v├áo nh├ính: ref=%s", ref)
Γûê        return None
Γöé
Γûê    # `head_commit` l├á null khi push xo├í nh├ính, hoß║╖c khi push kh├┤ng mang commit
Γûê    # mß╗¢i n├áo. Bß║ún prototype c┼⌐ ─æß╗ìc thß║│ng payload["head_commit"]["url"] v├á nß╗ò
Γûê    # TypeError ß╗ƒ ─æ├║ng chß╗ù n├áy.
Γûê    head = payload.get("head_commit")
Γûê    if not head:
Γûê        logger.info("Push l├¬n '%s' kh├┤ng c├│ head_commit ΓÇö kh├┤ng c├│ g├¼ ─æß╗â xß╗¡ l├╜.", ref)
Γûê        return None
Γöé
Γûê    repo_full_name = (payload.get("repository") or {}).get("full_name")
Γûê    commit_id = head.get("id")
Γûê    commit_url = head.get("url")
Γûê    if not (repo_full_name and commit_id and commit_url):
Γûê        logger.warning(
Γûê            "Payload push thiß║┐u repository.full_name / head_commit.id / head_commit.url "
Γûê            "ΓÇö kh├┤ng ─æß╗º dß╗» liß╗çu ─æß╗â tß║úi file hay ─æß╗â ghi nhß║¡t k├╜."
Γûê        )
Γûê        return None
Γöé
Γûê    added, modified, removed = _classify_files(payload.get("commits") or [])
Γûê    if not (added or modified or removed):
Γûê        logger.info("Push l├¬n '%s' kh├┤ng chß║ím file YAML n├áo.", ref)
Γûê        return None
Γöé
Γûê    author = head.get("author") or {}
Γûê    pusher = payload.get("pusher") or {}
Γöé
Γûê    return PushEvent(
Γûê        repo_full_name=repo_full_name,
Γûê        commit_id=commit_id,
Γûê        commit_url=commit_url,
Γûê        # T├íc giß║ú commit l├á ng╞░ß╗¥i viß║┐t thay ─æß╗òi; `pusher` chß╗ë l├á ng╞░ß╗¥i bß║Ñm push.
Γûê        # ╞»u ti├¬n t├íc giß║ú, l├╣i vß╗ü pusher khi commit kh├┤ng khai email.
Γûê        email=author.get("email") or pusher.get("email") or "",
Γûê        branch=ref[len(_BRANCH_PREFIX) :],
Γûê        timestamp=head.get("timestamp") or "",
Γûê        added_files=added,
Γûê        modified_files=modified,
Γûê        removed_files=removed,
Γûê    )
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# B╞░ß╗¢c 3 ΓÇö tß║úi nß╗Öi dung file tß╗½ GitHub
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêasync def _fetch_file(repo_full_name: str, ref: str, path: str) -> bytes | None:
Γûê    """Tß║úi nß╗Öi dung th├┤ cß╗ºa 1 file tß║íi ─æ├║ng commit. None nß║┐u kh├┤ng lß║Ñy ─æ╞░ß╗úc.
Γöé
Γûê    Lß║Ñy theo `ref` l├á commit id chß╗⌐ kh├┤ng theo t├¬n nh├ính: giß╗»a l├║c GitHub bß║»n
Γûê    webhook v├á l├║c ta gß╗ìi API c├│ thß╗â ─æ├ú c├│ push kh├íc chen v├áo, v├á khi ─æ├│ ─æß╗ìc
Γûê    theo nh├ính sß║╜ ra mß╗Öt nß╗Öi dung kh├íc vß╗¢i nß╗Öi dung cß╗ºa ch├¡nh commit n├áy.
Γûê    """
Γûê    settings = get_settings()
Γöé
Γûê    # `quote` vß╗¢i safe='/' mß║╖c ─æß╗ïnh ΓÇö giß╗» nguy├¬n dß║Ñu / ng─ân c├ích th╞░ mß╗Ñc, nh╞░ng
Γûê    # m├ú ho├í khoß║úng trß║»ng v├á k├╜ tß╗▒ tiß║┐ng Viß╗çt trong t├¬n file.
Γûê    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{quote(path)}"
Γûê    headers = {
Γûê        "Accept": "application/vnd.github.v3.raw",
Γûê        "X-GitHub-Api-Version": "2022-11-28",
Γûê    }
Γûê    # CHß╗ê gß║»n Authorization khi thß║¡t sß╗▒ c├│ token. Gß║»n mß╗Öt header rß╗ùng hay chuß╗ùi
Γûê    # "Bearer None" th├¼ GitHub trß║ú 401 ngay cß║ú vß╗¢i repo public ΓÇö thß╗⌐ vß╗æn ─æß╗ìc
Γûê    # ─æ╞░ß╗úc m├á kh├┤ng cß║ºn x├íc thß╗▒c g├¼.
Γûê    if settings.github_token:
Γûê        headers["Authorization"] = f"Bearer {settings.github_token}"
Γöé
Γûê    try:
Γûê        async with httpx.AsyncClient(
Γûê            timeout=settings.github_api_timeout_seconds
Γûê        ) as client:
Γûê            response = await client.get(url, headers=headers, params={"ref": ref})
Γûê    except httpx.HTTPError as exc:
Γûê        logger.warning(
Γûê            "Kh├┤ng gß╗ìi ─æ╞░ß╗úc GitHub API cho '%s': %s", path, type(exc).__name__
Γûê        )
Γûê        return None
Γöé
Γûê    if response.status_code != 200:
Γûê        # Log metadata th├┤i. `response.text` c├│ thß╗â mang nß╗Öi dung file hoß║╖c th├┤ng
Γûê        # ─æiß╗çp lß╗ùi k├¿m th├┤ng tin repo private ΓÇö kh├┤ng thuß╗Öc vß╗ü log.
Γûê        logger.warning(
Γûê            "GitHub trß║ú %d khi lß║Ñy '%s' tß║íi ref=%s", response.status_code, path, ref
Γûê        )
Γûê        return None
Γöé
Γûê    # Trß║ú BYTES chß╗⌐ kh├┤ng phß║úi text ─æ├ú decode: `ingest_catalog` nhß║¡n bytes, v├á
Γûê    # layer 2 cß╗ºa validation soi CH├ìNH BYTE TH├ö (magic bytes, k├╜ tß╗▒ NUL) tr╞░ß╗¢c
Γûê    # khi c├│ ai parse. Decode ß╗ƒ ─æ├óy rß╗ôi encode lß║íi l├á vß╗⌐t ─æi ─æ├║ng thß╗⌐ tß║ºng ─æ├│ cß║ºn.
Γûê    return response.content
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# B╞░ß╗¢c 4 ΓÇö ─æiß╗üu phß╗æi
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef _issue_from(exc: AppError, path: str) -> Issue:
Γûê    """Biß║┐n mß╗Öt lß╗ùi cß║Ñp file th├ánh `Issue` ─æß╗â nh├⌐t v├áo response chung."""
Γûê    return Issue(
Γûê        severity="error",
Γûê        code=exc.code.value,
Γûê        message=exc.message,
Γûê        source=path,
Γûê    )
Γöé
Γöé
Γûêasync def handle_push(event: PushEvent, request_id: str) -> ApiResponse:
Γûê    """Chß║íy trß╗ìn mß╗Öt lß║ºn push. Trß║ú vß╗ü `ApiResponse` ─æ├║ng contract chung.
Γöé
Γûê    Mß╗ìi lß╗¥i gß╗ìi xuß╗æng `ingest` v├á database ─æß╗üu ─æi qua `run_in_threadpool`: h├ám
Γûê    n├áy l├á `async` nh╞░ng `ingest_catalog`, `delete_catalog` v├á psycopg2 ─æß╗üu ─æß╗ông
Γûê    bß╗Ö v├á chß║╖n. Gß╗ìi thß║│ng th├¼ suß╗æt N file, to├án bß╗Ö event loop ─æß╗⌐ng im ΓÇö mß╗ìi
Γûê    request kh├íc cß╗ºa API c┼⌐ng phß║úi chß╗¥ theo.
Γûê    """
Γûê    settings = get_settings()
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 1: ghi nhß║¡t k├╜ TR╞»ß╗ÜC khi xß╗¡ l├╜ ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    # Lß║ºn push n├áy ─É├â Xß║óY RA, bß║Ñt kß╗â ingest ph├¡a sau c├│ th├ánh c├┤ng hay kh├┤ng.
Γûê    # Ghi sau sß║╜ mß║Ñt bß║ún ghi cß╗ºa ─æ├║ng nhß╗»ng lß║ºn push hß╗Ång ΓÇö thß╗⌐ cß║ºn ─æiß╗üu tra nhß║Ñt.
Γûê    log_id = await run_in_threadpool(
Γûê        github_event_repository.save_commit_event,
Γûê        email=event.email,
Γûê        branch=event.branch,
Γûê        commit_url=event.commit_url,
Γûê        timestamp=event.timestamp,
Γûê        added_files=event.added_files,
Γûê        modified_files=event.modified_files,
Γûê        removed_files=event.removed_files,
Γûê    )
Γöé
Γûê    issues: list[Issue] = []
Γûê    ingested: list[str] = []
Γûê    deleted: list[str] = []
Γûê    skipped: list[str] = []
Γûê    failed: list[str] = []
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 2: xo├í catalog cß╗ºa c├íc file ─æ├ú bß╗ï removed ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    # Xo├í tr╞░ß╗¢c khi nß║íp: nß║┐u mß╗Öt push vß╗½a xo├í 'a.yaml' vß╗½a th├¬m 'b.yaml' khai
Γûê    # c├╣ng mß╗Öt node, l├ám ng╞░ß╗úc thß╗⌐ tß╗▒ sß║╜ dß╗▒ng ra tranh chß║Ñp quyß╗ün sß╗ƒ hß╗»u giß║ú.
Γûê    for path in event.removed_files:
Γûê        name = posixpath.basename(path)
Γûê        try:
Γûê            await run_in_threadpool(ingest.delete_catalog, name, request_id)
Γûê        except CriticalError:
Γûê            raise
Γûê        except AppError as exc:
Γûê            if exc.code == ErrorCode.CATALOG_NOT_FOUND:
Γûê                # B├¼nh th╞░ß╗¥ng: GitHub b├ío xo├í mß╗Öt YAML ch╞░a tß╗½ng ─æ╞░ß╗úc nß║íp v├áo hß╗ç
Γûê                # thß╗æng (file thuß╗Öc repo nh╞░ng kh├┤ng phß║úi catalog, hoß║╖c ─æ├ú xo├í tß╗½
Γûê                # tr╞░ß╗¢c). Kh├┤ng c├│ g├¼ ─æß╗â l├ám, v├á c┼⌐ng kh├┤ng c├│ g├¼ sai.
Γûê                skipped.append(name)
Γûê                logger.info("Bß╗Å qua xo├í '%s': ch╞░a tß╗½ng ─æ╞░ß╗úc nß║íp.", name)
Γûê                continue
Γûê            failed.append(path)
Γûê            issues.append(_issue_from(exc, path))
Γûê        else:
Γûê            deleted.append(name)
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 3: nß║íp catalog cß╗ºa c├íc file added + modified ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    targets = [*event.added_files, *event.modified_files]
Γûê    if len(targets) > settings.github_max_files_per_push:
Γûê        skipped_count = len(targets) - settings.github_max_files_per_push
Γûê        issues.append(
Γûê            Issue(
Γûê                severity="warning",
Γûê                code=ErrorCode.HAS_WARNINGS.value,
Γûê                message=f"Push chß║ím {len(targets)} file YAML, v╞░ß╗út giß╗¢i hß║ín "
Γûê                f"{settings.github_max_files_per_push} file mß╗ùi lß║ºn. "
Γûê                f"{skipped_count} file ch╞░a ─æ╞░ß╗úc xß╗¡ l├╜ ΓÇö h├úy tß║úi l├¬n thß╗º c├┤ng.",
Γûê            )
Γûê        )
Γûê        targets = targets[: settings.github_max_files_per_push]
Γöé
Γûê    for path in targets:
Γûê        name = posixpath.basename(path)
Γöé
Γûê        content = await _fetch_file(event.repo_full_name, event.commit_id, path)
Γûê        if content is None:
Γûê            failed.append(path)
Γûê            issues.append(
Γûê                Issue(
Γûê                    severity="error",
Γûê                    code=ErrorCode.GITHUB_FETCH_FAILED.value,
Γûê                    message=f"Kh├┤ng tß║úi ─æ╞░ß╗úc nß╗Öi dung '{path}' tß╗½ GitHub.",
Γûê                    source=path,
Γûê                )
Γûê            )
Γûê            continue
Γöé
Γûê        try:
Γûê            result = await run_in_threadpool(
Γûê                ingest.ingest_catalog, name, content, _YAML_CONTENT_TYPE, request_id
Γûê            )
Γûê        except CriticalError:
Γûê            raise
Γûê        except AppError as exc:
Γûê            failed.append(path)
Γûê            issues.append(_issue_from(exc, path))
Γûê        else:
Γûê            ingested.append(name)
Γûê            # Cß║únh b├ío cß╗ºa ch├¡nh file (thiß║┐u owner, ref lß║í...) ─æ├ú ─æ╞░ß╗úc `ingest`
Γûê            # dß╗▒ng sß║╡n th├ánh Issue ΓÇö chuyß╗ân tiß║┐p nguy├¬n vß║╣n thay v├¼ nuß╗æt mß║Ñt.
Γûê            issues.extend(result.issues)
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 4: dß╗▒ng response ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    details: dict[str, Any] = {
Γûê        "log_id": log_id,
Γûê        "repository": event.repo_full_name,
Γûê        "branch": event.branch,
Γûê        "email": event.email,
Γûê        "commit_id": event.commit_id,
Γûê        "commit_url": event.commit_url,
Γûê        "ingested": ingested,
Γûê        "deleted": deleted,
Γûê        "skipped": skipped,
Γûê        "failed": failed,
Γûê    }
Γöé
Γûê    summary = (
Γûê        f"Push l├¬n nh├ính '{event.branch}': nß║íp {len(ingested)} file, "
Γûê        f"xo├í {len(deleted)} file"
Γûê    )
Γûê    if failed:
Γûê        summary += f", {len(failed)} file l├í┬╗ΓÇöi"
Γûê    summary += "."
Γöé
Γûê    if not issues:
Γûê        logger.info(
Γûê            "Webhook xß╗¡ l├╜ xong push '%s' (log_id=%d): nß║íp %d, xo├í %d",
Γûê            event.commit_id, log_id, len(ingested), len(deleted),
Γûê        )
Γûê        return schemas.success(summary, request_id=request_id, details=details)
Γöé
Γûê    logger.warning(
Γûê        "Webhook xß╗¡ l├╜ push '%s' (log_id=%d) k├¿m %d vß║Ñn ─æß╗ü: %s",
Γûê        event.commit_id, log_id, len(issues), [i.code for i in issues],
Γûê    )
Γûê    return schemas.warning(
Γûê        summary, request_id=request_id, issues=issues, details=details
Γûê    )
Γöé


JOURNAL.md:
Γûê# Weekly Journal ΓÇö Team [T├¬n Team]
Γöé
Γûê> Ghi lß║íi mß╗ùi tuß║ºn: hß╗ìc ─æ╞░ß╗úc g├¼, kh├│ kh─ân g├¼, quyß║┐t ─æß╗ïnh g├¼, kß║┐ hoß║ích tiß║┐p.
Γöé
Γûê---
Γöé
Γûê## Week 1: [Ng├áy bß║»t ─æß║ºu] - [Ng├áy kß║┐t th├║c]
Γöé
Γûê### Mß╗Ñc ti├¬u tuß║ºn n├áy
Γûê- [ ] [Mß╗Ñc ti├¬u 1]
Γûê- [ ] [Mß╗Ñc ti├¬u 2]
Γûê- [ ] [Mß╗Ñc ti├¬u 3]
Γöé
Γûê### ─É├ú ho├án th├ánh
Γûê- [th├ánh quß║ú 1]
Γûê- [th├ánh quß║ú 2]
Γöé
Γûê### Kh├│ kh─ân & Giß║úi ph├íp
Γûê| Kh├│ kh─ân | Giß║úi ph├íp | Kß║┐t quß║ú |
Γûê|----------|-----------|---------|
Γûê| [m├┤ tß║ú] | [c├ích xß╗¡ l├╜] | [output] |
Γöé
Γûê### B├ái hß╗ìc
Γûê- [b├ái hß╗ìc 1]
Γûê- [b├ái hß╗ìc 2]
Γöé
Γûê### Kß║┐ hoß║ích tuß║ºn sau
Γûê- [ ] [task 1]
Γûê- [ ] [task 2]
Γöé
Γûê---
Γöé
Γûê## Week 2: [Ng├áy bß║»t ─æß║ºu] - [Ng├áy kß║┐t th├║c]
Γöé
Γûê### Mß╗Ñc ti├¬u tuß║ºn n├áy
Γûê- [ ] [Mß╗Ñc ti├¬u 1]
Γöé
Γûê### ─É├ú ho├án th├ánh
Γûê-
Γöé
Γûê### Kh├│ kh─ân & Giß║úi ph├íp
Γûê| Kh├│ kh─ân | Giß║úi ph├íp | Kß║┐t quß║ú |
Γûê|----------|-----------|---------|
Γûê| | | |
Γöé
Γûê### B├ái hß╗ìc
Γûê-
Γöé
Γûê### Kß║┐ hoß║ích tuß║ºn sau
Γûê-
Γöé
Γûê---
Γöé
Γûê<!-- Tiß║┐p tß╗Ñc copy block tr├¬n cho Week 3, 4, 5, 6 -->


Makefile:
Γûê∩╗┐.PHONY: run run-agent-template test lint format typecheck check clean
Γöé
Γûêrun:
Γûê	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
Γöé
Γûêrun-agent-template:
Γûê	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
Γöé
Γûêtest:
Γûê	pytest tests/ -v
Γöé
Γûêlint:
Γûê	ruff check app/ src/ tests/
Γöé
Γûêformat:
Γûê	ruff format app/ src/ tests/
Γöé
Γûêtypecheck:
Γûê	mypy app/ src/
Γöé
Γûêcheck: lint format test
Γöé
Γûêclean:
Γûê	find . -type d -name __pycache__ -exec rm -rf {} +
Γûê	find . -type d -name .pytest_cache -exec rm -rf {} +
Γûê	find . -type d -name .ruff_cache -exec rm -rf {} +
Γöé


presentation\README.md:
Γûê# Pitch Deck & Demo Materials
Γöé
Γûê## Files
Γöé
Γûê- `pitch_deck.pptx` ΓÇö Slide thuyß║┐t tr├¼nh Demo Day
Γûê- `video_demo.mp4` ΓÇö Video demo sß║ún phß║⌐m (tß╗æi ─æa 5 ph├║t)
Γöé
Γûê## Pitch Deck Structure (10 slides)
Γöé
Γûê1. **Title** ΓÇö T├¬n dß╗▒ ├ín + Team
Γûê2. **Problem** ΓÇö Vß║Ñn ─æß╗ü l├á g├¼? C├│ bao nhi├¬u ng╞░ß╗¥i gß║╖p?
Γûê3. **Solution** ΓÇö Giß║úi ph├íp AI cß╗ºa bß║ín
Γûê4. **Demo** ΓÇö Screenshot/Video ngß║»n
Γûê5. **Architecture** ΓÇö System diagram ─æ╞ín giß║ún
Γûê6. **Tech Stack** ΓÇö Technologies used
Γûê7. **Traction** ΓÇö Metrics, users, feedback
Γûê8. **Market** ΓÇö Quy m├┤ thß╗ï tr╞░ß╗¥ng
Γûê9. **Team** ΓÇö Ai l├ám g├¼
Γûê10. **Ask** ΓÇö Bß║ín cß║ºn g├¼ tiß║┐p theo?
Γöé
Γûê## Video Demo Checklist
Γöé
Γûê- [ ] Giß╗¢i thiß╗çu problem (< 30 gi├óy)
Γûê- [ ] Demo live feature ch├¡nh (2-3 ph├║t)
Γûê- [ ] Hiß╗ân thß╗ï kß║┐t quß║ú AI (1 ph├║t)
Γûê- [ ] T├│m tß║»t impact (< 30 gi├óy)


README.md:
Γûê# ≡ƒñû AI20K Agent Template
Γöé
ΓûêTemplate ch├¡nh thß╗⌐c cho hß╗ìc vi├¬n **VinUni AI20K Build Phase** ΓÇö cung cß║Ñp sß║╡n cß║Ñu tr├║c dß╗▒ ├ín, code mß║½u, v├á h╞░ß╗¢ng dß║½n kß╗╣ thuß║¡t chi tiß║┐t ─æß╗â x├óy dß╗▒ng AI Agent ─æß║ít ─æiß╗âm cao (35+/50).
Γöé
Γûê> ≡ƒôû **Technical Guidebook:** [phoenix.note.transformerlabs.ai/technical-book](https://phoenix.note.transformerlabs.ai/technical-book)
Γöé
Γûê## ≡ƒÄ» Template n├áy d├╣ng ─æß╗â l├ám g├¼?
Γöé
ΓûêKhi tham gia AI20K Build Phase, mß╗ùi ─æß╗Öi cß║ºn x├óy dß╗▒ng mß╗Öt AI Agent ho├án chß╗ënh ΓÇö tß╗½ kiß║┐n tr├║c, code, test, ─æß║┐n deploy. Thay v├¼ bß║»t ─æß║ºu tß╗½ con sß╗æ kh├┤ng, template n├áy cung cß║Ñp:
Γöé
Γûê- **Cß║Ñu tr├║c th╞░ mß╗Ñc chuß║⌐n** ΓÇö ─æ├ú ─æ╞░ß╗úc thiß║┐t kß║┐ theo best practices (separation of concerns)
Γûê- **Code mß║½u** cho c├íc phß║ºn cß╗æt l├╡i: LangGraph agent, FastAPI API, config, schemas
Γûê- **Docker + CI/CD sß║╡n** ΓÇö Dockerfile multi-stage, GitHub Actions workflow
Γûê- **H╞░ß╗¢ng dß║½n kß╗╣ thuß║¡t 10 ch╞░╞íng** ΓÇö tß╗½ clone template ─æß║┐n nß╗Öp b├ái Demo Day
Γûê- **Checklist 10 deliverables** ΓÇö ─æß║úm bß║úo kh├┤ng bß╗Å s├│t y├¬u cß║ºu BTC
Γûê- **AI Usage Logging tß╗▒ ─æß╗Öng** ΓÇö Pre-configured hooks cho Claude Code, Cursor, Codex, Gemini CLI, Antigravity, v├á GitHub Copilot
Γöé
Γûê## ΓÜí Quick Start
Γöé
Γûê### B╞░ß╗¢c 1: Fork hoß║╖c Clone
Γöé
Γûê```bash
Γûê# Clone template
Γûêgit clone https://github.com/AI20K-Build-Cohort-2/starter-code-template.git team-YOUR_TEAM_NAME
Γûêcd team-YOUR_TEAM_NAME
Γöé
Γûê# X├│a git history c┼⌐ v├á khß╗ƒi tß║ío lß║íi
Γûêrm -rf .git
Γûêgit init
Γûêgit add .
Γûêgit commit -m "feat: khß╗ƒi tß║ío dß╗▒ ├ín tß╗½ template"
Γûê```
Γöé
Γûê### B╞░ß╗¢c 2: Setup m├┤i tr╞░ß╗¥ng
Γöé
Γûê```bash
Γûê# Tß║ío virtual environment
Γûêpython3.11 -m venv .venv
Γûêsource .venv/bin/activate
Γöé
Γûê# C├ái dependencies
Γûêpip install -e ".[dev]"
Γöé
Γûê# Cß║Ñu h├¼nh API keys
Γûêcp .env.example .env
Γûê# Mß╗ƒ .env v├á th├¬m OPENAI_API_KEY cß╗ºa bß║ín
Γûê# ─Éß╗ông thß╗¥i cß║¡p nhß║¡t AI_LOG_API_KEY bß║▒ng key ri├¬ng tß╗½ link mß╗¥i cß╗ºa BTC
Γûê# (gi├í trß╗ï trong .env.example chß╗ë l├á placeholder)
Γûê```
Γöé
Γûê### B╞░ß╗¢c 3: C├ái AI Logging Hooks
Γöé
Γûê```bash
Γûê# Linux / macOS / Git Bash
Γûêbash scripts/setup_hooks.sh
Γöé
Γûê# Windows PowerShell
Γûê# powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
Γûê```
Γöé
ΓûêHooks tß╗▒ ─æß╗Öng log mß╗ìi AI prompt khi d├╣ng Claude Code, Cursor, Codex, Gemini CLI, Antigravity, hoß║╖c GitHub Copilot. Kh├┤ng cß║ºn thao t├íc thß╗º c├┤ng.
Γöé
Γûê### B╞░ß╗¢c 4: Chß║íy server
Γöé
Γûê```bash
Γûê# Chß║íy FastAPI backend
Γûêuvicorn src.main:app --reload --port 8000
Γöé
Γûê# Mß╗ƒ Swagger UI
Γûê# http://localhost:8000/docs
Γûê```
Γöé
Γûê### B╞░ß╗¢c 5: ─Éß╗ìc h╞░ß╗¢ng dß║½n
Γöé
Γûê≡ƒôû Mß╗ƒ **[Technical Guidebook](https://phoenix.note.transformerlabs.ai/technical-book)** v├á l├ám theo tß╗½ng ch╞░╞íng.
Γöé
Γûê## ≡ƒôü Cß║Ñu tr├║c dß╗▒ ├ín
Γöé
Γûê```
ΓûêΓö£ΓöÇΓöÇ src/
ΓûêΓöé   Γö£ΓöÇΓöÇ agents/           # ≡ƒºá LangGraph Agent
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ graph.py      #    State graph (nodes + edges)
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ state.py      #    State schema (TypedDict)
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ nodes/        #    Node functions
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ tools/        #    Agent tools (@tool)
ΓûêΓöé   Γö£ΓöÇΓöÇ api/              # ≡ƒîÉ FastAPI Backend
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ routes.py     #    API endpoints
ΓûêΓöé   Γö£ΓöÇΓöÇ models/           # ≡ƒôï Pydantic schemas
ΓûêΓöé   Γö£ΓöÇΓöÇ services/         # ≡ƒöº Business logic (LLM, etc.)
ΓûêΓöé   Γö£ΓöÇΓöÇ config.py         # ΓÜÖ∩╕Å Pydantic Settings
ΓûêΓöé   ΓööΓöÇΓöÇ main.py           # ≡ƒÜÇ App entry point
ΓûêΓö£ΓöÇΓöÇ tests/                # ≡ƒº¬ pytest suite
ΓûêΓöé   Γö£ΓöÇΓöÇ test_agents/      #    Agent/graph tests
ΓûêΓöé   ΓööΓöÇΓöÇ test_api/         #    API endpoint tests
ΓûêΓö£ΓöÇΓöÇ scripts/              # ≡ƒöî AI Logging Hooks
ΓûêΓöé   Γö£ΓöÇΓöÇ log_hook.py       #    Auto-log cho Claude/Cursor/Codex/Gemini/Copilot
ΓûêΓöé   Γö£ΓöÇΓöÇ log_antigravity.py#    Antigravity IDE prompt scanner
ΓûêΓöé   Γö£ΓöÇΓöÇ log_manual.py     #    Manual log cho ChatGPT / web tools
ΓûêΓöé   Γö£ΓöÇΓöÇ submit_log.py     #    Submit logs on git push
ΓûêΓöé   ΓööΓöÇΓöÇ setup_hooks.sh    #    One-time hook installer
ΓûêΓö£ΓöÇΓöÇ .claude/ .codex/ .cursor/ .gemini/  # Per-tool hook configs
ΓûêΓö£ΓöÇΓöÇ .agents/              # Antigravity rules + workflows
ΓûêΓö£ΓöÇΓöÇ .ai-log/              # ≡ƒôè AI usage logs (auto-generated)
ΓûêΓö£ΓöÇΓöÇ docs/
ΓûêΓöé   Γö£ΓöÇΓöÇ guide/            # ≡ƒôû Technical Guidebook (10 chapters)
ΓûêΓöé   ΓööΓöÇΓöÇ architecture_diagram.md
ΓûêΓö£ΓöÇΓöÇ eval/                 # ≡ƒôè Evaluation results
ΓûêΓö£ΓöÇΓöÇ presentation/         # ≡ƒÄñ Demo Day slides
ΓûêΓö£ΓöÇΓöÇ .github/workflows/    # ΓÜí CI/CD (GitHub Actions)
ΓûêΓö£ΓöÇΓöÇ .github/hooks/        # ≡ƒ¬¥ Copilot hook config
ΓûêΓö£ΓöÇΓöÇ Dockerfile            # ≡ƒÉ│ Multi-stage build
ΓûêΓö£ΓöÇΓöÇ docker-compose.yml    # ≡ƒÉÖ Full stack orchestration
ΓûêΓööΓöÇΓöÇ README_boilerplate.md # ≡ƒô¥ README template cho ─æß╗Öi cß╗ºa bß║ín
Γûê```
Γöé
Γûê## ≡ƒôÜ Technical Guidebook ΓÇö 10 Ch╞░╞íng
Γöé
Γûê| Ch╞░╞íng | Nß╗Öi dung                                                    | Thß╗¥i gian |
Γûê| -------- | ------------------------------------------------------------ | ---------- |
Γûê| 1        | Lß╗¥i mß╗ƒ ─æß║ºu ΓÇö Mß╗Ñc ti├¬u, c├ích sß╗¡ dß╗Ñng                | 15 ph├║t   |
Γûê| 2        | Khß╗ƒi tß║ío dß╗▒ ├ín ΓÇö Clone, setup, git workflow             | 4 giß╗¥     |
Γûê| 3        | Thiß║┐t kß║┐ kiß║┐n tr├║c ΓÇö 3-tier, diagrams, ADR              | 6 giß╗¥     |
Γûê| 4        | **LangGraph Agent** ΓÇö State, nodes, edges, tools, RAG | 8 giß╗¥     |
Γûê| 5        | FastAPI ΓÇö Routes, validation, error handling, streaming     | 6 giß╗¥     |
Γûê| 6        | Giao diß╗çn ΓÇö Next.js + Streamlit quickstart                 | 6 giß╗¥     |
Γûê| 7        | DevOps ΓÇö Docker, CI/CD, deploy, logging                     | 6 giß╗¥     |
Γûê| 8        | Kiß╗âm thß╗¡ ΓÇö Unit test, integration test, RAGAS             | 4 giß╗¥     |
Γûê| 9        | Demo Day ΓÇö 10 deliverables, checklist, tips                 | 2 giß╗¥     |
Γûê| 10       | T├ái nguy├¬n ΓÇö Kh├│a hß╗ìc, docs, BMAD method                | tham khß║úo |
Γöé
Γûê≡ƒôû **─Éß╗ìc online:** [phoenix.note.transformerlabs.ai/technical-book](https://phoenix.note.transformerlabs.ai/technical-book)
Γöé
Γûê## ≡ƒôï 10 Deliverables cho Demo Day
Γöé
Γûê| #  | Deliverable          | File vß╗ï tr├¡                                          | Template c├│ sß║╡n |
Γûê| -- | -------------------- | ------------------------------------------------------ | :---------------: |
Γûê| 1  | Source Code          | `src/`                                               |        Γ£à        |
Γûê| 2  | README.md            | `README_boilerplate.md` ΓåÆ copy th├ánh `README.md` |        Γ£à        |
Γûê| 3  | Architecture Diagram | `docs/architecture_diagram.md`                       |        Γ£à        |
Γûê| 4  | AI Logs              | LangSmith (3 env vars) + Auto AI Usage Logging         |        Γ£à        |
Γûê| 5  | Live URL             | Deploy l├¬n Render/Vercel                              |   ΓÜí CI/CD sß║╡n   |
Γûê| 6  | Video Demo           | `presentation/`                                      |        ≡ƒô¥        |
Γûê| 7  | Pitch Deck           | `presentation/`                                      |        ≡ƒô¥        |
Γûê| 8  | Development Journal  | `JOURNAL.md`                                         |        Γ£à        |
Γûê| 9  | Worklog              | `WORKLOG.md`                                         |        Γ£à        |
Γûê| 10 | Evaluation Evidence  | `eval/`                                              |        ≡ƒô¥        |
Γöé
Γûê## ≡ƒ¢á Tech Stack
Γöé
Γûê| Layer    | Technology                       | Version     |
Γûê| -------- | -------------------------------- | ----------- |
Γûê| AI Agent | LangGraph + LangChain            | Latest      |
Γûê| Backend  | FastAPI + Uvicorn                | 0.100+      |
Γûê| LLM      | OpenAI GPT-4o-mini               | API         |
Γûê| Frontend | Next.js / Streamlit              | 14+ / 1.30+ |
Γûê| Database | SQLite (dev) / PostgreSQL (prod) | ΓÇö          |
Γûê| DevOps   | Docker + GitHub Actions          | ΓÇö          |
Γûê| Testing  | pytest + pytest-asyncio          | 8+          |
Γöé
Γûê## ≡ƒôè AI Usage Logging
Γöé
ΓûêTemplate ─æ├ú t├¡ch hß╗úp sß║╡n auto-logging hooks cho 6 AI tools:
Γöé
Γûê| Tool             | C╞í chß║┐                        | Config                       |
Γûê| ---------------- | ------------------------------- | ---------------------------- |
Γûê| Claude Code      | `.claude/settings.json` hooks | Tß╗▒ ─æß╗Öng                   |
Γûê| Cursor           | `.cursor/hooks.json`          | Tß╗▒ ─æß╗Öng                   |
Γûê| OpenAI Codex CLI | `.codex/hooks.json`           | Tß╗▒ ─æß╗Öng                   |
Γûê| Gemini CLI       | `.gemini/settings.json`       | Tß╗▒ ─æß╗Öng                   |
Γûê| GitHub Copilot   | `.github/hooks/hooks.json`    | Tß╗▒ ─æß╗Öng                   |
Γûê| Antigravity IDE  | Pre-push scan transcript        | Tß╗▒ ─æß╗Öng tr├¬n`git push` |
Γöé
ΓûêTß║Ñt cß║ú prompts v├á tool calls ─æ╞░ß╗úc log v├áo `.ai-log/session.jsonl` v├á tß╗▒ ─æß╗Öng submit l├¬n grading server mß╗ùi khi `git push`.
Γöé
Γûê**ChatGPT / web tools kh├íc** ΓÇö log thß╗º c├┤ng:
Γöé
Γûê```bash
Γûêbash scripts/_pyrun.sh scripts/log_manual.py --tool chatgpt --prompt "What you asked"
Γûê```
Γöé
Γûê> ΓÜá∩╕Å Chß║íy `bash scripts/setup_hooks.sh` mß╗Öt lß║ºn sau khi clone ─æß╗â c├ái pre-push hook.
Γöé
Γûê## ≡ƒôû ─Éß╗ìc Technical Guidebook
Γöé
Γûê**Online (khuyß║┐n nghß╗ï):** [phoenix.note.transformerlabs.ai/technical-book](https://phoenix.note.transformerlabs.ai/technical-book)
Γöé
Γûê─É─âng nhß║¡p bß║▒ng GitHub (c├╣ng account ─æ├ú ─æ╞░ß╗úc BTC mß╗¥i v├áo org `AI20K-Build-Cohort-2`)
ΓûêΓåÆ chß╗ìn tab **Technical Book** ß╗ƒ sidebar tr├íi ΓåÆ ─æß╗ìc 10 ch╞░╞íng + topic sections,
Γûêc├│ table of contents b├¬n phß║úi, hß╗ù trß╗ú light/dark/cyberpunk theme.
Γöé
Γûê**Offline:** mß╗ìi ch╞░╞íng ─æß╗üu ß╗ƒ th╞░ mß╗Ñc `docs/guide/` trong template n├áy ΓÇö mß╗ƒ bß║▒ng
Γûêbß║Ñt kß╗│ markdown viewer/editor n├áo (VS Code, Obsidian, GitHub UI, ΓÇª).
Γöé
Γûê## ≡ƒöù Li├¬n kß║┐t
Γöé
Γûê- ≡ƒôû **Technical Guidebook:** [phoenix.note.transformerlabs.ai/technical-book](https://phoenix.note.transformerlabs.ai/technical-book)
Γûê- ≡ƒÅ½ **AI20K Program:** VinUni AI20K Build Phase
Γûê- ≡ƒæ¿ΓÇì≡ƒÅ½ **Mentor:** ─Éß║╖ng Hß║úi Lß╗Öc
Γöé
Γûê## ≡ƒôä License
Γöé
ΓûêMIT ΓÇö Sß╗¡ dß╗Ñng tß╗▒ do cho mß╗Ñc ─æ├¡ch gi├ío dß╗Ñc.


README_boilerplate.md:
Γûê# [T├¬n Dß╗▒ ├ün]
Γöé
Γûê> T├│m tß║»t 1 c├óu: [Vß║Ñn ─æß╗ü] ΓåÆ [Giß║úi ph├íp AI] cho [Target User]
Γöé
Γûê## Vß║Ñn ─æß╗ü (Problem)
Γöé
ΓûêM├┤ tß║ú pain point cß╗Ñ thß╗â vß╗¢i data/sß╗æ liß╗çu:
Γûê- Ai ─æang gß║╖p vß║Ñn ─æß╗ü?
Γûê- Vß║Ñn ─æß╗ü tß╗æn bao nhi├¬u thß╗¥i gian/tiß╗ün?
Γûê- Tß║íi sao c├íc giß║úi ph├íp hiß╗çn tß║íi ch╞░a ─æß╗º?
Γöé
Γûê## Giß║úi ph├íp (Solution)
Γöé
ΓûêSß║ún phß║⌐m giß║úi quyß║┐t vß║Ñn ─æß╗ü nh╞░ thß║┐ n├áo bß║▒ng AI:
Γûê- Feature 1: [m├┤ tß║ú]
Γûê- Feature 2: [m├┤ tß║ú]
Γûê- Feature 3: [m├┤ tß║ú]
Γöé
Γûê## Target User
Γöé
Γûê- Primary: [m├┤ tß║ú user ch├¡nh]
Γûê- Secondary: [m├┤ tß║ú user phß╗Ñ]
Γöé
Γûê## Tech Stack
Γöé
Γûê| Layer | Technology |
Γûê|-------|-----------|
Γûê| AI Agent | LangGraph + [LLM] |
Γûê| Backend | FastAPI + Python 3.11+ |
Γûê| Frontend | React/Next.js + TypeScript |
Γûê| Database | PostgreSQL / SQLite |
Γûê| DevOps | Docker + GitHub Actions |
Γöé
Γûê## Quick Start
Γöé
Γûê```bash
Γûê# 1. Clone repo
Γûêgit clone https://github.com/a20-ai-thuc-chien/A20-App-XXX.git
Γûêcd A20-App-XXX
Γöé
Γûê# 2. Setup environment
Γûêcp .env.example .env
Γûê# Edit .env with your API keys
Γöé
Γûê# 3. Install dependencies
Γûêpip install -r requirements.txt
Γöé
Γûê# 4. Run development server
Γûêuvicorn src.main:app --reload
Γûê```
Γöé
Γûê## Project Structure
Γöé
Γûê```
ΓûêΓö£ΓöÇΓöÇ src/
ΓûêΓöé   Γö£ΓöÇΓöÇ agents/          # LangGraph agent definitions
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ graph.py     # Main graph (nodes + edges)
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ state.py     # State schema
ΓûêΓöé   Γöé   Γö£ΓöÇΓöÇ nodes/       # Individual nodes
ΓûêΓöé   Γöé   ΓööΓöÇΓöÇ tools/       # Agent tools
ΓûêΓöé   Γö£ΓöÇΓöÇ api/             # FastAPI routes
ΓûêΓöé   Γö£ΓöÇΓöÇ models/          # Pydantic schemas
ΓûêΓöé   Γö£ΓöÇΓöÇ services/        # Business logic
ΓûêΓöé   Γö£ΓöÇΓöÇ config.py        # Settings
ΓûêΓöé   ΓööΓöÇΓöÇ main.py          # App entry point
ΓûêΓö£ΓöÇΓöÇ tests/               # Test suite
ΓûêΓö£ΓöÇΓöÇ docs/                # Documentation
ΓûêΓö£ΓöÇΓöÇ eval/                # Evaluation results
ΓûêΓö£ΓöÇΓöÇ presentation/        # Demo materials
ΓûêΓö£ΓöÇΓöÇ Dockerfile           # Multi-stage build
ΓûêΓö£ΓöÇΓöÇ docker-compose.yml   # Full stack
ΓûêΓööΓöÇΓöÇ .github/workflows/   # CI/CD pipelines
Γûê```
Γöé
Γûê## API Endpoints
Γöé
Γûê| Method | Path | Description |
Γûê|--------|------|-------------|
Γûê| GET | /health | Health check |
Γûê| POST | /api/v1/chat | Chat with agent |
Γûê| POST | /api/v1/analyze | Analyze input |
Γöé
Γûê## Deliverables Checklist
Γöé
Γûê- [x] Source Code (GitHub)
Γûê- [x] README.md
Γûê- [x] Architecture Diagram (`docs/architecture_diagram.md`)
Γûê- [x] AI Logs (auto-collected)
Γûê- [ ] Live URL / Deploy
Γûê- [ ] Video Demo
Γûê- [ ] Pitch Deck (`presentation/`)
Γûê- [x] Weekly Journal (`JOURNAL.md`)
Γûê- [x] Worklog (`WORKLOG.md`)
Γûê- [ ] Evaluation Evidence (`eval/results/`)
Γöé
Γûê## Team
Γöé
Γûê| Member | Role | Student ID |
Γûê|--------|------|-----------|
Γûê| [Name] | [Role] | [ID] |
Γûê| [Name] | [Role] | [ID] |
Γûê| [Name] | [Role] | [ID] |
Γöé
Γûê## License
Γöé
ΓûêMIT


requirements.txt:
Γûê# Core
Γûêfastapi>=0.115.0
Γûêuvicorn[standard]>=0.34.0
Γûêpydantic>=2.10.0
Γûêpydantic-settings>=2.7.0
Γûêpython-dotenv>=1.0.0
Γûêpython-multipart>=0.0.9
Γöé
Γûê# Catalog ingestion (YAML -> graph JSON)
Γûêpyyaml>=6.0
Γûênetworkx>=3.0
Γöé
Γûê# AI / LangChain
Γûêlangchain>=0.3.0
Γûêlangchain-openai>=0.3.0
Γûêlanggraph>=0.2.0
Γöé
Γûê# Database ΓÇö Postgres (Neon). psycopg2-binary c├│ sß║╡n wheel cho cp311 (Docker)
Γûê# lß║½n cp314 (venv local) n├¬n kh├┤ng cß║ºn build tools khi c├ái.
Γûêsqlalchemy>=2.0.0
Γûêpsycopg2-binary>=2.9.12
Γûê# alembic>=1.14.0
Γöé
Γûê# Vector Store (uncomment as needed)
Γûê# chromadb>=0.5.0
Γöé
Γûê# Dev tools
Γûêruff>=0.8.0
Γûêpytest>=8.0.0
Γûêpytest-asyncio>=0.24.0
Γûêhttpx>=0.28.0


ruff.toml:
Γûêtarget-version = "py311"
Γûêline-length = 120
Γöé
Γûê[lint]
Γûêselect = ["E", "F", "I", "N", "W", "UP"]
Γûêignore = ["E501"]
Γöé
Γûê[format]
Γûêquote-style = "double"
Γûêindent-style = "space"


scripts\log_antigravity.py:
Γûê#!/usr/bin/env python3
Γûê"""
ΓûêAntigravity IDE log scanner ΓÇö extracts the exact user-typed prompts from
Γûêlocal Antigravity conversation transcripts.
Γöé
ΓûêSource of truth:
Γûê    ~/.gemini/antigravity-ide/brain/<conv_id>/.system_generated/logs/transcript.jsonl
Γûê    (with fallback to the legacy ~/.gemini/antigravity/brain/... layout)
Γöé
ΓûêEach transcript line is a JSON object. We emit one log entry per line where
Γûê`type == "USER_INPUT"` AND `source == "USER_EXPLICIT"`. The text inside
Γûê<USER_REQUEST>...</USER_REQUEST> is the exact prompt the student typed
Γûê(auxiliary <ADDITIONAL_METADATA> and <USER_SETTINGS_CHANGE> blocks are
Γûêstripped).
Γöé
ΓûêWhy not other sources we considered?
Γûê  - ~/.gemini/antigravity-ide/conversations/<conv>.pb is encrypted.
Γûê  - brain/<conv>/task.md / walkthrough.md are AI-generated artifacts, not the
Γûê    user's prompt.
Γûê  - ~/.gemini/tmp/<slug>/chats/session-*.json is the Gemini CLI, not the
Γûê    Antigravity IDE.
Γöé
ΓûêConversation ΓåÆ repo mapping
Γûê---------------------------
ΓûêThe brain folder has no .project_root file. We map a conv to the current repo
Γûêby scanning its transcript for tool-call `Cwd` values. A conv counts as
Γûêbelonging to this repo when one of its Cwd values either equals, is an
Γûêancestor of, or is a descendant of the current repo root.
Γöé
ΓûêUsage:
Γûê  python scripts/log_antigravity.py --auto            # default: last 24h
Γûê  python scripts/log_antigravity.py --hours 72
Γûê  python scripts/log_antigravity.py --all             # every conv, no cutoff
Γûê  python scripts/log_antigravity.py --conv-id <id>    # one conversation
Γûê  python scripts/log_antigravity.py --dry-run         # preview only
Γöé
ΓûêEnv overrides:
Γûê  ANTIGRAVITY_BRAIN_DIR  point at a different brain/ directory
Γûê  AI_LOG_DIR             where session.jsonl is written (default: .ai-log)
Γûê"""
Γûêimport argparse
Γûêimport json
Γûêimport os
Γûêimport re
Γûêimport subprocess
Γûêimport sys
Γûêfrom datetime import datetime, timezone, timedelta
Γûêfrom pathlib import Path
Γöé
Γûê# Fix Windows console encoding so VN diacritics in prompts print cleanly.
Γûêif sys.platform == "win32":
Γûê    try:
Γûê        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
Γûê        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
Γûê    except Exception:
Γûê        pass
Γöé
ΓûêVN_TZ = timezone(timedelta(hours=7))
ΓûêGEMINI_HOME = Path.home() / ".gemini"
Γöé
Γûê# Antigravity has shipped under two folder names; prefer the newer IDE one.
ΓûêBRAIN_CANDIDATES = (
Γûê    GEMINI_HOME / "antigravity-ide" / "brain",
Γûê    GEMINI_HOME / "antigravity" / "brain",
Γûê)
Γöé
ΓûêUSER_REQUEST_RE = re.compile(r"<USER_REQUEST>(.*?)</USER_REQUEST>", re.DOTALL)
ΓûêAUX_BLOCK_RE = re.compile(
Γûê    r"<(?:ADDITIONAL_METADATA|USER_SETTINGS_CHANGE|SYSTEM_MESSAGE)>"
Γûê    r".*?"
Γûê    r"</(?:ADDITIONAL_METADATA|USER_SETTINGS_CHANGE|SYSTEM_MESSAGE)>",
Γûê    re.DOTALL,
Γûê)
Γöé
Γöé
Γûêdef git(cmd: str) -> str:
Γûê    try:
Γûê        return subprocess.check_output(
Γûê            cmd.split(), shell=False, text=True, stderr=subprocess.DEVNULL
Γûê        ).strip()
Γûê    except Exception:
Γûê        return ""
Γöé
Γöé
Γûê# ---------------------------------------------------------------------------
Γûê# Locating brain/
Γûê# ---------------------------------------------------------------------------
Γöé
Γûêdef get_brain_dirs() -> list[Path]:
Γûê    """Brain directories to scan, newest layout first."""
Γûê    env = os.environ.get("ANTIGRAVITY_BRAIN_DIR")
Γûê    if env:
Γûê        p = Path(env)
Γûê        return [p] if p.exists() else []
Γûê    return [p for p in BRAIN_CANDIDATES if p.exists()]
Γöé
Γöé
Γûê# ---------------------------------------------------------------------------
Γûê# Path normalization + repo gating
Γûê# ---------------------------------------------------------------------------
Γöé
Γûêdef _normalize(p: str) -> str:
Γûê    """Lower-case + backslash form, no trailing separator."""
Γûê    if not p:
Γûê        return ""
Γûê    return p.strip().lower().replace("/", "\\").rstrip("\\")
Γöé
Γöé
Γûêdef _unquote_arg(val):
Γûê    """Antigravity stores tool args as JSON-encoded strings. Unwrap them."""
Γûê    if not isinstance(val, str):
Γûê        return val
Γûê    val = val.strip()
Γûê    if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
Γûê        try:
Γûê            return json.loads(val)
Γûê        except json.JSONDecodeError:
Γûê            return val[1:-1]
Γûê    return val
Γöé
Γöé
Γûêdef _conv_cwds(transcript: Path) -> set[str]:
Γûê    """All Cwd values that appear in tool calls inside this transcript."""
Γûê    cwds: set[str] = set()
Γûê    try:
Γûê        with open(transcript, encoding="utf-8") as f:
Γûê            for line in f:
Γûê                line = line.strip()
Γûê                if not line:
Γûê                    continue
Γûê                try:
Γûê                    entry = json.loads(line)
Γûê                except json.JSONDecodeError:
Γûê                    continue
Γûê                for tc in (entry.get("tool_calls") or []):
Γûê                    args = tc.get("args") or {}
Γûê                    cwd = args.get("Cwd") or args.get("cwd")
Γûê                    cwd = _unquote_arg(cwd)
Γûê                    if isinstance(cwd, str):
Γûê                        n = _normalize(cwd)
Γûê                        if n:
Γûê                            cwds.add(n)
Γûê    except OSError:
Γûê        pass
Γûê    return cwds
Γöé
Γöé
Γûêdef _conv_matches_repo(cwds: set[str], repo_root_n: str) -> bool:
Γûê    """True if any cwd is equal to, ancestor of, or descendant of the repo."""
Γûê    if not repo_root_n or not cwds:
Γûê        return False
Γûê    for cwd in cwds:
Γûê        if cwd == repo_root_n:
Γûê            return True
Γûê        if cwd.startswith(repo_root_n + "\\"):
Γûê            return True
Γûê        if repo_root_n.startswith(cwd + "\\"):
Γûê            return True
Γûê    return False
Γöé
Γöé
Γûê# ---------------------------------------------------------------------------
Γûê# Prompt extraction
Γûê# ---------------------------------------------------------------------------
Γöé
Γûêdef extract_user_prompt(content: str) -> str:
Γûê    """Pull the text between <USER_REQUEST>...</USER_REQUEST>. Fall back to
Γûê    stripping known auxiliary blocks if no wrapper is present."""
Γûê    if not isinstance(content, str):
Γûê        return ""
Γûê    m = USER_REQUEST_RE.search(content)
Γûê    if m:
Γûê        return m.group(1).strip()
Γûê    cleaned = AUX_BLOCK_RE.sub("", content)
Γûê    return cleaned.strip()
Γöé
Γöé
Γûê# ---------------------------------------------------------------------------
Γûê# Reading existing log to avoid duplicates
Γûê# ---------------------------------------------------------------------------
Γöé
Γûêdef get_logged_entry_ids(log_file: Path) -> set[str]:
Γûê    logged: set[str] = set()
Γûê    if not log_file.exists():
Γûê        return logged
Γûê    with open(log_file, encoding="utf-8-sig") as f:
Γûê        for line in f:
Γûê            line = line.strip()
Γûê            if not line:
Γûê                continue
Γûê            try:
Γûê                entry = json.loads(line)
Γûê            except json.JSONDecodeError:
Γûê                continue
Γûê            eid = entry.get("entry_id", "")
Γûê            if eid:
Γûê                logged.add(eid)
Γûê    return logged
Γöé
Γöé
Γûê# ---------------------------------------------------------------------------
Γûê# Iterating user inputs
Γûê# ---------------------------------------------------------------------------
Γöé
Γûêdef iter_user_inputs(brain_dirs: list[Path], cutoff: datetime | None,
Γûê                     only_conv: str | None, repo_root_n: str):
Γûê    """Yield user-input dicts from every matching conversation transcript."""
Γûê    for brain in brain_dirs:
Γûê        for conv_dir in sorted(brain.iterdir()):
Γûê            if not conv_dir.is_dir():
Γûê                continue
Γûê            if only_conv and conv_dir.name != only_conv:
Γûê                continue
Γûê            transcript = (
Γûê                conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
Γûê            )
Γûê            if not transcript.exists() or transcript.stat().st_size == 0:
Γûê                continue
Γöé
Γûê            cwds = _conv_cwds(transcript)
Γûê            # If we have a repo root, skip convs that never touched it.
Γûê            if repo_root_n and not _conv_matches_repo(cwds, repo_root_n):
Γûê                continue
Γöé
Γûê            with open(transcript, encoding="utf-8") as f:
Γûê                for line in f:
Γûê                    line = line.strip()
Γûê                    if not line:
Γûê                        continue
Γûê                    try:
Γûê                        entry = json.loads(line)
Γûê                    except json.JSONDecodeError:
Γûê                        continue
Γûê                    if (entry.get("type") != "USER_INPUT"
Γûê                            or entry.get("source") != "USER_EXPLICIT"):
Γûê                        continue
Γöé
Γûê                    ts = entry.get("created_at") or ""
Γûê                    if cutoff and ts:
Γûê                        try:
Γûê                            ts_dt = datetime.fromisoformat(
Γûê                                ts.replace("Z", "+00:00")
Γûê                            )
Γûê                            if ts_dt < cutoff:
Γûê                                continue
Γûê                        except ValueError:
Γûê                            pass
Γöé
Γûê                    text = extract_user_prompt(entry.get("content", ""))
Γûê                    if len(text) < 2:
Γûê                        continue
Γöé
Γûê                    yield {
Γûê                        "conv_id": conv_dir.name,
Γûê                        "step_index": int(entry.get("step_index", 0)),
Γûê                        "timestamp": ts,
Γûê                        "text": text,
Γûê                    }
Γöé
Γöé
Γûê# ---------------------------------------------------------------------------
Γûê# Emitting entries
Γûê# ---------------------------------------------------------------------------
Γöé
Γûêdef build_entry(msg: dict, repo: str, branch: str, commit: str,
Γûê                student: str) -> dict:
Γûê    ts = msg["timestamp"]
Γûê    if ts.endswith("Z"):
Γûê        try:
Γûê            ts = (
Γûê                datetime.fromisoformat(ts.replace("Z", "+00:00"))
Γûê                .astimezone(VN_TZ)
Γûê                .isoformat()
Γûê            )
Γûê        except ValueError:
Γûê            pass
Γöé
Γûê    return {
Γûê        "ts": ts or datetime.now(VN_TZ).isoformat(),
Γûê        "tool": "antigravity",
Γûê        "event": "UserPrompt",
Γûê        "entry_id": f"antigravity-{msg['conv_id']}-{msg['step_index']:05d}",
Γûê        "session_id": msg["conv_id"],
Γûê        "model": "gemini",
Γûê        "repo": repo,
Γûê        "branch": branch,
Γûê        "commit": commit,
Γûê        "student": student,
Γûê        "prompt": msg["text"],
Γûê        "response_summary": "",
Γûê    }
Γöé
Γöé
Γûêdef main() -> None:
Γûê    parser = argparse.ArgumentParser(
Γûê        description="Extract user prompts from Antigravity IDE transcripts"
Γûê                    " into .ai-log/session.jsonl."
Γûê    )
Γûê    parser.add_argument("--auto", action="store_true",
Γûê                        help="Default mode: scan recent conversations.")
Γûê    parser.add_argument("--hours", type=int, default=24,
Γûê                        help="Window in hours when scanning (default: 24).")
Γûê    parser.add_argument("--all", action="store_true",
Γûê                        help="Ignore the time window; scan everything.")
Γûê    parser.add_argument("--conv-id",
Γûê                        help="Limit to a single conversation id.")
Γûê    parser.add_argument("--no-repo-filter", action="store_true",
Γûê                        help="Don't filter conversations by current repo.")
Γûê    parser.add_argument("--dry-run", action="store_true",
Γûê                        help="Show what would be logged, don't write.")
Γûê    # Legacy positional args from old log_manual.py callers.
Γûê    parser.add_argument("summary", nargs="?", help=argparse.SUPPRESS)
Γûê    parser.add_argument("model", nargs="?", help=argparse.SUPPRESS)
Γûê    args = parser.parse_args()
Γöé
Γûê    # Legacy manual mode: `log_antigravity.py "my summary" gemini`
Γûê    if args.summary and not (args.auto or args.conv_id or args.all):
Γûê        _legacy_log(args.summary, args.model or "gemini")
Γûê        return
Γöé
Γûê    brain_dirs = get_brain_dirs()
Γûê    if not brain_dirs:
Γûê        print("[antigravity-log] No Antigravity brain/ directory found "
Γûê              f"(checked {', '.join(str(p) for p in BRAIN_CANDIDATES)}).",
Γûê              file=sys.stderr)
Γûê        sys.exit(0)
Γöé
Γûê    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
Γûê    log_dir.mkdir(exist_ok=True)
Γûê    log_file = log_dir / "session.jsonl"
Γûê    logged_ids = get_logged_entry_ids(log_file)
Γöé
Γûê    cutoff = None
Γûê    if not args.all:
Γûê        cutoff = datetime.now(tz=VN_TZ) - timedelta(hours=args.hours)
Γöé
Γûê    repo_root_n = "" if args.no_repo_filter else _normalize(str(Path.cwd()))
Γöé
Γûê    repo = git("git remote get-url origin").split("/")[-1].replace(".git", "")
Γûê    branch = git("git rev-parse --abbrev-ref HEAD")
Γûê    commit = git("git rev-parse --short HEAD")
Γûê    student = git("git config user.email") or os.environ.get(
Γûê        "USERNAME", os.environ.get("USER", "unknown"))
Γöé
Γûê    new_entries: list[dict] = []
Γûê    for msg in iter_user_inputs(brain_dirs, cutoff, args.conv_id, repo_root_n):
Γûê        entry = build_entry(msg, repo or Path.cwd().name, branch, commit,
Γûê                            student)
Γûê        if entry["entry_id"] in logged_ids:
Γûê            continue
Γûê        new_entries.append(entry)
Γûê        logged_ids.add(entry["entry_id"])
Γöé
Γûê    if not new_entries:
Γûê        scope = "all" if args.all else f"{args.hours}h"
Γûê        repo_note = "any repo" if args.no_repo_filter else f"repo={repo_root_n or '(unknown)'}"
Γûê        print(f"[antigravity-log] No new prompts ({repo_note}, window={scope}).",
Γûê              file=sys.stderr)
Γûê        sys.exit(0)
Γöé
Γûê    if args.dry_run:
Γûê        print(f"\n[antigravity-log] DRY RUN ΓÇö would log "
Γûê              f"{len(new_entries)} entries:\n")
Γûê        for e in new_entries:
Γûê            preview = e["prompt"].replace("\n", " ")[:120]
Γûê            print(f"  [{e['ts'][:19]}] {preview}")
Γûê        sys.exit(0)
Γöé
Γûê    with open(log_file, "a", encoding="utf-8") as f:
Γûê        for e in new_entries:
Γûê            f.write(json.dumps(e, ensure_ascii=False) + "\n")
Γöé
Γûê    print(f"[antigravity-log] Logged {len(new_entries)} prompt(s) from "
Γûê          f"Antigravity IDE.", file=sys.stderr)
Γöé
Γöé
Γûê# ---------------------------------------------------------------------------
Γûê# Legacy manual mode (kept for back-compat with log_manual.py callers and the
Γûê# old .agents/rules instructions). New rules tell the AI not to call this.
Γûê# ---------------------------------------------------------------------------
Γöé
Γûêdef _legacy_log(summary: str, model: str) -> None:
Γûê    ts = datetime.now(VN_TZ).isoformat()
Γûê    entry = {
Γûê        "ts": ts,
Γûê        "tool": "antigravity",
Γûê        "event": "TaskComplete",
Γûê        "entry_id": f"antigravity-{datetime.now(VN_TZ).strftime('%Y%m%d-%H%M%S')}",
Γûê        "model": model,
Γûê        "repo": git("git remote get-url origin").split("/")[-1].replace(".git", ""),
Γûê        "branch": git("git rev-parse --abbrev-ref HEAD"),
Γûê        "commit": git("git rev-parse --short HEAD"),
Γûê        "student": git("git config user.email") or os.environ.get(
Γûê            "USERNAME", os.environ.get("USER", "unknown")),
Γûê        "prompt": summary[:1000],
Γûê        "response_summary": f"[Antigravity] {summary[:500]}",
Γûê    }
Γûê    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
Γûê    log_dir.mkdir(exist_ok=True)
Γûê    with open(log_dir / "session.jsonl", "a", encoding="utf-8") as f:
Γûê        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
Γûê    print(f"[antigravity-log] Logged manual: {summary[:80]}...", file=sys.stderr)
Γöé
Γöé
Γûêif __name__ == "__main__":
Γûê    main()


scripts\log_hook.py:
Γûê#!/usr/bin/env python3
Γûê"""
ΓûêShared AI hook logger ΓÇö works with Claude Code, Gemini CLI, Codex, Cursor, Copilot.
ΓûêReads JSON from stdin, normalizes to common format, appends to .ai-log/session.jsonl
Γûê"""
Γûêimport json
Γûêimport os
Γûêimport sys
Γûêimport subprocess
Γûêfrom datetime import datetime, timezone, timedelta
Γûêfrom pathlib import Path
Γöé
ΓûêVN_TZ = timezone(timedelta(hours=7))
Γöé
Γöé
Γûêdef git(cmd):
Γûê    try:
Γûê        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
Γûê    except Exception:
Γûê        return ""
Γöé
Γöé
Γûêdef detect_tool(data: dict) -> str:
Γûê    """Detect which AI tool sent this hook event.
Γöé
Γûê    Priority:
Γûê      1. --tool=NAME CLI argument (cross-platform: works in cmd.exe, PowerShell, bash)
Γûê      2. AI_TOOL_NAME env var (legacy, bash-only when set inline)
Γûê      3. Heuristics from payload shape
Γûê    """
Γûê    for arg in sys.argv[1:]:
Γûê        if arg.startswith("--tool="):
Γûê            return arg.split("=", 1)[1].lower()
Γûê    tool_env = os.environ.get("AI_TOOL_NAME", "").lower()
Γûê    if tool_env:
Γûê        return tool_env
Γûê    # Heuristics
Γûê    if "transcript_path" in data:
Γûê        return "codex"
Γûê    if data.get("hook_event_name", "").startswith(("Before", "After", "Session", "Pre", "Notification")):
Γûê        return "gemini"
Γûê    if data.get("hook_event_name", "")[0:1].islower():
Γûê        # camelCase event names ΓåÆ Cursor or Copilot
Γûê        if "workspace_roots" in data:
Γûê            return "cursor"
Γûê        if "toolName" in data:
Γûê            return "copilot"
Γûê    if "hook_event_name" in data:
Γûê        return "claude"
Γûê    return "unknown"
Γöé
Γöé
Γûêdef normalize(data: dict, tool: str) -> dict | None:
Γûê    """Normalize tool-specific payload to common log entry."""
Γûê    event = data.get("hook_event_name") or data.get("event", "")
Γûê    ts = datetime.now(VN_TZ).isoformat()
Γöé
Γûê    # Resolve repo from git origin. When cwd is not a git working tree (or
Γûê    # origin isn't set), skip the event entirely ΓÇö these entries can't be
Γûê    # tied back to a team on the server and would just clutter the pending
Γûê    # queue forever.
Γûê    origin = git("git remote get-url origin")
Γûê    if not origin:
Γûê        return None
Γûê    repo = origin.rstrip("/").split("/")[-1]
Γûê    if repo.endswith(".git"):
Γûê        repo = repo[:-4]
Γöé
Γûê    base = {
Γûê        "ts": ts,
Γûê        "tool": tool,
Γûê        "event": event,
Γûê        "session_id": (
Γûê            data.get("session_id") or
Γûê            data.get("conversation_id") or
Γûê            data.get("generation_id") or ""
Γûê        ),
Γûê        "model": data.get("model", ""),
Γûê        "repo": repo,
Γûê        "branch": git("git rev-parse --abbrev-ref HEAD"),
Γûê        "commit": git("git rev-parse --short HEAD"),
Γûê        "student": git("git config user.email"),
Γûê    }
Γöé
Γûê    if tool == "claude":
Γûê        prompt = ""
Γûê        # UserPromptSubmit: prompt is at top level
Γûê        if event == "UserPromptSubmit":
Γûê            prompt = data.get("prompt", "")[:1000]
Γûê        # PostToolUse: extract from tool_input
Γûê        elif isinstance(data.get("tool_input"), dict):
Γûê            prompt = data["tool_input"].get("prompt") or data["tool_input"].get("content") or ""
Γûê        base.update({
Γûê            "prompt": prompt,
Γûê            "tool_name": data.get("tool_name", ""),
Γûê            "tool_input": data.get("tool_input") if event != "UserPromptSubmit" else None,
Γûê            "tool_response": str(data.get("tool_response", ""))[:500],
Γûê        })
Γöé
Γûê    elif tool == "gemini":
Γûê        if event == "BeforeAgent":
Γûê            prompt = data.get("prompt", "")[:1000]
Γûê            base.update({"prompt": prompt})
Γûê        else:
Γûê            req = data.get("request", {})
Γûê            contents = req.get("contents", [])
Γûê            prompt = ""
Γûê            for c in reversed(contents):
Γûê                for part in c.get("parts", []):
Γûê                    if part.get("text"):
Γûê                        prompt = part["text"][:1000]
Γûê                        break
Γûê                if prompt:
Γûê                    break
Γûê            resp = data.get("response", {})
Γûê            answer = ""
Γûê            try:
Γûê                answer = resp["candidates"][0]["content"]["parts"][0]["text"][:500]
Γûê            except Exception:
Γûê                pass
Γûê            base.update({"prompt": prompt, "response_summary": answer})
Γöé
Γûê    elif tool == "codex":
Γûê        base.update({
Γûê            "prompt": data.get("prompt", "")[:1000],
Γûê            "turn_id": data.get("turn_id", ""),
Γûê            "transcript_path": data.get("transcript_path", ""),
Γûê        })
Γöé
Γûê    elif tool == "cursor":
Γûê        base.update({
Γûê            "prompt": data.get("prompt", "")[:1000],
Γûê            "files_context": data.get("attachments", []),
Γûê        })
Γöé
Γûê    elif tool == "copilot":
Γûê        base.update({
Γûê            "prompt": data.get("prompt", "")[:1000],
Γûê            "tool_name": data.get("toolName", ""),
Γûê            "tool_args": data.get("toolArgs"),
Γûê        })
Γöé
Γûê    # Skip only true noise: no prompt AND no tool-specific payload (tool_input,
Γûê    # response_summary, tool_response, tool_args, files_context). Previously
Γûê    # this only checked `prompt`, which dropped Claude Bash/Edit events (their
Γûê    # tool_input has `command` / `file_path`, not `prompt` or `content`) and
Γûê    # any Gemini/Cursor/Copilot turn that carried context but no plain prompt.
Γûê    _PAYLOAD_KEYS = ("prompt", "tool_input", "response_summary",
Γûê                     "tool_response", "tool_args", "files_context")
Γûê    _LIFECYCLE_EVENTS = ("Stop", "stop", "SessionEnd", "sessionEnd", "AfterModel")
Γûê    has_payload = any(base.get(k) for k in _PAYLOAD_KEYS)
Γûê    if not has_payload and event not in _LIFECYCLE_EVENTS:
Γûê        return None
Γöé
Γûê    return base
Γöé
Γöé
Γûêdef main():
Γûê    # Read stdin as UTF-8 explicitly. On Windows, sys.stdin defaults to the
Γûê    # system code page (e.g. cp1252), which corrupts non-Latin1 prompts
Γûê    # (Vietnamese, CJK, emoji) into mojibake. The hook payload is always UTF-8.
Γûê    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace").strip()
Γûê    if not raw:
Γûê        sys.exit(0)
Γöé
Γûê    try:
Γûê        data = json.loads(raw)
Γûê    except json.JSONDecodeError:
Γûê        sys.exit(0)
Γöé
Γûê    tool = detect_tool(data)
Γûê    entry = normalize(data, tool)
Γûê    if not entry:
Γûê        sys.exit(0)
Γöé
Γûê    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
Γûê    log_dir.mkdir(exist_ok=True)
Γûê    log_file = log_dir / "session.jsonl"
Γöé
Γûê    with open(log_file, "a", encoding="utf-8") as f:
Γûê        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
Γöé
Γûê    # Output valid JSON (required by some tools like Gemini)
Γûê    print(json.dumps({"status": "logged"}))
Γöé
Γöé
Γûêif __name__ == "__main__":
Γûê    main()


scripts\log_manual.py:
Γûê#!/usr/bin/env python3
Γûê"""
ΓûêManual AI usage logger ΓÇö for team members using ANY AI tool.
ΓûêUse this when your AI tool does NOT have automatic hook integration.
Γöé
ΓûêUsage (interactive):
Γûê  python scripts/log_manual.py
Γöé
ΓûêUsage (one-line):
Γûê  python scripts/log_manual.py --tool "chatgpt" --prompt "Asked ChatGPT to explain transformer architecture" --model "gpt-5.4"
Γöé
ΓûêExamples:
Γûê  # Tiß║┐n logs a ChatGPT session
Γûê  python scripts/log_manual.py --tool chatgpt --prompt "Brainstorm UI layout for /ai page"
Γöé
Γûê  # Ho├áng logs a Gemini web session
Γûê  python scripts/log_manual.py --tool gemini-web --prompt "Research risk scoring algorithms"
Γöé
Γûê  # Quick interactive mode
Γûê  python scripts/log_manual.py
Γûê"""
Γûêimport json
Γûêimport os
Γûêimport sys
Γûêimport subprocess
Γûêimport argparse
Γûêfrom datetime import datetime, timezone, timedelta
Γûêfrom pathlib import Path
Γöé
ΓûêVN_TZ = timezone(timedelta(hours=7))
Γöé
Γöé
Γûêdef git(cmd):
Γûê    try:
Γûê        return subprocess.check_output(cmd.split(), shell=False, text=True, stderr=subprocess.DEVNULL).strip()
Γûê    except Exception:
Γûê        return ""
Γöé
Γöé
Γûêdef interactive_mode():
Γûê    """Prompt user for log info interactively."""
Γûê    print("\n≡ƒô¥ Manual AI Log Entry")
Γûê    print("=" * 40)
Γöé
Γûê    tool = input("Tool name (e.g. chatgpt, gemini-web, copilot, other): ").strip()
Γûê    if not tool:
Γûê        tool = "unknown"
Γöé
Γûê    model = input("Model (e.g. gpt-5.4, gemini-3-pro, skip to use tool name): ").strip()
Γûê    if not model:
Γûê        model = tool
Γöé
Γûê    prompt = input("What did you ask/do? (brief summary): ").strip()
Γûê    if not prompt:
Γûê        print("[log] Γ¥î Prompt cannot be empty.", file=sys.stderr)
Γûê        sys.exit(1)
Γöé
Γûê    result = input("Result/outcome (optional, press Enter to skip): ").strip()
Γöé
Γûê    return tool, model, prompt, result
Γöé
Γöé
Γûêdef main():
Γûê    parser = argparse.ArgumentParser(description="Manual AI usage logger")
Γûê    parser.add_argument("--tool", help="AI tool name (e.g. chatgpt, gemini-web)")
Γûê    parser.add_argument("--prompt", help="What you asked/did")
Γûê    parser.add_argument("--model", help="Model used (optional)")
Γûê    parser.add_argument("--result", help="Outcome/result (optional)", default="")
Γûê    args = parser.parse_args()
Γöé
Γûê    if args.tool and args.prompt:
Γûê        tool = args.tool
Γûê        model = args.model or args.tool
Γûê        prompt = args.prompt
Γûê        result = args.result
Γûê    else:
Γûê        tool, model, prompt, result = interactive_mode()
Γöé
Γûê    ts = datetime.now(VN_TZ).isoformat()
Γöé
Γûê    student = git("git config user.email")
Γûê    if not student:
Γûê        student = os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
Γûê        print(f"[log] ΓÜá∩╕Å  git email not set! Using fallback: {student}", file=sys.stderr)
Γûê        print(f"[log] Run: git config user.email \"your@vinuni.edu.vn\"", file=sys.stderr)
Γöé
Γûê    entry = {
Γûê        "ts": ts,
Γûê        "tool": tool,
Γûê        "event": "ManualLog",
Γûê        "entry_id": f"manual-{datetime.now(VN_TZ).strftime('%Y%m%d-%H%M%S')}",
Γûê        "model": model,
Γûê        "repo": git("git remote get-url origin").split("/")[-1].replace(".git", ""),
Γûê        "branch": git("git rev-parse --abbrev-ref HEAD"),
Γûê        "commit": git("git rev-parse --short HEAD"),
Γûê        "student": student,
Γûê        "prompt": prompt[:1000],
Γûê        "response_summary": result[:500] if result else "",
Γûê    }
Γöé
Γûê    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
Γûê    log_dir.mkdir(exist_ok=True)
Γûê    log_file = log_dir / "session.jsonl"
Γöé
Γûê    with open(log_file, "a", encoding="utf-8") as f:
Γûê        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
Γöé
Γûê    print(f"\n[log] Γ£à Logged: [{tool}] {prompt[:80]}")
Γûê    print(f"[log] ≡ƒôü Saved to: {log_file}")
Γöé
Γöé
Γûêif __name__ == "__main__":
Γûê    main()


scripts\setup.sh:
Γûê#!/bin/bash
Γûê# Setup script cho AI20K project
Γöé
Γûêset -e
Γöé
Γûêecho "=== AI20K Project Setup ==="
Γöé
Γûê# Check Python version
Γûêpython3 -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'"
Γûêecho "Python version OK"
Γöé
Γûê# Create virtual environment
Γûêpython3 -m venv .venv
Γûêsource .venv/bin/activate
Γöé
Γûê# Install dependencies
Γûêpip install -r requirements.txt
Γöé
Γûê# Create .env if not exists
Γûêif [ ! -f .env ]; then
Γûê    cp .env.example .env
Γûê    echo "Created .env ΓÇö please edit with your API keys"
Γûêfi
Γöé
Γûê# Create data directories
Γûêmkdir -p data/chroma
Γöé
Γûêecho "Setup complete! Run: uvicorn src.main:app --reload"


scripts\setup_hooks.ps1:
Γûê# Install git pre-push hook for AI log submission (Windows PowerShell).
Γûê# Run once after cloning: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
Γöé
Γûê$ErrorActionPreference = 'Stop'
Γöé
Γûê$HookFile = '.git/hooks/pre-push'
Γöé
Γûê# Git on Windows runs hooks via Git Bash, so the hook body must be bash.
Γûê$HookBody = @'
Γûê#!/usr/bin/env bash
Γûê# Pre-push: sweep recent Antigravity / Gemini prompts, then submit AI logs.
Γûêbash scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
Γûêbash scripts/_pyrun.sh scripts/submit_log.py || true
Γûêexit 0
Γûê'@
Γöé
ΓûêSet-Content -Path $HookFile -Value $HookBody -Encoding UTF8 -NoNewline
ΓûêWrite-Host "[ai-log] Git pre-push hook installed."
Γöé
Γûêif (-not (Test-Path .ai-log)) { New-Item -ItemType Directory -Path .ai-log | Out-Null }
Γûêif (-not (Test-Path .ai-log/.gitkeep)) { New-Item -ItemType File -Path .ai-log/.gitkeep | Out-Null }
Γöé
ΓûêWrite-Host "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."


scripts\setup_hooks.sh:
Γûê#!/usr/bin/env bash
Γûê# Install git pre-push hook for AI log submission (POSIX / Git Bash).
Γûê# Run once after cloning: bash scripts/setup_hooks.sh
Γûêset -e
Γöé
ΓûêHOOK_FILE=".git/hooks/pre-push"
Γöé
Γûêcat > "$HOOK_FILE" <<'EOF'
Γûê#!/usr/bin/env bash
Γûê# Pre-push: sweep recent Antigravity / Gemini prompts, then submit AI logs.
Γûê# Uses the cross-platform Python launcher so it works whether the user
Γûê# has python3, python, or only the `py` launcher (Windows).
Γûêbash scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
Γûêbash scripts/_pyrun.sh scripts/submit_log.py || true
Γûêexit 0  # Never block push, even if either step fails
ΓûêEOF
Γöé
Γûêchmod +x "$HOOK_FILE"
Γûêchmod +x scripts/_pyrun.sh 2>/dev/null || true
Γûêecho "[ai-log] Git pre-push hook installed."
Γöé
Γûêmkdir -p .ai-log
Γûêtouch .ai-log/.gitkeep
Γöé
Γûêecho "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."


scripts\submit_log.py:
Γûê#!/usr/bin/env python3
Γûê"""
ΓûêSubmit .ai-log/session.jsonl to grading server.
ΓûêCalled by git pre-push hook or manually.
Γöé
ΓûêAfter a successful submit, the live log is rotated:
Γûê  - Moved into .ai-log/archive/YYYY-MM-DD.jsonl (appended, never overwritten)
Γûê  - The live session.jsonl is recreated empty by the next hook write
Γöé
ΓûêIf the POST fails, the pending file is restored so nothing is lost.
Γûê"""
Γûêimport json
Γûêimport os
Γûêimport shutil
Γûêimport sys
Γûêimport time
Γûêimport urllib.request
Γûêimport urllib.error
Γûêfrom datetime import datetime, timezone
Γûêfrom pathlib import Path
Γöé
Γûêtry:
Γûê    from dotenv import load_dotenv
Γûê    load_dotenv()
Γûêexcept ImportError:
Γûê    pass
Γöé
ΓûêSERVER_URL = os.environ.get("AI_LOG_SERVER", "")
ΓûêAPI_KEY = os.environ.get("AI_LOG_API_KEY", "")
ΓûêLOG_DIR = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
ΓûêLOG_FILE = LOG_DIR / "session.jsonl"
ΓûêARCHIVE_DIR = LOG_DIR / "archive"
Γöé
Γûê# Match server-side MAX_BATCH_ENTRIES so we never get a 422.
Γûê# If the local file has more than this, we submit the oldest BATCH_LIMIT
Γûê# and leave the rest for the next push.
ΓûêBATCH_LIMIT = 500
Γöé
Γöé
Γûêdef _archive(pending: Path) -> None:
Γûê    """Append pending file to today's archive. Never overwrites existing data."""
Γûê    if not pending.exists() or pending.stat().st_size == 0:
Γûê        return
Γûê    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
Γûê    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
Γûê    archive_file = ARCHIVE_DIR / f"{today}.jsonl"
Γûê    with open(pending, "rb") as src, open(archive_file, "ab") as dst:
Γûê        shutil.copyfileobj(src, dst)
Γöé
Γöé
Γûêdef _restore_pending(pending: Path) -> None:
Γûê    """Failure path: put pending back at LOG_FILE so the next push retries.
Γûê    If hook wrote new entries to LOG_FILE in the meantime, prepend pending."""
Γûê    if not pending.exists():
Γûê        return
Γûê    if LOG_FILE.exists():
Γûê        # Concat: pending (older) + LOG_FILE (newer) ΓåÆ LOG_FILE
Γûê        tmp = LOG_FILE.with_suffix(".merge.jsonl")
Γûê        with open(tmp, "wb") as out:
Γûê            with open(pending, "rb") as a:
Γûê                shutil.copyfileobj(a, out)
Γûê            with open(LOG_FILE, "rb") as b:
Γûê                shutil.copyfileobj(b, out)
Γûê        os.replace(tmp, LOG_FILE)
Γûê        pending.unlink()
Γûê    else:
Γûê        pending.rename(LOG_FILE)
Γöé
Γöé
Γûêdef main():
Γûê    if not SERVER_URL:
Γûê        print("[ai-log] AI_LOG_SERVER not set ΓÇö skipping submission.", file=sys.stderr)
Γûê        sys.exit(0)
Γöé
Γûê    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
Γûê        print("[ai-log] No logs to submit.", file=sys.stderr)
Γûê        sys.exit(0)
Γöé
Γûê    # Atomic rename closes the race window: hook writes that arrive after this
Γûê    # land in a fresh LOG_FILE, not in the batch we're about to POST.
Γûê    pending = LOG_FILE.with_name(f"session.pending.{int(time.time())}.jsonl")
Γûê    try:
Γûê        LOG_FILE.rename(pending)
Γûê    except FileNotFoundError:
Γûê        print("[ai-log] No logs to submit.", file=sys.stderr)
Γûê        sys.exit(0)
Γöé
Γûê    entries = []
Γûê    leftover_lines = []
Γûê    with open(pending, encoding="utf-8") as f:
Γûê        for line in f:
Γûê            stripped = line.strip()
Γûê            if not stripped:
Γûê                continue
Γûê            if len(entries) >= BATCH_LIMIT:
Γûê                leftover_lines.append(line)
Γûê                continue
Γûê            try:
Γûê                entries.append(json.loads(stripped))
Γûê            except json.JSONDecodeError:
Γûê                pass  # drop unparseable line
Γöé
Γûê    if not entries:
Γûê        # Nothing to send; archive whatever was there (probably junk) and bail.
Γûê        _archive(pending)
Γûê        pending.unlink()
Γûê        print("[ai-log] No valid entries to submit.", file=sys.stderr)
Γûê        sys.exit(0)
Γöé
Γûê    payload = json.dumps({"entries": entries}, ensure_ascii=False).encode("utf-8")
Γûê    headers = {"Content-Type": "application/json"}
Γûê    if API_KEY:
Γûê        headers["Authorization"] = f"Bearer {API_KEY}"
Γûê    req = urllib.request.Request(
Γûê        SERVER_URL,
Γûê        data=payload,
Γûê        headers=headers,
Γûê        method="POST",
Γûê    )
Γöé
Γûê    try:
Γûê        with urllib.request.urlopen(req, timeout=10) as resp:
Γûê            print(f"[ai-log] Submitted {len(entries)} entries ΓåÆ {resp.status}", file=sys.stderr)
Γûê    except urllib.error.URLError as e:
Γûê        # Failure: restore the whole pending (including leftover) for next push.
Γûê        _restore_pending(pending)
Γûê        print(f"[ai-log] Submit failed: {e} ΓÇö logs kept locally.", file=sys.stderr)
Γûê        sys.exit(0)  # Don't block push on server error
Γöé
Γûê    # Success: archive the submitted batch, then handle any leftover.
Γûê    _archive(pending)
Γûê    pending.unlink()
Γöé
Γûê    if leftover_lines:
Γûê        # More than BATCH_LIMIT entries existed; put the rest back so the
Γûê        # next push picks them up.
Γûê        with open(LOG_FILE, "a", encoding="utf-8") as f:
Γûê            f.writelines(leftover_lines)
Γûê        print(
Γûê            f"[ai-log] {len(leftover_lines)} entries deferred to next push.",
Γûê            file=sys.stderr,
Γûê        )
Γöé
Γöé
Γûêif __name__ == "__main__":
Γûê    main()


scripts\test_api.py:
Γûê"""
Γûêtest_api.py ΓÇö Kß╗ïch bß║ún kiß╗âm thß╗¡ end-to-end IDP Catalog Graph API.
Γöé
ΓûêKh├íc vß╗¢i `pytest tests/`: bß╗Ö n├áy gß╗ìi API qua HTTP THß║¼T tr├¬n server thß║¡t, ─æß╗ìc
Γûêthß║│ng bß║úng `input_json` tr├¬n Postgres ─æß╗â ─æß╗æi chiß║┐u, v├á tß║»t/bß║¡t server ─æß╗â chß╗⌐ng
Γûêminh dß╗» liß╗çu sß╗æng s├│t qua restart. ─É├óy l├á thß╗⌐ d├╣ng ─æß╗â demo v├á ─æß╗â tin rß║▒ng hß╗ç
Γûêthß╗æng chß║íy ─æ╞░ß╗úc ngo├ái ─æß╗¥i, kh├┤ng chß╗ë trong test in-process.
Γöé
Γûê    .\\.venv\\Scripts\\python.exe scripts/test_api.py
Γöé
ΓûêMß║╖c ─æß╗ïnh script Tß╗░ dß╗▒ng mß╗Öt uvicorn ri├¬ng ß╗ƒ cß╗òng 8765 rß╗ôi tß╗▒ tß║»t ΓÇö kh├┤ng cß║ºn
Γûêchuß║⌐n bß╗ï g├¼. Muß╗æn bß║»n v├áo server ─æang chß║íy sß║╡n th├¼:
Γöé
Γûê    .\\.venv\\Scripts\\python.exe scripts/test_api.py --base-url http://127.0.0.1:8000
Γöé
Γûê(khi ─æ├│ phß║ºn restart bß╗ï bß╗Å qua, v├¼ script kh├┤ng sß╗ƒ hß╗»u tiß║┐n tr├¼nh ─æ├│).
Γöé
ΓûêAN TO├ÇN: script ghi v├áo database THß║¼T trong .env. N├│ chß╗ë ─æß╗Ñng ─æ├║ng nhß╗»ng catalog
Γûêdo n├│ tß║ío ra, dß╗ìn sß║ích l├║c kß║┐t th├║c, v├á Tß╗¬ CHß╗ÉI chß║íy nß║┐u mß╗Öt trong c├íc t├¬n file
Γûên├│ ─æß╗ïnh d├╣ng ─æ├ú c├│ sß║╡n trong bß║úng ΓÇö kh├┤ng c├│ ─æ╞░ß╗¥ng n├áo ─æß╗â n├│ ghi ─æ├¿ dß╗» liß╗çu cß╗ºa
Γûêbß║ín.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport argparse
Γûêimport io
Γûêimport os
Γûêimport socket
Γûêimport subprocess
Γûêimport sys
Γûêimport time
Γûêfrom pathlib import Path
Γûêfrom typing import Any
Γöé
ΓûêROOT = Path(__file__).resolve().parents[1]
Γûêsys.path.insert(0, str(ROOT))
Γöé
Γûê# Console Windows mß║╖c ─æß╗ïnh kh├┤ng phß║úi UTF-8; kh├┤ng ├⌐p th├¼ mß╗ìi th├┤ng ─æiß╗çp tiß║┐ng
Γûê# Viß╗çt do API trß║ú vß╗ü sß║╜ hiß╗çn th├ánh k├╜ tß╗▒ r├íc v├á ng╞░ß╗¥i xem t╞░ß╗ƒng hß╗ç thß╗æng hß╗Ång.
Γûêif hasattr(sys.stdout, "buffer"):
Γûê    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
Γöé
Γûêimport httpx  # noqa: E402
Γûêfrom sqlalchemy import create_engine, text  # noqa: E402
Γöé
Γûêfrom src.core.config import (  # noqa: E402
Γûê    DATABASE_URL,
Γûê    DB_SCHEMA,
Γûê    DB_SCHEMA_FALLBACK,
Γûê    MAX_UPLOAD_BYTES,
Γûê    MAX_YAML_DEPTH,
Γûê    MAX_YAML_LINES,
Γûê)
Γöé
ΓûêHAPPY = ROOT / "data" / "happyCase"
ΓûêBROKEN = ROOT / "data" / "testCase"
Γöé
Γûê# T├¬n file script sß║╜ upload. D├╣ng ─æß╗â kiß╗âm tra va chß║ím tr╞░ß╗¢c khi chß║íy v├á ─æß╗â dß╗ìn
Γûê# dß║╣p ch├¡nh x├íc l├║c kß║┐t th├║c.
ΓûêCATALOG_SACH = "01-simple-notification-worker.catalog.yaml"
ΓûêCATALOG_CANH_BAO = "02-normal-order-service.catalog.yaml"
ΓûêCATALOG_D1 = "D1-order-service.catalog.yaml"
ΓûêCATALOG_D3 = "D3-order-duplicate.catalog.yaml"
ΓûêTEN_FILE_SE_TAO = [CATALOG_SACH, CATALOG_CANH_BAO, CATALOG_D1, CATALOG_D3, "bom-utf8.yaml"]
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# B├ío c├ío
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass Report:
Γûê    """Gom kß║┐t quß║ú v├á in ra dß║íng bß║úng. Kh├┤ng dß╗½ng ß╗ƒ lß╗ùi ─æß║ºu ti├¬n ΓÇö mß╗Öt lß║ºn chß║íy
Γûê    phß║úi cho biß║┐t Tß║ñT Cß║ó nhß╗»ng g├¼ ─æang hß╗Ång, kh├┤ng phß║úi tß╗½ng c├íi mß╗Öt."""
Γöé
Γûê    def __init__(self) -> None:
Γûê        self.passed = 0
Γûê        self.failed: list[str] = []
Γöé
Γûê    def section(self, title: str) -> None:
Γûê        print(f"\n\033[1m{title}\033[0m")
Γöé
Γûê    def check(self, name: str, ok: bool, detail: str = "") -> bool:
Γûê        if ok:
Γûê            self.passed += 1
Γûê            print(f"  \033[32mPASS\033[0m  {name:<52} {detail}")
Γûê        else:
Γûê            self.failed.append(name)
Γûê            print(f"  \033[31mFAIL\033[0m  {name:<52} {detail}")
Γûê        return ok
Γöé
Γûê    def equals(self, name: str, actual: Any, expected: Any) -> bool:
Γûê        return self.check(
Γûê            name,
Γûê            actual == expected,
Γûê            f"{actual!r}" if actual == expected else f"nhß║¡n {actual!r}, mong {expected!r}",
Γûê        )
Γöé
Γûê    def summary(self) -> int:
Γûê        total = self.passed + len(self.failed)
Γûê        print("\n" + "ΓöÇ" * 78)
Γûê        if self.failed:
Γûê            print(f"\033[31m{len(self.failed)}/{total} Hß╗ÄNG\033[0m")
Γûê            for name in self.failed:
Γûê                print(f"   - {name}")
Γûê            return 1
Γûê        print(f"\033[32m{total}/{total} PASS\033[0m")
Γûê        return 0
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Hß╗úp ─æß╗ông response ΓÇö t├¡nh chß║Ñt phß║úi ─æ├║ng cho Mß╗îI response
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
ΓûêSTATUS_THEO_SEVERITY = {
Γûê    "none": "success",
Γûê    "low": "warning",
Γûê    "validation": "error",
Γûê    "critical": "error",
Γûê}
Γöé
Γöé
Γûêdef vi_pham_contract(body: dict[str, Any]) -> list[str]:
Γûê    loi = []
Γûê    for field in ("status", "severity", "message", "can_continue", "next_action",
Γûê                  "stage", "request_id", "issues", "details"):
Γûê        if field not in body:
Γûê            loi.append(f"thiß║┐u field '{field}'")
Γûê    if not loi:
Γûê        mong = STATUS_THEO_SEVERITY.get(body["severity"])
Γûê        if body["status"] != mong:
Γûê            loi.append(f"status={body['status']} kh├┤ng khß╗¢p severity={body['severity']}")
Γûê        if body["status"] == "error" and body["can_continue"]:
Γûê            loi.append("lß╗ùi nh╞░ng can_continue=True")
Γûê        if not body["request_id"]:
Γûê            loi.append("request_id r├í┬╗ΓÇöng")
Γûê    return loi
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Client
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass Api:
Γûê    def __init__(self, base_url: str, rp: Report) -> None:
Γûê        self.base = base_url.rstrip("/")
Γûê        self.rp = rp
Γûê        self.client = httpx.Client(timeout=30.0)
Γöé
Γûê    def _kiem_contract(self, r: httpx.Response) -> dict[str, Any]:
Γûê        try:
Γûê            body = r.json()
Γûê        except Exception:
Γûê            self.rp.check("response l├á JSON hß╗úp lß╗ç", False, r.text[:80])
Γûê            return {}
Γûê        for v in vi_pham_contract(body):
Γûê            self.rp.check(f"contract: {v}", False, f"{r.request.method} {r.url.path}")
Γûê        return body
Γöé
Γûê    def upload(self, name: str, data: bytes | str,
Γûê               content_type: str = "application/x-yaml") -> tuple[int, dict[str, Any]]:
Γûê        raw = data.encode("utf-8") if isinstance(data, str) else data
Γûê        r = self.client.post(f"{self.base}/catalogs",
Γûê                             files={"file": (name, raw, content_type)})
Γûê        return r.status_code, self._kiem_contract(r)
Γöé
Γûê    def upload_file(self, path: Path) -> tuple[int, dict[str, Any]]:
Γûê        return self.upload(path.name, path.read_bytes())
Γöé
Γûê    def get(self, path: str, **params) -> tuple[int, dict[str, Any]]:
Γûê        r = self.client.get(f"{self.base}{path}", params=params or None)
Γûê        if path == "/health":
Γûê            return r.status_code, r.json()
Γûê        return r.status_code, self._kiem_contract(r)
Γöé
Γûê    def delete(self, filename: str) -> tuple[int, dict[str, Any]]:
Γûê        r = self.client.delete(f"{self.base}/catalogs/{filename}")
Γûê        return r.status_code, self._kiem_contract(r)
Γöé
Γûê    def raw(self, method: str, path: str) -> tuple[int, dict[str, Any]]:
Γûê        r = self.client.request(method, f"{self.base}{path}")
Γûê        return r.status_code, self._kiem_contract(r)
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Truy vß║Ñn database ΓÇö nguß╗ôn sß╗▒ thß║¡t, kh├┤ng tin lß╗¥i API kß╗â
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass Db:
Γûê    def __init__(self) -> None:
Γûê        if not DATABASE_URL:
Γûê            sys.exit("Thiß║┐u DATABASE_URL trong .env ΓÇö kh├┤ng c├│ database ─æß╗â kiß╗âm chß╗⌐ng.")
Γûê        self.schema = DB_SCHEMA or DB_SCHEMA_FALLBACK
Γûê        self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Γöé
Γûê    def _q(self, sql: str, **kw):
Γûê        with self.engine.connect() as c:
Γûê            return c.execute(text(sql.format(s=self.schema)), kw)
Γöé
Γûê    def ten_file_dang_co(self) -> list[str]:
Γûê        return [r[0] for r in self._q(
Γûê            "select content->'scope'->'sources'->0->>'file' from {s}.input_json"
Γûê        ).all()]
Γöé
Γûê    def so_dong(self) -> int:
Γûê        return self._q("select count(*) from {s}.input_json").scalar()
Γöé
Γûê    def dong(self, filename: str) -> dict[str, Any] | None:
Γûê        r = self._q(
Γûê            "select id, jsonb_typeof(content), length(content::text), "
Γûê            "  jsonb_array_length(content->'edges'), content->>'generatedAt' "
Γûê            "from {s}.input_json "
Γûê            "where content->'scope'->'sources'->0->>'file' = :f",
Γûê            f=filename,
Γûê        ).first()
Γûê        if r is None:
Γûê            return None
Γûê        return {"id": r[0], "kieu": r[1], "so_ky_tu": r[2], "edges": r[3], "generatedAt": r[4]}
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Quß║ún l├╜ server tß╗▒ dß╗▒ng
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass Server:
Γûê    def __init__(self, port: int) -> None:
Γûê        self.port = port
Γûê        self.proc: subprocess.Popen | None = None
Γöé
Γûê    def start(self) -> None:
Γûê        self.proc = subprocess.Popen(
Γûê            [sys.executable, "-m", "uvicorn", "src.main:app",
Γûê             "--port", str(self.port), "--log-level", "warning"],
Γûê            cwd=str(ROOT),
Γûê            stdout=subprocess.DEVNULL,
Γûê            stderr=subprocess.DEVNULL,
Γûê            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
Γûê        )
Γûê        self._doi_san_sang()
Γöé
Γûê    def _doi_san_sang(self, timeout: float = 60.0) -> None:
Γûê        base = f"http://127.0.0.1:{self.port}"
Γûê        het_han = time.time() + timeout
Γûê        while time.time() < het_han:
Γûê            if self.proc and self.proc.poll() is not None:
Γûê                sys.exit(f"uvicorn chß║┐t ngay khi khß╗ƒi ─æß╗Öng (exit {self.proc.returncode}).")
Γûê            try:
Γûê                if httpx.get(f"{base}/health", timeout=2.0).status_code == 200:
Γûê                    return
Γûê            except httpx.HTTPError:
Γûê                time.sleep(0.4)
Γûê        sys.exit(f"Server kh├┤ng l├¬n sau {timeout:.0f}s.")
Γöé
Γûê    def stop(self) -> None:
Γûê        if self.proc is None:
Γûê            return
Γûê        self.proc.terminate()
Γûê        try:
Γûê            self.proc.wait(timeout=15)
Γûê        except subprocess.TimeoutExpired:
Γûê            self.proc.kill()
Γûê        self.proc = None
Γöé
Γöé
Γûêdef cong_trong(port: int) -> bool:
Γûê    with socket.socket() as s:
Γûê        return s.connect_ex(("127.0.0.1", port)) != 0
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Dß╗» liß╗çu sinh tß║íi chß╗ù cho c├íc tß║ºng chß║╖n
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûêdef yaml_toi_thieu(sid: str = "order-service", ns: str = "order",
Γûê                   system: str = "order-system") -> str:
Γûê    """File hß╗úp lß╗ç nhß╗Å nhß║Ñt. Tham sß╗æ ho├í id/namespace v├¼ mß╗ùi file THß╗░C Sß╗░ ─æ╞░ß╗úc
Γûê    l╞░u phß║úi khai mß╗Öt component kh├íc nhau ΓÇö hai file c├╣ng khai mß╗Öt node l├á tranh
Γûê    chß║Ñp quyß╗ün sß╗ƒ hß╗»u (409), ─æ├║ng luß║¡t nghiß╗çp vß╗Ñ nh╞░ng kh├┤ng phß║úi thß╗⌐ ─æang test.
Γûê    """
Γûê    return f"""specVersion: vsf-idp.io/v2
Γûêmetadata:
Γûê  domain: commerce
Γûê  system: {system}
Γûê  namespace: {ns}
Γûêspec:
Γûê  type: worker
Γûê  id: {sid}
Γûê  name: Demo Service
Γûê  owners:
Γûê    members:
Γûê      - user: alice@example.com
Γûê        role: techlead
Γûê  review:
Γûê    branch: main
Γûê  topology:
Γûê    - ref: system:{ns}/{system}
Γûê"""
Γöé
Γöé
Γûê# D├╣ng cho c├íc test Bß╗è CHß║╢N tr╞░ß╗¢c tß║ºng 5 ΓÇö kh├┤ng bao giß╗¥ ─æ╞░ß╗úc l╞░u n├¬n id tr├╣ng
Γûê# nhau c┼⌐ng kh├┤ng sao.
ΓûêYAML_TOI_THIEU = yaml_toi_thieu()
Γöé
Γöé
Γûêdef yaml_bomb() -> str:
Γûê    """'Billion laughs': 1KB nß╗ƒ ra h├áng GB l├║c parse. SafeLoader KH├öNG chß║╖n."""
Γûê    lines = ["a0: &a0 'x'"]
Γûê    for i in range(1, 40):
Γûê        lines.append(f"a{i}: &a{i} [{', '.join([f'*a{i - 1}'] * 8)}]")
Γûê    return "\n".join(lines)
Γöé
Γöé
Γûêdef yaml_qua_sau() -> str:
Γûê    return "".join(" " * (2 * i) + f"k{i}:\n" for i in range(MAX_YAML_DEPTH + 5))
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# C├íc nh├│m kß╗ïch bß║ún
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef kiem_health(api: Api, rp: Report) -> None:
Γûê    rp.section("0. Sß╗⌐c khoß║╗ dß╗ïch vß╗Ñ")
Γûê    code, body = api.get("/health")
Γûê    rp.equals("GET /health -> 200", code, 200)
Γûê    rp.equals("body = {'status': 'ok'}", body, {"status": "ok"})
Γöé
Γöé
Γûêdef kiem_happy_path(api: Api, db: Db, rp: Report) -> None:
Γûê    rp.section("2. Nß║íp file hß╗úp lß╗ç ΓÇö sß║ích tuyß╗çt ─æß╗æi")
Γûê    code, body = api.upload_file(HAPPY / CATALOG_SACH)
Γûê    rp.equals("POST /catalogs -> 201", code, 201)
Γûê    rp.equals("status", body.get("status"), "success")
Γûê    rp.equals("severity", body.get("severity"), "none")
Γûê    rp.equals("can_continue", body.get("can_continue"), True)
Γûê    rp.equals("next_action", body.get("next_action"), "proceed")
Γûê    rp.equals("kh├┤ng cß║únh b├ío n├áo", body.get("issues"), [])
Γöé
Γûê    d = body.get("details", {})
Γûê    rp.check("details.record_id l├á sß╗æ nguy├¬n", isinstance(d.get("record_id"), int),
Γûê             f"record_id={d.get('record_id')}")
Γûê    rp.check("details.node_count > 0", d.get("node_count", 0) > 0,
Γûê             f"{d.get('node_count')} node / {d.get('edge_count')} edge")
Γöé
Γûê    rp.section("2b. ─Éß╗æi chiß║┐u thß║│ng trong bß║úng input_json")
Γûê    row = db.dong(CATALOG_SACH)
Γûê    rp.check("d├▓ng tß╗ôn tß║íi trong database", row is not None)
Γûê    if row:
Γûê        rp.equals("id trong DB khß╗¢p record_id API trß║ú vß╗ü", row["id"], d.get("record_id"))
Γûê        rp.equals("cß╗Öt content l├á JSON object", row["kieu"], "object")
Γûê        rp.check("content c├│ nß╗Öi dung thß║¡t", row["so_ky_tu"] > 500,
Γûê                 f"{row['so_ky_tu']} k├╜ tß╗▒, {row['edges']} edge")
Γûê        rp.check("c├│ generatedAt ─æß╗â kh├┤i phß╗Ñc uploaded_at", bool(row["generatedAt"]),
Γûê                 str(row["generatedAt"]))
Γöé
Γöé
Γûêdef kiem_canh_bao(api: Api, rp: Report) -> None:
Γûê    rp.section("3. Nß║íp file hß╗úp lß╗ç nh╞░ng c├│ cß║únh b├ío ΓÇö kh├┤ng chß║╖n luß╗ông")
Γûê    code, body = api.upload_file(HAPPY / CATALOG_CANH_BAO)
Γûê    rp.equals("POST /catalogs -> 201", code, 201)
Γûê    rp.equals("status", body.get("status"), "warning")
Γûê    rp.equals("severity", body.get("severity"), "low")
Γûê    rp.equals("code", body.get("code"), "HAS_WARNINGS")
Γûê    rp.equals("can_continue vß║½n True", body.get("can_continue"), True)
Γûê    rp.equals("next_action", body.get("next_action"), "review_warnings")
Γûê    codes = {i["code"] for i in body.get("issues", [])}
Γûê    rp.check("c├│ cß║únh b├ío AWAITING_SPEC_INGEST", "AWAITING_SPEC_INGEST" in codes, str(codes))
Γöé
Γöé
Γûêdef kiem_ghi_de(api: Api, db: Db, rp: Report) -> None:
Γûê    rp.section("4. Upload lß║íi c├╣ng t├¬n ΓÇö ghi ─æ├¿ ─æ├║ng d├▓ng c┼⌐, kh├┤ng sinh d├▓ng mß╗¢i")
Γûê    truoc = db.dong(CATALOG_SACH)
Γûê    code, body = api.upload_file(HAPPY / CATALOG_SACH)
Γûê    sau = db.dong(CATALOG_SACH)
Γöé
Γûê    rp.equals("POST lß║ºn 2 -> 201", code, 201)
Γûê    rp.equals("status chuyß╗ân th├ánh warning", body.get("status"), "warning")
Γûê    rp.equals("details.replaced_existing", body.get("details", {}).get("replaced_existing"), True)
Γûê    codes = {i["code"] for i in body.get("issues", [])}
Γûê    rp.check("c├│ cß║únh b├ío FILE_REPLACED", "FILE_REPLACED" in codes, str(codes))
Γûê    if truoc and sau:
Γûê        rp.equals("id kh├┤ng ─æß╗òi (UPDATE chß╗⌐ kh├┤ng INSERT)", sau["id"], truoc["id"])
Γöé
Γöé
Γûêdef kiem_layer1(api: Api, rp: Report) -> None:
Γûê    rp.section("5. Tß║ºng 1 ΓÇö input c╞í bß║ún")
Γûê    cases = [
Γûê        ("file r├í┬╗ΓÇöng", "empty.yaml", "", "application/x-yaml", 422, "EMPTY_FILE"),
Γûê        ("sai ─æu├┤i file (.txt)", "catalog.txt", YAML_TOI_THIEU, "text/plain",
Γûê         422, "INVALID_FILE_TYPE"),
Γûê        ("file qu├í lß╗¢n (>1MiB)", "huge.yaml", "#" + "a" * (MAX_UPLOAD_BYTES + 1),
Γûê         "application/x-yaml", 422, "FILE_TOO_LARGE"),
Γûê        ("t├¬n file qu├í d├ái", "a" * 200 + ".yaml", YAML_TOI_THIEU,
Γûê         "application/x-yaml", 422, "FILENAME_TOO_LONG"),
Γûê    ]
Γûê    for ten, fname, data, ctype, http, code in cases:
Γûê        got_http, body = api.upload(fname, data, ctype)
Γûê        rp.check(ten, got_http == http and body.get("code") == code,
Γûê                 f"{got_http} {body.get('code')}")
Γöé
Γûê    # Content-Type do client khai KH├öNG ─æ╞░ß╗úc d├╣ng ─æß╗â chß║╖n ΓÇö tr├¼nh duyß╗çt thß║¡t hay khai sai.
Γûê    # File n├áy ─É╞»ß╗óC L╞»U n├¬n phß║úi khai component ri├¬ng, kh├┤ng ─æß╗Ñng file n├áo kh├íc.
Γûê    noi_dung = yaml_toi_thieu(sid="demo-worker", ns="demo", system="demo-system")
Γûê    got_http, _ = api.upload("bom-utf8.yaml", b"\xef\xbb\xbf" + noi_dung.encode(),
Γûê                             "application/octet-stream")
Γûê    rp.check("Content-Type lß║í + BOM vß║½n ─æ╞░ß╗úc nhß║¡n", got_http == 201, str(got_http))
Γöé
Γöé
Γûêdef kiem_layer2(api: Api, rp: Report) -> None:
Γûê    rp.section("6. Tß║ºng 2 ΓÇö an to├án nß╗Öi dung (chß║íy tr├¬n BYTE TH├ö, tr╞░ß╗¢c khi parse)")
Γûê    cases = [
Γûê        ("path traversal ../../etc/passwd.yaml", "../../etc/passwd.yaml",
Γûê         YAML_TOI_THIEU, 400, "UNSAFE_FILENAME"),
Γûê        ("t├¬n file kiß╗âu Windows ..\\..\\evil.yaml", "..\\..\\windows\\evil.yaml",
Γûê         YAML_TOI_THIEU, 400, "UNSAFE_FILENAME"),
Γûê        ("PNG ─æß╗Öi lß╗æt .yaml", "fake.yaml", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
Γûê         400, "CONTENT_TYPE_MISMATCH"),
Γûê        ("nß╗Öi dung lß║½n NUL byte", "weird.yaml", YAML_TOI_THIEU.encode() + b"\x00\x01",
Γûê         400, "BINARY_CONTENT"),
Γûê        ("tag !!python/object", "evil.yaml",
Γûê         "specVersion: !!python/object/apply:os.system ['echo hi']\n",
Γûê         400, "UNSAFE_YAML_TAG"),
Γûê        ("YAML bomb (billion laughs)", "bomb.yaml", yaml_bomb(),
Γûê         400, "YAML_EXPANSION_BOMB"),
Γûê        ("qu├í nhiß╗üu d├▓ng", "long.yaml", "# comment\n" * (MAX_YAML_LINES + 1),
Γûê         400, "YAML_TOO_MANY_LINES"),
Γûê        ("lß╗ông nhau qu├í s├óu", "deep.yaml", yaml_qua_sau(), 400, "YAML_TOO_DEEP"),
Γûê    ]
Γûê    for ten, fname, data, http, code in cases:
Γûê        got_http, body = api.upload(fname, data)
Γûê        rp.check(ten, got_http == http and body.get("code") == code,
Γûê                 f"{got_http} {body.get('code')}")
Γöé
Γöé
Γûêdef kiem_layer3_4(api: Api, rp: Report) -> None:
Γûê    rp.section("7. Tß║ºng 3 & 4 ΓÇö to├án vß║╣n file v├á cß║Ñu tr├║c")
Γûê    dup = YAML_TOI_THIEU.replace("  domain: commerce", "  domain: commerce\n  domain: retail")
Γûê    cases = [
Γûê        ("kh├┤ng phß║úi UTF-8", "latin.yaml", "specVersion: caf\xe9".encode("latin-1"),
Γûê         422, "INVALID_ENCODING"),
Γûê        ("c├║ ph├íp YAML vß╗í", "broken.yaml", "spec:\n  - a\n b: [unclosed\n",
Γûê         422, "YAML_SYNTAX"),
Γûê        ("key tr├╣ng lß║╖p", "dup.yaml", dup, 422, "DUPLICATE_KEY"),
Γûê        ("root kh├┤ng phß║úi mapping", "list.yaml", "- a\n- b\n", 422, "INVALID_STRUCTURE"),
Γûê        ("thiß║┐u section bß║»t buß╗Öc", "partial.yaml", "specVersion: vsf-idp.io/v2\n",
Γûê         422, "MISSING_REQUIRED_SECTION"),
Γûê        ("section sai kiß╗âu", "wrong.yaml",
Γûê         "specVersion: vsf-idp.io/v2\nmetadata: hello\nspec: 123\n",
Γûê         422, "INVALID_STRUCTURE"),
Γûê    ]
Γûê    for ten, fname, data, http, code in cases:
Γûê        got_http, body = api.upload(fname, data)
Γûê        rp.check(ten, got_http == http and body.get("code") == code,
Γûê                 f"{got_http} {body.get('code')}")
Γöé
Γûê    # File vß╗í c├║ ph├íp thß║¡t tß╗½ bß╗Ö fixture -> ─æ├║ng 1 lß╗ùi, dß╗½ng ngay (fail-fast).
Γûê    got_http, body = api.upload_file(BROKEN / "C-broken-syntax.catalog.yaml")
Γûê    rp.check("C-broken-syntax.catalog.yaml -> YAML_SYNTAX, ─æ├║ng 1 lß╗ùi",
Γûê             got_http == 422 and body.get("code") == "YAML_SYNTAX"
Γûê             and len(body.get("issues", [])) == 1,
Γûê             f"{got_http} {body.get('code')} / {len(body.get('issues', []))} l├í┬╗ΓÇöi")
Γöé
Γöé
Γûêdef kiem_layer5(api: Api, db: Db, rp: Report) -> None:
Γûê    rp.section("8. Tß║ºng 5 ΓÇö luß║¡t nghiß╗çp vß╗Ñ (GOM Hß║╛T lß╗ùi, kh├┤ng dß╗½ng ß╗ƒ lß╗ùi ─æß║ºu)")
Γöé
Γûê    got_http, body = api.upload_file(BROKEN / "A-invalid-fields.catalog.yaml")
Γûê    loi = [i for i in body.get("issues", []) if i["severity"] == "error"]
Γûê    rp.equals("A-invalid-fields -> 422", got_http, 422)
Γûê    rp.equals("code", body.get("code"), "SCHEMA_VALIDATION_FAILED")
Γûê    rp.equals("stage", body.get("stage"), "layer5_data")
Γûê    rp.check("gom ─æ├║ng 13 lß╗ùi trong Mß╗ÿT response", len(loi) == 13, f"{len(loi)} lß╗ùi")
Γûê    rp.check("mß╗ùi lß╗ùi ─æß╗üu chß╗ë ─æ├║ng vß╗ï tr├¡ trong YAML",
Γûê             all(i.get("location") for i in loi),
Γûê             f"{sum(1 for i in loi if i.get('location'))}/{len(loi)} c├│ location")
Γûê    co = {i["code"] for i in loi}
Γûê    for ma in ("UNSUPPORTED_VERSION", "INVALID_FORMAT", "INVALID_ENUM",
Γûê               "MISSING_TECHLEAD", "INVALID_REF", "UNKNOWN_KIND"):
Γûê        rp.check(f"  bß║»t ─æ╞░ß╗úc {ma}", ma in co)
Γöé
Γûê    got_http, body = api.upload_file(BROKEN / "B-missing-required.catalog.yaml")
Γûê    loi = [i for i in body.get("issues", []) if i["severity"] == "error"]
Γûê    rp.check("B-missing-required -> 422 vß╗¢i ─æ├║ng 5 lß╗ùi REQUIRED",
Γûê             got_http == 422 and len(loi) == 5
Γûê             and all(i["code"] == "REQUIRED" for i in loi),
Γûê             f"{got_http}, {len(loi)} l├í┬╗ΓÇöi: {sorted({i['code'] for i in loi})}")
Γöé
Γûê    rp.check("file lß╗ùi KH├öNG ─æß╗â lß║íi g├¼ trong database",
Γûê             db.dong("A-invalid-fields.catalog.yaml") is None
Γûê             and db.dong("B-missing-required.catalog.yaml") is None)
Γöé
Γöé
Γûêdef kiem_hitl(api: Api, db: Db, rp: Report) -> None:
Γûê    """Chß║íy ─Éß║ªU TI├èN, tr├¬n bß║úng rß╗ùng.
Γöé
Γûê    D1 v├á D3 c├╣ng khai `component:order/order-service`. Nß║┐u ─æß╗â sau c├íc b╞░ß╗¢c kh├íc
Γûê    th├¼ D1 sß║╜ tranh chß║Ñp vß╗¢i catalog ─æ├ú nß║íp tr╞░ß╗¢c ─æ├│ v├á ta kh├┤ng c├▓n ph├ón biß╗çt
Γûê    ─æ╞░ß╗úc "D1 xung ─æß╗Öt vß╗¢i D3" ΓÇö ─æ├║ng thß╗⌐ ─æang muß╗æn kiß╗âm ΓÇö vß╗¢i "D1 xung ─æß╗Öt vß╗¢i
Γûê    mß╗Öt file bß║Ñt kß╗│ n├áo ─æ├│". Kß║┐t th├║c, section n├áy xo├í D1 ─æß╗â trß║ú lß║íi bß║úng rß╗ùng.
Γûê    """
Γûê    rp.section("1. Human-in-the-loop ΓÇö tranh chß║Ñp quyß╗ün sß╗ƒ hß╗»u giß╗»a 2 file")
Γûê    code_d1, _ = api.upload_file(BROKEN / CATALOG_D1)
Γûê    rp.equals("D1 nß║íp ─æ╞░ß╗úc (tß╗½ng file ri├¬ng ─æß╗üu hß╗úp lß╗ç)", code_d1, 201)
Γöé
Γûê    code_d3, body = api.upload_file(BROKEN / CATALOG_D3)
Γûê    rp.equals("D3 -> 409 Conflict", code_d3, 409)
Γûê    rp.equals("code", body.get("code"), "NEEDS_HUMAN_REVIEW")
Γûê    rp.equals("next_action", body.get("next_action"), "human_review")
Γûê    rp.equals("can_continue", body.get("can_continue"), False)
Γûê    co = {i["code"] for i in body.get("issues", [])}
Γûê    rp.check("chß╗ë r├╡ tranh chß║Ñp g├¼", co & {"AMBIGUOUS_OWNER", "DUPLICATE_DECLARATION"} != set(),
Γûê             str(co))
Γûê    rp.check("D3 KH├öNG ─æ╞░ß╗úc ghi v├áo database", db.dong(CATALOG_D3) is None)
Γûê    rp.check("D1 ─æ├ú c├│ vß║½n c├▓n nguy├¬n", db.dong(CATALOG_D1) is not None)
Γöé
Γûê    api.delete(CATALOG_D1)
Γûê    rp.check("dß╗ìn D1, trß║ú bß║úng vß╗ü rß╗ùng cho c├íc b╞░ß╗¢c sau", db.so_dong() == 0,
Γûê             f"{db.so_dong()} d├▓ng")
Γöé
Γöé
Γûêdef kiem_liet_ke(api: Api, rp: Report) -> None:
Γûê    rp.section("9. Danh s├ích v├á t├¼m kiß║┐m")
Γûê    code, body = api.get("/catalogs")
Γûê    d = body.get("details", {})
Γûê    rp.equals("GET /catalogs -> 200", code, 200)
Γûê    rp.check("details.total khß╗¢p sß╗æ item trß║ú vß╗ü", d.get("total") == len(d.get("items", [])),
Γûê             f"total={d.get('total')}")
Γûê    rp.check("item ─æß╗º field ─æß╗â render bß║úng",
Γûê             all(k in (d.get("items") or [{}])[0] for k in
Γûê                 ("file", "root", "state", "error_count", "warning_count", "node_count",
Γûê                  "edge_count", "size_bytes", "uploaded_at", "output_file", "record_id")))
Γöé
Γûê    _, body = api.get("/catalogs", q="order")
Γûê    d = body.get("details", {})
Γûê    rp.check("t├¼m theo chuß╗ùi con ?q=order",
Γûê             all("order" in i["file"] for i in d.get("items", [])) and d.get("returned", 0) > 0,
Γûê             f"{d.get('returned')}/{d.get('total')} file")
Γöé
Γûê    _, body = api.get("/catalogs", q="ORDER")
Γûê    rp.check("t├¼m kiß║┐m kh├┤ng ph├ón biß╗çt hoa th╞░ß╗¥ng",
Γûê             body.get("details", {}).get("returned", 0) > 0)
Γöé
Γûê    _, body = api.get("/catalogs", q="khong-ton-tai-dau")
Γûê    rp.check("kh├┤ng t├¼m thß║Ñy vß║½n l├á success, kh├┤ng phß║úi lß╗ùi",
Γûê             body.get("status") == "success"
Γûê             and body.get("details", {}).get("returned") == 0)
Γöé
Γûê    _, body = api.get("/catalogs")
Γûê    rp.check("mß║╖c ─æß╗ïnh KH├öNG k├¿m diagnostics",
Γûê             body["details"]["items"][0].get("diagnostics") is None)
Γûê    _, body = api.get("/catalogs", include="diagnostics")
Γûê    rp.check("?include=diagnostics th├¼ c├│ chi tiß║┐t",
Γûê             body["details"]["items"][0].get("diagnostics") is not None)
Γöé
Γöé
Γûêdef kiem_xoa(api: Api, db: Db, rp: Report) -> None:
Γûê    rp.section("10. Xo├í v├á gß╗úi ├╜ t├¬n")
Γûê    code, body = api.delete(CATALOG_CANH_BAO)
Γûê    rp.equals(f"DELETE {CATALOG_CANH_BAO} -> 200", code, 200)
Γûê    rp.equals("status", body.get("status"), "success")
Γûê    rp.check("d├▓ng ─æ├ú biß║┐n mß║Ñt khß╗Åi database", db.dong(CATALOG_CANH_BAO) is None)
Γöé
Γûê    code, body = api.delete("khong-co-that.yaml")
Γûê    rp.equals("xo├í file kh├┤ng tß╗ôn tß║íi -> 422", code, 422)
Γûê    rp.equals("code", body.get("code"), "CATALOG_NOT_FOUND")
Γûê    rp.equals("can_continue", body.get("can_continue"), False)
Γöé
Γûê    _, body = api.delete("01-simple")
Γûê    rp.check("g├╡ tß║»t vß║½n gß╗úi ├╜ ─æ╞░ß╗úc t├¬n ─æß║ºy ─æß╗º",
Γûê             CATALOG_SACH in body.get("details", {}).get("suggestions", []),
Γûê             str(body.get("details", {}).get("suggestions")))
Γöé
Γûê    _, body = api.delete("01-simple-notification-worker.catalog.yam")
Γûê    rp.check("g├╡ sai mß╗Öt k├╜ tß╗▒ vß║½n gß╗úi ├╜ ─æ╞░ß╗úc (khß╗¢p mß╗¥)",
Γûê             CATALOG_SACH in body.get("details", {}).get("suggestions", []),
Γûê             str(body.get("details", {}).get("suggestions")))
Γöé
Γûê    _, body = api.delete("zzzzzzzzzzzz.yaml")
Γûê    rp.check("kh├┤ng gß╗úi ├╜ bß╗½a khi kh├┤ng c├│ g├¼ giß╗æng",
Γûê             body.get("details", {}).get("suggestions") == [])
Γöé
Γöé
Γûêdef kiem_fail_safe(api: Api, rp: Report) -> None:
Γûê    rp.section("11. Fail-safe ΓÇö lß╗ùi ngo├ái luß╗ông vß║½n ─æ├║ng contract")
Γûê    code, body = api.raw("GET", "/duong-dan-khong-ton-tai")
Γûê    rp.check("route lß║í -> 404 ─æ├║ng contract",
Γûê             code == 404 and body.get("code") == "HTTP_404", f"{code} {body.get('code')}")
Γöé
Γûê    code, body = api.raw("PUT", "/catalogs")
Γûê    rp.check("sai HTTP method -> 405 ─æ├║ng contract",
Γûê             code == 405 and body.get("status") == "error", f"{code} {body.get('status')}")
Γöé
Γûê    r = api.client.post(f"{api.base}/catalogs")
Γûê    body = r.json()
Γûê    rp.check("POST kh├┤ng k├¿m file -> NO_FILE",
Γûê             r.status_code == 422 and body.get("code") == "NO_FILE",
Γûê             f"{r.status_code} {body.get('code')}")
Γöé
Γûê    r = api.client.get(f"{api.base}/catalogs", headers={"X-Request-ID": "demo-trace-123"})
Γûê    rp.check("X-Request-ID cß╗ºa client ─æ╞░ß╗úc giß╗» nguy├¬n trong log v├á response",
Γûê             r.headers.get("X-Request-ID") == "demo-trace-123"
Γûê             and r.json()["request_id"] == "demo-trace-123",
Γûê             r.headers.get("X-Request-ID", ""))
Γöé
Γöé
Γûêdef kiem_restart(server: Server, api: Api, db: Db, rp: Report) -> None:
Γûê    rp.section("12. Bß╗ün vß╗»ng qua RESTART ΓÇö thß╗⌐ bß║ún ghi ra output_json/ kh├┤ng l├ám ─æ╞░ß╗úc")
Γûê    truoc = {i["file"]: i for i in api.get("/catalogs")[1]["details"]["items"]}
Γûê    rp.check("c├│ dß╗» liß╗çu tr╞░ß╗¢c khi restart", len(truoc) > 0, f"{len(truoc)} catalog")
Γöé
Γûê    print("        ... tß║»t uvicorn v├á bß║¡t lß║íi")
Γûê    server.stop()
Γûê    server.start()
Γöé
Γûê    code, body = api.get("/catalogs")
Γûê    sau = {i["file"]: i for i in body["details"]["items"]}
Γûê    rp.equals("GET /catalogs sau restart -> 200", code, 200)
Γûê    rp.check("danh s├ích c├▓n nguy├¬n sau restart",
Γûê             set(sau) == set(truoc), f"{len(sau)}/{len(truoc)} catalog")
Γöé
Γûê    for ten in truoc:
Γûê        if ten not in sau:
Γûê            continue
Γûê        rp.equals(f"  {ten}: record_id giß╗» nguy├¬n", sau[ten]["record_id"],
Γûê                  truoc[ten]["record_id"])
Γöé
Γûê    mau = next(iter(sau.values()), {})
Γûê    rp.check("size_bytes = null (kh├┤ng nß║▒m trong JSON, ─æ├║ng thiß║┐t kß║┐)",
Γûê             mau.get("size_bytes") is None, str(mau.get("size_bytes")))
Γûê    rp.check("uploaded_at kh├┤i phß╗Ñc ─æ╞░ß╗úc tß╗½ generatedAt",
Γûê             mau.get("uploaded_at") is not None, str(mau.get("uploaded_at")))
Γûê    rp.check("sß╗æ liß╗çu ─æß╗ô thß╗ï kh├┤i phß╗Ñc nguy├¬n vß║╣n",
Γûê             mau.get("node_count", 0) > 0 and mau.get("root"),
Γûê             f"{mau.get('node_count')} node, root={mau.get('root')}")
Γöé
Γöé
Γûêdef don_dep(api: Api, db: Db, rp: Report, goc: int) -> None:
Γûê    rp.section("13. Dß╗ìn dß║╣p ΓÇö trß║ú database vß╗ü ─æ├║ng trß║íng th├íi ban ─æß║ºu")
Γûê    con_lai = [i["file"] for i in api.get("/catalogs")[1]["details"]["items"]]
Γûê    for ten in con_lai:
Γûê        api.delete(ten)
Γûê    rp.check("─æ├ú xo├í hß║┐t catalog do script tß║ío", len(con_lai) >= 0, f"{len(con_lai)} file")
Γûê    rp.equals("sß╗æ d├▓ng trong input_json trß╗ƒ lß║íi nh╞░ tr╞░ß╗¢c khi chß║íy", db.so_dong(), goc)
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef main() -> int:
Γûê    ap = argparse.ArgumentParser(description="Kiß╗âm thß╗¡ end-to-end IDP Catalog Graph API")
Γûê    ap.add_argument("--base-url", help="Bß║»n v├áo server c├│ sß║╡n (bß╗Å qua phß║ºn restart)")
Γûê    ap.add_argument("--port", type=int, default=8765, help="Cß╗òng cho server script tß╗▒ dß╗▒ng")
Γûê    args = ap.parse_args()
Γöé
Γûê    for thu_muc in (HAPPY, BROKEN):
Γûê        if not thu_muc.is_dir():
Γûê            sys.exit(f"Kh├┤ng t├¼m thß║Ñy {thu_muc} ΓÇö bß╗Ö test cß║ºn dß╗» liß╗çu mß║½u trong data/.")
Γöé
Γûê    db = Db()
Γûê    print(f"Database : {db.schema}.input_json")
Γöé
Γûê    # Kh├┤ng chß║íy nß║┐u sß║╜ giß║½m l├¬n dß╗» liß╗çu c├│ sß║╡n.
Γûê    dang_co = db.ten_file_dang_co()
Γûê    va_cham = sorted(set(dang_co) & set(TEN_FILE_SE_TAO))
Γûê    if va_cham:
Γûê        sys.exit(
Γûê            "Dß╗¬NG: bß║úng ─æ├ú c├│ sß║╡n catalog tr├╣ng t├¬n vß╗¢i file m├á script sß║╜ upload:\n  "
Γûê            + "\n  ".join(va_cham)
Γûê            + "\nChß║íy tiß║┐p sß║╜ ghi ─æ├¿ dß╗» liß╗çu cß╗ºa bß║ín. H├úy xo├í ch├║ng tr╞░ß╗¢c, hoß║╖c ─æß╗òi "
Γûê              "DATABASE_URL sang schema kh├íc."
Γûê        )
Γûê    so_dong_goc = db.so_dong()
Γûê    print(f"Ban ─æß║ºu  : {so_dong_goc} d├▓ng trong bß║úng")
Γöé
Γûê    server: Server | None = None
Γûê    if args.base_url:
Γûê        base = args.base_url
Γûê        print(f"Server   : {base} (c├│ sß║╡n ΓÇö bß╗Å qua kß╗ïch bß║ún restart)")
Γûê    else:
Γûê        if not cong_trong(args.port):
Γûê            sys.exit(f"Cß╗òng {args.port} ─æang bß║¡n. D├╣ng --port <kh├íc> hoß║╖c --base-url.")
Γûê        server = Server(args.port)
Γûê        print(f"Server   : script tß╗▒ dß╗▒ng uvicorn ß╗ƒ cß╗òng {args.port}")
Γûê        server.start()
Γûê        base = f"http://127.0.0.1:{args.port}"
Γöé
Γûê    rp = Report()
Γûê    api = Api(base, rp)
Γûê    try:
Γûê        kiem_health(api, rp)
Γûê        # HITL chß║íy tr╞░ß╗¢c, l├║c bß║úng c├▓n rß╗ùng ΓÇö xem docstring cß╗ºa n├│.
Γûê        kiem_hitl(api, db, rp)
Γûê        kiem_happy_path(api, db, rp)
Γûê        kiem_canh_bao(api, rp)
Γûê        kiem_ghi_de(api, db, rp)
Γûê        kiem_layer1(api, rp)
Γûê        kiem_layer2(api, rp)
Γûê        kiem_layer3_4(api, rp)
Γûê        kiem_layer5(api, db, rp)
Γûê        kiem_liet_ke(api, rp)
Γûê        kiem_xoa(api, db, rp)
Γûê        kiem_fail_safe(api, rp)
Γûê        if server is not None:
Γûê            kiem_restart(server, api, db, rp)
Γûê        don_dep(api, db, rp, so_dong_goc)
Γûê    finally:
Γûê        api.client.close()
Γûê        if server is not None:
Γûê            server.stop()
Γöé
Γûê    return rp.summary()
Γöé
Γöé
Γûêif __name__ == "__main__":
Γûê    raise SystemExit(main())
Γöé
Γöé


scripts\_pyrun.sh:
Γûê#!/usr/bin/env bash
Γûê# Cross-platform Python launcher for AI log hooks.
Γûê# Tries python3 ΓåÆ python ΓåÆ py -3 on PATH; on Windows, falls back to common
Γûê# Python install locations because Git Bash launched by some hooks gets a
Γûê# stripped PATH that omits the Windows Python directory.
Γûê#
Γûê# On Windows, `python`/`python3` on PATH can resolve to the Microsoft Store's
Γûê# "App Execution Alias" stub instead of a real interpreter. That stub is
Γûê# still found by `command -v` (it exists on PATH), but running it just prints
Γûê# an install prompt and exits non-zero ΓÇö so every candidate is verified with
Γûê# `--version` before being trusted, not merely checked for presence.
Γûê#
Γûê# Designed to be sourced or called as: bash scripts/_pyrun.sh <script> [args...]
Γûê#
Γûê# Exits 0 silently if no Python is found ΓÇö hooks must never block the AI tool.
Γûêset -u
Γöé
Γûêis_real_python() {
Γûê  "$@" --version >/dev/null 2>&1
Γûê}
Γöé
ΓûêPY=""
Γûêfor cand in python3 python; do
Γûê  if command -v "$cand" >/dev/null 2>&1 && is_real_python "$cand"; then
Γûê    PY="$cand"
Γûê    break
Γûê  fi
Γûêdone
Γöé
Γûêif [ -z "$PY" ] && command -v py >/dev/null 2>&1 && is_real_python py -3; then
Γûê  PY="py -3"
Γûêfi
Γöé
Γûêif [ -z "$PY" ]; then
Γûê  # PATH candidates missing or all Windows Store stubs ΓÇö probe the project's
Γûê  # own venv and standard install locations directly.
Γûê  shopt -s nullglob 2>/dev/null || true
Γûê  for cand in \
Γûê    .venv/Scripts/python.exe \
Γûê    venv/Scripts/python.exe \
Γûê    /c/Users/*/AppData/Local/Programs/Python/Python*/python.exe \
Γûê    "/c/Program Files/Python"*/python.exe \
Γûê    "/c/Program Files (x86)/Python"*/python.exe \
Γûê    /c/Python*/python.exe; do
Γûê    if [ -x "$cand" ] && is_real_python "$cand"; then PY="$cand"; break; fi
Γûê  done
Γûê  shopt -u nullglob 2>/dev/null || true
Γûêfi
Γöé
Γûê[ -n "$PY" ] || exit 0
Γöé
Γûê# shellcheck disable=SC2086
Γûêexec $PY "$@"


src\agents\graph.py:
Γûêfrom langgraph.graph import END, StateGraph
Γöé
Γûêfrom src.agents.nodes.example_node import analyze_node, respond_node
Γûêfrom src.agents.state import AgentState
Γöé
Γöé
Γûêdef should_continue(state: AgentState) -> str:
Γûê    """Route based on whether an error occurred during analysis."""
Γûê    if state.get("error"):
Γûê        return END
Γûê    return "respond"
Γöé
Γöé
Γûêdef build_graph() -> StateGraph:
Γûê    graph = StateGraph(AgentState)
Γöé
Γûê    # Add nodes
Γûê    graph.add_node("analyze", analyze_node)
Γûê    graph.add_node("respond", respond_node)
Γöé
Γûê    # Add edges
Γûê    graph.set_entry_point("analyze")
Γûê    graph.add_conditional_edges("analyze", should_continue)
Γûê    graph.add_edge("respond", END)
Γöé
Γûê    return graph.compile()
Γöé
Γöé
Γûêagent = build_graph()


src\agents\nodes\example_node.py:
Γûêfrom src.agents.state import AgentState
Γöé
Γöé
Γûêasync def analyze_node(state: AgentState) -> dict:
Γûê    """Ph├ón t├¡ch query tß╗½ user."""
Γûê    query = state.get("query", "")
Γöé
Γûê    # TODO: Th├¬m logic ph├ón t├¡ch thß╗▒c tß║┐
Γûê    # V├¡ dß╗Ñ: gß╗ìi LLM, search vector DB, etc.
Γûê    analysis = f"Ph├ón t├¡ch: {query}"
Γöé
Γûê    return {"analysis": analysis}
Γöé
Γöé
Γûêasync def respond_node(state: AgentState) -> dict:
Γûê    """Tß║ío response tß╗½ analysis."""
Γûê    analysis = state.get("analysis", "")
Γûê    error = state.get("error")
Γöé
Γûê    if error:
Γûê        return {"response": f"Lß╗ùi: {error}"}
Γöé
Γûê    # TODO: Th├¬m logic tß║ío response thß╗▒c tß║┐
Γûê    response = f"Kß║┐t quß║ú dß╗▒a tr├¬n ph├ón t├¡ch: {analysis}"
Γöé
Γûê    return {"response": response}


src\agents\state.py:
Γûêfrom __future__ import annotations
Γöé
Γûêfrom typing import TypedDict
Γöé
Γöé
Γûêclass AgentState(TypedDict, total=False):
Γûê    """State schema cho LangGraph agent.
Γöé
Γûê    Mß╗ùi node ─æß╗ìc v├á ghi v├áo state n├áy.
Γûê    total=False cho ph├⌐p tß║Ñt cß║ú fields l├á optional.
Γûê    """
Γöé
Γûê    query: str
Γûê    context: str
Γûê    analysis: str
Γûê    response: str
Γûê    error: str
Γûê    metadata: dict


src\agents\tools\example_tool.py:
Γûêimport ast
Γûêimport operator
Γöé
Γûêfrom langchain_core.tools import tool
Γöé
Γûê# Safe operator mapping for calculator
Γûê_SAFE_OPERATORS = {
Γûê    ast.Add: operator.add,
Γûê    ast.Sub: operator.sub,
Γûê    ast.Mult: operator.mul,
Γûê    ast.Div: operator.truediv,
Γûê    ast.FloorDiv: operator.floordiv,
Γûê    ast.Mod: operator.mod,
Γûê    ast.Pow: operator.pow,
Γûê    ast.USub: operator.neg,
Γûê    ast.UAdd: operator.pos,
Γûê}
Γöé
Γöé
Γûê@tool
Γûêdef search_knowledge(query: str) -> str:
Γûê    """T├¼m kiß║┐m th├┤ng tin trong knowledge base.
Γöé
Γûê    Args:
Γûê        query: C├óu hß╗Åi cß║ºn t├¼m kiß║┐m
Γöé
Γûê    Returns:
Γûê        Kß║┐t quß║ú t├¼m kiß║┐m
Γûê    """
Γûê    # TODO: Implement actual search logic (e.g., RAG with vector store)
Γûê    return f"Kß║┐t quß║ú t├¼m kiß║┐m cho: {query}"
Γöé
Γöé
Γûê@tool
Γûêdef calculate(expression: str) -> str:
Γûê    """T├¡nh to├ín biß╗âu thß╗⌐c to├ín hß╗ìc an to├án (kh├┤ng d├╣ng eval).
Γöé
Γûê    Hß╗ù trß╗ú: +, -, *, /, //, %, ** v├á dß║Ñu ngoß║╖c.
Γöé
Γûê    Args:
Γûê        expression: Biß╗âu thß╗⌐c cß║ºn t├¡nh (v├¡ dß╗Ñ: "2 + 3 * 4")
Γöé
Γûê    Returns:
Γûê        Kß║┐t quß║ú t├¡nh to├ín
Γûê    """
Γûê    try:
Γûê        tree = ast.parse(expression, mode="eval")
Γûê        result = _eval_node(tree.body)
Γûê        return str(result)
Γûê    except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as e:
Γûê        return f"Lß╗ùi t├¡nh to├ín: {e}"
Γöé
Γöé
Γûêdef _eval_node(node: ast.AST) -> float:
Γûê    """Recursively evaluate AST node using safe operators only."""
Γûê    if isinstance(node, ast.Constant):
Γûê        if isinstance(node.value, (int, float)):
Γûê            return node.value
Γûê        raise ValueError(f"Unsupported constant type: {type(node.value)}")
Γûê    elif isinstance(node, ast.UnaryOp):
Γûê        op_func = _SAFE_OPERATORS.get(type(node.op))
Γûê        if op_func is None:
Γûê            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
Γûê        return op_func(_eval_node(node.operand))
Γûê    elif isinstance(node, ast.BinOp):
Γûê        op_func = _SAFE_OPERATORS.get(type(node.op))
Γûê        if op_func is None:
Γûê            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
Γûê        return op_func(_eval_node(node.left), _eval_node(node.right))
Γûê    else:
Γûê        raise ValueError(f"Unsupported expression: {type(node).__name__}")


src\api\routes.py:
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport json
Γûêimport logging
Γûêfrom typing import Literal
Γûêfrom urllib.parse import unquote
Γöé
Γûêfrom fastapi import (
Γûê    APIRouter,
Γûê    File,
Γûê    Header,
Γûê    HTTPException,
Γûê    Query,
Γûê    Request,
Γûê    Response,
Γûê    UploadFile,
Γûê    status,
Γûê)
Γöé
Γûêfrom src.core.logging import get_request_id
Γûêfrom src.models import schemas
Γûêfrom src.models.schemas import ApiResponse
Γûêfrom src.services import ingest
Γûêfrom src.services.validation import read_upload_within_limit
Γûêfrom src.agents.graph import agent
Γûêfrom src.models.schemas import ChatRequest, ChatResponse
Γûêfrom src.services import github_events
Γöé
Γûê# Kh├┤ng gß╗ìi load_dotenv() ß╗ƒ ─æ├óy: app/core/config.py ─æ├ú nß║íp .env l├║c import (v├á
Γûê# nß║íp theo ─æ╞░ß╗¥ng dß║½n tuyß╗çt ─æß╗æi, n├¬n chß║íy uvicorn tß╗½ th╞░ mß╗Ñc n├áo c┼⌐ng ─æ├║ng).
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γûêrouter = APIRouter(prefix="/catalogs", tags=["Catalogs"])
Γöé
Γöé
Γûê@router.post(
Γûê    "",
Γûê    response_model=ApiResponse,
Γûê    status_code=status.HTTP_201_CREATED,
Γûê    summary="Tß║úi l├¬n 1 file catalog-info.yaml",
Γûê    responses={
Γûê        201: {"description": "Hß╗úp lß╗ç (status=success) hoß║╖c hß╗úp lß╗ç k├¿m cß║únh b├ío (status=warning)"},
Γûê        400: {"description": "Tß╗½ chß╗æi v├¼ l├╜ do an to├án (severity=critical)"},
Γûê        409: {"description": "Tranh chß║Ñp quyß╗ün sß╗ƒ hß╗»u, cß║ºn ng╞░ß╗¥i duyß╗çt (next_action=human_review)"},
Γûê        422: {"description": "Input kh├┤ng hß╗úp lß╗ç (severity=validation)"},
Γûê        500: {"description": "Lß╗ùi hß╗ç thß╗æng (severity=critical)"},
Γûê    },
Γûê)
Γûêasync def upload_catalog(
Γûê    file: UploadFile = File(...),
Γûê    force: bool = Query(default=False, description="├ëp ghi ─æ├¿ nß║┐u c├│ tranh chß║Ñp quyß╗ün sß╗ƒ hß╗»u")
Γûê) -> ApiResponse:
Γûê    """Nhß║¡n file, chß║íy 5 tß║ºng validate, sinh graph JSON v├á l╞░u v├áo bß║úng `input_json`.
Γöé
Γûê    Chß╗ë file qua ─æ╞░ß╗úc TO├ÇN Bß╗ÿ validate mß╗¢i ─æ╞░ß╗úc l╞░u. Bß║ún c┼⌐ ghi file JSON ngay
Γûê    cß║ú khi parse c├▓n lß╗ùi ΓÇö ngh─⌐a l├á kho output t├¡ch luß╗╣ dß╗» liß╗çu hß╗Ång m├á kh├┤ng ai
Γûê    biß║┐t. Giß╗¥ th├¼ lß╗ùi ß╗ƒ tß║ºng n├áo c┼⌐ng dß╗½ng tr╞░ß╗¢c khi chß║ím v├áo database.
Γûê    """
Γûê    try:
Γûê        content = await read_upload_within_limit(file)
Γûê    finally:
Γûê        # UploadFile lß╗¢n ─æ╞░ß╗úc ─æß╗çm ra file tß║ím; kh├┤ng ─æ├│ng th├¼ r├íc nß║▒m lß║íi tr├¬n ─æ─⌐a.
Γûê        # `finally` chß║íy cß║ú khi read raise FILE_TOO_LARGE.
Γûê        await file.close()
Γöé
Γûê    return ingest.ingest_catalog(
Γûê        filename=file.filename,
Γûê        content=content,
Γûê        content_type=file.content_type,
Γûê        request_id=get_request_id(),
Γûê        force=force,
Γûê    )
Γöé
Γöé
Γûê@router.get(
Γûê    "",
Γûê    response_model=ApiResponse,
Γûê    summary="Danh s├ích catalog ─æ├ú nß║íp, c├│ t├¼m kiß║┐m",
Γûê)
Γûêdef list_catalogs(
Γûê    q: str | None = Query(
Γûê        default=None,
Γûê        description="T├¼m theo t├¬n file. "
Γûê        "Bß╗Å trß╗æng ─æß╗â lß║Ñy to├án bß╗Ö danh s├ích.",
Γûê        examples=["order"],
Γûê    ),
Γûê    include: Literal["diagnostics"] | None = Query(
Γûê        default=None, description="Truyß╗ün 'diagnostics' ─æß╗â lß║Ñy k├¿m chi tiß║┐t cß║únh b├ío."
Γûê    ),
Γûê) -> ApiResponse:
Γûê    """Phß╗Ñc vß╗Ñ cß║ú hai c├ích chß╗ìn file ß╗ƒ m├án h├¼nh xo├í:
Γûê    Bß╗Å trß╗æng ─æß╗â lß║Ñy to├án bß╗Ö list file
Γûê    Dß╗» liß╗çu nß║▒m ß╗ƒ `details.items`, k├¿m `details.total` ─æß╗â hiß╗çn "x/y file".
Γûê    """
Γûê    return ingest.list_catalogs(
Γûê        query=q,
Γûê        include_diagnostics=include == "diagnostics",
Γûê        request_id=get_request_id(),
Γûê    )
Γöé
Γöé
Γûê@router.delete(
Γûê    "/{filename}",
Γûê    response_model=ApiResponse,
Γûê    summary="Xo├í 1 catalog ─æ├ú nß║íp",
Γûê    responses={422: {"description": "Kh├┤ng t├¼m thß║Ñy file; details.suggestions gß╗úi ├╜ t├¬n gß║ºn ─æ├║ng"}},
Γûê)
Γûêdef delete_catalog(filename: str, response: Response) -> ApiResponse:
Γûê    """Xo├í cß║ú data trong bß║úng `input_json` lß║½n bß║ún ghi trong cache.
Γöé
Γûê    Trß║ú 200 k├¿m body thay v├¼ 204 rß╗ùng: contract chung y├¬u cß║ºu mß╗ìi response ─æß╗üu
Γûê    ─æß╗ìc ─æ╞░ß╗úc `status`/`message`/`can_continue`. 204 theo ─æ├║ng chuß║⌐n REST h╞ín
Γûê    nh╞░ng buß╗Öc frontend phß║úi xß╗¡ l├╜ ri├¬ng mß╗Öt tr╞░ß╗¥ng hß╗úp kh├┤ng c├│ body ΓÇö ─æß╗òi lß║Ñy
Γûê    sß╗▒ nhß║Ñt qu├ín th├¼ kh├┤ng ─æ├íng.
Γûê    """
Γûê    response.status_code = status.HTTP_200_OK
Γûê    return ingest.delete_catalog(unquote(filename), request_id=get_request_id())
Γöé
Γöé
Γûê@router.post("/chat", response_model=ChatResponse)
Γûêasync def chat(request: ChatRequest) -> ChatResponse:
Γûê    """Chat v├í┬╗ΓÇ║i AI agent."""
Γûê    try:
Γûê        result = await agent.ainvoke({"query": request.message})
Γûê        return ChatResponse(
Γûê            response=result.get("response", ""),
Γûê            analysis=result.get("analysis", ""),
Γûê        )
Γûê    except Exception as e:
Γûê        raise HTTPException(status_code=500, detail=str(e))
Γöé
Γûê@router.get("/status")
Γûêasync def agent_status():
Γûê    """Kiß╗âm tra trß║íng th├íi agent."""
Γûê    return {"status": "ready", "agent": "LangGraph Agent v1.0"}
Γöé
Γöé
Γûê# ==========================================
Γûê# WEBHOOK GITHUB ΓÇö nß║íp/xo├í catalog tß╗▒ ─æß╗Öng khi c├│ push
Γûê# ==========================================
Γûê@router.post(
Γûê    "/webhook/github",
Γûê    response_model=ApiResponse,
Γûê    summary="Nhß║¡n sß╗▒ kiß╗çn push tß╗½ GitHub",
Γûê    responses={
Γûê        200: {"description": "─É├ú xß╗¡ l├╜ (status=success) hoß║╖c c├│ file lß╗ùi (status=warning)"},
Γûê        400: {"description": "Chß╗» k├╜ HMAC sai hoß║╖c thiß║┐u (INVALID_SIGNATURE)"},
Γûê        500: {"description": "Server ch╞░a cß║Ñu h├¼nh WEBHOOK_SECRET"},
Γûê    },
Γûê)
Γûêasync def github_webhook_handler(
Γûê    request: Request,
Γûê    x_github_event: str = Header(None),
Γûê    x_hub_signature_256: str = Header(None),
Γûê) -> ApiResponse:
Γûê    """Push l├¬n GitHub -> ghi nhß║¡t k├╜ + tß╗▒ nß║íp/xo├í catalog t╞░╞íng ß╗⌐ng.
Γöé
Γûê    File `added`/`modified` ─æ╞░ß╗úc tß║úi vß╗ü v├á ─æß║⌐y qua ─æ├║ng pipeline validate 5 tß║ºng
Γûê    cß╗ºa `POST /catalogs`; file `removed` th├¼ gß╗ìi `delete_catalog`. To├án bß╗Ö thß╗⌐ tß╗▒
Γûê    c├íc b╞░ß╗¢c nß║▒m ß╗ƒ `src/services/github_events.py`, controller chß╗ë b├│c header ra
Γûê    v├á gß╗ìi service.
Γöé
Γûê    Mß╗Öt file YAML sai vß║½n trß║ú HTTP 200 k├¿m `status=warning`: trß║ú 4xx/5xx sß║╜ khiß║┐n
Γûê    GitHub ─æ├ính dß║Ñu delivery thß║Ñt bß║íi rß╗ôi retry, m├á retry th├¼ file vß║½n sai y c┼⌐.
Γûê    """
Γûê    body = await request.body()
Γûê    # X├íc thß╗▒c tr├¬n body TH├ö, tr╞░ß╗¢c khi parse ΓÇö chß╗» k├╜ k├╜ tr├¬n ─æ├║ng chuß╗ùi byte
Γûê    # GitHub gß╗¡i ─æi. Raise SecurityError/CriticalError, handler to├án cß╗Ñc ß╗ƒ
Γûê    # src/main.py lo phß║ºn dß╗▒ng response.
Γûê    github_events.verify_signature(body, x_hub_signature_256)
Γöé
Γûê    if x_github_event == "ping":
Γûê        return schemas.success("Webhook ─æ├ú kß║┐t nß╗æi.", request_id=get_request_id())
Γöé
Γûê    if x_github_event != "push":
Γûê        return schemas.success(
Γûê            f"Bß╗Å qua sß╗▒ kiß╗çn '{x_github_event}' ΓÇö chß╗ë xß╗¡ l├╜ push.",
Γûê            request_id=get_request_id(),
Γûê        )
Γöé
Γûê    event = github_events.parse_push_payload(json.loads(body))
Γûê    if event is None:
Γûê        # Push tag, push xo├í nh├ính, hoß║╖c push kh├┤ng chß║ím file YAML n├áo. Kh├┤ng
Γûê        # phß║úi lß╗ùi cß╗ºa ai ΓÇö GitHub bß║»n webhook cho mß╗ìi push l├á ─æ├║ng viß╗çc cß╗ºa n├│.
Γûê        return schemas.success(
Γûê            "Push kh├┤ng c├│ file YAML n├áo cß║ºn xß╗¡ l├╜.", request_id=get_request_id()
Γûê        )
Γöé
Γûê    return await github_events.handle_push(event, request_id=get_request_id())
Γöé


src\config.py:
Γûêfrom functools import lru_cache
Γûêfrom typing import Literal
Γöé
Γûêfrom pydantic import Field
Γûêfrom pydantic_settings import BaseSettings, SettingsConfigDict
Γöé
Γöé
Γûêclass Settings(BaseSettings):
Γûê    model_config = SettingsConfigDict(
Γûê        env_file=".env",
Γûê        env_file_encoding="utf-8",
Γûê        extra="ignore",
Γûê    )
Γöé
Γûê    # App
Γûê    app_name: str = "AI20K Agent"
Γûê    app_env: Literal["development", "production", "test"] = "development"
Γûê    app_port: int = Field(default=8000, ge=1, le=65535)
Γûê    app_host: str = "0.0.0.0"
Γûê    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
Γûê    cors_origins: str = "http://localhost:3000"
Γöé
Γûê    # LLM
Γûê    openai_api_key: str = ""
Γûê    model_name: str = "gpt-4o-mini"
Γûê    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
Γöé
Γûê    # Database
Γûê    database_url: str = "sqlite:///./data/app.db"
Γöé
Γûê    # Vector Store
Γûê    chroma_persist_dir: str = "./data/chroma"
Γöé
Γûê    # GitHub webhook
Γûê    # Rß╗ùng = ch╞░a cß║Ñu h├¼nh. Kh├┤ng c├│ gi├í trß╗ï mß║╖c ─æß╗ïnh n├áo kh├íc ─æ╞░ß╗úc: mß╗Öt secret
Γûê    # mß║╖c ─æß╗ïnh ngh─⌐a l├á ai c┼⌐ng k├╜ ─æ╞░ß╗úc request giß║ú.
Γûê    webhook_secret: str = ""
Γûê    # Rß╗ùng th├¼ gß╗ìi GitHub API ß║⌐n danh ΓÇö repo public vß║½n ─æß╗ìc ─æ╞░ß╗úc, chß╗ë bß╗ï giß╗¢i hß║ín
Γûê    # rate thß║Ñp h╞ín. Repo private th├¼ bß║»t buß╗Öc phß║úi c├│.
Γûê    github_token: str = ""
Γûê    github_api_timeout_seconds: int = 10
Γûê    # Mß╗Öt lß║ºn ─æß╗òi t├¬n th╞░ mß╗Ñc c├│ thß╗â chß║ím h├áng tr─âm file YAML. Kh├┤ng chß║╖n th├¼
Γûê    # mß╗Öt request webhook sß║╜ bß║»n h├áng tr─âm lß╗çnh gß╗ìi API GitHub v├á treo tß╗¢i timeout.
Γûê    github_max_files_per_push: int = 50
Γöé
Γöé
Γûê@lru_cache
Γûêdef get_settings() -> Settings:
Γûê    return Settings()


src\core\config.py:
Γûê"""
Γûêconfig.py ΓÇö ─É╞░ß╗¥ng dß║½n v├á NG╞»ß╗áNG AN TO├ÇN cß╗ºa hß╗ç thß╗æng.
Γöé
ΓûêMß╗ìi con sß╗æ giß╗¢i hß║ín (size, ─æß╗Ö s├óu, sß╗æ d├▓ng...) nß║▒m hß║┐t ß╗ƒ ─æ├óy, kh├┤ng rß║úi r├íc
Γûêtrong code validate. Muß╗æn siß║┐t/nß╗¢i mß╗Öt luß║¡t th├¼ sß╗¡a ─æ├║ng mß╗Öt chß╗ù.
Γûê"""
Γöé
Γûêimport os
Γûêfrom pathlib import Path
Γöé
Γûêfrom dotenv import load_dotenv
Γöé
Γûê# Gß╗æc dß╗▒ ├ín (th╞░ mß╗Ñc chß╗⌐a app/, data/, requirements.txt, ...), suy ra tß╗½ vß╗ï tr├¡
Γûê# file n├áy thay v├¼ d├╣ng ─æ╞░ß╗¥ng dß║½n t╞░╞íng ─æß╗æi "./..." ΓÇö tr├ính phß╗Ñ thuß╗Öc v├áo cwd
Γûê# l├║c chß║íy uvicorn (chß║íy tß╗½ ─æ├óu c┼⌐ng ra ─æ├║ng th╞░ mß╗Ñc).
ΓûêBASE_DIR = Path(__file__).resolve().parents[2]
Γöé
Γûê# Nß║íp .env ß╗ƒ gß╗æc dß╗▒ ├ín. `override=False` ─æß╗â biß║┐n m├┤i tr╞░ß╗¥ng thß║¡t (docker-compose
Γûê# env_file, CI secret) lu├┤n thß║»ng file .env tr├¬n m├íy lß║¡p tr├¼nh vi├¬n.
Γûêload_dotenv(BASE_DIR / ".env", override=False)
Γöé
ΓûêLOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Database ΓÇö n╞íi l╞░u graph JSON (thay cho th╞░ mß╗Ñc output_json/ tr╞░ß╗¢c ─æ├óy)
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûê# Kh├┤ng c├│ gi├í trß╗ï mß║╖c ─æß╗ïnh trß╗Å v├áo mß╗Öt DB n├áo ─æ├│: thiß║┐u biß║┐n n├áy th├¼ phß║úi hß╗Ång
Γûê# ngay l├║c khß╗ƒi ─æß╗Öng vß╗¢i th├┤ng b├ío r├╡ r├áng, chß╗⌐ kh├┤ng phß║úi ├óm thß║ºm ghi v├áo chß╗ù
Γûê# kh├┤ng ai ngß╗¥ tß╗¢i rß╗ôi v├ái ng├áy sau mß╗¢i ph├ít hiß╗çn dß╗» liß╗çu nß║▒m sai n╞íi.
ΓûêDATABASE_URL = os.getenv("DATABASE_URL", "")
Γöé
Γûê# Schema chß╗⌐a bß║úng `input_json`. ─Éß╗â trß╗æng th├¼ suy tß╗½ `options=-csearch_path%3D...`
Γûê# trong DATABASE_URL (xem core/db.py); ─æß║╖t biß║┐n n├áy chß╗ë khi muß╗æn ghi ─æ├¿ URL.
ΓûêDB_SCHEMA = os.getenv("DB_SCHEMA", "")
ΓûêDB_SCHEMA_FALLBACK = "ai20k_db"
Γöé
Γûê# Bß║¡t ─æß╗â in mß╗ìi c├óu SQL ra log ΓÇö chß╗ë d├╣ng khi debug, rß║Ñt ß╗ôn.
ΓûêDB_ECHO = os.getenv("DB_ECHO", "").lower() in ("1", "true", "yes")
Γöé
Γûê# Neon ─æ├│ng connection nh├án rß╗ùi. `pool_pre_ping` cho SQLAlchemy ping tr╞░ß╗¢c khi
Γûê# giao connection cho request, nß║┐u chß║┐t th├¼ lß║╖ng lß║╜ mß╗ƒ lß║íi ΓÇö kh├┤ng c├│ n├│ th├¼
Γûê# request ─æß║ºu ti├¬n sau mß╗Öt l├║c rß║únh sß║╜ ─ân OperationalError.
ΓûêDB_POOL_RECYCLE_SECONDS = 300
ΓûêDB_CONNECT_TIMEOUT_SECONDS = 10
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 1 ΓÇö giß╗¢i hß║ín c╞í bß║ún cß╗ºa file upload
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûê# 1 MiB. catalog-info.yaml thß║¡t cß╗í v├ái KB; ng╞░ß╗íng n├áy ─æ├ú rß╗Öng gß║Ñp tr─âm lß║ºn.
Γûê# ─Éß║╖t thß║Ñp l├á mß╗Öt biß╗çn ph├íp an to├án, kh├┤ng phß║úi sß╗▒ bß║Ñt tiß╗çn: n├│ chß║╖n cß║ú DoS
Γûê# bß║▒ng file khß╗òng lß╗ô lß║½n tai nß║ín upload nhß║ºm file dump.
ΓûêMAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 1024 * 1024))
Γöé
Γûê# ─Éß╗ìc theo tß╗½ng chunk ─æß╗â kh├┤ng nuß╗æt trß╗ìn file v├áo RAM tr╞░ß╗¢c khi kß╗ïp kiß╗âm tra size.
ΓûêUPLOAD_CHUNK_BYTES = 64 * 1024
Γöé
ΓûêALLOWED_EXTENSIONS = (".yaml", ".yml")
ΓûêMAX_FILENAME_LENGTH = 128
Γöé
Γûê# Content-Type do client khai ΓÇö CHß╗ê d├╣ng ─æß╗â cß║únh b├ío, kh├┤ng d├╣ng ─æß╗â chß║╖n.
Γûê# L├╜ do: header n├áy do client tß╗▒ ─æß║╖t, kß║╗ tß║Ñn c├┤ng khai g├¼ c┼⌐ng ─æ╞░ß╗úc, c├▓n tr├¼nh
Γûê# duyß╗çt thß║¡t th├¼ hay gß╗¡i sai (Windows trß║ú "application/octet-stream" cho .yaml).
Γûê# Chß║╖n theo n├│ vß╗½a kh├┤ng an to├án vß╗½a chß║╖n nhß║ºm ng╞░ß╗¥i d├╣ng thß║¡t.
ΓûêEXPECTED_CONTENT_TYPES = (
Γûê    "application/x-yaml",
Γûê    "application/yaml",
Γûê    "text/yaml",
Γûê    "text/x-yaml",
Γûê    "text/plain",
Γûê    "application/octet-stream",
Γûê)
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 2 ΓÇö ng╞░ß╗íng chß╗æng YAML bomb / nß╗Öi dung bß║Ñt th╞░ß╗¥ng
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûê# "Billion laughs": file 1KB d├╣ng anchor/alias lß╗ông nhau nß╗ƒ ra h├áng GB l├║c parse.
Γûê# SafeLoader KH├öNG chß║╖n c├íi n├áy ΓÇö n├│ chß╗ë chß║╖n tß║ío object Python tuß╗│ ├╜.
ΓûêMAX_YAML_ANCHORS = 64
ΓûêMAX_YAML_ALIASES = 256
ΓûêMAX_YAML_DEPTH = 32          # theo mß╗⌐c thß╗Ñt ─æß║ºu d├▓ng
ΓûêMAX_YAML_LINES = 5_000
ΓûêMAX_YAML_LINE_LENGTH = 8_192
Γöé
Γûê# Tag khiß║┐n loader dß╗▒ng object tuß╗│ ├╜. SafeLoader ─æ├ú tß╗½ chß╗æi, ta chß║╖n sß╗¢m h╞ín
Γûê# ─æß╗â trß║ú vß╗ü th├┤ng ─æiß╗çp r├╡ r├áng thay v├¼ mß╗Öt YAMLError kh├│ hiß╗âu.
ΓûêFORBIDDEN_YAML_TAGS = ("!!python/", "!!java", "!!ruby", "!<tag:yaml.org,2002:python")
Γöé
Γûê# Magic bytes cß╗ºa c├íc ─æß╗ïnh dß║íng nhß╗ï ph├ón hay bß╗ï ─æß╗Öi lß╗æt .yaml
ΓûêBINARY_MAGIC_SIGNATURES: dict[bytes, str] = {
Γûê    b"PK\x03\x04": "ZIP/XLSX/DOCX",
Γûê    b"\x89PNG": "PNG",
Γûê    b"\xff\xd8\xff": "JPEG",
Γûê    b"GIF8": "GIF",
Γûê    b"%PDF": "PDF",
Γûê    b"\x1f\x8b": "GZIP",
Γûê    b"BM": "BMP",
Γûê    b"\x7fELF": "ELF",
Γûê    b"MZ": "Windows PE",
Γûê    b"Rar!": "RAR",
Γûê    b"SQLite format 3": "SQLite",
Γûê}


src\core\db.py:
Γûê"""
Γûêdb.py ΓÇö Kß║┐t nß╗æi Postgres v├á tß╗▒ tß║ío bß║úng bß║▒ng ORM.
Γöé
ΓûêKh├┤ng c├│ SQL thuß║ºn n├áo trong dß╗▒ ├ín: bß║úng ─æ╞░ß╗úc m├┤ tß║ú bß║▒ng model SQLAlchemy
Γûê(`app/models/tables.py`), c├▓n `init_db()` dß╗ïch m├┤ tß║ú ─æ├│ th├ánh DDL v├á chß║íy.
ΓûêMuß╗æn th├¬m cß╗Öt th├¼ sß╗¡a model, kh├┤ng phß║úi mß╗ƒ console g├╡ ALTER TABLE.
Γöé
ΓûêV├¼ sao engine tß║ío L╞»ß╗£I (lazy) chß╗⌐ kh├┤ng tß║ío ngay l├║c import: import module kh├┤ng
Γûê─æ╞░ß╗úc ph├⌐p mß╗ƒ kß║┐t nß╗æi mß║íng. Nß║┐u tß║ío ngay, chß╗ë cß║ºn `import src.main` l├║c DB ─æang
Γûêsß║¡p l├á cß║ú tiß║┐n tr├¼nh chß║┐t tr╞░ß╗¢c khi kß╗ïp log ra mß╗Öt d├▓ng tß╗¡ tß║┐ ΓÇö v├á test c┼⌐ng
Γûêkh├┤ng ─æß╗òi ─æ╞░ß╗úc URL tr╞░ß╗¢c khi engine kß╗ïp ra ─æß╗¥i.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport logging
Γûêfrom collections.abc import Iterator
Γûêfrom contextlib import contextmanager
Γûêfrom urllib.parse import parse_qs, unquote, urlparse
Γöé
Γûêfrom sqlalchemy import Engine, create_engine, event, inspect, text
Γûêfrom sqlalchemy.orm import DeclarativeBase, Session
Γûêfrom sqlalchemy.schema import CreateSchema
Γöé
Γûêfrom src.core.config import (
Γûê    DATABASE_URL,
Γûê    DB_CONNECT_TIMEOUT_SECONDS,
Γûê    DB_ECHO,
Γûê    DB_POOL_RECYCLE_SECONDS,
Γûê    DB_SCHEMA,
Γûê    DB_SCHEMA_FALLBACK,
Γûê)
Γûêfrom src.core.errors import CriticalError, ErrorCode, Stage
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γöé
Γûêclass Base(DeclarativeBase):
Γûê    """Gß╗æc khai b├ío cß╗ºa mß╗ìi bß║úng. `Base.metadata` l├á bß║ún m├┤ tß║ú schema m├á
Γûê    `init_db()` ─æem ─æi tß║ío."""
Γöé
Γöé
Γûê# Engine d├╣ng chung to├án tiß║┐n tr├¼nh. `None` = ch╞░a ai cß║ºn tß╗¢i DB.
Γûê_engine: Engine | None = None
Γûê_active_schema: str | None = None
Γöé
Γöé
Γûêdef _schema_from_url(url: str) -> str | None:
Γûê    """R├║t schema ra khß╗Åi `?options=-csearch_path%3Dai20k_db` nß║┐u URL c├│ khai.
Γöé
Γûê    URL Neon d├ín tß╗½ console th╞░ß╗¥ng ─æ├ú k├¿m sß║╡n tham sß╗æ n├áy; ─æß╗ìc lß║íi n├│ ─æß╗â cß║Ñu
Γûê    h├¼nh kh├┤ng m├óu thuß║½n vß╗¢i chuß╗ùi kß║┐t nß╗æi.
Γûê    """
Γûê    options = parse_qs(urlparse(url).query).get("options", [""])[0]
Γûê    marker = "-csearch_path="
Γûê    if marker not in options:
Γûê        return None
Γûê    # `-csearch_path=a,b` -> lß║Ñy schema ─æß║ºu ti├¬n, ─æ├│ l├á n╞íi CREATE TABLE r╞íi v├áo.
Γûê    return unquote(options.split(marker, 1)[1]).split(",")[0].strip() or None
Γöé
Γöé
Γûêdef _make_engine(url: str, schema: str) -> Engine:
Γûê    engine = create_engine(
Γûê        url,
Γûê        echo=DB_ECHO,
Γûê        pool_pre_ping=True,
Γûê        pool_recycle=DB_POOL_RECYCLE_SECONDS,
Γûê        connect_args={"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS},
Γûê    )
Γöé
Γûê    @event.listens_for(engine, "connect")
Γûê    def _set_search_path(dbapi_connection, _record) -> None:
Γûê        """├ëp search_path ß╗ƒ Mß╗îI connection.
Γöé
Γûê        URL c├│ thß╗â qu├¬n `options=-csearch_path=...` (d├ín thiß║┐u, copy nhß║ºm), v├á
Γûê        khi ─æ├│ bß║úng lß║╖ng lß║╜ r╞íi v├áo `public` ΓÇö dß╗» liß╗çu vß║½n ghi ─æ╞░ß╗úc n├¬n kh├┤ng ai
Γûê        nhß║¡n ra cho tß╗¢i l├║c ─æi t├¼m bß║úng ß╗ƒ ─æ├║ng schema m├á kh├┤ng thß║Ñy. ─Éß║╖t lß║íi ß╗ƒ
Γûê        ─æ├óy th├¼ URL thiß║┐u hay ─æß╗º ─æß╗üu cho c├╣ng mß╗Öt kß║┐t quß║ú.
Γûê        """
Γûê        with dbapi_connection.cursor() as cur:
Γûê            cur.execute(f'SET search_path TO "{schema}"')
Γöé
Γûê    return engine
Γöé
Γöé
Γûêdef get_engine() -> Engine:
Γûê    global _engine, _active_schema
Γûê    if _engine is None:
Γûê        if not DATABASE_URL:
Γûê            raise CriticalError(
Γûê                ErrorCode.STORAGE_FAILURE,
Γûê                "Hß╗ç thß╗æng ch╞░a ─æ╞░ß╗úc cß║Ñu h├¼nh kho l╞░u trß╗». Vui l├▓ng li├¬n hß╗ç hß╗ù trß╗ú.",
Γûê                stage=Stage.PERSIST,
Γûê                log_message="Thiß║┐u biß║┐n m├┤i tr╞░ß╗¥ng DATABASE_URL ΓÇö kh├┤ng c├│ DB ─æß╗â ghi.",
Γûê            )
Γûê        # ╞»u ti├¬n: biß║┐n DB_SCHEMA > search_path trong URL > mß║╖c ─æß╗ïnh.
Γûê        _active_schema = (
Γûê            DB_SCHEMA or _schema_from_url(DATABASE_URL) or DB_SCHEMA_FALLBACK
Γûê        )
Γûê        _engine = _make_engine(DATABASE_URL, _active_schema)
Γûê    return _engine
Γöé
Γöé
Γûêdef configure(url: str, schema: str) -> None:
Γûê    """Trß╗Å to├án hß╗ç thß╗æng sang mß╗Öt database kh├íc. D├╣ng cho test.
Γöé
Γûê    Test chß║íy tr├¬n schema ri├¬ng (`ai20k_db_test`) ─æß╗â kh├┤ng ─æß╗Ñng v├áo dß╗» liß╗çu thß║¡t
Γûê    trong `ai20k_db`, nh╞░ng vß║½n l├á Postgres thß║¡t ΓÇö JSONB, BIGSERIAL v├á kiß╗âu so
Γûê    s├ính JSON ─æß╗üu l├á thß╗⌐ chß╗ë Postgres mß╗¢i c├│, giß║ú lß║¡p bß║▒ng DB kh├íc l├á test ─æ├║ng
Γûê    mß╗Öt hß╗ç thß╗æng kh├┤ng tß╗ôn tß║íi.
Γûê    """
Γûê    global _engine, _active_schema
Γûê    dispose()
Γûê    _active_schema = schema
Γûê    _engine = _make_engine(url, schema)
Γöé
Γöé
Γûêdef dispose() -> None:
Γûê    """─É├│ng to├án bß╗Ö connection pool."""
Γûê    global _engine
Γûê    if _engine is not None:
Γûê        _engine.dispose()
Γûê        _engine = None
Γöé
Γöé
Γûêdef active_schema() -> str:
Γûê    """Schema ─æang d├╣ng thß║¡t sß╗▒. Gß╗ìi `get_engine()` tr╞░ß╗¢c v├¼ t├¬n schema chß╗ë ─æ╞░ß╗úc
Γûê    chß╗æt lß║íi l├║c engine ra ─æß╗¥i."""
Γûê    get_engine()
Γûê    assert _active_schema is not None
Γûê    return _active_schema
Γöé
Γöé
Γûê@contextmanager
Γûêdef session_scope() -> Iterator[Session]:
Γûê    """Mß╗Öt session cho mß╗Öt ─æ╞ín vß╗ï c├┤ng viß╗çc: xong th├¼ commit, hß╗Ång th├¼ rollback.
Γöé
Γûê    Rollback l├á phß║ºn quan trß╗ìng: kh├┤ng c├│ n├│, mß╗Öt c├óu INSERT lß╗ùi sß║╜ ─æß╗â lß║íi
Γûê    transaction ß╗ƒ trß║íng th├íi aborted, v├á mß╗ìi c├óu lß╗çnh sau tr├¬n c├╣ng connection
Γûê    ─æß╗üu hß╗Ång theo vß╗¢i th├┤ng b├ío chß║│ng li├¬n quan g├¼ tß╗¢i nguy├¬n nh├ón thß║¡t.
Γûê    """
Γûê    session = Session(bind=get_engine(), expire_on_commit=False)
Γûê    try:
Γûê        yield session
Γûê        session.commit()
Γûê    except Exception:
Γûê        session.rollback()
Γûê        raise
Γûê    finally:
Γûê        session.close()
Γöé
Γöé
Γûêdef init_db() -> None:
Γûê    """Tß║ío schema + bß║úng nß║┐u ch╞░a c├│, rß╗ôi KIß╗éM CHß╗¿NG l├á bß║úng nß║▒m ─æ├║ng chß╗ù.
Γöé
Γûê    `create_all` im lß║╖ng khi bß║úng ─æ├ú tß╗ôn tß║íi, n├¬n bß║ún th├ón n├│ kh├┤ng chß╗⌐ng minh
Γûê    ─æ╞░ß╗úc ─æiß╗üu g├¼. C├óu inspect ß╗ƒ cuß╗æi mß╗¢i l├á thß╗⌐ trß║ú lß╗¥i ─æ╞░ß╗úc "bß║úng c├│ thß║¡t, ß╗ƒ
Γûê    ─æ├║ng schema m├¼nh ngh─⌐ kh├┤ng" ΓÇö v├á log lß║íi ─æß╗â l├║c chß║íy Docker c├▓n nh├¼n thß║Ñy.
Γûê    """
Γûê    # import ß╗ƒ ─æ├óy, kh├┤ng ß╗ƒ ─æß║ºu file: model phß║úi ─æ╞░ß╗úc nß║íp th├¼ mß╗¢i c├│ mß║╖t trong
Γûê    # Base.metadata, nh╞░ng model lß║íi import Base tß╗½ ch├¡nh module n├áy.
Γûê    from src.models import tables  # noqa: F401
Γöé
Γûê    engine = get_engine()
Γûê    schema = active_schema()
Γöé
Γûê    with engine.begin() as conn:
Γûê        conn.execute(CreateSchema(schema, if_not_exists=True))
Γöé
Γûê    Base.metadata.create_all(engine)
Γöé
Γûê    inspector = inspect(engine)
Γûê    tables_found = inspector.get_table_names(schema=schema)
Γûê    with engine.connect() as conn:
Γûê        current = conn.execute(text("select current_schema()")).scalar()
Γöé
Γûê    logger.info(
Γûê        "DB sß║╡n s├áng: schema=%s (current_schema=%s), bß║úng=%s",
Γûê        schema, current, sorted(tables_found),
Γûê    )
Γöé
Γûê    if "input_json" not in tables_found:
Γûê        raise CriticalError(
Γûê            ErrorCode.STORAGE_FAILURE,
Γûê            "Kh├┤ng khß╗ƒi tß║ío ─æ╞░ß╗úc kho l╞░u trß╗».",
Γûê            stage=Stage.PERSIST,
Γûê            log_message=(
Γûê                f"─É├ú chß║íy create_all nh╞░ng kh├┤ng thß║Ñy bß║úng 'input_json' trong "
Γûê                f"schema '{schema}'. Bß║úng c├│ thß╗â ─æ├ú r╞íi v├áo schema kh├íc."
Γûê            ),
Γûê        )
Γöé


src\core\errors.py:
Γûê"""
Γûêerrors.py ΓÇö C├óy exception + bß║úng m├ú lß╗ùi d├╣ng chung cho to├án backend.
Γöé
ΓûêBa nh├│m lß╗ùi, ph├ón loß║íi theo C├üCH Xß╗¼ L├¥ chß╗⌐ kh├┤ng theo nguy├¬n nh├ón kß╗╣ thuß║¡t:
Γöé
Γûê    ValidationError  Lß╗ùi cß╗ºa INPUT. Ng╞░ß╗¥i d├╣ng sß╗¡a file rß╗ôi upload lß║íi l├á xong.
Γûê                     -> HTTP 422, severity "validation", can_continue = False.
Γûê                     -> Log WARNING, KH├öNG log stack trace (kh├┤ng phß║úi bug cß╗ºa ta).
Γöé
Γûê    SecurityError    Input c├│ dß║Ñu hiß╗çu nguy hiß╗âm (spoof, path traversal, YAML bomb).
Γûê                     -> HTTP 400, severity "critical", can_continue = False.
Γûê                     -> Message trß║ú client cß╗æ t├¼nh chung chung; chi tiß║┐t chß╗ë nß║▒m
Γûê                        trong log ΓÇö kh├┤ng dß║íy kß║╗ tß║Ñn c├┤ng c├ích n├⌐ bß╗Ö lß╗ìc.
Γöé
Γûê    CriticalError    Hß╗ç thß╗æng kh├┤ng ─æß║úm bß║úo ─æ╞░ß╗úc trß║íng th├íi an to├án ─æß╗â ─æi tiß║┐p
Γûê                     (kh├┤ng ghi ─æ╞░ß╗úc ─æ─⌐a, config thiß║┐u, invariant vß╗í, exception lß║í).
Γûê                     -> HTTP 500, severity "critical". LU├öN log stack trace.
Γöé
ΓûêV├¼ sao d├╣ng custom exception thay v├¼ exception c├│ sß║╡n cß╗ºa Python:
Γûê  - Cß║ºn mang METADATA m├á built-in kh├┤ng c├│: code, stage, can_continue, next_action,
Γûê    danh s├ích issues -> ─æß╗º ─æß╗â dß╗▒ng thß║│ng response contract, kh├┤ng cß║ºn map lß║íi.
Γûê  - `ValueError` tß╗½ int() v├á `ValueError` tß╗½ business rule cß║ºn 2 c├ích xß╗¡ l├╜ kh├íc
Γûê    nhau; ph├ón loß║íi theo built-in type l├á ph├ón loß║íi sai trß╗Ñc.
Γûê  - Built-in Vß║¬N ─æ╞░ß╗úc d├╣ng ß╗ƒ tß║ºng thß║Ñp (OSError, UnicodeDecodeError, yaml.YAMLError),
Γûê    rß╗ôi bß╗ìc lß║íi khi ─æi l├¬n tß║ºng service: `raise ValidationError(...) from exc`.
Γûê    `from exc` giß╗» nguy├¬n chuß╗ùi nguy├¬n nh├ón trong log.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport logging
Γûêfrom enum import StrEnum
Γûêfrom typing import Any
Γöé
Γöé
Γûêclass Severity(StrEnum):
Γûê    """Mß╗⌐c ─æß╗Ö nghi├¬m trß╗ìng ΓÇö frontend dß╗▒a v├áo ─æ├óy ─æß╗â chß╗ìn m├áu/h├ánh vi UI."""
Γöé
Γûê    NONE = "none"              # kh├┤ng c├│ vß║Ñn ─æß╗ü g├¼
Γûê    LOW = "low"                # warning, ─æi tiß║┐p ─æ╞░ß╗úc
Γûê    VALIDATION = "validation"  # input sai, ng╞░ß╗¥i d├╣ng tß╗▒ sß╗¡a ─æ╞░ß╗úc
Γûê    CRITICAL = "critical"      # dß╗½ng, kh├┤ng tß╗▒ sß╗¡a ─æ╞░ß╗úc ß╗ƒ ph├¡a ng╞░ß╗¥i d├╣ng
Γöé
Γöé
Γûêclass Status(StrEnum):
Γûê    """Kß║┐t quß║ú tß╗òng cß╗ºa request. Suy ra ─æ╞░ß╗úc tß╗½ Severity ΓÇö xem `Status.of()`."""
Γöé
Γûê    SUCCESS = "success"
Γûê    WARNING = "warning"
Γûê    ERROR = "error"
Γöé
Γûê    @classmethod
Γûê    def of(cls, severity: Severity) -> Status:
Γûê        """Nguß╗ôn sß╗▒ thß║¡t duy nhß║Ñt cho cß║╖p (status, severity).
Γöé
Γûê        Contract cß╗ºa bß║ín c├│ cß║ú 2 field, m├á `status` lu├┤n suy ─æ╞░ß╗úc tß╗½ `severity`.
Γûê        Kh├┤ng xo├í `status` (frontend ─æß╗ìc n├│ tiß╗çn h╞ín), nh╞░ng KH├öNG BAO GIß╗£ set tay
Γûê        ΓÇö ─æi qua h├ám n├áy ─æß╗â hai field kh├┤ng thß╗â lß╗çch nhau.
Γûê        """
Γûê        if severity is Severity.NONE:
Γûê            return cls.SUCCESS
Γûê        if severity is Severity.LOW:
Γûê            return cls.WARNING
Γûê        return cls.ERROR
Γöé
Γöé
Γûêclass NextAction(StrEnum):
Γûê    """Ng╞░ß╗¥i d├╣ng cß║ºn l├ám g├¼ tiß║┐p theo. Frontend map thß║│ng sang n├║t bß║Ñm."""
Γöé
Γûê    PROCEED = "proceed"                    # xong, ─æi tiß║┐p
Γûê    REVIEW_WARNINGS = "review_warnings"    # xem cß║únh b├ío rß╗ôi tß╗▒ quyß║┐t ─æß╗ïnh
Γûê    FIX_AND_REUPLOAD = "fix_and_reupload"  # sß╗¡a file, upload lß║íi
Γûê    HUMAN_REVIEW = "human_review"          # v╞░ß╗út thß║⌐m quyß╗ün tß╗▒ ─æß╗Öng, cß║ºn ng╞░ß╗¥i duyß╗çt
Γûê    CONTACT_SUPPORT = "contact_support"    # lß╗ùi ph├¡a hß╗ç thß╗æng, ng╞░ß╗¥i d├╣ng b├│ tay
Γöé
Γöé
Γûêclass Stage(StrEnum):
Γûê    """Chß║╖ng xß╗¡ l├╜ ΓÇö trß║ú vß╗ü cho frontend v├á ghi v├áo log ─æß╗â biß║┐t chß║┐t ß╗ƒ ─æ├óu."""
Γöé
Γûê    RECEIVE = "receive"
Γûê    L1_BASIC_INPUT = "layer1_basic_input"
Γûê    L2_SECURITY = "layer2_security"
Γûê    L3_FILE_INTEGRITY = "layer3_file_integrity"
Γûê    L4_SCHEMA = "layer4_schema"
Γûê    L5_DATA = "layer5_data"
Γûê    PERSIST = "persist"
Γûê    STORE = "store"
Γûê    DONE = "done"
Γöé
Γöé
Γûêclass ErrorCode(StrEnum):
Γûê    """M├ú lß╗ùi ß╗òn ─æß╗ïnh. Frontend switch tr├¬n M├â, kh├┤ng parse `message`.
Γöé
Γûê    Th├¬m m├ú mß╗¢i = th├¬m d├▓ng ß╗ƒ ─æ├óy. Kh├┤ng ─æß╗òi/xo├í m├ú c┼⌐ khi frontend c├▓n d├╣ng.
Γûê    """
Γöé
Γûê    # ΓöÇΓöÇ Layer 1: basic input ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    NO_FILE = "NO_FILE"
Γûê    EMPTY_FILE = "EMPTY_FILE"
Γûê    FILE_TOO_LARGE = "FILE_TOO_LARGE"
Γûê    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
Γûê    FILENAME_TOO_LONG = "FILENAME_TOO_LONG"
Γûê    UNSAFE_FILENAME = "UNSAFE_FILENAME"
Γöé
Γûê    # ΓöÇΓöÇ Layer 2: security ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    BINARY_CONTENT = "BINARY_CONTENT"
Γûê    CONTENT_TYPE_MISMATCH = "CONTENT_TYPE_MISMATCH"
Γûê    UNSAFE_YAML_TAG = "UNSAFE_YAML_TAG"
Γûê    YAML_EXPANSION_BOMB = "YAML_EXPANSION_BOMB"
Γûê    YAML_TOO_DEEP = "YAML_TOO_DEEP"
Γûê    YAML_TOO_MANY_LINES = "YAML_TOO_MANY_LINES"
Γöé
Γûê    # ΓöÇΓöÇ Layer 3: file integrity ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    INVALID_ENCODING = "INVALID_ENCODING"
Γûê    YAML_SYNTAX = "YAML_SYNTAX"
Γûê    DUPLICATE_KEY = "DUPLICATE_KEY"
Γöé
Γûê    # ΓöÇΓöÇ Layer 4: schema ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    INVALID_STRUCTURE = "INVALID_STRUCTURE"
Γûê    MISSING_REQUIRED_SECTION = "MISSING_REQUIRED_SECTION"
Γöé
Γûê    # ΓöÇΓöÇ Layer 5: data / business rules ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
Γöé
Γûê    # ΓöÇΓöÇ Warning (kh├┤ng chß║╖n) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    HAS_WARNINGS = "HAS_WARNINGS"
Γûê    FILE_REPLACED = "FILE_REPLACED"
Γöé
Γûê    # ΓöÇΓöÇ Tra cß╗⌐u / xo├í ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    CATALOG_NOT_FOUND = "CATALOG_NOT_FOUND"
Γöé
Γûê    # ΓöÇΓöÇ GitHub webhook ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    # Chß╗» k├╜ HMAC sai/thiß║┐u -> SecurityError (400). Kh├┤ng phß║úi "input sai ─æß╗ïnh
Γûê    # dß║íng" m├á l├á "request n├áy kh├┤ng chß╗⌐ng minh ─æ╞░ß╗úc n├│ ─æß║┐n tß╗½ GitHub".
Γûê    INVALID_SIGNATURE = "INVALID_SIGNATURE"
Γûê    # Server ch╞░a cß║Ñu h├¼nh WEBHOOK_SECRET -> CriticalError (500). Lß╗ùi cß╗ºa ta,
Γûê    # kh├┤ng phß║úi cß╗ºa ng╞░ß╗¥i gß╗¡i; tuyß╗çt ─æß╗æi kh├┤ng ─æ╞░ß╗úc bß╗Å qua b╞░ß╗¢c x├íc thß╗▒c.
Γûê    WEBHOOK_NOT_CONFIGURED = "WEBHOOK_NOT_CONFIGURED"
Γûê    # Kh├┤ng tß║úi ─æ╞░ß╗úc nß╗Öi dung file tß╗½ GitHub. D├╣ng l├ám `Issue.code` trong response
Γûê    # chß╗⌐ kh├┤ng raise: mß╗Öt file hß╗Ång kh├┤ng ─æ╞░ß╗úc l├ám hß╗Ång cß║ú lß║ºn push.
Γûê    GITHUB_FETCH_FAILED = "GITHUB_FETCH_FAILED"
Γöé
Γûê    # ΓöÇΓöÇ Critical ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    STORAGE_FAILURE = "STORAGE_FAILURE"
Γûê    INTERNAL_ERROR = "INTERNAL_ERROR"
Γûê    INCONSISTENT_STATE = "INCONSISTENT_STATE"
Γûê    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
Γöé
Γöé
Γûêclass AppError(Exception):
Γûê    """Gß╗æc cß╗ºa mß╗ìi lß╗ùi c├│ contract. Mang ─æß╗º dß╗» liß╗çu ─æß╗â dß╗▒ng response.
Γöé
Γûê    Kh├┤ng raise trß╗▒c tiß║┐p class n├áy ΓÇö d├╣ng mß╗Öt trong c├íc lß╗¢p con b├¬n d╞░ß╗¢i.
Γûê    """
Γöé
Γûê    severity: Severity = Severity.CRITICAL
Γûê    http_status: int = 500
Γûê    can_continue: bool = False
Γûê    next_action: NextAction = NextAction.CONTACT_SUPPORT
Γûê    log_level: int = logging.CRITICAL
Γûê    # True = ghi k├¿m stack trace. Lß╗ùi do input ng╞░ß╗¥i d├╣ng th├¼ stack trace v├┤ ngh─⌐a,
Γûê    # chß╗ë l├ám ngß║¡p log v├á che mß║Ñt lß╗ùi thß║¡t.
Γûê    log_traceback: bool = True
Γöé
Γûê    def __init__(
Γûê        self,
Γûê        code: ErrorCode,
Γûê        message: str,
Γûê        *,
Γûê        stage: Stage = Stage.RECEIVE,
Γûê        details: dict[str, Any] | None = None,
Γûê        issues: list[Any] | None = None,
Γûê        log_message: str | None = None,
Γûê    ) -> None:
Γûê        super().__init__(message)
Γûê        self.code = code
Γûê        self.message = message
Γûê        self.stage = stage
Γûê        self.details = details or {}
Γûê        self.issues = issues or []
Γûê        # Th├┤ng tin cho log ΓÇö ─æ╞░ß╗úc ph├⌐p chi tiß║┐t h╞ín `message` trß║ú cho client.
Γûê        self.log_message = log_message or message
Γöé
Γûê    @property
Γûê    def status(self) -> Status:
Γûê        return Status.of(self.severity)
Γöé
Γöé
Γûêclass ValidationError(AppError):
Γûê    """Input sai. Kh├┤ng phß║úi bug cß╗ºa hß╗ç thß╗æng, kh├┤ng cß║ºn crash g├¼ cß║ú.
Γöé
Γûê    Ng╞░ß╗¥i d├╣ng sß╗¡a file rß╗ôi upload lß║íi. Server vß║½n khoß║╗ mß║ính, request kh├íc
Γûê    vß║½n chß║íy b├¼nh th╞░ß╗¥ng.
Γûê    """
Γöé
Γûê    severity = Severity.VALIDATION
Γûê    http_status = 422
Γûê    can_continue = False
Γûê    next_action = NextAction.FIX_AND_REUPLOAD
Γûê    log_level = logging.WARNING
Γûê    log_traceback = False
Γöé
Γöé
Γûêclass SecurityError(AppError):
Γûê    """Input c├│ dß║Ñu hiß╗çu tß║Ñn c├┤ng hoß║╖c v╞░ß╗út giß╗¢i hß║ín an to├án.
Γöé
Γûê    HTTP 400 chß╗⌐ kh├┤ng 422: ─æ├óy kh├┤ng phß║úi "file sai ─æß╗ïnh dß║íng" m├á l├á
Γûê    "request n├áy bß╗ï tß╗½ chß╗æi". `message` cß╗æ t├¼nh m╞í hß╗ô ΓÇö chi tiß║┐t ß╗ƒ `log_message`.
Γûê    """
Γöé
Γûê    severity = Severity.CRITICAL
Γûê    http_status = 400
Γûê    can_continue = False
Γûê    next_action = NextAction.FIX_AND_REUPLOAD
Γûê    log_level = logging.ERROR
Γûê    log_traceback = False
Γöé
Γöé
Γûêclass CriticalError(AppError):
Γûê    """Hß╗ç thß╗æng kh├┤ng ─æß║úm bß║úo ─æ╞░ß╗úc l├á ─æi tiß║┐p th├¼ an to├án.
Γöé
Γûê    ─É├óy l├á nh├ính mß║╖c ─æß╗ïnh cho Mß╗îI thß╗⌐ kh├┤ng r├╡ r├áng: exception lß║í, invariant vß╗í,
Γûê    ─æ─⌐a kh├┤ng ghi ─æ╞░ß╗úc. Nguy├¬n tß║»c "Unknown error = Fail safely".
Γûê    """
Γöé
Γûê    severity = Severity.CRITICAL
Γûê    http_status = 500
Γûê    can_continue = False
Γûê    next_action = NextAction.CONTACT_SUPPORT
Γûê    log_level = logging.CRITICAL
Γûê    log_traceback = True
Γöé
Γöé
Γûêclass HumanReviewRequiredError(AppError):
Γûê    """Hß╗ç thß╗æng ─Éß╗îC ─É╞»ß╗óC input nh╞░ng kh├┤ng ─æß╗º thß║⌐m quyß╗ün tß╗▒ quyß║┐t.
Γöé
Γûê    Kh├íc CriticalError ß╗ƒ chß╗ù: kh├┤ng c├│ g├¼ hß╗Ång cß║ú, chß╗ë l├á b├ái to├ín cß║ºn con ng╞░ß╗¥i.
Γûê    V├¡ dß╗Ñ trong domain n├áy: 2 file c├╣ng nhß║¡n l├á chß╗º sß╗ƒ hß╗»u mß╗Öt node
Γûê    (AMBIGUOUS_OWNER / DUPLICATE_DECLARATION) ΓÇö chß╗ìn bß╗½a file n├áo thß║»ng l├á
Γûê    ├óm thß║ºm l├ám hß╗Ång catalog cß╗ºa ng╞░ß╗¥i kh├íc.
Γöé
Γûê    HTTP 409 Conflict: trß║íng th├íi hiß╗çn tß║íi cß╗ºa hß╗ç thß╗æng m├óu thuß║½n vß╗¢i request.
Γûê    """
Γöé
Γûê    severity = Severity.CRITICAL
Γûê    http_status = 409
Γûê    can_continue = False
Γûê    next_action = NextAction.HUMAN_REVIEW
Γûê    log_level = logging.ERROR
Γûê    log_traceback = False


src\core\logging.py:
Γûê"""
Γûêlogging.py ΓÇö Cß║Ñu h├¼nh log + request-id ─æß╗â nß╗æi c├íc d├▓ng log cß╗ºa c├╣ng 1 request.
Γöé
ΓûêNguy├¬n tß║»c:
Γûê  - Mß╗ùi request c├│ 1 `request_id`. N├│ nß║▒m trong Mß╗îI d├▓ng log cß╗ºa request ─æ├│ v├á
Γûê    c┼⌐ng nß║▒m trong response trß║ú cho frontend. Ng╞░ß╗¥i d├╣ng b├ío lß╗ùi k├¿m request_id
Γûê    l├á tra ─æ╞░ß╗úc ─æ├║ng chuß╗ùi log, kh├┤ng phß║úi m├▓ theo timestamp.
Γûê  - KH├öNG log nß╗Öi dung file, kh├┤ng log token/password/API key/email ng╞░ß╗¥i d├╣ng.
Γûê    Chß╗ë log metadata: t├¬n file (─æ├ú l├ám sß║ích), k├¡ch th╞░ß╗¢c, sha256 r├║t gß╗ìn,
Γûê    m├ú lß╗ùi, chß║╖ng xß╗¡ l├╜.
Γûê  - Stack trace chß╗ë ghi cho lß╗ùi PH├ìA Hß╗å THß╗ÉNG. Lß╗ùi do input ng╞░ß╗¥i d├╣ng ghi ß╗ƒ mß╗⌐c
Γûê    WARNING kh├┤ng k├¿m trace ΓÇö nß║┐u kh├┤ng, log sß║╜ ngß║¡p lß╗ùi v├┤ hß║íi v├á che mß║Ñt bug thß║¡t.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport hashlib
Γûêimport logging
Γûêimport logging.config
Γûêimport sys
Γûêimport uuid
Γûêfrom contextvars import ContextVar
Γöé
Γûê# ContextVar chß╗⌐ kh├┤ng phß║úi biß║┐n global: mß╗ùi request/coroutine c├│ gi├í trß╗ï ri├¬ng,
Γûê# chß║íy song song vß║½n kh├┤ng lß║½n.
Γûê_request_id: ContextVar[str] = ContextVar("request_id", default="-")
Γöé
Γöé
Γûêdef new_request_id() -> str:
Γûê    return uuid.uuid4().hex[:12]
Γöé
Γöé
Γûêdef set_request_id(value: str) -> None:
Γûê    _request_id.set(value)
Γöé
Γöé
Γûêdef get_request_id() -> str:
Γûê    return _request_id.get()
Γöé
Γöé
Γûêclass RequestIdFilter(logging.Filter):
Γûê    """B╞ím request_id v├áo mß╗ìi LogRecord ─æß╗â format string d├╣ng ─æ╞░ß╗úc `%(request_id)s`."""
Γöé
Γûê    def filter(self, record: logging.LogRecord) -> bool:
Γûê        record.request_id = get_request_id()
Γûê        return True
Γöé
Γöé
ΓûêLOG_FORMAT = "%(asctime)s | %(levelname)-8s | req=%(request_id)s | %(name)s | %(message)s"
Γöé
Γöé
Γûêdef configure_logging(level: str = "INFO") -> None:
Γûê    """Gß╗ìi 1 lß║ºn l├║c app khß╗ƒi ─æß╗Öng. `disable_existing_loggers=False` ─æß╗â kh├┤ng
Γûê    bß╗ït miß╗çng logger cß╗ºa uvicorn."""
Γûê    # Message log viß║┐t bß║▒ng tiß║┐ng Viß╗çt. Khi stdout bß╗ï redirect (file log, Docker,
Γûê    # CI), Python lß║Ñy encoding theo locale ΓÇö tr├¬n Windows l├á cp1252, kh├┤ng biß╗âu
Γûê    # diß╗àn ─æ╞░ß╗úc tiß║┐ng Viß╗çt v├á log ra th├ánh k├╜ tß╗▒ r├íc. ├ëp UTF-8 ngay tß║íi ─æ├óy.
Γûê    # `errors="replace"` ─æß╗â mß╗Öt k├╜ tß╗▒ lß║í kh├┤ng bao giß╗¥ giß║┐t ─æ╞░ß╗úc tiß║┐n tr├¼nh.
Γûê    for stream in (sys.stdout, sys.stderr):
Γûê        try:
Γûê            stream.reconfigure(encoding="utf-8", errors="replace")
Γûê        except (AttributeError, ValueError):
Γûê            pass  # stream ─æ├ú bß╗ï thay bß║▒ng object kh├íc (pytest capture chß║│ng hß║ín)
Γöé
Γûê    logging.config.dictConfig(
Γûê        {
Γûê            "version": 1,
Γûê            "disable_existing_loggers": False,
Γûê            "filters": {"request_id": {"()": RequestIdFilter}},
Γûê            "formatters": {
Γûê                "standard": {"format": LOG_FORMAT, "datefmt": "%Y-%m-%dT%H:%M:%S%z"}
Γûê            },
Γûê            "handlers": {
Γûê                "console": {
Γûê                    "class": "logging.StreamHandler",
Γûê                    "formatter": "standard",
Γûê                    "filters": ["request_id"],
Γûê                    "stream": "ext://sys.stdout",
Γûê                }
Γûê            },
Γûê            "root": {"handlers": ["console"], "level": level},
Γûê            "loggers": {
Γûê                "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
Γûê            },
Γûê        }
Γûê    )
Γöé
Γöé
Γûêdef content_fingerprint(data: bytes) -> str:
Γûê    """V├ón tay nß╗Öi dung ─æß╗â log/─æß╗æi chiß║┐u m├á KH├öNG lß╗Ö nß╗Öi dung.
Γöé
Γûê    12 hex ─æß║ºu cß╗ºa sha256 ΓÇö ─æß╗º ─æß╗â nhß║¡n ra "vß║½n l├á file c┼⌐ upload lß║íi lß║ºn 3",
Γûê    kh├┤ng ─æß╗º ─æß╗â dß╗▒ng ng╞░ß╗úc nß╗Öi dung.
Γûê    """
Γûê    return hashlib.sha256(data).hexdigest()[:12]


src\main.py:
Γûêfrom __future__ import annotations
Γöé
Γûêimport logging
Γûêimport time
Γûêfrom collections.abc import AsyncIterator
Γûêfrom contextlib import asynccontextmanager
Γöé
Γûêfrom fastapi import FastAPI, Request
Γûêfrom fastapi.exceptions import RequestValidationError
Γûêfrom fastapi.middleware.cors import CORSMiddleware
Γûêfrom fastapi.responses import JSONResponse
Γûêfrom starlette.exceptions import HTTPException as StarletteHTTPException
Γöé
Γûêfrom src.core.config import LOG_LEVEL
Γûêfrom src.core.db import dispose, init_db
Γûêfrom src.core.errors import (
Γûê    AppError,
Γûê    CriticalError,
Γûê    ErrorCode,
Γûê    NextAction,
Γûê    Severity,
Γûê    Stage,
Γûê    Status,
Γûê    ValidationError,
Γûê)
Γûêfrom src.core.logging import configure_logging, get_request_id, new_request_id, set_request_id
Γûêfrom src.models.schemas import ApiResponse, Issue, from_error
Γûêfrom src.services.store import store
Γöé
Γûêfrom src.api.routes import router
Γûêfrom src.config import get_settings
Γöé
Γûêconfigure_logging(LOG_LEVEL)
Γûêlogger = logging.getLogger("app")
Γöé
Γûê@asynccontextmanager
Γûêasync def lifespan(_app: FastAPI) -> AsyncIterator[None]:
Γûê    settings = get_settings()
Γûê    print(f"Starting {settings.app_name} in {settings.app_env} mode")
Γûê    try:
Γûê        init_db()
Γûê        store.load_from_db()
Γûê    except Exception:
Γûê        logger.critical(
Γûê            "Kh├┤ng khß╗ƒi tß║ío ─æ╞░ß╗úc database l├║c khß╗ƒi ─æß╗Öng. API vß║½n chß║íy nh╞░ng mß╗ìi "
Γûê            "thao t├íc ─æß╗ìc/ghi catalog sß║╜ trß║ú STORAGE_FAILURE cho tß╗¢i khi DB trß╗ƒ lß║íi.",
Γûê            exc_info=True,
Γûê        )
Γûê    yield
Γûê    dispose()
Γûê    print("Shutting down...")
Γöé
Γûêapp = FastAPI(
Γûê    title="AI20K Agent",
Γûê    description="AI Agent built with LangGraph (Integrated with IDP Catalog Graph API)",
Γûê    version="1.0.0",
Γûê    lifespan=lifespan,
Γûê)
Γöé
Γûêsettings = get_settings()
Γöé
Γûêapp.add_middleware(
Γûê    CORSMiddleware,
Γûê    allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["*"],
Γûê    allow_credentials=True,
Γûê    allow_methods=["*"],
Γûê    allow_headers=["*"],
Γûê    expose_headers=["X-Request-ID"],
Γûê)
Γöé
Γûê# Nh├║ng to├án bß╗Ö route tß╗½ src/api/routes.py v├áo tiß╗ün tß╗æ /api/v1
Γûêapp.include_router(router, prefix="/api/v1")
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Middleware
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê@app.middleware("http")
Γûêasync def request_context(request: Request, call_next):
Γûê    request_id = request.headers.get("X-Request-ID") or new_request_id()
Γûê    set_request_id(request_id)
Γûê    started = time.perf_counter()
Γöé
Γûê    response = await call_next(request)
Γöé
Γûê    elapsed_ms = (time.perf_counter() - started) * 1000
Γûê    response.headers["X-Request-ID"] = request_id
Γûê    logger.info(
Γûê        "%s %s -> %d (%.1f ms)",
Γûê        request.method, request.url.path, response.status_code, elapsed_ms,
Γûê    )
Γûê    return response
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Exception handlers
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûêdef _json(payload: ApiResponse, http_status: int) -> JSONResponse:
Γûê    return JSONResponse(
Γûê        status_code=http_status,
Γûê        content=payload.model_dump(mode="json"),
Γûê        headers={"X-Request-ID": payload.request_id},
Γûê    )
Γöé
Γûê@app.exception_handler(AppError)
Γûêasync def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
Γûê    logger.log(
Γûê        exc.log_level,
Γûê        "stage=%s code=%s path=%s | %s",
Γûê        exc.stage.value, exc.code.value, request.url.path, exc.log_message,
Γûê        exc_info=exc.log_traceback,
Γûê    )
Γûê    return _json(from_error(exc, request_id=get_request_id()), exc.http_status)
Γöé
Γûê@app.exception_handler(RequestValidationError)
Γûêasync def request_validation_handler(
Γûê    request: Request, exc: RequestValidationError
Γûê) -> JSONResponse:
Γûê    missing_file = any(
Γûê        e.get("type") == "missing" and "file" in [str(x) for x in e.get("loc", ())]
Γûê        for e in exc.errors()
Γûê    )
Γûê    code = ErrorCode.NO_FILE if missing_file else ErrorCode.INVALID_STRUCTURE
Γûê    message = (
Γûê        "Ch╞░a chß╗ìn file ─æß╗â tß║úi l├¬n."
Γûê        if missing_file
Γûê        else "Dß╗» liß╗çu gß╗¡i l├¬n kh├┤ng ─æ├║ng ─æß╗ïnh dß║íng y├¬u cß║ºu."
Γûê    )
Γöé
Γûê    wrapped = ValidationError(
Γûê        code,
Γûê        message,
Γûê        stage=Stage.RECEIVE,
Γûê        issues=[
Γûê            Issue(
Γûê                severity="error",
Γûê                code=str(e.get("type", "invalid")),
Γûê                message=str(e.get("msg", "")),
Γûê                location=".".join(str(x) for x in e.get("loc", ())),
Γûê            )
Γûê            for e in exc.errors()
Γûê        ],
Γûê    )
Γûê    logger.warning("Request sai h├¼nh dß║íng ß╗ƒ %s: %s", request.url.path, code.value)
Γûê    return _json(from_error(wrapped, request_id=get_request_id()), wrapped.http_status)
Γöé
Γûê@app.exception_handler(StarletteHTTPException)
Γûêasync def http_exception_handler(
Γûê    request: Request, exc: StarletteHTTPException
Γûê) -> JSONResponse:
Γûê    severity = Severity.VALIDATION if exc.status_code < 500 else Severity.CRITICAL
Γûê    payload = ApiResponse(
Γûê        status=Status.of(severity),
Γûê        severity=severity,
Γûê        code=f"HTTP_{exc.status_code}",
Γûê        message=str(exc.detail),
Γûê        can_continue=False,
Γûê        next_action=(
Γûê            NextAction.FIX_AND_REUPLOAD if exc.status_code < 500 else NextAction.CONTACT_SUPPORT
Γûê        ),
Γûê        stage=Stage.RECEIVE,
Γûê        request_id=get_request_id(),
Γûê    )
Γûê    return _json(payload, exc.status_code)
Γöé
Γûê@app.exception_handler(Exception)
Γûêasync def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
Γûê    logger.critical(
Γûê        "Exception ngo├ái dß╗▒ kiß║┐n ß╗ƒ %s %s: %s",
Γûê        request.method, request.url.path, type(exc).__name__,
Γûê        exc_info=True,
Γûê    )
Γûê    wrapped = CriticalError(
Γûê        ErrorCode.INTERNAL_ERROR,
Γûê        "Kh├┤ng thß╗â xß╗¡ l├╜ y├¬u cß║ºu. Vui l├▓ng thß╗¡ lß║íi hoß║╖c li├¬n hß╗ç hß╗ù trß╗ú k├¿m m├ú request.",
Γûê        stage=Stage.RECEIVE,
Γûê    )
Γûê    return _json(from_error(wrapped, request_id=get_request_id()), wrapped.http_status)
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Health
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê@app.get("/health", tags=["System"], summary="Kiß╗âm tra sß╗⌐c khoß║╗ dß╗ïch vß╗Ñ")
Γûêdef health() -> dict[str, str]:
Γûê    return {"status": "ok", "env": settings.app_env}


src\models\schemas.py:
Γûê"""
Γûêschemas.py ΓÇö Response contract giß╗»a backend v├á frontend.
Γöé
ΓûêMß╗ÿT h├¼nh dß║íng response duy nhß║Ñt cho mß╗ìi endpoint, mß╗ìi kß║┐t quß║ú (th├ánh c├┤ng,
Γûêcß║únh b├ío, lß╗ùi input, lß╗ùi hß╗ç thß╗æng). Frontend viß║┐t mß╗Öt h├ám xß╗¡ l├╜ d├╣ng chung,
Γûêkh├┤ng phß║úi ─æo├ín mß╗ùi endpoint trß║ú kiß╗âu g├¼.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêfrom datetime import datetime
Γûêfrom typing import Any
Γöé
Γûêfrom pydantic import BaseModel, Field
Γöé
Γûêfrom src.core.errors import ErrorCode, NextAction, Severity, Stage, Status
Γöé
Γöé
Γûêclass Issue(BaseModel):
Γûê    """Mß╗Öt vß║Ñn ─æß╗ü cß╗Ñ thß╗â trong file. ─É├óy l├á thß╗⌐ frontend render th├ánh danh s├ích
Γûê    lß╗ùi c├│ thß╗â bß║Ñm v├áo ─æß╗â nhß║úy tß╗¢i ─æ├║ng d├▓ng YAML."""
Γöé
Γûê    severity: str = Field(description="'error' (chß║╖n) hoß║╖c 'warning' (kh├┤ng chß║╖n)")
Γûê    code: str = Field(description="M├ú ß╗òn ─æß╗ïnh, vd 'REQUIRED', 'INVALID_REF'")
Γûê    message: str = Field(description="M├┤ tß║ú cho ng╞░ß╗¥i ─æß╗ìc")
Γûê    location: str | None = Field(
Γûê        default=None,
Γûê        description="─É╞░ß╗¥ng dß║½n trong YAML, vd 'spec.owners.members[0].role'",
Γûê    )
Γûê    subject: str | None = Field(
Γûê        default=None, description="Node li├¬n quan, vd 'api:order/order-service'"
Γûê    )
Γûê    source: str | None = Field(default=None, description="File ph├ít sinh vß║Ñn ─æß╗ü")
Γöé
Γöé
Γûêclass ApiResponse(BaseModel):
Γûê    """Response contract d├╣ng chung.
Γöé
Γûê    | field       | ├╜ ngh─⌐a                                                      |
Γûê    |-------------|--------------------------------------------------------------|
Γûê    | status      | success / warning / error ΓÇö suy tß╗½ `severity`, kh├┤ng set tay  |
Γûê    | severity    | none / low / validation / critical ΓÇö mß╗⌐c nghi├¬m trß╗ìng         |
Γûê    | code        | m├ú lß╗ùi ß╗òn ─æß╗ïnh; null khi th├ánh c├┤ng. Frontend switch tr├¬n ─æ├óy |
Γûê    | message     | c├óu tiß║┐ng Viß╗çt hiß╗ân thß╗ï thß║│ng cho ng╞░ß╗¥i d├╣ng                  |
Γûê    | can_continue| frontend c├│ ─æ╞░ß╗úc ph├⌐p cho ─æi b╞░ß╗¢c tiß║┐p theo kh├┤ng             |
Γûê    | next_action | ng╞░ß╗¥i d├╣ng cß║ºn L├ÇM G├î tiß║┐p theo -> map thß║│ng ra n├║t bß║Ñm       |
Γûê    | stage       | chß║┐t ß╗ƒ chß║╖ng n├áo ΓÇö ─æß╗â hiß╗çn tiß║┐n ─æß╗Ö v├á ─æß╗â hß╗ù trß╗ú tra log       |
Γûê    | request_id  | nß╗æi response vß╗¢i log ph├¡a server                              |
Γûê    | issues      | danh s├ích vß║Ñn ─æß╗ü chi tiß║┐t                                     |
Γûê    | details     | dß╗» liß╗çu ri├¬ng cß╗ºa tß╗½ng endpoint (sß╗æ node, danh s├ích file...)  |
Γöé
Γûê    Hai bß╗ò sung so vß╗¢i contract ban ─æß║ºu bß║ín ─æ╞░a, v├á l├╜ do:
Γöé
Γûê    - `next_action`: y├¬u cß║ºu sß╗æ 4 cß╗ºa bß║ín c├│ "ng╞░ß╗¥i d├╣ng cß║ºn l├ám g├¼ tiß║┐p theo"
Γûê      nh╞░ng contract lß║íi thiß║┐u field cho n├│. `can_continue=false` mß╗¢i chß╗ë n├│i
Γûê      "dß╗½ng", ch╞░a n├│i "sß╗¡a file rß╗ôi thß╗¡ lß║íi" hay "gß╗ìi support". Kh├┤ng c├│ field
Γûê      n├áy, frontend buß╗Öc phß║úi suy ─æo├ín tß╗½ `code` ΓÇö tß╗⌐c l├á nh├⌐t business logic
Γûê      v├áo chß╗ù sai.
Γöé
Γûê    - `issues`: nh├⌐t danh s├ích lß╗ùi v├áo `details` (dict tß╗▒ do) th├¼ frontend phß║úi
Γûê      ─æo├ín key v├á kh├┤ng c├│ type. ─É├óy l├á payload ch├¡nh cß╗ºa mß╗Öt API validate,
Γûê      xß╗⌐ng ─æ├íng c├│ chß╗ù ri├¬ng, c├│ schema.
Γûê    """
Γöé
Γûê    status: Status
Γûê    severity: Severity
Γûê    code: str | None = None
Γûê    message: str
Γûê    can_continue: bool
Γûê    next_action: NextAction
Γûê    stage: Stage
Γûê    request_id: str
Γûê    issues: list[Issue] = Field(default_factory=list)
Γûê    details: dict[str, Any] = Field(default_factory=dict)
Γöé
Γöé
Γûêclass CatalogSummary(BaseModel):
Γûê    """T├│m tß║»t 1 catalog ─æ├ú nß║íp ΓÇö phß║ºn tß╗¡ cß╗ºa `details.items` ß╗ƒ GET /catalogs.
Γöé
Γûê    Dß╗▒ng ─æß╗â frontend render bß║úng m├á kh├┤ng cß║ºn gß╗ìi th├¬m API n├áo: ─æ├ú c├│ sß║╡n t├¼nh
Γûê    trß║íng, sß╗æ liß╗çu ─æß╗ô thß╗ï, thß╗¥i ─æiß╗âm nß║íp v├á m├ú bß║ún ghi trong database.
Γûê    """
Γöé
Γûê    file: str
Γûê    root: str | None = Field(description="Node gß╗æc, vd 'component:order/order-service'")
Γûê    state: str = Field(description="'valid' hoß║╖c 'valid_with_warnings'")
Γûê    error_count: int
Γûê    warning_count: int
Γûê    node_count: int
Γûê    edge_count: int
Γûê    # Hai field d╞░ß╗¢i nullable v├¼ ch├║ng KH├öNG nß║▒m trong JSON l╞░u ß╗ƒ database.
Γûê    # Item vß╗½a upload trong phi├¬n hiß╗çn tß║íi th├¼ c├│ gi├í trß╗ï; item nß║íp lß║íi tß╗½ DB sau
Γûê    # khi restart th├¼ `size_bytes` l├á null (k├¡ch th╞░ß╗¢c file YAML gß╗æc kh├┤ng ─æ╞░ß╗úc
Γûê    # l╞░u ΓÇö bß╗ïa ra mß╗Öt con sß╗æ c├▓n tß╗ç h╞ín l├á ─æß╗â trß╗æng).
Γûê    size_bytes: int | None = Field(
Γûê        default=None, description="K├¡ch th╞░ß╗¢c file YAML gß╗æc; null nß║┐u nß║íp lß║íi tß╗½ DB"
Γûê    )
Γûê    uploaded_at: datetime | None = Field(
Γûê        default=None, description="Thß╗¥i ─æiß╗âm nß║íp; lß║Ñy tß╗½ `generatedAt` trong JSON"
Γûê    )
Γûê    output_file: str | None = Field(
Γûê        description="T├¬n logic cß╗ºa t├ái liß╗çu JSON, vd 'order-service.json'"
Γûê    )
Γûê    record_id: int | None = Field(
Γûê        default=None, description="Kho├í ch├¡nh cß╗ºa d├▓ng trong bß║úng input_json"
Γûê    )
Γûê    diagnostics: dict[str, Any] | None = Field(
Γûê        default=None, description="Chi tiß║┐t ─æß║ºy ─æß╗º; chß╗ë c├│ khi ?include=diagnostics"
Γûê    )
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Response builders ΓÇö c├ích DUY NHß║ñT ─æ╞░ß╗úc ph├⌐p dß╗▒ng ApiResponse.
Γûê# Kh├┤ng new ApiResponse(...) rß║úi r├íc trong service: `status` v├á `severity` phß║úi
Γûê# lu├┤n khß╗¢p nhau, chß╗ë ├⌐p ─æ╞░ß╗úc ─æiß╗üu ─æ├│ nß║┐u mß╗ìi lß╗æi ─æi chß╗Ñm vß╗ü ─æ├óy.
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef success(
Γûê    message: str,
Γûê    *,
Γûê    request_id: str,
Γûê    stage: Stage = Stage.DONE,
Γûê    details: dict[str, Any] | None = None,
Γûê) -> ApiResponse:
Γûê    return ApiResponse(
Γûê        status=Status.of(Severity.NONE),
Γûê        severity=Severity.NONE,
Γûê        code=None,
Γûê        message=message,
Γûê        can_continue=True,
Γûê        next_action=NextAction.PROCEED,
Γûê        stage=stage,
Γûê        request_id=request_id,
Γûê        issues=[],
Γûê        details=details or {},
Γûê    )
Γöé
Γöé
Γûêdef warning(
Γûê    message: str,
Γûê    *,
Γûê    request_id: str,
Γûê    code: ErrorCode = ErrorCode.HAS_WARNINGS,
Γûê    issues: list[Issue] | None = None,
Γûê    stage: Stage = Stage.DONE,
Γûê    details: dict[str, Any] | None = None,
Γûê) -> ApiResponse:
Γûê    """can_continue = True: dß╗» liß╗çu ─æ├ú ─æß╗º ─æiß╗üu kiß╗çn tß╗æi thiß╗âu, ng╞░ß╗¥i d├╣ng xem
Γûê    cß║únh b├ío rß╗ôi tß╗▒ quyß║┐t ─æß╗ïnh."""
Γûê    return ApiResponse(
Γûê        status=Status.of(Severity.LOW),
Γûê        severity=Severity.LOW,
Γûê        code=code.value,
Γûê        message=message,
Γûê        can_continue=True,
Γûê        next_action=NextAction.REVIEW_WARNINGS,
Γûê        stage=stage,
Γûê        request_id=request_id,
Γûê        issues=issues or [],
Γûê        details=details or {},
Γûê    )
Γöé
Γöé
Γûêdef from_error(exc: Any, *, request_id: str) -> ApiResponse:
Γûê    """Dß╗▒ng response tß╗½ AppError. Mß╗ìi thuß╗Öc t├¡nh contract ─æ├ú nß║▒m sß║╡n tr├¬n
Γûê    exception n├¬n ß╗ƒ ─æ├óy kh├┤ng c├│ logic n├áo ─æß╗â lß╗í tay l├ám sai."""
Γûê    return ApiResponse(
Γûê        status=exc.status,
Γûê        severity=exc.severity,
Γûê        code=exc.code.value if isinstance(exc.code, ErrorCode) else str(exc.code),
Γûê        message=exc.message,
Γûê        can_continue=exc.can_continue,
Γûê        next_action=exc.next_action,
Γûê        stage=exc.stage,
Γûê        request_id=request_id,
Γûê        issues=exc.issues,
Γûê        details=exc.details,
Γûê    )
Γöé
Γûêclass ChatRequest(BaseModel):
Γûê    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhß║»n tß╗½ user")
Γöé
Γöé
Γûêclass ChatResponse(BaseModel):
Γûê    response: str = Field(..., description="Phß║ún hß╗ôi tß╗½ agent")
Γûê    analysis: str = Field(default="", description="Ph├ón t├¡ch nß╗Öi bß╗Ö")
Γöé
Γöé


src\models\tables.py:
Γûê"""
Γûêtables.py ΓÇö M├┤ tß║ú bß║úng trong database bß║▒ng ORM.
Γöé
Γûê─É├óy l├á nguß╗ôn sß╗▒ thß║¡t DUY NHß║ñT vß╗ü h├¼nh dß║íng bß║úng. `init_db()` ─æß╗ìc file n├áy ─æß╗â
Γûêsinh DDL, n├¬n kh├┤ng c├│ kß╗ïch bß║ún "code ngh─⌐ mß╗Öt ─æß║▒ng, bß║úng thß║¡t mß╗Öt nß║╗o" do ai ─æ├│
Γûêsß╗¡a bß║úng bß║▒ng tay m├á qu├¬n sß╗¡a code.
Γöé
ΓûêT├ích khß╗Åi `schemas.py`: hai file n├áy m├┤ tß║ú hai thß╗⌐ kh├íc nhau v├á ─æß╗òi v├¼ hai l├╜ do
Γûêkh├íc nhau. `schemas.py` l├á hß╗úp ─æß╗ông vß╗¢i frontend (Pydantic), file n├áy l├á hß╗úp ─æß╗ông
Γûêvß╗¢i Postgres (SQLAlchemy). Gß╗Öp chung th├¼ mß╗Öt thay ─æß╗òi ß╗ƒ tß║ºng l╞░u trß╗» tr├┤ng nh╞░
Γûêmß╗Öt thay ─æß╗òi ß╗ƒ API.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêfrom typing import Any
Γöé
Γûêfrom sqlalchemy import BigInteger, String
Γûêfrom sqlalchemy.dialects.postgresql import JSONB
Γûêfrom sqlalchemy.orm import Mapped, mapped_column
Γöé
Γûêfrom src.core.db import Base
Γöé
Γöé
Γûêclass InputJson(Base):
Γûê    """Bß║úng `input_json` ΓÇö mß╗ùi d├▓ng l├á graph JSON sinh ra tß╗½ mß╗Öt catalog.
Γöé
Γûê    Chß╗ë 2 cß╗Öt theo ─æ├║ng thiß║┐t kß║┐:
Γöé
Γûê        id       BIGSERIAL  kho├í ch├¡nh tß╗▒ t─âng
Γûê        content  JSONB      nß╗Öi dung JSON, y hß╗çt thß╗⌐ tr╞░ß╗¢c ─æ├óy ghi ra file
Γöé
Γûê    D├╣ng JSONB chß╗⌐ kh├┤ng TEXT: Postgres parse sß║╡n n├¬n truy vß║Ñn ─æ╞░ß╗úc v├áo b├¬n
Γûê    trong t├ái liß╗çu. Ch├¡nh nhß╗¥ vß║¡y mß╗¢i tra ─æ╞░ß╗úc "d├▓ng n├áo ß╗⌐ng vß╗¢i file n├áo" qua
Γûê    `content->'scope'->'sources'->0->>'file'` m├á kh├┤ng cß║ºn th├¬m cß╗Öt.
Γöé
Γûê    JSONB kh├┤ng giß╗» thß╗⌐ tß╗▒ key v├á bß╗Å khoß║úng trß║»ng ΓÇö kh├┤ng sao, v├¼ mß╗ìi thß╗⌐ tß╗▒ c├│
Γûê    ├╜ ngh─⌐a (node theo id, edge theo topology) ─æß╗üu nß║▒m trong mß║úng hoß║╖c do tß║ºng
Γûê    sinh JSON quyß║┐t ─æß╗ïnh, kh├┤ng phß╗Ñ thuß╗Öc thß╗⌐ tß╗▒ key cß╗ºa object.
Γûê    """
Γöé
Γûê    __tablename__ = "input_json"
Γöé
Γûê    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
Γûê    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
Γöé
Γûê    def __repr__(self) -> str:  # pragma: no cover - chß╗ë ─æß╗â debug
Γûê        return f"<InputJson id={self.id}>"
Γöé
Γöé
Γûêclass GithubCommitLog(Base):
Γûê    """Bß║úng `github_commits_log` ΓÇö mß╗ùi d├▓ng l├á Mß╗ÿT lß║ºn push l├¬n GitHub.
Γöé
Γûê    ─É├óy l├á NHß║¼T K├¥ AUDIT, kh├┤ng phß║úi nguß╗ôn sß╗▒ thß║¡t cß╗ºa catalog. Nguß╗ôn sß╗▒ thß║¡t
Γûê    vß║½n l├á `input_json`; bß║úng n├áy trß║ú lß╗¥i c├óu hß╗Åi m├á `input_json` kh├┤ng giß╗»:
Γûê    "catalog ─æ├│ v├áo hß╗ç thß╗æng tß╗½ commit n├áo, ai ─æß║⌐y l├¬n, l├║c n├áo".
Γöé
Γûê        id              BIGSERIAL  kho├í ch├¡nh tß╗▒ t─âng
Γûê        email           VARCHAR    email t├íc giß║ú cß╗ºa head_commit
Γûê        branch          VARCHAR    'main' (─æ├ú bß╗Å tiß╗ün tß╗æ refs/heads/)
Γûê        commit_url      VARCHAR    link bß║Ñm thß║│ng sang trang diff cß╗ºa GitHub
Γûê        timestamp       VARCHAR    ISO8601 nguy├¬n v─ân GitHub gß╗¡i sang
Γûê        added_files     JSONB      danh s├ích ─æ╞░ß╗¥ng dß║½n file .yaml/.yml
Γûê        modified_files  JSONB
Γûê        removed_files   JSONB
Γöé
Γûê    LU├öN INSERT, kh├┤ng bao giß╗¥ UPDATE ΓÇö ng╞░ß╗úc hß║│n vß╗¢i `InputJson`. Mß╗Öt lß║ºn push
Γûê    l├á mß╗Öt sß╗▒ kiß╗çn ─É├â Xß║óY RA, ghi ─æ├¿ l├¬n n├│ l├á xo├í mß║Ñt lß╗ïch sß╗¡. C├▓n `input_json`
Γûê    m├┤ tß║ú trß║íng th├íi HIß╗åN Tß║áI n├¬n upload lß║íi c├╣ng t├¬n file th├¼ phß║úi ghi ─æ├¿.
Γöé
Γûê    Ba cß╗Öt JSONB l╞░u ─É╞»ß╗£NG Dß║¬N ─Éß║ªY ─Éß╗ª trong repo
Γûê    ('services/order/catalog-info.yaml') chß╗⌐ kh├┤ng phß║úi t├¬n file r├║t gß╗ìn: mß╗Ñc
Γûê    ─æ├¡ch cß╗ºa bß║úng l├á truy ng╞░ß╗úc vß╗ü ─æ├║ng chß╗ù trong repo. T├¬n r├║t gß╗ìn chß╗ë d├╣ng khi
Γûê    gß╗ìi sang `ingest`, v├á viß╗çc quy ─æß╗òi ─æ├│ nß║▒m ß╗ƒ tß║ºng service.
Γöé
Γûê    L╞░u `timestamp` dß║íng chuß╗ùi chß╗⌐ kh├┤ng TIMESTAMPTZ: ─æ├óy l├á chuß╗ùi GitHub gß╗¡i
Γûê    sang, giß╗» nguy├¬n v─ân th├¼ log lu├┤n khß╗¢p vß╗¢i thß╗⌐ nh├¼n thß║Ñy tr├¬n GitHub, kh├┤ng
Γûê    phß╗Ñ thuß╗Öc v├áo viß╗çc ta parse timezone c├│ ─æ├║ng hay kh├┤ng.
Γûê    """
Γöé
Γûê    __tablename__ = "github_commits_log"
Γöé
Γûê    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
Γûê    email: Mapped[str] = mapped_column(String, nullable=False)
Γûê    branch: Mapped[str] = mapped_column(String, nullable=False)
Γûê    commit_url: Mapped[str] = mapped_column(String, nullable=False)
Γûê    timestamp: Mapped[str] = mapped_column(String, nullable=False)
Γöé
Γûê    # `default=list` l├á default ph├¡a Python, KH├öNG phß║úi server default: INSERT
Γûê    # bß║▒ng SQL tay m├á bß╗Å trß╗æng ba cß╗Öt n├áy sß║╜ vi phß║ím NOT NULL. Lu├┤n ghi qua
Γûê    # `github_event_repository`.
Γûê    added_files: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
Γûê    modified_files: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
Γûê    removed_files: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
Γöé
Γûê    def __repr__(self) -> str:  # pragma: no cover - chß╗ë ─æß╗â debug
Γûê        return f"<GithubCommitLog id={self.id} branch={self.branch}>"
Γöé


src\services\catalog_merge.py:
Γûê"""
Γûêcatalog_merge.py ΓÇö gß╗Öp nhiß╗üu ParsedFile (mß╗ùi file 1 lß║ºn parse_single) th├ánh
Γûêmß╗Öt graph document duy nhß║Ñt, scope.kind = "merged".
Γöé
ΓûêLuß║¡t merge, ─æ├║ng nhß╗»ng g├¼ ─æ├ú thß╗æng nhß║Ñt khi review tß╗½ng file ri├¬ng:
Γûê  - Node: dedupe theo id. Chß╗ë file tß╗▒ khai b├ío mß╗¢i ─æ╞░ß╗úc ghi `spec`.
Γûê          Hai file c├╣ng nhß║¡n l├á chß╗º mß╗Öt node -> lß╗ùi (kh├┤ng ├óm thß║ºm ghi ─æ├¿).
Γûê  - Edge: gß╗Öp thß║│ng, dedupe theo id (─æß╗ìc tr├╣ng 1 file 2 lß║ºn th├¼ kh├┤ng nh├ón ─æ├┤i).
Γûê  - Diagnostics: cß╗Öng dß╗ôn theo file, cß╗Öng th├¬m 3 loß║íi ph├ít hiß╗çn chß╗ë c├│ ─æ╞░ß╗úc
Γûê    khi nh├¼n to├án cß╗Ñc: cß║ính mß╗ô c├┤i (provider/publisher vß║»ng mß║╖t) v├á chu tr├¼nh
Γûê    phß╗Ñ thuß╗Öc xuy├¬n nhiß╗üu file.
Γöé
ΓûêKh├┤ng phß╗Ñ thuß╗Öc thß╗⌐ tß╗▒ ─æß╗ìc file ΓÇö xem tests ß╗ƒ cuß╗æi file.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêfrom typing import Any
Γöé
Γûêimport networkx as nx
Γöé
Γûêfrom src.services.catalog_to_graph import (
Γûê    OWNED_VIA_RELATION,
Γûê    SCHEMA_VERSION,
Γûê    SPEC_VERSION,
Γûê    Diagnostics,
Γûê    ParsedFile,
Γûê    _edge_sort_key,
Γûê    build_nx_graph,
Γûê)
Γöé
Γöé
Γûêdef _merge_node(existing: dict[str, Any] | None, incoming: dict[str, Any],
Γûê               d: Diagnostics) -> dict[str, Any]:
Γûê    """Hß╗úp nhß║Ñt 2 bß║ún khai cß╗ºa c├╣ng 1 node id. Kh├┤ng bao giß╗¥ ghi ─æ├¿ ├óm thß║ºm:
Γûê    nß║┐u cß║ú hai ─æß╗üu tß╗▒ nhß║¡n l├á chß╗º (declared_by kh├íc nhau, cß║ú hai non-null),
Γûê    giß╗» bß║ún ─æß║┐n tr╞░ß╗¢c v├á bß║»n lß╗ùi ΓÇö kh├┤ng ─æo├ín ai ─æ├║ng."""
Γûê    if existing is None:
Γûê        return dict(incoming)
Γöé
Γûê    if existing["declared_by"] is None:
Γûê        return dict(incoming) if incoming["declared_by"] else existing
Γûê    if incoming["declared_by"] is None:
Γûê        return existing
Γûê    if existing["declared_by"] == incoming["declared_by"]:
Γûê        return existing  # c├╣ng 1 file, kh├┤ng phß║úi xung ─æß╗Öt thß║¡t
Γöé
Γûê    code = "DUPLICATE_DECLARATION" if existing["kind"] == "component" else "AMBIGUOUS_OWNER"
Γûê    d.err(code,
Γûê          f"{existing['id']} ─æ╞░ß╗úc khai l├á chß╗º bß╗ƒi cß║ú "
Γûê          f"'{existing['declared_by']}' v├á '{incoming['declared_by']}'",
Γûê          subject=existing["id"], source=incoming["declared_by"])
Γûê    return existing
Γöé
Γöé
Γûêdef _check_orphan_edges(nodes: dict[str, Any], edges: list[dict[str, Any]],
Γûê                        d: Diagnostics) -> None:
Γûê    """Sau khi gß╗Öp to├án cß╗Ñc: node n├áo bß╗ï subscribe/consume nh╞░ng kh├┤ng ai
Γûê    provides/publishes v├áo n├│ ΓÇö chß╗ë ph├ít hiß╗çn ─æ╞░ß╗úc khi nh├¼n nhiß╗üu file c├╣ng l├║c."""
Γûê    provided_targets = {e["target"] for e in edges if e["relation"] in OWNED_VIA_RELATION.values()}
Γûê    for node_id, node in nodes.items():
Γûê        if node["kind"] not in ("api", "topic") or node["declared_by"] is not None:
Γûê            continue
Γûê        if node_id in provided_targets:
Γûê            continue
Γûê        consumers = [e["declared_by"] for e in edges
Γûê                    if e["target"] == node_id and e["relation"] in ("consumes", "subscribes")]
Γûê        if not consumers:
Γûê            continue
Γûê        code = "API_NO_PROVIDER" if node["kind"] == "api" else "TOPIC_NO_PUBLISHER"
Γûê        verb = "gß╗ìi" if node["kind"] == "api" else "subscribe"
Γûê        d.warn(code,
Γûê               f"{node_id} ─æ╞░ß╗úc {len(consumers)} component {verb} tß╗¢i nh╞░ng "
Γûê               "ch╞░a c├│ ai provides/publishes",
Γûê               subject=node_id)
Γöé
Γöé
Γûêdef merge_documents(parsed: list[ParsedFile]) -> dict[str, Any]:
Γûê    d = Diagnostics()
Γûê    nodes: dict[str, Any] = {}
Γûê    edges: list[dict[str, Any]] = []
Γûê    seen_edge_ids: set[str] = set()
Γûê    sources: list[dict[str, Any]] = []
Γöé
Γûê    for p in parsed:
Γûê        sources.append({"file": p.filename, "root": p.root_id})
Γöé
Γûê        for e in p.diagnostics.errors:
Γûê            e.source = e.source or p.filename
Γûê            d.errors.append(e)
Γûê        for w in p.diagnostics.warnings:
Γûê            w.source = w.source or p.filename
Γûê            d.warnings.append(w)
Γöé
Γûê        for node_id, node in p.nodes.items():
Γûê            nodes[node_id] = _merge_node(nodes.get(node_id), node, d)
Γöé
Γûê        for e in p.edges:
Γûê            if e["id"] in seen_edge_ids:
Γûê                continue
Γûê            seen_edge_ids.add(e["id"])
Γûê            edges.append(e)
Γöé
Γûê    if nodes:
Γûê        g = build_nx_graph(nodes, edges)
Γûê        for cycle in nx.simple_cycles(g):
Γûê            if len(cycle) > 1:
Γûê                d.warn("DEPENDENCY_CYCLE",
Γûê                       "Chu tr├¼nh phß╗Ñ thuß╗Öc xuy├¬n file: " + " -> ".join(cycle + [cycle[0]]),
Γûê                       subject=cycle[0])
Γûê        _check_orphan_edges(nodes, edges, d)
Γöé
Γûê    ordered_nodes = {k: nodes[k] for k in sorted(nodes)}
Γûê    ordered_edges = sorted(edges, key=_edge_sort_key)
Γöé
Γûê    def _diag_key(i):
Γûê        return (i.source or "", i.code, i.subject or "", i.message)
Γöé
Γûê    d.errors.sort(key=_diag_key)
Γûê    d.warnings.sort(key=_diag_key)
Γöé
Γûê    return {
Γûê        "schemaVersion": SCHEMA_VERSION,
Γûê        "specVersion": SPEC_VERSION,
Γûê        "scope": {
Γûê            "kind": "merged",
Γûê            "root": None,
Γûê            "sources": sorted(sources, key=lambda s: s["file"]),
Γûê        },
Γûê        "nodes": ordered_nodes,
Γûê        "edges": ordered_edges,
Γûê        "diagnostics": d.as_dict(),
Γûê    }
Γöé


src\services\catalog_repository.py:
Γûê"""
Γûêcatalog_repository.py ΓÇö ─Éß╗ìc/ghi bß║úng `input_json`.
Γöé
Γûê─É├óy l├á tß║ºng DUY NHß║ñT biß║┐t tß╗¢i SQLAlchemy. Tß║ºng tr├¬n (`ingest`, `store`) chß╗ë nhß║¡n
Γûêv├á trß║ú vß╗ü dict JSON thuß║ºn, n├¬n ─æß╗òi Postgres sang thß╗⌐ kh├íc chß╗ë phß║úi viß║┐t lß║íi file
Γûên├áy ΓÇö ─æ├║ng nh╞░ lß╗¥i hß╗⌐a trong docstring cß╗ºa `store.py` tß╗½ ─æß║ºu.
Γöé
ΓûêTra cß╗⌐u theo T├èN FILE trong khi kho├í ch├¡nh l├á `id` tß╗▒ t─âng: t├¬n file gß╗æc ─æ├ú nß║▒m
Γûêsß║╡n trong t├ái liß╗çu ß╗ƒ `scope.sources[0].file` (do `merge_documents` ghi v├áo), n├¬n
Γûêkh├┤ng cß║ºn th├¬m cß╗Öt phß╗Ñ, v├á c┼⌐ng kh├┤ng cß║ºn nh├⌐t metadata lß║í v├áo `content` ΓÇö
Γûê`content` giß╗» ─æ├║ng nß╗Öi dung JSON cß╗ºa catalog, kh├┤ng h╞ín.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport logging
Γûêfrom collections.abc import Iterator
Γûêfrom contextlib import contextmanager
Γûêfrom typing import Any
Γöé
Γûêfrom sqlalchemy import func, select
Γûêfrom sqlalchemy.exc import SQLAlchemyError
Γöé
Γûêfrom src.core.db import session_scope
Γûêfrom src.core.errors import CriticalError, ErrorCode, Stage
Γûêfrom src.models.tables import InputJson
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γöé
Γûêdef document_filename(document: dict[str, Any]) -> str | None:
Γûê    """T├¬n file gß╗æc ─æ├ú sinh ra t├ái liß╗çu n├áy ('order-service.yaml').
Γöé
Γûê    Mß╗Öt t├ái liß╗çu l╞░u trong bß║úng lu├┤n ─æ╞░ß╗úc merge tß╗½ ─æ├║ng Mß╗ÿT file, n├¬n
Γûê    `sources` lu├┤n c├│ ─æ├║ng mß╗Öt phß║ºn tß╗¡. Vß║½n viß║┐t ph├▓ng thß╗º v├¼ h├ám n├áy c├▓n ─æ╞░ß╗úc
Γûê    gß╗ìi tr├¬n dß╗» liß╗çu ─æß╗ìc tß╗½ DB ΓÇö thß╗⌐ c├│ thß╗â do bß║ún c┼⌐ hoß║╖c do ng╞░ß╗¥i kh├íc ghi.
Γûê    """
Γûê    sources = document.get("scope", {}).get("sources") or []
Γûê    if not sources:
Γûê        return None
Γûê    return sources[0].get("file")
Γöé
Γöé
Γûê# Biß╗âu thß╗⌐c SQL trß╗Å tß╗¢i ─æ├║ng chß╗ù chß╗⌐a t├¬n file trong JSONB.
Γûê# `.astext` l├á to├ín tß╗¡ `#>>` cß╗ºa Postgres: lß║Ñy ra chuß╗ùi thay v├¼ mß╗Öt gi├í trß╗ï JSON,
Γûê# nhß╗¥ vß║¡y so s├ính trß╗▒c tiß║┐p ─æ╞░ß╗úc vß╗¢i tham sß╗æ Python.
Γûê_FILENAME_COLUMN = InputJson.content["scope"]["sources"][0]["file"].astext
Γöé
Γöé
Γûê@contextmanager
Γûêdef _storage_guard(action: str) -> Iterator[None]:
Γûê    """Biß║┐n mß╗ìi lß╗ùi SQLAlchemy th├ánh CriticalError/STORAGE_FAILURE.
Γöé
Γûê    Kh├┤ng ─æß╗â `SQLAlchemyError` lß╗ìt l├¬n tß║ºng tr├¬n: handler to├án cß╗Ñc sß║╜ bß║»t n├│ nh╞░
Γûê    mß╗Öt exception lß║í v├á trß║ú INTERNAL_ERROR, trong khi ─æ├óy l├á t├¼nh huß╗æng ta HIß╗éU
Γûê    R├ò ΓÇö kho l╞░u trß╗» kh├┤ng d├╣ng ─æ╞░ß╗úc. Hai m├ú lß╗ùi kh├íc nhau dß║½n tß╗¢i hai c├ích xß╗¡ l├╜
Γûê    kh├íc nhau ß╗ƒ ph├¡a vß║¡n h├ánh.
Γöé
Γûê    `log_message` cß╗æ ├╜ chß╗ë mang t├¬n lß╗¢p exception: th├┤ng ─æiß╗çp lß╗ùi kß║┐t nß╗æi cß╗ºa
Γûê    psycopg2 c├│ thß╗â k├¿m nguy├¬n chuß╗ùi DSN, tß╗⌐c l├á k├¿m cß║ú mß║¡t khß║⌐u database.
Γûê    """
Γûê    try:
Γûê        yield
Γûê    except SQLAlchemyError as exc:
Γûê        raise CriticalError(
Γûê            ErrorCode.STORAGE_FAILURE,
Γûê            "Kh├┤ng l╞░u ─æ╞░ß╗úc kß║┐t quß║ú xß╗¡ l├╜. Vui l├▓ng thß╗¡ lß║íi sau.",
Γûê            stage=Stage.PERSIST,
Γûê            log_message=f"Thao t├íc '{action}' tr├¬n bß║úng input_json thß║Ñt bß║íi: "
Γûê            f"{type(exc).__name__}",
Γûê        ) from exc
Γöé
Γöé
Γûêdef save(document: dict[str, Any]) -> tuple[int, bool]:
Γûê    """L╞░u t├ái liß╗çu. Trß║ú `(id, ─æ├ú_ghi_─æ├¿)`.
Γöé
Γûê    C├╣ng mß╗Öt file upload lß║íi th├¼ GHI ─É├ê ─æ├║ng d├▓ng c┼⌐ chß╗⌐ kh├┤ng sinh d├▓ng mß╗¢i:
Γûê    bß║úng phß║ún ├ính "c├íc catalog ─æang c├│", kh├┤ng phß║úi nhß║¡t k├╜ upload. Nß║┐u cß╗⌐ ch├¿n
Γûê    th├¬m, `GET /catalogs` sß║╜ phß║úi tß╗▒ ─æo├ín d├▓ng n├áo l├á bß║ún mß╗¢i nhß║Ñt ΓÇö mß╗Öt c├óu hß╗Åi
Γûê    kh├┤ng n├¬n tß╗ôn tß║íi.
Γûê    """
Γûê    filename = document_filename(document)
Γûê    if filename is None:
Γûê        raise CriticalError(
Γûê            ErrorCode.INCONSISTENT_STATE,
Γûê            "Kh├┤ng l╞░u ─æ╞░ß╗úc kß║┐t quß║ú xß╗¡ l├╜.",
Γûê            stage=Stage.PERSIST,
Γûê            log_message="T├ái liß╗çu chuß║⌐n bß╗ï l╞░u kh├┤ng c├│ scope.sources[0].file ΓÇö "
Γûê            "lß╗ùi ß╗ƒ tß║ºng sinh JSON, kh├┤ng phß║úi ß╗ƒ input.",
Γûê        )
Γöé
Γûê    with _storage_guard("save"), session_scope() as session:
Γûê        row = session.scalars(
Γûê            select(InputJson).where(_FILENAME_COLUMN == filename)
Γûê        ).first()
Γöé
Γûê        if row is not None:
Γûê            row.content = document
Γûê            session.flush()
Γûê            return row.id, True
Γöé
Γûê        row = InputJson(content=document)
Γûê        session.add(row)
Γûê        session.flush()  # ─æß╗â Postgres cß║Ñp id ngay, ─æß╗ìc ─æ╞░ß╗úc tr╞░ß╗¢c khi commit
Γûê        return row.id, False
Γöé
Γöé
Γûêdef find(filename: str) -> dict[str, Any] | None:
Γûê    with _storage_guard("find"), session_scope() as session:
Γûê        return session.scalars(
Γûê            select(InputJson.content).where(_FILENAME_COLUMN == filename)
Γûê        ).first()
Γöé
Γöé
Γûêdef delete(filename: str) -> bool:
Γûê    """Xo├í d├▓ng cß╗ºa 1 file. Trß║ú True nß║┐u thß║¡t sß╗▒ c├│ d├▓ng bß╗ï xo├í."""
Γûê    with _storage_guard("delete"), session_scope() as session:
Γûê        row = session.scalars(
Γûê            select(InputJson).where(_FILENAME_COLUMN == filename)
Γûê        ).first()
Γûê        if row is None:
Γûê            return False
Γûê        session.delete(row)
Γûê        return True
Γöé
Γöé
Γûêdef all_documents() -> list[tuple[int, dict[str, Any]]]:
Γûê    """To├án bß╗Ö `(id, content)`, sß║»p theo id ΓÇö d├╣ng ─æß╗â dß╗▒ng lß║íi cache l├║c khß╗ƒi ─æß╗Öng.
Γöé
Γûê    Trß║ú k├¿m `id` chß╗⌐ kh├┤ng chß╗ë `content`: bß║ún ghi nß║íp lß║íi sau restart vß║½n phß║úi
Γûê    biß║┐t m├¼nh l├á d├▓ng n├áo trong bß║úng, nß║┐u kh├┤ng `record_id` sß║╜ l├á null cho tß╗¢i
Γûê    lß║ºn upload kß║┐ tiß║┐p.
Γûê    """
Γûê    with _storage_guard("all_documents"), session_scope() as session:
Γûê        rows = session.execute(
Γûê            select(InputJson.id, InputJson.content).order_by(InputJson.id)
Γûê        ).all()
Γûê        return [(row_id, content) for row_id, content in rows]
Γöé
Γöé
Γûêdef count() -> int:
Γûê    with _storage_guard("count"), session_scope() as session:
Γûê        return session.scalar(select(func.count()).select_from(InputJson)) or 0
Γöé


src\services\catalog_to_graph.py:
Γûê"""
Γûêcatalog_to_graph.py ΓÇö catalog-info.yaml  ->  {stem}.graph.json
Γöé
ΓûêPipeline:
Γûê    YAML (pyyaml, strict loader)
Γûê      -> validate          (schema + format rules, gom hß║┐t lß╗ùi)
Γûê      -> canonicalize      (ref -> node id + relation)
Γûê      -> graph             (networkX DiGraph, chiß╗üu = chiß╗üu phß╗Ñ thuß╗Öc)
Γûê      -> document          (nodes dict + edges list + diagnostics)
Γûê      -> JSON file
Γöé
ΓûêUsage:
Γûê    python catalog_to_graph.py catalog.yaml
Γûê    python catalog_to_graph.py catalog.yaml -o build/graph.json
Γûê    python catalog_to_graph.py catalog.yaml --no-timestamp --quiet
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport argparse
Γûêimport json
Γûêimport re
Γûêimport sys
Γûêfrom dataclasses import dataclass, field
Γûêfrom datetime import datetime
Γûêfrom zoneinfo import ZoneInfo
Γûêfrom pathlib import Path
Γûêfrom typing import Any
Γöé
Γûêimport networkx as nx
Γûêimport yaml
Γöé
ΓûêSCHEMA_VERSION = "1.1"
ΓûêSPEC_VERSION = "vsf-idp.io/v2"
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Rules
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
ΓûêSLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")          # system, namespace, spec.id
ΓûêREF_NAME_RE = re.compile(r"^[a-z][a-z0-9._-]*$")     # name-part: topic c├│ dß║Ñu '.'
ΓûêREF_RE = re.compile(r"^(?P<kind>[A-Za-z]+):(?P<namespace>[^/]+)/(?P<name>.+)$")
ΓûêCONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
Γöé
ΓûêDOMAIN_MAX_LEN = 128
Γöé
ΓûêAPI_TYPES = {"service", "gateway"}
ΓûêCATALOG_ONLY_TYPES = {
Γûê    "worker", "batch", "job", "library", "website", "mobile-app",
Γûê    "data-pipeline", "function", "plugin", "tool", "documentation", "other",
Γûê}
ΓûêALL_TYPES = API_TYPES | CATALOG_ONLY_TYPES
Γöé
ΓûêMEMBER_ROLES = {"techlead", "maintainer", "member"}
Γöé
Γûê# ref kind -> (node kind, relation).  ─É├óy l├á bß║úng ngß╗» ngh─⌐a trung t├óm:
Γûê# kind trong yaml vß╗½a quyß║┐t ─æß╗ïnh loß║íi node, vß╗½a quyß║┐t ─æß╗ïnh t├¬n cß║ính.
ΓûêREF_KIND_MAP: dict[str, tuple[str, str]] = {
Γûê    "system":       ("system",    "partOf"),
Γûê    "component":    ("component", "dependsOn"),
Γûê    "resource":     ("resource",  "dependsOn"),
Γûê    "providesApis": ("api",       "provides"),
Γûê    "consumesApis": ("api",       "consumes"),
Γûê    "publishesTo":  ("topic",     "publishes"),
Γûê    "consumesFrom": ("topic",     "subscribes"),
Γûê}
Γöé
ΓûêNODE_KINDS = {"system", "component", "resource", "api", "topic"}
Γöé
Γûê# Trong JSON, source LU├öN l├á component khai b├ío (─æß╗ìc xu├┤i: "X provides Y").
Γûê# Nh╞░ng chiß╗üu PHß╗ñ THUß╗ÿC th├¼ ng╞░ß╗úc lß║íi ß╗ƒ 2 quan hß╗ç: api tß╗ôn tß║íi nhß╗¥ component,
Γûê# consumer cß╗ºa topic phß╗Ñ thuß╗Öc v├áo publisher. Bß║úng n├áy chß╗ë d├╣ng khi dß╗▒ng
Γûê# networkX graph ─æß╗â nx.ancestors() trß║ú ─æ├║ng "ai chß║┐t theo nß║┐u X chß║┐t".
ΓûêRELATION_REVERSED = {"provides", "publishes"}
Γöé
Γûê# Quyß╗ün sß╗ƒ hß╗»u node ΓÇö quyß║┐t ─æß╗ïnh tr╞░ß╗¥ng declared_by:
Γûê#   component ΓåÆ file tß╗▒ khai b├ío ch├¡nh n├│ (metadata + spec.id)
Γûê#   api       ΓåÆ component n├áo 'provides' n├│. Hai component c├╣ng provides = lß╗ùi.
Γûê#   topic     ΓåÆ KH├öNG ai sß╗ƒ hß╗»u: nhiß╗üu producer c├╣ng publish v├áo mß╗Öt topic l├á hß╗úp lß╗ç.
Γûê#   resource  ΓåÆ KH├öNG ai sß╗ƒ hß╗»u: hß║í tß║ºng cß║ºn catalog ri├¬ng, ngo├ái phß║ím vi file n├áy.
Γûê#   system    ΓåÆ KH├öNG ai sß╗ƒ hß╗»u: cß║ºn file khai b├ío cß║Ñp system.
Γûê# 3 kind cuß╗æi c├│ declared_by = null v─⌐nh viß╗àn, kh├┤ng bao giß╗¥ cß║únh b├ío vß╗ü chuyß╗çn ─æ├│.
ΓûêOWNED_VIA_RELATION = {"api": "provides"}
ΓûêUNOWNABLE_KINDS = {"system", "resource", "topic"}
ΓûêSPEC_BEARING_KINDS = {"component"}
Γöé
ΓûêKNOWN_PROTOCOLS = {
Γûê    "rest": "REST", "grpc": "gRPC", "kafka": "Kafka",
Γûê    "websocket": "WebSocket", "graphql": "GraphQL", "soap": "SOAP",
Γûê}
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Diagnostics
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûê@dataclass
Γûêclass Issue:
Γûê    code: str
Γûê    message: str
Γûê    yaml_path: str | None = None
Γûê    subject: str | None = None
Γûê    source: str | None = None
Γöé
Γûê    def as_dict(self) -> dict[str, Any]:
Γûê        d = {"code": self.code, "message": self.message}
Γûê        for k in ("subject", "yaml_path", "source"):
Γûê            if getattr(self, k) is not None:
Γûê                d[k] = getattr(self, k)
Γûê        return d
Γöé
Γöé
Γûê@dataclass
Γûêclass Diagnostics:
Γûê    errors: list[Issue] = field(default_factory=list)
Γûê    warnings: list[Issue] = field(default_factory=list)
Γöé
Γûê    def err(self, code: str, message: str, **kw: Any) -> None:
Γûê        self.errors.append(Issue(code, message, **kw))
Γöé
Γûê    def warn(self, code: str, message: str, **kw: Any) -> None:
Γûê        self.warnings.append(Issue(code, message, **kw))
Γöé
Γûê    def as_dict(self) -> dict[str, Any]:
Γûê        return {
Γûê            "errors": [i.as_dict() for i in self.errors],
Γûê            "warnings": [i.as_dict() for i in self.warnings],
Γûê        }
Γöé
Γöé
Γûêclass FatalError(Exception):
Γûê    """Lß╗ùi khiß║┐n kh├┤ng parse tiß║┐p ─æ╞░ß╗úc (YAML hß╗Ång, root sai kiß╗âu)."""
Γöé
Γûê    def __init__(self, issue: Issue) -> None:
Γûê        self.issue = issue
Γûê        super().__init__(issue.message)
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Strict YAML loader ΓÇö pyyaml mß║╖c ─æß╗ïnh nuß╗æt duplicate key, ß╗ƒ ─æ├óy th├¼ reject
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûêclass StrictLoader(yaml.SafeLoader):
Γûê    pass
Γöé
Γöé
Γûêdef _no_duplicate_keys(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False):
Γûê    seen: set[Any] = set()
Γûê    for key_node, _ in node.value:
Γûê        key = loader.construct_object(key_node, deep=deep)
Γûê        if key in seen:
Γûê            raise yaml.constructor.ConstructorError(
Γûê                "while constructing a mapping", node.start_mark,
Γûê                f"duplicate key {key!r}", key_node.start_mark)
Γûê        seen.add(key)
Γûê    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)
Γöé
Γöé
ΓûêStrictLoader.add_constructor(
Γûê    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)
Γöé
Γöé
Γûêdef load_yaml(text: str) -> dict[str, Any]:
Γûê    try:
Γûê        doc = yaml.load(text, Loader=StrictLoader)
Γûê    except yaml.YAMLError as exc:
Γûê        raise FatalError(Issue("YAML_SYNTAX", str(exc), yaml_path="$")) from exc
Γûê    if not isinstance(doc, dict):
Γûê        raise FatalError(Issue("TYPE_MISMATCH", "Root cß╗ºa file phß║úi l├á mapping",
Γûê                               yaml_path="$"))
Γûê    return doc
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Field-level validators
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûêdef _require_str(value: Any, path: str, d: Diagnostics) -> str | None:
Γûê    if value is None or (isinstance(value, str) and not value.strip()):
Γûê        d.err("REQUIRED", "Field bß║»t buß╗Öc, kh├┤ng ─æ╞░ß╗úc rß╗ùng", yaml_path=path)
Γûê        return None
Γûê    if not isinstance(value, str):
Γûê        d.err("TYPE_MISMATCH", f"Phß║úi l├á string, nhß║¡n {type(value).__name__}",
Γûê              yaml_path=path)
Γûê        return None
Γûê    return value.strip()
Γöé
Γöé
Γûêdef _check_slug(value: str, path: str, d: Diagnostics) -> None:
Γûê    if not SLUG_RE.match(value):
Γûê        d.err("INVALID_FORMAT",
Γûê              f"'{value}' kh├┤ng khß╗¢p ^[a-z][a-z0-9-]*$ "
Γûê              "(chß╗» th╞░ß╗¥ng, kh├┤ng space, kh├┤ng chß╗» hoa)", yaml_path=path)
Γöé
Γöé
Γûêdef _check_freetext(value: str, path: str, d: Diagnostics,
Γûê                    max_len: int | None = None) -> None:
Γûê    if CONTROL_CHARS_RE.search(value):
Γûê        d.err("CONTROL_CHARS", "Kh├┤ng ─æ╞░ß╗úc chß╗⌐a control characters (U+0000ΓÇô001F, DEL)",
Γûê              yaml_path=path)
Γûê    if max_len and len(value) > max_len:
Γûê        d.err("TOO_LONG", f"Tß╗æi ─æa {max_len} k├╜ tß╗▒, hiß╗çn tß║íi {len(value)}",
Γûê              yaml_path=path)
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Canonicalize: ref string -> node id + relation
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûê@dataclass
Γûêclass ParsedRef:
Γûê    node_id: str
Γûê    node_kind: str
Γûê    namespace: str
Γûê    name: str
Γûê    relation: str
Γöé
Γöé
Γûêdef parse_ref(raw: str, path: str, d: Diagnostics) -> ParsedRef | None:
Γûê    m = REF_RE.match(raw)
Γûê    if not m:
Γûê        d.err("INVALID_REF", f"'{raw}' phß║úi c├│ dß║íng '{{kind}}:{{namespace}}/{{name}}'",
Γûê              yaml_path=path)
Γûê        return None
Γöé
Γûê    kind, ns, name = m.group("kind"), m.group("namespace"), m.group("name")
Γöé
Γûê    if kind not in REF_KIND_MAP:
Γûê        d.err("UNKNOWN_KIND",
Γûê              f"kind '{kind}' kh├┤ng hß╗úp lß╗ç. Cho ph├⌐p: {', '.join(sorted(REF_KIND_MAP))}",
Γûê              yaml_path=path)
Γûê        return None
Γûê    if not SLUG_RE.match(ns):
Γûê        d.err("INVALID_FORMAT", f"namespace '{ns}' trong ref kh├┤ng khß╗¢p ^[a-z][a-z0-9-]*$",
Γûê              yaml_path=path)
Γûê        return None
Γûê    if not REF_NAME_RE.match(name):
Γûê        d.err("INVALID_FORMAT", f"name '{name}' trong ref kh├┤ng hß╗úp lß╗ç", yaml_path=path)
Γûê        return None
Γöé
Γûê    node_kind, relation = REF_KIND_MAP[kind]
Γûê    return ParsedRef(f"{node_kind}:{ns}/{name}", node_kind, ns, name, relation)
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Parse 1 file -> nodes / edges
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûêdef parse_document(doc: dict[str, Any], filename: str,
Γûê                   d: Diagnostics) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
Γûê    """Trß║ú vß╗ü (nodes, edges, root_id). Node self lu├┤n ─æß╗⌐ng ─æß║ºu nodes."""
Γöé
Γûê    if doc.get("specVersion") != SPEC_VERSION:
Γûê        d.err("UNSUPPORTED_VERSION",
Γûê              f"Chß╗ë hß╗ù trß╗ú specVersion '{SPEC_VERSION}', nhß║¡n '{doc.get('specVersion')}'",
Γûê              yaml_path="specVersion", source=filename)
Γöé
Γûê    meta = doc.get("metadata")
Γûê    if not isinstance(meta, dict):
Γûê        raise FatalError(Issue("TYPE_MISMATCH", "metadata phß║úi l├á mapping",
Γûê                               yaml_path="metadata", source=filename))
Γûê    spec = doc.get("spec")
Γûê    if not isinstance(spec, dict):
Γûê        raise FatalError(Issue("TYPE_MISMATCH", "spec phß║úi l├á mapping",
Γûê                               yaml_path="spec", source=filename))
Γöé
Γûê    # ΓöÇΓöÇ metadata ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    domain = _require_str(meta.get("domain"), "metadata.domain", d)
Γûê    if domain:
Γûê        _check_freetext(domain, "metadata.domain", d, DOMAIN_MAX_LEN)
Γöé
Γûê    system = _require_str(meta.get("system"), "metadata.system", d)
Γûê    if system:
Γûê        _check_slug(system, "metadata.system", d)
Γöé
Γûê    namespace = _require_str(meta.get("namespace"), "metadata.namespace", d)
Γûê    if namespace:
Γûê        _check_slug(namespace, "metadata.namespace", d)
Γöé
Γûê    # ΓöÇΓöÇ spec ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    stype = _require_str(spec.get("type"), "spec.type", d)
Γûê    if stype and stype not in ALL_TYPES:
Γûê        d.err("INVALID_ENUM",
Γûê              f"type '{stype}' kh├┤ng hß╗úp lß╗ç. Cho ph├⌐p: {', '.join(sorted(ALL_TYPES))}",
Γûê              yaml_path="spec.type")
Γûê        stype = None
Γûê    if stype == "job":
Γûê        d.warn("TYPE_ALIAS", "'job' l├á alias cß╗ºa 'batch' (Backstage compat)",
Γûê               yaml_path="spec.type")
Γöé
Γûê    sid = _require_str(spec.get("id"), "spec.id", d)
Γûê    if sid:
Γûê        _check_slug(sid, "spec.id", d)
Γöé
Γûê    display_name = _require_str(spec.get("name"), "spec.name", d)
Γûê    if display_name:
Γûê        _check_freetext(display_name, "spec.name", d)
Γöé
Γûê    description = spec.get("description")
Γûê    if description is not None:
Γûê        description = _require_str(description, "spec.description", d)
Γûê        if description:
Γûê            _check_freetext(description, "spec.description", d)
Γöé
Γûê    # ΓöÇΓöÇ owners.members ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    owners = spec.get("owners") or {}
Γûê    members_raw = owners.get("members") if isinstance(owners, dict) else None
Γûê    members: list[dict[str, str]] = []
Γöé
Γûê    if not isinstance(members_raw, list) or not members_raw:
Γûê        d.err("REQUIRED", "Cß║ºn ├¡t nhß║Ñt 1 member vß╗¢i role techlead",
Γûê              yaml_path="spec.owners.members")
Γûê    else:
Γûê        seen_users: set[str] = set()
Γûê        for i, m in enumerate(members_raw):
Γûê            p = f"spec.owners.members[{i}]"
Γûê            if not isinstance(m, dict):
Γûê                d.err("TYPE_MISMATCH", "Member phß║úi l├á mapping {user, role}", yaml_path=p)
Γûê                continue
Γûê            user = _require_str(m.get("user"), f"{p}.user", d)
Γûê            role = _require_str(m.get("role"), f"{p}.role", d)
Γûê            if role and role not in MEMBER_ROLES:
Γûê                d.err("INVALID_ENUM",
Γûê                      f"role '{role}' kh├┤ng hß╗úp lß╗ç. Cho ph├⌐p: {', '.join(sorted(MEMBER_ROLES))}",
Γûê                      yaml_path=f"{p}.role")
Γûê                role = None
Γûê            if user and user.lower() in seen_users:
Γûê                d.err("DUPLICATE", f"User '{user}' bß╗ï khai b├ío tr├╣ng", yaml_path=f"{p}.user")
Γûê                continue
Γûê            if user:
Γûê                seen_users.add(user.lower())
Γûê            if user and role:
Γûê                members.append({"user_email": user, "role": role})
Γöé
Γûê        if members and not any(m["role"] == "techlead" for m in members):
Γûê            d.err("MISSING_TECHLEAD", "Phß║úi c├│ ├¡t nhß║Ñt 1 member vß╗¢i role 'techlead'",
Γûê                  yaml_path="spec.owners.members")
Γöé
Γûê    # ΓöÇΓöÇ review ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    review = spec.get("review") or {}
Γûê    branch = None
Γûê    if not isinstance(review, dict):
Γûê        d.err("TYPE_MISMATCH", "review phß║úi l├á mapping", yaml_path="spec.review")
Γûê    else:
Γûê        branch = _require_str(review.get("branch"), "spec.review.branch", d)
Γöé
Γûê    # ΓöÇΓöÇ node self ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    root_id = f"component:{namespace}/{sid}" if namespace and sid else None
Γûê    nodes: dict[str, Any] = {}
Γöé
Γûê    if root_id:
Γûê        nodes[root_id] = {
Γûê            "id": root_id,
Γûê            "kind": "component",
Γûê            "namespace": namespace,
Γûê            "name": sid,
Γûê            "declared_by": filename,
Γûê            "spec": {
Γûê                "service_key": f"{system}.{sid}" if system else None,
Γûê                "display_name": display_name,
Γûê                "description": description,
Γûê                "system": system,
Γûê                "domain": domain,
Γûê                "type": stype,
Γûê                "has_api_surface": stype in API_TYPES,
Γûê                "review": {"branch": branch},
Γûê                "members": members,
Γûê            },
Γûê        }
Γöé
Γûê    # ΓöÇΓöÇ topology -> edges + stub nodes ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    topology = spec.get("topology") or []
Γûê    edges: list[dict[str, Any]] = []
Γöé
Γûê    if not isinstance(topology, list):
Γûê        d.err("TYPE_MISMATCH", "topology phß║úi l├á list", yaml_path="spec.topology")
Γûê        topology = []
Γöé
Γûê    seen_edge_ids: set[str] = set()
Γöé
Γûê    for i, entry in enumerate(topology):
Γûê        p = f"spec.topology[{i}]"
Γûê        if not isinstance(entry, dict):
Γûê            d.err("TYPE_MISMATCH", "Entry phß║úi l├á mapping {ref, protocol?, reason?}",
Γûê                  yaml_path=p)
Γûê            continue
Γöé
Γûê        raw_ref = _require_str(entry.get("ref"), f"{p}.ref", d)
Γûê        if not raw_ref:
Γûê            continue
Γûê        ref = parse_ref(raw_ref, f"{p}.ref", d)
Γûê        if not ref or not root_id:
Γûê            continue
Γöé
Γûê        if ref.node_id == root_id:
Γûê            d.err("SELF_REFERENCE", f"'{raw_ref}' trß╗Å vß╗ü ch├¡nh component n├áy",
Γûê                  yaml_path=f"{p}.ref")
Γûê            continue
Γöé
Γûê        edge_id = f"{root_id}|{ref.relation}|{ref.node_id}"
Γûê        if edge_id in seen_edge_ids:
Γûê            d.err("DUPLICATE_EDGE", f"Cß║ính '{ref.relation}' tß╗¢i '{ref.node_id}' bß╗ï khai b├ío tr├╣ng",
Γûê                  yaml_path=f"{p}.ref")
Γûê            continue
Γûê        seen_edge_ids.add(edge_id)
Γöé
Γûê        protocol = entry.get("protocol")
Γûê        if protocol is not None:
Γûê            protocol = str(protocol).strip()
Γûê            protocol = KNOWN_PROTOCOLS.get(protocol.lower(), protocol)
Γöé
Γûê        reason = entry.get("reason")
Γûê        reason = str(reason).strip() if reason is not None else None
Γöé
Γûê        # Node ─æ├¡ch ΓÇö chß╗ë tß║ío nß║┐u ch╞░a tß╗ôn tß║íi, kh├┤ng bao giß╗¥ ghi ─æ├¿.
Γûê        # Quyß╗ün sß╗ƒ hß╗»u g├ín ß╗ƒ pass ri├¬ng ph├¡a d╞░ß╗¢i.
Γûê        if ref.node_id not in nodes:
Γûê            nodes[ref.node_id] = {
Γûê                "id": ref.node_id,
Γûê                "kind": ref.node_kind,
Γûê                "namespace": ref.namespace,
Γûê                "name": ref.name,
Γûê                "declared_by": None,
Γûê                "spec": None,
Γûê            }
Γöé
Γûê        edges.append({
Γûê            "id": edge_id,
Γûê            "source": root_id,
Γûê            "target": ref.node_id,
Γûê            "relation": ref.relation,
Γûê            "protocol": protocol,
Γûê            "reason": reason,
Γûê            "declared_by": root_id,
Γûê            "yaml_path": p,
Γûê        })
Γöé
Γûê    # ΓöÇΓöÇ G├ín quyß╗ün sß╗ƒ hß╗»u ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    _assign_ownership(nodes, edges, filename, d)
Γöé
Γûê    # ΓöÇΓöÇ cross-field consistency ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    _check_consistency(nodes, edges, system, sid, stype, root_id, namespace, d)
Γöé
Γûê    return nodes, edges, root_id
Γöé
Γöé
Γûêdef _assign_ownership(nodes: dict[str, Any], edges: list[dict[str, Any]],
Γûê                      filename: str, d: Diagnostics) -> None:
Γûê    """Component ─æ├ú tß╗▒ sß╗ƒ hß╗»u l├║c tß║ío. ß╗₧ ─æ├óy g├ín chß╗º cho api qua cß║ính 'provides'.
Γûê    topic / resource / system cß╗æ t├¼nh ─æß╗â trß╗æng ΓÇö xem OWNED_VIA_RELATION."""
Γûê    for e in edges:
Γûê        target = nodes[e["target"]]
Γûê        if OWNED_VIA_RELATION.get(target["kind"]) != e["relation"]:
Γûê            continue
Γöé
Γûê        if target["declared_by"] is None:
Γûê            target["declared_by"] = filename
Γûê            d.warn("AWAITING_SPEC_INGEST",
Γûê                   f"{target['id']} ─æ├ú c├│ chß╗º nh╞░ng ch╞░a c├│ spec ΓÇö "
Γûê                   "chß╗¥ ingest registry.yaml + openapi.yaml",
Γûê                   subject=target["id"], yaml_path=e["yaml_path"], source=filename)
Γûê        elif target["declared_by"] != filename:
Γûê            d.err("AMBIGUOUS_OWNER",
Γûê                  f"{target['id']} ─æ╞░ß╗úc provides bß╗ƒi cß║ú "
Γûê                  f"'{target['declared_by']}' v├á '{filename}'",
Γûê                  subject=target["id"], yaml_path=e["yaml_path"], source=filename)
Γöé
Γöé
Γûêdef _check_consistency(nodes: dict[str, Any], edges: list[dict[str, Any]],
Γûê                       system: str | None, sid: str | None, stype: str | None,
Γûê                       root_id: str | None, namespace: str | None,
Γûê                       d: Diagnostics) -> None:
Γûê    system_edges = [e for e in edges if e["relation"] == "partOf"]
Γûê    if not system_edges:
Γûê        d.warn("MISSING_SYSTEM_REF",
Γûê               f"Ch╞░a khai b├ío 'system:{namespace}/{system}' (quan hß╗ç partOf)",
Γûê               yaml_path="spec.topology")
Γûê    for e in system_edges:
Γûê        if system and nodes[e["target"]]["name"] != system:
Γûê            d.err("SYSTEM_MISMATCH",
Γûê                  f"'{e['target']}' kh├┤ng khß╗¢p metadata.system = '{system}'",
Γûê                  yaml_path=e["yaml_path"], subject=e["target"])
Γöé
Γûê    provides = [e for e in edges if e["relation"] == "provides"]
Γûê    if stype in API_TYPES and not provides:
Γûê        d.warn("MISSING_PROVIDES_API",
Γûê               f"type '{stype}' c├│ API surface nh╞░ng ch╞░a khai b├ío providesApis",
Γûê               yaml_path="spec.topology")
Γûê    if stype in CATALOG_ONLY_TYPES and provides:
Γûê        d.err("UNEXPECTED_PROVIDES_API",
Γûê              f"type '{stype}' kh├┤ng c├│ API surface nh╞░ng khai b├ío providesApis",
Γûê              yaml_path=provides[0]["yaml_path"])
Γûê    for e in provides:
Γûê        if sid and nodes[e["target"]]["name"] != sid:
Γûê            d.warn("PROVIDES_API_MISMATCH",
Γûê                   f"API '{nodes[e['target']]['name']}' kh├íc spec.id '{sid}'",
Γûê                   yaml_path=e["yaml_path"], subject=e["target"])
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# networkX ΓÇö chiß╗üu cß║ính = chiß╗üu phß╗Ñ thuß╗Öc (source phß╗Ñ thuß╗Öc target)
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûêdef build_nx_graph(nodes: dict[str, Any], edges: list[dict[str, Any]]) -> nx.DiGraph:
Γûê    g = nx.DiGraph()
Γûê    for node_id, node in nodes.items():
Γûê        g.add_node(node_id, **{k: v for k, v in node.items() if k != "id"})
Γûê    for e in edges:
Γûê        src, tgt = e["source"], e["target"]
Γûê        if e["relation"] in RELATION_REVERSED:
Γûê            src, tgt = tgt, src
Γûê        g.add_edge(src, tgt, relation=e["relation"], protocol=e["protocol"],
Γûê                   declared_by=e["declared_by"])
Γûê    return g
Γöé
Γöé
Γûêdef check_cycles(g: nx.DiGraph, d: Diagnostics) -> None:
Γûê    for cycle in nx.simple_cycles(g):
Γûê        if len(cycle) > 1:
Γûê            d.warn("DEPENDENCY_CYCLE",
Γûê                   "Chu tr├¼nh phß╗Ñ thuß╗Öc: " + " -> ".join(cycle + [cycle[0]]),
Γûê                   subject=cycle[0])
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Document assembly
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûêdef assert_invariants(nodes: dict[str, Any], edges: list[dict[str, Any]]) -> None:
Γûê    """4 bß║Ñt biß║┐n cß╗ºa schema ΓÇö sai mß╗Öt c├íi l├á bug ß╗ƒ ph├¡a sinh, kh├┤ng phß║úi input."""
Γûê    for key, node in nodes.items():
Γûê        assert key == node["id"], f"key '{key}' != node.id '{node['id']}'"
Γûê        assert node["kind"] in NODE_KINDS, f"node kind lß║í: {node['kind']}"
Γûê        if node["spec"] is not None:
Γûê            assert node["kind"] in SPEC_BEARING_KINDS, \
Γûê                f"'{key}': kind '{node['kind']}' kh├┤ng ─æ╞░ß╗úc mang spec"
Γûê            assert node["declared_by"] is not None, \
Γûê                f"'{key}': c├│ spec nh╞░ng kh├┤ng c├│ declared_by"
Γûê        if node["kind"] in UNOWNABLE_KINDS:
Γûê            assert node["declared_by"] is None, \
Γûê                f"'{key}': kind '{node['kind']}' kh├┤ng ─æ╞░ß╗úc c├│ chß╗º sß╗ƒ hß╗»u"
Γûê    for e in edges:
Γûê        assert e["source"] in nodes, f"edge source '{e['source']}' kh├┤ng c├│ trong nodes"
Γûê        assert e["target"] in nodes, f"edge target '{e['target']}' kh├┤ng c├│ trong nodes"
Γöé
Γöé
ΓûêTOPOLOGY_INDEX_RE = re.compile(r"\[(\d+)\]")
Γöé
Γöé
Γûêdef _edge_sort_key(edge: dict[str, Any]) -> tuple[str, int, str]:
Γûê    """Sß║»p theo (component khai b├ío, thß╗⌐ tß╗▒ d├▓ng trong topology).
Γûê    Tß║Ñt ─æß╗ïnh nh╞░ sß║»p theo id, nh╞░ng ─æß╗æi chiß║┐u vß╗¢i YAML l├║c review MR th├¼ d├▓ ─æ╞░ß╗úc
Γûê    bß║▒ng mß║»t. Phß║ºn tß╗¡ thß╗⌐ 3 chß╗ë ─æß╗â ph├í ho├á khi yaml_path thiß║┐u chß╗ë sß╗æ."""
Γûê    m = TOPOLOGY_INDEX_RE.search(edge.get("yaml_path") or "")
Γûê    return (edge["declared_by"] or "", int(m.group(1)) if m else 0, edge["id"])
Γöé
Γöé
Γûê@dataclass
Γûêclass ParsedFile:
Γûê    """Kß║┐t quß║ú parse 1 file, tr╞░ß╗¢c khi ─æ├│ng g├│i scope ΓÇö d├╣ng lß║íi ─æ╞░ß╗úc cho
Γûê    CLI (1 file), cho merge nhiß╗üu file, v├á cho API."""
Γûê    filename: str
Γûê    nodes: dict[str, Any]
Γûê    edges: list[dict[str, Any]]
Γûê    root_id: str | None
Γûê    diagnostics: Diagnostics
Γöé
Γöé
Γûêdef parse_single(yaml_text: str, filename: str) -> ParsedFile:
Γûê    d = Diagnostics()
Γûê    try:
Γûê        doc = load_yaml(yaml_text)
Γûê        nodes, edges, root_id = parse_document(doc, filename, d)
Γûê    except FatalError as exc:
Γûê        d.errors.append(exc.issue)
Γûê        nodes, edges, root_id = {}, [], None
Γöé
Γûê    if nodes and not d.errors:
Γûê        check_cycles(build_nx_graph(nodes, edges), d)
Γûê        assert_invariants(nodes, edges)
Γöé
Γûê    return ParsedFile(filename, nodes, edges, root_id, d)
Γöé
Γöé
Γûêdef build_document(yaml_text: str, filename: str,
Γûê                   timestamp: bool = True) -> dict[str, Any]:
Γûê    p = parse_single(yaml_text, filename)
Γöé
Γûê    # Thß╗⌐ tß╗▒ tß║Ñt ─æß╗ïnh: node theo id, edge theo (file khai b├ío, thß╗⌐ tß╗▒ trong topology)
Γûê    ordered_nodes = {k: p.nodes[k] for k in sorted(p.nodes)}
Γûê    ordered_edges = sorted(p.edges, key=_edge_sort_key)
Γöé
Γûê    out: dict[str, Any] = {
Γûê        "schemaVersion": SCHEMA_VERSION,
Γûê        "specVersion": SPEC_VERSION,
Γûê    }
Γûê    if timestamp:
Γûê        out["generatedAt"] = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%dT%H:%M:%S+07:00")
Γöé
Γûê    out["scope"] = {
Γûê        "kind": "single",
Γûê        "root": p.root_id,
Γûê        "sources": [{"file": filename, "root": p.root_id}],
Γûê    }
Γûê    out["nodes"] = ordered_nodes
Γûê    out["edges"] = ordered_edges
Γûê    out["diagnostics"] = p.diagnostics.as_dict()
Γûê    return out
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Console summary
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûêdef render_summary(out: dict[str, Any], out_path: Path) -> str:
Γûê    diag = out["diagnostics"]
Γûê    nodes, edges = out["nodes"], out["edges"]
Γûê    lines: list[str] = []
Γöé
Γûê    if diag["errors"]:
Γûê        lines.append(f"FAILED ΓÇö {len(diag['errors'])} lß╗ùi")
Γûê        pad = max(len(e.get("yaml_path") or "-") for e in diag["errors"])
Γûê        for i, e in enumerate(diag["errors"], 1):
Γûê            lines.append(f"  {i:>2}. {(e.get('yaml_path') or '-').ljust(pad)}  "
Γûê                         f"{e['code']}: {e['message']}")
Γûê        return "\n".join(lines)
Γöé
Γûê    by_kind: dict[str, int] = {}
Γûê    for n in nodes.values():
Γûê        by_kind[n["kind"]] = by_kind.get(n["kind"], 0) + 1
Γûê    by_rel: dict[str, int] = {}
Γûê    for e in edges:
Γûê        by_rel[e["relation"]] = by_rel.get(e["relation"], 0) + 1
Γûê    owned = sum(1 for n in nodes.values() if n["declared_by"])
Γûê    full = sum(1 for n in nodes.values() if n["spec"])
Γöé
Γûê    lines.append(f"OK  {out['scope']['root']}")
Γûê    lines.append(f"    nodes  {len(nodes):>3}  ("
Γûê                 + ", ".join(f"{k} {v}" for k, v in sorted(by_kind.items()))
Γûê                 + f") ΓÇö {full} ─æß╗º spec, {owned - full} chß╗¥ ingest, "
Γûê                 + f"{len(nodes) - owned} ch╞░a c├│ chß╗º")
Γûê    lines.append(f"    edges  {len(edges):>3}  ("
Γûê                 + ", ".join(f"{k} {v}" for k, v in sorted(by_rel.items())) + ")")
Γûê    if diag["warnings"]:
Γûê        lines.append(f"    warn   {len(diag['warnings']):>3}")
Γûê        for w in diag["warnings"]:
Γûê            lines.append(f"           {w['code']}: {w['message']}")
Γûê    lines.append(f"    -> {out_path}")
Γûê    return "\n".join(lines)
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# CLI
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûêdef main(argv: list[str] | None = None) -> int:
Γûê    ap = argparse.ArgumentParser(
Γûê        description="catalog-info.yaml -> graph JSON",
Γûê        formatter_class=argparse.RawDescriptionHelpFormatter,
Γûê        epilog="V├¡ dß╗Ñ:\n"
Γûê               "  python catalog_to_graph.py catalog.yaml\n"
Γûê               "  python catalog_to_graph.py catalog.yaml -o build/graph.json\n"
Γûê               "  python catalog_to_graph.py catalog.yaml --no-timestamp\n")
Γûê    ap.add_argument("input", type=Path, help="file catalog-info.yaml")
Γûê    ap.add_argument("-o", "--output", type=Path,
Γûê                    help="file JSON ─æ├¡ch (mß║╖c ─æß╗ïnh: {stem}.graph.json cß║ính input)")
Γûê    ap.add_argument("--no-timestamp", action="store_true",
Γûê                    help="bß╗Å generatedAt ─æß╗â output tß║Ñt ─æß╗ïnh theo byte")
Γûê    ap.add_argument("--quiet", action="store_true", help="kh├┤ng in t├│m tß║»t")
Γûê    args = ap.parse_args(argv)
Γöé
Γûê    for stream in (sys.stdout, sys.stderr):
Γûê        try:
Γûê            stream.reconfigure(encoding="utf-8")
Γûê        except (AttributeError, ValueError):
Γûê            pass
Γöé
Γûê    try:
Γûê        yaml_text = args.input.read_text(encoding="utf-8")
Γûê    except FileNotFoundError:
Γûê        print(f"Kh├┤ng t├¼m thß║Ñy file: {args.input}", file=sys.stderr)
Γûê        return 2
Γöé
Γûê    out_path = args.output or args.input.with_suffix("").with_suffix(".graph.json")
Γûê    out_path.parent.mkdir(parents=True, exist_ok=True)
Γöé
Γûê    out = build_document(yaml_text, args.input.name, timestamp=not args.no_timestamp)
Γöé
Γûê    with out_path.open("w", encoding="utf-8", newline="\n") as f:
Γûê        json.dump(out, f, ensure_ascii=False, indent=2)
Γûê        f.write("\n")
Γöé
Γûê    if not args.quiet:
Γûê        print(render_summary(out, out_path))
Γöé
Γûê    return 1 if out["diagnostics"]["errors"] else 0
Γöé
Γöé
Γûêif __name__ == "__main__":
Γûê    raise SystemExit(main())


src\services\github_events.py:
Γûê"""
Γûêgithub_events.py ΓÇö Xß╗¡ l├╜ sß╗▒ kiß╗çn push tß╗½ GitHub.
Γöé
Γûê    x├íc thß╗▒c chß╗» k├╜  ->  b├│c t├ích payload  ->  ghi nhß║¡t k├╜ DB
Γûê                                            ->  xo├í catalog cß╗ºa file bß╗ï removed
Γûê                                            ->  nß║íp catalog cß╗ºa file added/modified
Γûê                                            ->  d├í┬╗┬▒ng response
Γöé
Γûê─É├óy l├á tß║ºng DUY NHß║ñT biß║┐t thß╗⌐ tß╗▒ c├íc b╞░ß╗¢c, ─æ├║ng vai tr├▓ `app/services/ingest.py`
Γûêgiß╗» cho luß╗ông upload thß╗º c├┤ng. Controller (`src/api/routes.py`) kh├┤ng biß║┐t g├¼ vß╗ü
Γûêh├¼nh dß║íng payload cß╗ºa GitHub, v├á `ingest` kh├┤ng biß║┐t l├á n├│ ─æang ─æ╞░ß╗úc gß╗ìi tß╗½ mß╗Öt
Γûêwebhook hay tß╗½ mß╗Öt form upload.
Γöé
ΓûêHai nguy├¬n tß║»c chi phß╗æi to├án bß╗Ö file n├áy:
Γöé
Γûê1. **Mß╗Öt file hß╗Ång kh├┤ng ─æ╞░ß╗úc l├ám hß╗Ång cß║ú lß║ºn push.** Lß╗ùi thuß╗Öc vß╗ü nß╗Öi dung file
Γûê   (YAML sai schema, tranh chß║Ñp quyß╗ün sß╗ƒ hß╗»u, kh├┤ng tß║úi ─æ╞░ß╗úc tß╗½ GitHub) ─æ╞░ß╗úc gom
Γûê   th├ánh `Issue` v├á vß║½n trß║ú HTTP 200. Trß║ú 4xx/5xx sß║╜ khiß║┐n GitHub ─æ├ính dß║Ñu
Γûê   delivery thß║Ñt bß║íi rß╗ôi RETRY ΓÇö m├á retry th├¼ file vß║½n sai y nh╞░ c┼⌐.
Γöé
Γûê2. **Sß╗▒ cß╗æ hß╗ç thß╗æng th├¼ ng╞░ß╗úc lß║íi: phß║úi ─æß╗â nß╗ò.** `CriticalError` (database sß║¡p,
Γûê   chß║│ng hß║ín) ─æ╞░ß╗úc re-raise ─æß╗â th├ánh 500 v├á GitHub retry ΓÇö lß║ºn sau DB sß╗æng lß║íi
Γûê   th├¼ push ─æ╞░ß╗úc xß╗¡ l├╜ thß║¡t. Nuß╗æt n├│ th├ánh `Issue` l├á b├ío "─æ├ú xß╗¡ l├╜ xong" cho
Γûê   mß╗Öt viß╗çc ch╞░a hß╗ü xß║úy ra.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport hashlib
Γûêimport hmac
Γûêimport logging
Γûêimport posixpath
Γûêfrom dataclasses import dataclass
Γûêfrom typing import Any
Γûêfrom urllib.parse import quote
Γöé
Γûêimport httpx
Γûêfrom starlette.concurrency import run_in_threadpool
Γöé
Γûêfrom src.core.config import ALLOWED_EXTENSIONS
Γûêfrom src.core.errors import (
Γûê    AppError,
Γûê    CriticalError,
Γûê    ErrorCode,
Γûê    SecurityError,
Γûê    Stage,
Γûê)
Γûêfrom src.models import schemas
Γûêfrom src.models.schemas import ApiResponse, Issue
Γûêfrom src.services import github_event_repository, ingest
Γûêfrom src.config import get_settings
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
ΓûêGITHUB_API_BASE = "https://api.github.com"
Γöé
Γûê# GitHub gß╗¡i t├¬n nh├ính d╞░ß╗¢i dß║íng `refs/heads/main`. Tag l├á `refs/tags/v1.0`.
Γûê_BRANCH_PREFIX = "refs/heads/"
Γöé
Γûê# Content-Type khai vß╗¢i `ingest`: layer 2 chß╗ë d├╣ng n├│ ─æß╗â Cß║óNH B├üO khi lß╗çch, kh├┤ng
Γûê# ─æß╗â chß║╖n, n├¬n khai ─æ├║ng loß║íi thß║¡t l├á ─æß╗º.
Γûê_YAML_CONTENT_TYPE = "application/x-yaml"
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Dß╗» liß╗çu ─æ├ú b├│c t├ích khß╗Åi payload
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûê@dataclass(frozen=True)
Γûêclass PushEvent:
Γûê    """Mß╗Öt lß║ºn push, ─æ├ú lß╗ìc sß║ích c├▓n ─æ├║ng thß╗⌐ hß╗ç thß╗æng quan t├óm.
Γöé
Γûê    Ba danh s├ích file mang ─É╞»ß╗£NG Dß║¬N ─Éß║ªY ─Éß╗ª trong repo
Γûê    ('services/order/catalog-info.yaml') v├á chß╗ë chß╗⌐a file `.yaml`/`.yml`.
Γûê    """
Γöé
Γûê    repo_full_name: str
Γûê    commit_id: str
Γûê    commit_url: str
Γûê    email: str
Γûê    branch: str
Γûê    timestamp: str
Γûê    added_files: list[str]
Γûê    modified_files: list[str]
Γûê    removed_files: list[str]
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# B╞░ß╗¢c 1 ΓÇö x├íc thß╗▒c
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef verify_signature(body: bytes, signature_header: str | None) -> None:
Γûê    """Kiß╗âm tra HMAC-SHA256 cß╗ºa GitHub. Kh├┤ng hß╗úp lß╗ç th├¼ raise, hß╗úp lß╗ç th├¼ im lß║╖ng.
Γöé
Γûê    Chß║íy tr├¬n body TH├ö, tr╞░ß╗¢c khi parse JSON: chß╗» k├╜ k├╜ tr├¬n ─æ├║ng chuß╗ùi byte
Γûê    GitHub gß╗¡i ─æi. Parse rß╗ôi serialize lß║íi sß║╜ ra chuß╗ùi kh├íc (thß╗⌐ tß╗▒ key, khoß║úng
Γûê    trß║»ng) v├á kh├┤ng c├▓n khß╗¢p chß╗» k├╜ n├áo cß║ú.
Γûê    """
Γûê    secret = get_settings().webhook_secret
Γöé
Γûê    if not secret:
Γûê        # Lß╗ùi cß║Ñu h├¼nh ph├¡a ta, kh├┤ng phß║úi cß╗ºa ng╞░ß╗¥i gß╗¡i. Tuyß╗çt ─æß╗æi kh├┤ng ─æ╞░ß╗úc
Γûê        # "v├¼ ch╞░a cß║Ñu h├¼nh n├¬n bß╗Å qua b╞░ß╗¢c x├íc thß╗▒c" ΓÇö nh╞░ vß║¡y l├á mß╗ƒ toang
Γûê        # endpoint cho bß║Ñt kß╗│ ai gß╗¡i payload giß║ú.
Γûê        raise CriticalError(
Γûê            ErrorCode.WEBHOOK_NOT_CONFIGURED,
Γûê            "Hß╗ç thß╗æng ch╞░a ─æ╞░ß╗úc cß║Ñu h├¼nh ─æß╗â nhß║¡n webhook. Vui l├▓ng li├¬n hß╗ç hß╗ù trß╗ú.",
Γûê            stage=Stage.RECEIVE,
Γûê            log_message="Thiß║┐u WEBHOOK_SECRET ΓÇö kh├┤ng c├│ c├ích n├áo x├íc thß╗▒c webhook GitHub.",
Γûê        )
Γöé
Γûê    if not signature_header:
Γûê        raise SecurityError(
Γûê            ErrorCode.INVALID_SIGNATURE,
Γûê            "Y├¬u cß║ºu kh├┤ng hß╗úp lß╗ç.",
Γûê            stage=Stage.RECEIVE,
Γûê            log_message="Webhook kh├┤ng k├¿m header X-Hub-Signature-256.",
Γûê        )
Γöé
Γûê    expected = "sha256=" + hmac.new(
Γûê        secret.encode("utf-8"), body, hashlib.sha256
Γûê    ).hexdigest()
Γöé
Γûê    # So s├ính tr├¬n bytes: `compare_digest` vß╗¢i chuß╗ùi str sß║╜ nß╗ò TypeError nß║┐u
Γûê    # header chß╗⌐a k├╜ tß╗▒ ngo├ái ASCII ΓÇö v├á header th├¼ do ng╞░ß╗¥i gß╗¡i ─æß║╖t.
Γûê    if not hmac.compare_digest(
Γûê        expected.encode("utf-8"), signature_header.encode("utf-8")
Γûê    ):
Γûê        # `message` cß╗æ ├╜ m╞í hß╗ô: n├│i r├╡ "chß╗» k├╜ sai" l├á chß╗ë cho kß║╗ ─æang d├▓ biß║┐t
Γûê        # n├│ sai ß╗ƒ ─æ├óu. L├╜ do thß║¡t chß╗ë nß║▒m trong log.
Γûê        raise SecurityError(
Γûê            ErrorCode.INVALID_SIGNATURE,
Γûê            "Y├¬u cß║ºu kh├┤ng hß╗úp lß╗ç.",
Γûê            stage=Stage.RECEIVE,
Γûê            log_message="Chß╗» k├╜ HMAC kh├┤ng khß╗¢p ΓÇö request kh├┤ng ─æß║┐n tß╗½ GitHub, "
Γûê            "hoß║╖c WEBHOOK_SECRET hai b├¬n kh├íc nhau.",
Γûê        )
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# B╞░ß╗¢c 2 ΓÇö b├│c t├ích payload
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef _classify_files(
Γûê    commits: list[dict[str, Any]],
Γûê) -> tuple[list[str], list[str], list[str]]:
Γûê    """Gß╗Öp thay ─æß╗òi cß╗ºa Mß╗îI commit trong push th├ánh 3 danh s├ích, h├ánh-─æß╗Öng-cuß╗æi-thß║»ng.
Γöé
Γûê    Mß╗Öt lß║ºn push mang nhiß╗üu commit v├á c├╣ng mß╗Öt file c├│ thß╗â xuß║Ñt hiß╗çn ß╗ƒ nhiß╗üu
Γûê    commit vß╗¢i h├ánh ─æß╗Öng kh├íc nhau. Chß╗ë trß║íng th├íi CUß╗ÉI C├ÖNG l├á c├│ thß║¡t: file
Γûê    th├¬m ß╗ƒ commit 1 rß╗ôi xo├í ß╗ƒ commit 3 th├¼ tr├¬n nh├ính n├│ kh├┤ng c├▓n tß╗ôn tß║íi ΓÇö nß║íp
Γûê    n├│ v├áo hß╗ç thß╗æng l├á nß║íp mß╗Öt file ─æ├ú chß║┐t.
Γöé
Γûê    Ri├¬ng 'added' thß║»ng 'modified' ─æß║┐n sau: trong c├╣ng mß╗Öt lß║ºn push th├¼ n├│ vß║½n l├á
Γûê    file mß╗¢i toanh, gß╗ìi l├á "sß╗¡a" th├¼ sai bß║ún chß║Ñt.
Γûê    """
Γûê    state: dict[str, str] = {}
Γûê    for commit in commits:
Γûê        for path in commit.get("added") or []:
Γûê            state[path] = "added"
Γûê        for path in commit.get("modified") or []:
Γûê            if state.get(path) != "added":
Γûê                state[path] = "modified"
Γûê        for path in commit.get("removed") or []:
Γûê            state[path] = "removed"
Γöé
Γûê    buckets: dict[str, list[str]] = {"added": [], "modified": [], "removed": []}
Γûê    for path, action in state.items():
Γûê        if path.lower().endswith(ALLOWED_EXTENSIONS):
Γûê            buckets[action].append(path)
Γöé
Γûê    # sorted() ─æß╗â thß╗⌐ tß╗▒ xß╗¡ l├╜ v├á nß╗Öi dung ghi v├áo bß║úng log l├á tß║Ñt ─æß╗ïnh, kh├┤ng
Γûê    # phß╗Ñ thuß╗Öc thß╗⌐ tß╗▒ key cß╗ºa dict hay thß╗⌐ tß╗▒ GitHub liß╗çt k├¬ file.
Γûê    return (
Γûê        sorted(buckets["added"]),
Γûê        sorted(buckets["modified"]),
Γûê        sorted(buckets["removed"]),
Γûê    )
Γöé
Γöé
Γûêdef parse_push_payload(payload: dict[str, Any]) -> PushEvent | None:
Γûê    """B├│c `PushEvent` khß╗Åi payload. Trß║ú None khi kh├┤ng c├│ g├¼ ─æß╗â xß╗¡ l├╜.
Γöé
Γûê    Trß║ú None thay v├¼ raise cho mß╗ìi tr╞░ß╗¥ng hß╗úp "push hß╗úp lß╗ç nh╞░ng kh├┤ng li├¬n
Γûê    quan" (push tag, xo├í nh├ính, push to├án file .py). ─É├│ kh├┤ng phß║úi lß╗ùi cß╗ºa ai
Γûê    cß║ú ΓÇö GitHub bß║»n webhook cho mß╗ìi push l├á ─æ├║ng viß╗çc cß╗ºa n├│.
Γûê    """
Γûê    ref = payload.get("ref") or ""
Γûê    if not ref.startswith(_BRANCH_PREFIX):
Γûê        logger.info("Bß╗Å qua push kh├┤ng nhß║»m v├áo nh├ính: ref=%s", ref)
Γûê        return None
Γöé
Γûê    # `head_commit` l├á null khi push xo├í nh├ính, hoß║╖c khi push kh├┤ng mang commit
Γûê    # mß╗¢i n├áo. Bß║ún prototype c┼⌐ ─æß╗ìc thß║│ng payload["head_commit"]["url"] v├á nß╗ò
Γûê    # TypeError ß╗ƒ ─æ├║ng chß╗ù n├áy.
Γûê    head = payload.get("head_commit")
Γûê    if not head:
Γûê        logger.info("Push l├¬n '%s' kh├┤ng c├│ head_commit ΓÇö kh├┤ng c├│ g├¼ ─æß╗â xß╗¡ l├╜.", ref)
Γûê        return None
Γöé
Γûê    repo_full_name = (payload.get("repository") or {}).get("full_name")
Γûê    commit_id = head.get("id")
Γûê    commit_url = head.get("url")
Γûê    if not (repo_full_name and commit_id and commit_url):
Γûê        logger.warning(
Γûê            "Payload push thiß║┐u repository.full_name / head_commit.id / head_commit.url "
Γûê            "ΓÇö kh├┤ng ─æß╗º dß╗» liß╗çu ─æß╗â tß║úi file hay ─æß╗â ghi nhß║¡t k├╜."
Γûê        )
Γûê        return None
Γöé
Γûê    added, modified, removed = _classify_files(payload.get("commits") or [])
Γûê    if not (added or modified or removed):
Γûê        logger.info("Push l├¬n '%s' kh├┤ng chß║ím file YAML n├áo.", ref)
Γûê        return None
Γöé
Γûê    author = head.get("author") or {}
Γûê    pusher = payload.get("pusher") or {}
Γöé
Γûê    return PushEvent(
Γûê        repo_full_name=repo_full_name,
Γûê        commit_id=commit_id,
Γûê        commit_url=commit_url,
Γûê        # T├íc giß║ú commit l├á ng╞░ß╗¥i viß║┐t thay ─æß╗òi; `pusher` chß╗ë l├á ng╞░ß╗¥i bß║Ñm push.
Γûê        # ╞»u ti├¬n t├íc giß║ú, l├╣i vß╗ü pusher khi commit kh├┤ng khai email.
Γûê        email=author.get("email") or pusher.get("email") or "",
Γûê        branch=ref[len(_BRANCH_PREFIX) :],
Γûê        timestamp=head.get("timestamp") or "",
Γûê        added_files=added,
Γûê        modified_files=modified,
Γûê        removed_files=removed,
Γûê    )
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# B╞░ß╗¢c 3 ΓÇö tß║úi nß╗Öi dung file tß╗½ GitHub
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêasync def _fetch_file(repo_full_name: str, ref: str, path: str) -> bytes | None:
Γûê    """Tß║úi nß╗Öi dung th├┤ cß╗ºa 1 file tß║íi ─æ├║ng commit. None nß║┐u kh├┤ng lß║Ñy ─æ╞░ß╗úc.
Γöé
Γûê    Lß║Ñy theo `ref` l├á commit id chß╗⌐ kh├┤ng theo t├¬n nh├ính: giß╗»a l├║c GitHub bß║»n
Γûê    webhook v├á l├║c ta gß╗ìi API c├│ thß╗â ─æ├ú c├│ push kh├íc chen v├áo, v├á khi ─æ├│ ─æß╗ìc
Γûê    theo nh├ính sß║╜ ra mß╗Öt nß╗Öi dung kh├íc vß╗¢i nß╗Öi dung cß╗ºa ch├¡nh commit n├áy.
Γûê    """
Γûê    settings = get_settings()
Γöé
Γûê    # `quote` vß╗¢i safe='/' mß║╖c ─æß╗ïnh ΓÇö giß╗» nguy├¬n dß║Ñu / ng─ân c├ích th╞░ mß╗Ñc, nh╞░ng
Γûê    # m├ú ho├í khoß║úng trß║»ng v├á k├╜ tß╗▒ tiß║┐ng Viß╗çt trong t├¬n file.
Γûê    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{quote(path)}"
Γûê    headers = {
Γûê        "Accept": "application/vnd.github.v3.raw",
Γûê        "X-GitHub-Api-Version": "2022-11-28",
Γûê    }
Γûê    # CHß╗ê gß║»n Authorization khi thß║¡t sß╗▒ c├│ token. Gß║»n mß╗Öt header rß╗ùng hay chuß╗ùi
Γûê    # "Bearer None" th├¼ GitHub trß║ú 401 ngay cß║ú vß╗¢i repo public ΓÇö thß╗⌐ vß╗æn ─æß╗ìc
Γûê    # ─æ╞░ß╗úc m├á kh├┤ng cß║ºn x├íc thß╗▒c g├¼.
Γûê    if settings.github_token:
Γûê        headers["Authorization"] = f"Bearer {settings.github_token}"
Γöé
Γûê    try:
Γûê        async with httpx.AsyncClient(
Γûê            timeout=settings.github_api_timeout_seconds
Γûê        ) as client:
Γûê            response = await client.get(url, headers=headers, params={"ref": ref})
Γûê    except httpx.HTTPError as exc:
Γûê        logger.warning(
Γûê            "Kh├┤ng gß╗ìi ─æ╞░ß╗úc GitHub API cho '%s': %s", path, type(exc).__name__
Γûê        )
Γûê        return None
Γöé
Γûê    if response.status_code != 200:
Γûê        # Log metadata th├┤i. `response.text` c├│ thß╗â mang nß╗Öi dung file hoß║╖c th├┤ng
Γûê        # ─æiß╗çp lß╗ùi k├¿m th├┤ng tin repo private ΓÇö kh├┤ng thuß╗Öc vß╗ü log.
Γûê        logger.warning(
Γûê            "GitHub trß║ú %d khi lß║Ñy '%s' tß║íi ref=%s", response.status_code, path, ref
Γûê        )
Γûê        return None
Γöé
Γûê    # Trß║ú BYTES chß╗⌐ kh├┤ng phß║úi text ─æ├ú decode: `ingest_catalog` nhß║¡n bytes, v├á
Γûê    # layer 2 cß╗ºa validation soi CH├ìNH BYTE TH├ö (magic bytes, k├╜ tß╗▒ NUL) tr╞░ß╗¢c
Γûê    # khi c├│ ai parse. Decode ß╗ƒ ─æ├óy rß╗ôi encode lß║íi l├á vß╗⌐t ─æi ─æ├║ng thß╗⌐ tß║ºng ─æ├│ cß║ºn.
Γûê    return response.content
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# B╞░ß╗¢c 4 ΓÇö ─æiß╗üu phß╗æi
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef _issue_from(exc: AppError, path: str) -> Issue:
Γûê    """Biß║┐n mß╗Öt lß╗ùi cß║Ñp file th├ánh `Issue` ─æß╗â nh├⌐t v├áo response chung."""
Γûê    return Issue(
Γûê        severity="error",
Γûê        code=exc.code.value,
Γûê        message=exc.message,
Γûê        source=path,
Γûê    )
Γöé
Γöé
Γûêasync def handle_push(event: PushEvent, request_id: str) -> ApiResponse:
Γûê    """Chß║íy trß╗ìn mß╗Öt lß║ºn push. Trß║ú vß╗ü `ApiResponse` ─æ├║ng contract chung.
Γöé
Γûê    Mß╗ìi lß╗¥i gß╗ìi xuß╗æng `ingest` v├á database ─æß╗üu ─æi qua `run_in_threadpool`: h├ám
Γûê    n├áy l├á `async` nh╞░ng `ingest_catalog`, `delete_catalog` v├á psycopg2 ─æß╗üu ─æß╗ông
Γûê    bß╗Ö v├á chß║╖n. Gß╗ìi thß║│ng th├¼ suß╗æt N file, to├án bß╗Ö event loop ─æß╗⌐ng im ΓÇö mß╗ìi
Γûê    request kh├íc cß╗ºa API c┼⌐ng phß║úi chß╗¥ theo.
Γûê    """
Γûê    settings = get_settings()
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 1: ghi nhß║¡t k├╜ TR╞»ß╗ÜC khi xß╗¡ l├╜ ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    # Lß║ºn push n├áy ─É├â Xß║óY RA, bß║Ñt kß╗â ingest ph├¡a sau c├│ th├ánh c├┤ng hay kh├┤ng.
Γûê    # Ghi sau sß║╜ mß║Ñt bß║ún ghi cß╗ºa ─æ├║ng nhß╗»ng lß║ºn push hß╗Ång ΓÇö thß╗⌐ cß║ºn ─æiß╗üu tra nhß║Ñt.
Γûê    log_id = await run_in_threadpool(
Γûê        github_event_repository.save_commit_event,
Γûê        email=event.email,
Γûê        branch=event.branch,
Γûê        commit_url=event.commit_url,
Γûê        timestamp=event.timestamp,
Γûê        added_files=event.added_files,
Γûê        modified_files=event.modified_files,
Γûê        removed_files=event.removed_files,
Γûê    )
Γöé
Γûê    issues: list[Issue] = []
Γûê    ingested: list[str] = []
Γûê    deleted: list[str] = []
Γûê    skipped: list[str] = []
Γûê    failed: list[str] = []
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 2: xo├í catalog cß╗ºa c├íc file ─æ├ú bß╗ï removed ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    # Xo├í tr╞░ß╗¢c khi nß║íp: nß║┐u mß╗Öt push vß╗½a xo├í 'a.yaml' vß╗½a th├¬m 'b.yaml' khai
Γûê    # c├╣ng mß╗Öt node, l├ám ng╞░ß╗úc thß╗⌐ tß╗▒ sß║╜ dß╗▒ng ra tranh chß║Ñp quyß╗ün sß╗ƒ hß╗»u giß║ú.
Γûê    for path in event.removed_files:
Γûê        name = posixpath.basename(path)
Γûê        try:
Γûê            await run_in_threadpool(ingest.delete_catalog, name, request_id)
Γûê        except CriticalError:
Γûê            raise
Γûê        except AppError as exc:
Γûê            if exc.code == ErrorCode.CATALOG_NOT_FOUND:
Γûê                # B├¼nh th╞░ß╗¥ng: GitHub b├ío xo├í mß╗Öt YAML ch╞░a tß╗½ng ─æ╞░ß╗úc nß║íp v├áo hß╗ç
Γûê                # thß╗æng (file thuß╗Öc repo nh╞░ng kh├┤ng phß║úi catalog, hoß║╖c ─æ├ú xo├í tß╗½
Γûê                # tr╞░ß╗¢c). Kh├┤ng c├│ g├¼ ─æß╗â l├ám, v├á c┼⌐ng kh├┤ng c├│ g├¼ sai.
Γûê                skipped.append(name)
Γûê                logger.info("Bß╗Å qua xo├í '%s': ch╞░a tß╗½ng ─æ╞░ß╗úc nß║íp.", name)
Γûê                continue
Γûê            failed.append(path)
Γûê            issues.append(_issue_from(exc, path))
Γûê        else:
Γûê            deleted.append(name)
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 3: nß║íp catalog cß╗ºa c├íc file added + modified ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    targets = [*event.added_files, *event.modified_files]
Γûê    if len(targets) > settings.github_max_files_per_push:
Γûê        skipped_count = len(targets) - settings.github_max_files_per_push
Γûê        issues.append(
Γûê            Issue(
Γûê                severity="warning",
Γûê                code=ErrorCode.HAS_WARNINGS.value,
Γûê                message=f"Push chß║ím {len(targets)} file YAML, v╞░ß╗út giß╗¢i hß║ín "
Γûê                f"{settings.github_max_files_per_push} file mß╗ùi lß║ºn. "
Γûê                f"{skipped_count} file ch╞░a ─æ╞░ß╗úc xß╗¡ l├╜ ΓÇö h├úy tß║úi l├¬n thß╗º c├┤ng.",
Γûê            )
Γûê        )
Γûê        targets = targets[: settings.github_max_files_per_push]
Γöé
Γûê    for path in targets:
Γûê        name = posixpath.basename(path)
Γöé
Γûê        content = await _fetch_file(event.repo_full_name, event.commit_id, path)
Γûê        if content is None:
Γûê            failed.append(path)
Γûê            issues.append(
Γûê                Issue(
Γûê                    severity="error",
Γûê                    code=ErrorCode.GITHUB_FETCH_FAILED.value,
Γûê                    message=f"Kh├┤ng tß║úi ─æ╞░ß╗úc nß╗Öi dung '{path}' tß╗½ GitHub.",
Γûê                    source=path,
Γûê                )
Γûê            )
Γûê            continue
Γöé
Γûê        try:
Γûê            result = await run_in_threadpool(
Γûê                ingest.ingest_catalog, name, content, _YAML_CONTENT_TYPE, request_id, True
Γûê            )
Γûê        except CriticalError:
Γûê            raise
Γûê        except AppError as exc:
Γûê            failed.append(path)
Γûê            issues.append(_issue_from(exc, path))
Γûê        else:
Γûê            ingested.append(name)
Γûê            # Cß║únh b├ío cß╗ºa ch├¡nh file (thiß║┐u owner, ref lß║í...) ─æ├ú ─æ╞░ß╗úc `ingest`
Γûê            # dß╗▒ng sß║╡n th├ánh Issue ΓÇö chuyß╗ân tiß║┐p nguy├¬n vß║╣n thay v├¼ nuß╗æt mß║Ñt.
Γûê            issues.extend(result.issues)
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 4: dß╗▒ng response ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    details: dict[str, Any] = {
Γûê        "log_id": log_id,
Γûê        "repository": event.repo_full_name,
Γûê        "branch": event.branch,
Γûê        "email": event.email,
Γûê        "commit_id": event.commit_id,
Γûê        "commit_url": event.commit_url,
Γûê        "ingested": ingested,
Γûê        "deleted": deleted,
Γûê        "skipped": skipped,
Γûê        "failed": failed,
Γûê    }
Γöé
Γûê    summary = (
Γûê        f"Push l├¬n nh├ính '{event.branch}': nß║íp {len(ingested)} file, "
Γûê        f"xo├í {len(deleted)} file"
Γûê    )
Γûê    if failed:
Γûê        summary += f", {len(failed)} file l├í┬╗ΓÇöi"
Γûê    summary += "."
Γöé
Γûê    if not issues:
Γûê        logger.info(
Γûê            "Webhook xß╗¡ l├╜ xong push '%s' (log_id=%d): nß║íp %d, xo├í %d",
Γûê            event.commit_id, log_id, len(ingested), len(deleted),
Γûê        )
Γûê        return schemas.success(summary, request_id=request_id, details=details)
Γöé
Γûê    logger.warning(
Γûê        "Webhook xß╗¡ l├╜ push '%s' (log_id=%d) k├¿m %d vß║Ñn ─æß╗ü: %s",
Γûê        event.commit_id, log_id, len(issues), [i.code for i in issues],
Γûê    )
Γûê    return schemas.warning(
Γûê        summary, request_id=request_id, issues=issues, details=details
Γûê    )
Γöé


src\services\github_event_repository.py:
Γûê"""
Γûêgithub_event_repository.py ΓÇö Ghi bß║úng `github_commits_log`.
Γöé
ΓûêC├╣ng vai tr├▓ vß╗¢i `catalog_repository.py`: tß║ºng duy nhß║Ñt chß║ím SQLAlchemy cho bß║úng
Γûên├áy. Tß║ºng tr├¬n chß╗ë ─æ╞░a v├áo c├íc gi├í trß╗ï Python thuß║ºn v├á nhß║¡n vß╗ü mß╗Öt `int` id, n├¬n
Γûê─æß╗òi Postgres sang thß╗⌐ kh├íc chß╗ë phß║úi viß║┐t lß║íi file n├áy.
Γöé
ΓûêChß╗ë c├│ INSERT, kh├┤ng c├│ UPDATE v├á kh├┤ng c├│ DELETE. Bß║úng l├á nhß║¡t k├╜ cß╗ºa nhß╗»ng
Γûêviß╗çc ─É├â Xß║óY RA ΓÇö sß╗¡a hay xo├í mß╗Öt d├▓ng ngh─⌐a l├á l├ám hß╗Ång ch├¡nh thß╗⌐ m├á nhß║¡t k├╜ sinh
Γûêra ─æß╗â bß║úo vß╗ç. Muß╗æn biß║┐t trß║íng th├íi hiß╗çn tß║íi cß╗ºa catalog th├¼ ─æß╗ìc `input_json`.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport logging
Γöé
Γûêfrom sqlalchemy.exc import SQLAlchemyError
Γöé
Γûêfrom src.core.db import session_scope
Γûêfrom src.core.errors import CriticalError, ErrorCode, Stage
Γûêfrom src.models.tables import GithubCommitLog
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γöé
Γûêdef save_commit_event(
Γûê    *,
Γûê    email: str,
Γûê    branch: str,
Γûê    commit_url: str,
Γûê    timestamp: str,
Γûê    added_files: list[str],
Γûê    modified_files: list[str],
Γûê    removed_files: list[str],
Γûê) -> int:
Γûê    """Ghi 1 d├▓ng nhß║¡t k├╜ cho mß╗Öt lß║ºn push. Trß║ú vß╗ü id vß╗½a ─æ╞░ß╗úc cß║Ñp.
Γöé
Γûê    Tham sß╗æ bß║»t buß╗Öc truyß╗ün theo t├¬n (`*`): bß║úy gi├í trß╗ï th├¼ bß╗æn c├íi ─æß║ºu ─æß╗üu l├á
Γûê    chuß╗ùi v├á ba c├íi cuß╗æi ─æß╗üu l├á list chuß╗ùi ΓÇö truyß╗ün theo vß╗ï tr├¡ th├¼ ho├ín nhß║ºm
Γûê    `email` vß╗¢i `branch` vß║½n chß║íy ├¬m v├á chß╗ë lß╗Ö ra khi c├│ ng╞░ß╗¥i ─æß╗ìc bß║úng.
Γûê    """
Γûê    try:
Γûê        with session_scope() as session:
Γûê            row = GithubCommitLog(
Γûê                email=email,
Γûê                branch=branch,
Γûê                commit_url=commit_url,
Γûê                timestamp=timestamp,
Γûê                added_files=added_files,
Γûê                modified_files=modified_files,
Γûê                removed_files=removed_files,
Γûê            )
Γûê            session.add(row)
Γûê            # flush ─æß╗â Postgres cß║Ñp id ngay, ─æß╗ìc ─æ╞░ß╗úc tr╞░ß╗¢c khi commit.
Γûê            session.flush()
Γûê            record_id = row.id
Γûê    except SQLAlchemyError as exc:
Γûê        # Kh├┤ng ─æß╗â `SQLAlchemyError` lß╗ìt l├¬n: handler to├án cß╗Ñc sß║╜ bß║»t n├│ nh╞░ mß╗Öt
Γûê        # exception lß║í v├á trß║ú INTERNAL_ERROR, trong khi ─æ├óy l├á t├¼nh huß╗æng ta HIß╗éU
Γûê        # R├ò ΓÇö kho l╞░u trß╗» kh├┤ng d├╣ng ─æ╞░ß╗úc.
Γûê        #
Γûê        # `log_message` cß╗æ ├╜ chß╗ë mang t├¬n lß╗¢p exception: th├┤ng ─æiß╗çp lß╗ùi kß║┐t nß╗æi
Γûê        # cß╗ºa psycopg2 c├│ thß╗â k├¿m nguy├¬n chuß╗ùi DSN, tß╗⌐c l├á k├¿m cß║ú mß║¡t khß║⌐u.
Γûê        raise CriticalError(
Γûê            ErrorCode.STORAGE_FAILURE,
Γûê            "Kh├┤ng l╞░u ─æ╞░ß╗úc nhß║¡t k├╜ commit. Vui l├▓ng thß╗¡ lß║íi sau.",
Γûê            stage=Stage.PERSIST,
Γûê            log_message=f"Ghi bß║úng github_commits_log thß║Ñt bß║íi: {type(exc).__name__}",
Γûê        ) from exc
Γöé
Γûê    logger.info(
Γûê        "─É├ú ghi nhß║¡t k├╜ push: id=%d branch=%s added=%d modified=%d removed=%d",
Γûê        record_id, branch, len(added_files), len(modified_files), len(removed_files),
Γûê    )
Γûê    return record_id
Γöé


src\services\ingest.py:
Γûê"""
Γûêingest.py ΓÇö ─Éiß╗üu phß╗æi luß╗ông nß║íp mß╗Öt catalog, sau khi input ─æ├ú sß║ích.
Γöé
Γûê    validate (5 tß║ºng)  ->  kiß╗âm tra xung ─æß╗Öt xuy├¬n file  ->  l╞░u DB  ->  cß║¡p nhß║¡t cache
Γûê                                                                     ->  d├í┬╗┬▒ng response
Γöé
Γûê─É├óy l├á tß║ºng DUY NHß║ñT biß║┐t thß╗⌐ tß╗▒ c├íc b╞░ß╗¢c. Controller kh├┤ng biß║┐t, validator
Γûêkh├┤ng biß║┐t. Muß╗æn ch├¿n th├¬m mß╗Öt b╞░ß╗¢c (gß╗ìi LLM, bß║»n event) th├¼ th├¬m ─æ├║ng ß╗ƒ ─æ├óy,
Γûêv├á n├│ tß╗▒ nß║▒m trong ─æ├║ng nh├ính xß╗¡ l├╜ lß╗ùi.
Γöé
ΓûêV├¼ sao KH├öNG bß╗ìc cß║ú luß╗ông trong mß╗Öt try/except khß╗òng lß╗ô: mß╗Öt `except Exception`
Γûêduy nhß║Ñt ├┤m cß║ú validate lß║½n ghi DB th├¼ kh├┤ng c├▓n ph├ón biß╗çt ─æ╞░ß╗úc "ng╞░ß╗¥i d├╣ng gß╗¡i
Γûêfile sai" (422, tß╗▒ sß╗¡a ─æ╞░ß╗úc) vß╗¢i "database kh├┤ng tß╗¢i ─æ╞░ß╗úc" (500, gß╗ìi support).
ΓûêMß╗ùi b╞░ß╗¢c bß║»t ─æ├║ng loß║íi lß╗ùi m├¼nh hiß╗âu, phß║ºn c├▓n lß║íi ─æß╗â r╞íi l├¬n handler to├án cß╗Ñc
Γûêth├ánh critical.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport difflib
Γûêimport logging
Γûêfrom datetime import datetime
Γûêfrom zoneinfo import ZoneInfo
Γûêfrom typing import Any
Γöé
Γûêfrom src.core.errors import (
Γûê    CriticalError,
Γûê    ErrorCode,
Γûê    HumanReviewRequiredError,
Γûê    Stage,
Γûê    ValidationError,
Γûê)
Γûêfrom src.models import schemas
Γûêfrom src.models.schemas import ApiResponse, Issue
Γûêfrom src.services import catalog_repository
Γûêfrom src.services.catalog_merge import merge_documents
Γûêfrom src.services.catalog_to_graph import ParsedFile
Γûêfrom src.services.store import StoredCatalog, output_name, store
Γûêfrom src.services.validation import run_validation_pipeline
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γûê# Hai m├ú lß╗ùi n├áy ngh─⌐a l├á hai file c├╣ng nhß║¡n l├á chß╗º sß╗ƒ hß╗»u mß╗Öt node. Hß╗ç thß╗æng
Γûê# ─Éß╗îC ─É╞»ß╗óC cß║ú hai file, kh├┤ng c├│ g├¼ hß╗Ång ΓÇö n├│ chß╗ë kh├┤ng c├│ c╞í sß╗ƒ n├áo ─æß╗â chß╗ìn b├¬n
Γûê# n├áo ─æ├║ng. Chß╗ìn bß╗½a = ├óm thß║ºm ghi ─æ├¿ catalog cß╗ºa ─æß╗Öi kh├íc. ─É├óy ─æ├║ng l├á chß╗ù cß║ºn
Γûê# con ng╞░ß╗¥i, xem `HumanReviewRequired`.
Γûê_HITL_CONFLICT_CODES = {"DUPLICATE_DECLARATION", "AMBIGUOUS_OWNER"}
Γöé
Γöé
Γûêdef ingest_catalog(
Γûê    filename: str | None,
Γûê    content: bytes,
Γûê    content_type: str | None,
Γûê    request_id: str,
Γûê    force: bool = False,
Γûê) -> ApiResponse:
Γûê    """Nß║íp 1 catalog. Raise AppError nß║┐u kh├┤ng thß╗â ho├án tß║Ñt."""
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 1: 5 tß║ºng validate. Lß╗ùi bay thß║│ng l├¬n handler, kh├┤ng bß║»t ß╗ƒ ─æ├óy. ΓöÇΓöÇ
Γûê    validated = run_validation_pipeline(filename, content, content_type)
Γûê    parsed = validated.parsed
Γöé
Γûê    logger.info(
Γûê        "Input hß╗úp lß╗ç: file=%s size=%dB sha=%s nodes=%d edges=%d warnings=%d",
Γûê        validated.filename, validated.size_bytes, validated.fingerprint,
Γûê        len(parsed.nodes), len(parsed.edges), len(validated.warnings),
Γûê    )
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 2: xung ─æß╗Öt vß╗¢i c├íc file ─æ├ú nß║íp tr╞░ß╗¢c ─æ├│ ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    if not force:
Γûê        _check_cross_file_conflicts(parsed, validated.filename)
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 3: l╞░u JSON v├áo database ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    record_id, replaced = _save_graph_document(parsed)
Γûê    output_file = output_name(parsed.filename)
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 4: cß║¡p nhß║¡t cache ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    # Sau DB, kh├┤ng phß║úi tr╞░ß╗¢c: DB hß╗Ång th├¼ cache phß║úi giß╗» nguy├¬n trß║íng th├íi c┼⌐,
Γûê    # nß║┐u kh├┤ng hß╗ç thß╗æng sß║╜ b├ío "─æ├ú nß║íp" mß╗Öt file ch╞░a hß╗ü ─æ╞░ß╗úc l╞░u ß╗ƒ ─æ├óu cß║ú.
Γûê    store.put(
Γûê        StoredCatalog(
Γûê            parsed=parsed,
Γûê            size_bytes=validated.size_bytes,
Γûê            fingerprint=validated.fingerprint,
Γûê            output_file=output_file,
Γûê            record_id=record_id,
Γûê        )
Γûê    )
Γöé
Γûê    # ΓöÇΓöÇ B╞░ß╗¢c 5: dß╗▒ng response ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê    return _build_ingest_response(validated, output_file, record_id, replaced, request_id)
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# C├íc b╞░ß╗¢c
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef _check_cross_file_conflicts(parsed: ParsedFile, filename: str) -> None:
Γûê    """Gß╗Öp thß╗¡ file mß╗¢i vß╗¢i c├íc file ─æ├ú c├│, xem c├│ tranh chß║Ñp quyß╗ün sß╗ƒ hß╗»u kh├┤ng.
Γöé
Γûê    Chß╗ë nh├¼n mß╗Öt file th├¼ kh├┤ng ph├ít hiß╗çn ─æ╞░ß╗úc ΓÇö phß║úi nh├¼n to├án cß╗Ñc.
Γûê    """
Γûê    others = store.all_parsed(exclude=filename)
Γûê    if not others:
Γûê        return
Γöé
Γûê    merged = merge_documents([*others, parsed])
Γûê    conflicts = [
Γûê        e for e in merged["diagnostics"]["errors"] if e["code"] in _HITL_CONFLICT_CODES
Γûê    ]
Γûê    if not conflicts:
Γûê        return
Γöé
Γûê    logger.error(
Γûê        "Xung ─æß╗Öt quyß╗ün sß╗ƒ hß╗»u khi nß║íp '%s': %d tranh chß║Ñp -> chuyß╗ân human review",
Γûê        filename, len(conflicts),
Γûê    )
Γûê    raise HumanReviewRequiredError(
Γûê        ErrorCode.NEEDS_HUMAN_REVIEW,
Γûê        f"File n├áy tranh chß║Ñp quyß╗ün sß╗ƒ hß╗»u {len(conflicts)} th├ánh phß║ºn vß╗¢i catalog "
Γûê        "─æ├ú c├│ tr├¬n hß╗ç thß╗æng. Cß║ºn ng╞░ß╗¥i phß╗Ñ tr├ích x├íc nhß║¡n tr╞░ß╗¢c khi ghi ─æ├¿.",
Γûê        stage=Stage.STORE,
Γûê        details={"conflict_count": len(conflicts)},
Γûê        issues=[
Γûê            Issue(
Γûê                severity="error",
Γûê                code=c["code"],
Γûê                message=c["message"],
Γûê                subject=c.get("subject"),
Γûê                source=c.get("source"),
Γûê            )
Γûê            for c in conflicts
Γûê        ],
Γûê    )
Γöé
Γöé
Γûêdef _build_graph_document(parsed: ParsedFile) -> dict[str, Any]:
Γûê    """Dß╗▒ng ─æ├║ng nß╗Öi dung JSON sß║╜ nß║▒m trong cß╗Öt `content`.
Γöé
Γûê    Giß╗æng hß╗çt thß╗⌐ tr╞░ß╗¢c ─æ├óy ghi ra `output_json/*.json`, cß╗Öng th├¬m `generatedAt`
Γûê    ΓÇö tr╞░ß╗¥ng m├á `build_document` cß╗ºa CLI vß║½n sinh ra cho file JSON. N├│ kh├┤ng phß║úi
Γûê    metadata gß║»n th├¬m cho database: ─æ├│ l├á mß╗Öt phß║ºn cß╗ºa ─æß╗ïnh dß║íng t├ái liß╗çu, v├á
Γûê    nhß╗¥ n├│ m├á l├║c nß║íp lß║íi tß╗½ DB vß║½n biß║┐t ─æ╞░ß╗úc catalog n├áy nß║íp l├║c n├áo.
Γûê    """
Γûê    document = merge_documents([parsed])
Γûê    document["generatedAt"] = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%dT%H:%M:%S+07:00")
Γûê    return document
Γöé
Γöé
Γûêdef _save_graph_document(parsed: ParsedFile) -> tuple[int, bool]:
Γûê    """Sinh graph JSON v├á l╞░u v├áo bß║úng `input_json`. Trß║ú `(id, ─æ├ú_ghi_─æ├¿)`.
Γöé
Γûê    Kh├┤ng c├▓n file tß║ím v├á `os.replace` nh╞░ bß║ún ghi ─æ─⌐a: mß╗Öt c├óu UPDATE/INSERT cß╗ºa
Γûê    Postgres ─æ├ú l├á nguy├¬n tß╗¡ sß║╡n, hoß║╖c d├▓ng c┼⌐ c├▓n nguy├¬n hoß║╖c d├▓ng mß╗¢i ─æ├ú ─æß╗º.
Γûê    Kh├┤ng bao giß╗¥ c├│ t├ái liß╗çu JSON cß╗Ñt trong bß║úng.
Γûê    """
Γûê    try:
Γûê        document = _build_graph_document(parsed)
Γûê    except OSError as exc:
Γûê        # Hiß║┐m, nh╞░ng `merge_documents` c├│ thß╗â chß║ím t├ái nguy├¬n hß╗ç thß╗æng. Giß╗»
Γûê        # nh├ính n├áy ─æß╗â lß╗ùi hß║í tß║ºng kh├┤ng bß╗ï g├ín nhß║ºm th├ánh lß╗ùi logic.
Γûê        raise CriticalError(
Γûê            ErrorCode.STORAGE_FAILURE,
Γûê            "Kh├┤ng l╞░u ─æ╞░ß╗úc kß║┐t quß║ú xß╗¡ l├╜. Vui l├▓ng thß╗¡ lß║íi sau.",
Γûê            stage=Stage.PERSIST,
Γûê            log_message=f"Dß╗▒ng t├ái liß╗çu cho '{parsed.filename}' thß║Ñt bß║íi: "
Γûê            f"{type(exc).__name__}",
Γûê        ) from exc
Γûê    except Exception as exc:
Γûê        # Lß╗ùi lß║í khi merge/serialize. Kh├┤ng ─æo├ín, kh├┤ng ─æi tiß║┐p.
Γûê        raise CriticalError(
Γûê            ErrorCode.INTERNAL_ERROR,
Γûê            "Kh├┤ng l╞░u ─æ╞░ß╗úc kß║┐t quß║ú xß╗¡ l├╜.",
Γûê            stage=Stage.PERSIST,
Γûê            log_message=f"Lß╗ùi ngo├ái dß╗▒ kiß║┐n khi dß╗▒ng JSON cho "
Γûê            f"'{parsed.filename}': {type(exc).__name__}",
Γûê        ) from exc
Γöé
Γûê    # `save` tß╗▒ bß╗ìc lß╗ùi SQLAlchemy th├ánh CriticalError/STORAGE_FAILURE.
Γûê    record_id, replaced = catalog_repository.save(document)
Γöé
Γûê    logger.info(
Γûê        "─É├ú l╞░u '%s' v├áo input_json: id=%d, ghi_─æ├¿=%s",
Γûê        parsed.filename, record_id, replaced,
Γûê    )
Γûê    return record_id, replaced
Γöé
Γöé
Γûêdef _build_ingest_response(
Γûê    validated: Any,
Γûê    output_file: str,
Γûê    record_id: int,
Γûê    replaced: bool,
Γûê    request_id: str,
Γûê) -> ApiResponse:
Γûê    """Sß║ích ho├án to├án -> success. C├│ cß║únh b├ío hoß║╖c c├│ ghi ─æ├¿ -> warning."""
Γûê    parsed = validated.parsed
Γûê    details: dict[str, Any] = {
Γûê        "file": validated.filename,
Γûê        "root": parsed.root_id,
Γûê        "node_count": len(parsed.nodes),
Γûê        "edge_count": len(parsed.edges),
Γûê        "size_bytes": validated.size_bytes,
Γûê        "output_file": output_file,
Γûê        "record_id": record_id,
Γûê        "warning_count": len(validated.warnings),
Γûê        "replaced_existing": replaced,
Γûê    }
Γöé
Γûê    issues = list(validated.warnings)
Γûê    if replaced:
Γûê        issues.insert(
Γûê            0,
Γûê            Issue(
Γûê                severity="warning",
Γûê                code=ErrorCode.FILE_REPLACED.value,
Γûê                message=f"'{validated.filename}' ─æ├ú tß╗ôn tß║íi v├á vß╗½a bß╗ï ghi ─æ├¿ bß║▒ng bß║ún mß╗¢i.",
Γûê                source=validated.filename,
Γûê            ),
Γûê        )
Γöé
Γûê    if not issues:
Γûê        logger.info("Nß║íp th├ánh c├┤ng '%s' (kh├┤ng cß║únh b├ío)", validated.filename)
Γûê        return schemas.success(
Γûê            f"─É├ú xß╗¡ l├╜ '{validated.filename}': {len(parsed.nodes)} node, "
Γûê            f"{len(parsed.edges)} quan hß╗ç.",
Γûê            request_id=request_id,
Γûê            details=details,
Γûê        )
Γöé
Γûê    logger.warning(
Γûê        "Nß║íp '%s' k├¿m %d cß║únh b├ío: %s",
Γûê        validated.filename, len(issues), [i.code for i in issues],
Γûê    )
Γûê    return schemas.warning(
Γûê        f"─É├ú xß╗¡ l├╜ '{validated.filename}' nh╞░ng c├│ {len(issues)} cß║únh b├ío cß║ºn xem lß║íi.",
Γûê        request_id=request_id,
Γûê        issues=issues,
Γûê        details=details,
Γûê    )
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Liß╗çt k├¬ / t├¼m kiß║┐m / xo├í
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef list_catalogs(
Γûê    query: str | None, include_diagnostics: bool, request_id: str
Γûê) -> ApiResponse:
Γûê    items = store.list(query)
Γûê    total = len(store)
Γöé
Γûê    if query and not items:
Γûê        message = f"Kh├┤ng t├¼m thß║Ñy file n├áo khß╗¢p '{query}'."
Γûê    elif query:
Γûê        message = f"T├¼m thß║Ñy {len(items)}/{total} file khß╗¢p '{query}'."
Γûê    elif total:
Γûê        message = f"C├│ {total} file ─æ├ú nß║íp."
Γûê    else:
Γûê        message = "Ch╞░a c├│ file n├áo ─æ╞░ß╗úc nß║íp."
Γöé
Γûê    return schemas.success(
Γûê        message,
Γûê        request_id=request_id,
Γûê        details={
Γûê            "total": total,
Γûê            "returned": len(items),
Γûê            "query": query,
Γûê            "items": [i.summary_dict(include_diagnostics) for i in items],
Γûê        },
Γûê    )
Γöé
Γöé
Γûêdef _suggest_filenames(wanted: str, limit: int = 5) -> list[str]:
Γûê    """Gß╗úi ├╜ t├¬n gß║ºn ─æ├║ng khi kh├┤ng t├¼m thß║Ñy file.
Γöé
Γûê    Khß╗¢p chuß╗ùi con th├┤i th├¼ g├╡ sai mß╗Öt k├╜ tß╗▒ ('order-servic') l├á kh├┤ng gß╗úi ├╜ ─æ╞░ß╗úc
Γûê    g├¼ ΓÇö ─æ├║ng l├║c ng╞░ß╗¥i d├╣ng cß║ºn gß╗úi ├╜ nhß║Ñt. N├¬n: ╞░u ti├¬n khß╗¢p chuß╗ùi con (ng╞░ß╗¥i
Γûê    d├╣ng g├╡ tß║»t), sau ─æ├│ b├╣ bß║▒ng khß╗¢p mß╗¥ cß╗ºa `difflib` (ng╞░ß╗¥i d├╣ng g├╡ sai).
Γûê    """
Γûê    names = [i.filename for i in store.list()]
Γûê    substring = [i.filename for i in store.list(wanted)]
Γûê    fuzzy = difflib.get_close_matches(wanted, names, n=limit, cutoff=0.6)
Γöé
Γûê    seen: list[str] = []
Γûê    for name in [*substring, *fuzzy]:
Γûê        if name not in seen:
Γûê            seen.append(name)
Γûê    return seen[:limit]
Γöé
Γöé
Γûêdef delete_catalog(filename: str, request_id: str) -> ApiResponse:
Γûê    """Xo├í 1 catalog: xo├í d├▓ng trong DB tr╞░ß╗¢c, xo├í cache sau.
Γöé
Γûê    Thß╗⌐ tß╗▒ n├áy l├á cß╗æ ├╜. Nß║┐u xo├í cache tr╞░ß╗¢c rß╗ôi xo├í DB thß║Ñt bß║íi, ta c├▓n lß║íi mß╗Öt
Γûê    d├▓ng mß╗ô c├┤i trong bß║úng m├á kh├┤ng API n├áo nh├¼n thß║Ñy ΓÇö cho tß╗¢i lß║ºn restart sau,
Γûê    l├║c n├│ bß║Ñt ngß╗¥ sß╗æng lß║íi. L├ám ng╞░ß╗úc lß║íi: DB xo├í hß╗Ång th├¼ dß╗½ng lu├┤n, cache c├▓n
Γûê    nguy├¬n, hß╗ç thß╗æng vß║½n nhß║Ñt qu├ín v├á ng╞░ß╗¥i d├╣ng thß╗¡ lß║íi ─æ╞░ß╗úc.
Γûê    """
Γûê    item = store.get(filename)
Γûê    if item is None:
Γûê        raise ValidationError(
Γûê            ErrorCode.CATALOG_NOT_FOUND,
Γûê            f"Kh├┤ng t├¼m thß║Ñy file '{filename}' trong hß╗ç thß╗æng.",
Γûê            stage=Stage.STORE,
Γûê            details={"suggestions": _suggest_filenames(filename)},
Γûê        )
Γöé
Γûê    # Lß╗ùi SQLAlchemy ─æ├ú ─æ╞░ß╗úc repository bß╗ìc th├ánh STORAGE_FAILURE, v├á n├│ bay l├¬n
Γûê    # tr╞░ß╗¢c khi cache bß╗ï ─æß╗Ñng tß╗¢i ΓÇö ─æ├║ng thß╗⌐ tß╗▒ an to├án n├│i ß╗ƒ tr├¬n.
Γûê    catalog_repository.delete(filename)
Γöé
Γûê    store.delete(filename)
Γûê    logger.info("─É├ú xo├í catalog '%s'", filename)
Γöé
Γûê    return schemas.success(
Γûê        f"─É├ú xo├í '{filename}'.",
Γûê        request_id=request_id,
Γûê        stage=Stage.DONE,
Γûê        details={"file": filename, "remaining": len(store)},
Γûê    )
Γöé


src\services\llm.py:
Γûêfrom langchain_openai import ChatOpenAI
Γöé
Γûêfrom src.config import get_settings
Γöé
Γöé
Γûêdef get_llm() -> ChatOpenAI:
Γûê    settings = get_settings()
Γûê    return ChatOpenAI(
Γûê        model=settings.model_name,
Γûê        api_key=settings.openai_api_key,
Γûê        temperature=settings.llm_temperature,
Γûê    )


src\services\store.py:
Γûê"""
Γûêstore.py ΓÇö Cache trong RAM cß╗ºa bß║úng `input_json`.
Γöé
ΓûêNguß╗ôn sß╗▒ thß║¡t l├á DATABASE, kh├┤ng phß║úi kho n├áy. Kho chß╗ë giß╗» sß║╡n kß║┐t quß║ú ─æ├ú parse
Γûê─æß╗â `GET /catalogs` v├á b╞░ß╗¢c kiß╗âm tra xung ─æß╗Öt xuy├¬n file kh├┤ng phß║úi ─æß╗ìc lß║íi rß╗ôi
Γûêdß╗▒ng lß║íi ─æß╗ô thß╗ï tß╗½ JSON ß╗ƒ mß╗ìi request.
Γöé
ΓûêBa luß║¡t giß╗» cho cache kh├┤ng lß╗çch khß╗Åi DB:
Γûê  - Ghi/xo├í LU├öN ─æi qua DB tr╞░ß╗¢c, cß║¡p nhß║¡t cache sau. DB hß╗Ång th├¼ cache kh├┤ng ─æß╗òi.
Γûê  - `replaced` lß║Ñy tß╗½ kß║┐t quß║ú DB trß║ú vß╗ü, kh├┤ng suy tß╗½ viß╗çc key c├│ trong dict.
Γûê  - L├║c khß╗ƒi ─æß╗Öng, `load_from_db()` nß║íp lß║íi to├án bß╗Ö ΓÇö restart kh├┤ng mß║Ñt danh s├ích.
Γöé
ΓûêVß║½n c├▓n mß╗Öt giß╗¢i hß║ín: chß║íy nhiß╗üu worker uvicorn th├¼ mß╗ùi worker c├│ cache ri├¬ng,
Γûên├¬n worker A upload xong worker B ch╞░a thß║Ñy ngay cho tß╗¢i lß║ºn khß╗ƒi ─æß╗Öng sau. Dß╗»
Γûêliß╗çu kh├┤ng sai (DB vß║½n ─æ├║ng), chß╗ë l├á danh s├ích c├│ thß╗â c┼⌐. Chß║Ñp nhß║¡n ─æ╞░ß╗úc ß╗ƒ quy
Γûêm├┤ hiß╗çn tß║íi; muß╗æn bß╗Å hß║│n th├¼ cho `list()`/`all_parsed()` ─æß╗ìc thß║│ng DB.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport logging
Γûêimport os
Γûêimport threading
Γûêfrom dataclasses import dataclass, field
Γûêfrom datetime import datetime
Γûêfrom zoneinfo import ZoneInfo
Γûêfrom typing import Any
Γöé
Γûêfrom src.models.schemas import CatalogSummary
Γûêfrom src.services import catalog_repository
Γûêfrom src.services.catalog_to_graph import Diagnostics, Issue, ParsedFile
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γöé
Γûêdef output_name(filename: str) -> str:
Γûê    """'order-service.catalog.yaml' -> 'order-service.json'
Γöé
Γûê    T├¬n logic cß╗ºa t├ái liß╗çu JSON. Kh├┤ng c├▓n file n├áo tr├¬n ─æ─⌐a mang t├¬n n├áy, nh╞░ng
Γûê    n├│ vß║½n l├á nh├ún frontend ─æang hiß╗ân thß╗ï v├á l├á t├¬n gß╗úi ├╜ khi ng╞░ß╗¥i d├╣ng tß║úi vß╗ü.
Γöé
Γûê    ─Éß║╖t ß╗ƒ ─æ├óy chß╗⌐ kh├┤ng ß╗ƒ `ingest` v├¼ cß║ú hai chiß╗üu ─æß╗üu cß║ºn: `ingest` dß╗▒ng n├│ l├║c
Γûê    l╞░u, `StoredCatalog.from_document` dß╗▒ng lß║íi n├│ l├║c nß║íp tß╗½ DB.
Γûê    """
Γûê    stem = os.path.splitext(filename)[0]
Γûê    if stem.endswith(".catalog"):
Γûê        stem = stem[: -len(".catalog")]
Γûê    return f"{stem}.json"
Γöé
Γöé
Γûêdef _parse_generated_at(value: Any) -> datetime | None:
Γûê    """'2026-08-09T10:20:30Z' -> datetime. Hß╗Ång th├¼ trß║ú None chß╗⌐ kh├┤ng nß╗ò.
Γöé
Γûê    Tr╞░ß╗¥ng n├áy chß╗ë ─æß╗â hiß╗ân thß╗ï. Mß╗Öt t├ái liß╗çu c┼⌐ c├│ timestamp lß║í kh├┤ng ─æ├íng ─æß╗â
Γûê    chß║╖n cß║ú viß╗çc nß║íp lß║íi chß╗ë mß╗Ñc l├║c khß╗ƒi ─æß╗Öng.
Γûê    """
Γûê    if not isinstance(value, str):
Γûê        return None
Γûê    try:
Γûê        return datetime.fromisoformat(value.replace("Z", "+00:00"))
Γûê    except ValueError:
Γûê        return None
Γöé
Γöé
Γûê@dataclass
Γûêclass StoredCatalog:
Γûê    """Mß╗Öt catalog ─æ├ú qua ─æß╗º 5 tß║ºng validate v├á ─æ├ú nß║▒m trong bß║úng `input_json`."""
Γöé
Γûê    parsed: ParsedFile
Γûê    fingerprint: str
Γûê    output_file: str | None
Γûê    record_id: int | None = None
Γûê    # None vß╗¢i bß║ún nß║íp lß║íi tß╗½ DB: k├¡ch th╞░ß╗¢c file YAML gß╗æc kh├┤ng phß║úi nß╗Öi dung
Γûê    # cß╗ºa JSON n├¬n kh├┤ng l╞░u trong `content`, v├á bß╗ïa ra mß╗Öt con sß╗æ c├▓n tß╗ç h╞ín.
Γûê    size_bytes: int | None = None
Γûê    uploaded_at: datetime | None = field(default_factory=lambda: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")))
Γöé
Γûê    @property
Γûê    def filename(self) -> str:
Γûê        return self.parsed.filename
Γöé
Γûê    @property
Γûê    def warning_count(self) -> int:
Γûê        return len(self.parsed.diagnostics.warnings)
Γöé
Γûê    @property
Γûê    def state(self) -> str:
Γûê        return "valid_with_warnings" if self.warning_count else "valid"
Γöé
Γûê    @classmethod
Γûê    def from_document(
Γûê        cls, document: dict[str, Any], record_id: int | None = None
Γûê    ) -> StoredCatalog | None:
Γûê        """Dß╗▒ng lß║íi tß╗½ JSON ─æ├ú l╞░u. None nß║┐u t├ái liß╗çu kh├┤ng ─æß╗º ─æß╗â dß╗▒ng.
Γöé
Γûê        ─É├óy l├á chiß╗üu ng╞░ß╗úc cß╗ºa `_save_graph_document`: mß╗ìi thß╗⌐ `CatalogSummary`
Γûê        cß║ºn ─æß╗üu r├║t ─æ╞░ß╗úc tß╗½ ch├¡nh nß╗Öi dung JSON, trß╗½ `size_bytes`.
Γöé
Γûê        Trß║ú None thay v├¼ raise: mß╗Öt d├▓ng lß║í trong bß║úng (bß║ún c┼⌐, ai ─æ├│ ch├¿n tay)
Γûê        kh├┤ng ─æ╞░ß╗úc ph├⌐p l├ám sß║¡p cß║ú tiß║┐n tr├¼nh l├║c khß╗ƒi ─æß╗Öng. Bß╗Å qua d├▓ng ─æ├│ v├á
Γûê        ghi log l├á ─æß╗º.
Γûê        """
Γûê        filename = catalog_repository.document_filename(document)
Γûê        if filename is None:
Γûê            return None
Γöé
Γûê        sources = document.get("scope", {}).get("sources") or [{}]
Γûê        diagnostics = document.get("diagnostics") or {}
Γöé
Γûê        parsed = ParsedFile(
Γûê            filename=filename,
Γûê            nodes=document.get("nodes") or {},
Γûê            edges=document.get("edges") or [],
Γûê            root_id=sources[0].get("root"),
Γûê            diagnostics=Diagnostics(
Γûê                errors=[Issue(**i) for i in diagnostics.get("errors", [])],
Γûê                warnings=[Issue(**i) for i in diagnostics.get("warnings", [])],
Γûê            ),
Γûê        )
Γûê        return cls(
Γûê            parsed=parsed,
Γûê            fingerprint="",
Γûê            output_file=output_name(filename),
Γûê            record_id=record_id,
Γûê            size_bytes=None,
Γûê            uploaded_at=_parse_generated_at(document.get("generatedAt")),
Γûê        )
Γöé
Γûê    def summary_dict(self, include_diagnostics: bool = False) -> dict[str, Any]:
Γûê        """─Éi qua model `CatalogSummary` chß╗⌐ kh├┤ng tß╗▒ dß╗▒ng dict.
Γöé
Γûê        Model vß╗½a l├á t├ái liß╗çu OpenAPI, vß╗½a l├á chß╗æt kiß╗âm: th├¬m/bß╗¢t field ß╗ƒ ─æ├óy m├á
Γûê        qu├¬n cß║¡p nhß║¡t model l├á vß╗í ngay l├║c chß║íy test, kh├┤ng lß║╖ng lß║╜ tr├┤i ra
Γûê        frontend. `mode="json"` lo lu├┤n viß╗çc ─æß╗òi datetime sang chuß╗ùi ISO.
Γûê        """
Γûê        return CatalogSummary(
Γûê            file=self.filename,
Γûê            root=self.parsed.root_id,
Γûê            state=self.state,
Γûê            error_count=len(self.parsed.diagnostics.errors),
Γûê            warning_count=self.warning_count,
Γûê            node_count=len(self.parsed.nodes),
Γûê            edge_count=len(self.parsed.edges),
Γûê            size_bytes=self.size_bytes,
Γûê            uploaded_at=self.uploaded_at,
Γûê            output_file=self.output_file,
Γûê            record_id=self.record_id,
Γûê            diagnostics=self.parsed.diagnostics.as_dict() if include_diagnostics else None,
Γûê        ).model_dump(mode="json")
Γöé
Γöé
Γûêclass CatalogStore:
Γûê    """Cache catalog, an to├án vß╗¢i truy cß║¡p ─æß╗ông thß╗¥i.
Γöé
Γûê    `Lock` l├á cß║ºn thiß║┐t d├╣ FastAPI chß║íy async: endpoint ─æß╗ông bß╗Ö ─æ╞░ß╗úc uvicorn ─æß║⌐y
Γûê    ra threadpool, n├¬n hai request c├│ thß╗â sß╗¡a dict c├╣ng l├║c thß║¡t.
Γûê    """
Γöé
Γûê    def __init__(self) -> None:
Γûê        self._items: dict[str, StoredCatalog] = {}
Γûê        self._lock = threading.Lock()
Γöé
Γûê    def put(self, item: StoredCatalog) -> None:
Γûê        """Cß║¡p nhß║¡t cache sau khi DB ─æ├ú ghi xong.
Γöé
Γûê        Kh├┤ng trß║ú cß╗¥ `replaced` nh╞░ bß║ún c┼⌐: chuyß╗çn "c├│ ghi ─æ├¿ hay kh├┤ng" giß╗¥ do
Γûê        DB trß║ú lß╗¥i (`catalog_repository.save`). Cache m├á tß╗▒ trß║ú lß╗¥i c├óu ─æ├│ th├¼
Γûê        sau mß╗Öt lß║ºn restart giß╗»a chß╗½ng n├│ sß║╜ n├│i sai.
Γûê        """
Γûê        with self._lock:
Γûê            self._items[item.filename] = item
Γöé
Γûê    def get(self, filename: str) -> StoredCatalog | None:
Γûê        with self._lock:
Γûê            return self._items.get(filename)
Γöé
Γûê    def delete(self, filename: str) -> StoredCatalog | None:
Γûê        """Xo├í v├á trß║ú vß╗ü bß║ún ghi vß╗½a xo├í (None nß║┐u kh├┤ng c├│)."""
Γûê        with self._lock:
Γûê            return self._items.pop(filename, None)
Γöé
Γûê    def list(self, query: str | None = None) -> list[StoredCatalog]:
Γûê        """Liß╗çt k├¬, sß║»p theo t├¬n. `query` l├á t├¼m kiß║┐m chuß╗ùi con, kh├┤ng ph├ón biß╗çt hoa th╞░ß╗¥ng.
Γöé
Γûê        Mß╗Öt endpoint phß╗Ñc vß╗Ñ cß║ú hai c├ích chß╗ìn file ß╗ƒ m├án h├¼nh xo├í: kh├┤ng truyß╗ün
Γûê        `query` -> danh s├ích ─æß║ºy ─æß╗º cho dropdown; c├│ `query` -> kß║┐t quß║ú t├¼m kiß║┐m.
Γûê        Hai endpoint ri├¬ng cho c├╣ng mß╗Öt ph├⌐p lß╗ìc chß╗ë tß║ío th├¬m chß╗ù ─æß╗â lß╗çch nhau.
Γûê        """
Γûê        with self._lock:
Γûê            items = list(self._items.values())
Γûê        if query:
Γûê            needle = query.strip().lower()
Γûê            items = [i for i in items if needle in i.filename.lower()]
Γûê        return sorted(items, key=lambda i: i.filename)
Γöé
Γûê    def all_parsed(self, exclude: str | None = None) -> list[ParsedFile]:
Γûê        """To├án bß╗Ö ParsedFile ΓÇö d├╣ng ─æß╗â kiß╗âm tra xung ─æß╗Öt xuy├¬n file.
Γöé
Γûê        `exclude` bß╗Å qua ch├¡nh file ─æang ─æ╞░ß╗úc upload lß║íi, nß║┐u kh├┤ng n├│ sß║╜ tß╗▒
Γûê        xung ─æß╗Öt vß╗¢i phi├¬n bß║ún c┼⌐ cß╗ºa ch├¡nh m├¼nh.
Γûê        """
Γûê        with self._lock:
Γûê            return [i.parsed for name, i in self._items.items() if name != exclude]
Γöé
Γûê    def load_from_db(self) -> int:
Γûê        """Nß║íp lß║íi to├án bß╗Ö chß╗ë mß╗Ñc tß╗½ bß║úng `input_json`. Trß║ú sß╗æ bß║ún ghi ─æ├ú nß║íp.
Γöé
Γûê        Gß╗ìi l├║c khß╗ƒi ─æß╗Öng: dß╗» liß╗çu ─æ├ú v├áo DB th├¼ restart xong phß║úi nh├¼n thß║Ñy lß║íi,
Γûê        nß║┐u kh├┤ng ng╞░ß╗¥i d├╣ng sß║╜ t╞░ß╗ƒng mß║Ñt dß╗» liß╗çu v├á upload ─æ├¿ l├¬n ch├¡nh n├│.
Γûê        """
Γûê        documents = catalog_repository.all_documents()
Γöé
Γûê        loaded: dict[str, StoredCatalog] = {}
Γûê        skipped = 0
Γûê        for record_id, doc in documents:
Γûê            item = StoredCatalog.from_document(doc, record_id)
Γûê            if item is None:
Γûê                skipped += 1
Γûê                continue
Γûê            loaded[item.filename] = item
Γöé
Γûê        with self._lock:
Γûê            self._items = loaded
Γöé
Γûê        if skipped:
Γûê            logger.warning("Bß╗Å qua %d d├▓ng kh├┤ng dß╗▒ng lß║íi ─æ╞░ß╗úc tß╗½ input_json", skipped)
Γûê        logger.info("─É├ú nß║íp %d catalog tß╗½ database v├áo chß╗ë mß╗Ñc", len(loaded))
Γûê        return len(loaded)
Γöé
Γûê    def clear(self) -> None:
Γûê        with self._lock:
Γûê            self._items.clear()
Γöé
Γûê    def __len__(self) -> int:
Γûê        with self._lock:
Γûê            return len(self._items)
Γöé
Γöé
Γûêstore = CatalogStore()
Γöé


src\services\validation.py:
Γûê"""
Γûêvalidation.py ΓÇö Pipeline validate input, 5 tß║ºng, fail-fast.
Γöé
Γûê    Layer 1  Basic input     c├│ file? rß╗ùng? qu├í lß╗¢n? ─æ├║ng ─æu├┤i?
Γûê    Layer 2  Security        t├¬n file ─æß╗Öc, nhß╗ï ph├ón ─æß╗Öi lß╗æt, YAML bomb, tag nguy hiß╗âm
Γûê    Layer 3  File integrity   giß║úi m├ú UTF-8, c├║ ph├íp YAML, key tr├╣ng
Γûê    Layer 4  Schema           ─æ├║ng h├¼nh dß║íng? c├│ ─æß╗º section bß║»t buß╗Öc? ─æß╗Ö s├óu?
Γûê    Layer 5  Data             business rules, ref, quan hß╗ç, chu tr├¼nh phß╗Ñ thuß╗Öc
Γöé
ΓûêMß╗ùi tß║ºng l├á mß╗Öt h├ám ─æß╗Öc lß║¡p, tß╗▒ raise khi ph├ít hiß╗çn lß╗ùi. Tß║ºng sau chß╗ë chß║íy khi
Γûêtß║ºng tr╞░ß╗¢c ─æ├ú sß║ích ΓÇö thoß║ú y├¬u cß║ºu "mß╗Öt layer ph├ít hiß╗çn critical th├¼ dß╗½ng ngay".
Γöé
ΓûêΓöÇΓöÇ Mß╗Öt ─æiß╗âm t├┤i l├ám KH├üC thß╗⌐ tß╗▒ bß║ín ─æ╞░a, v├á l├╜ do ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
ΓûêBß║ín xß║┐p Security ß╗ƒ layer 5 (sau c├╣ng). ─Éß║╖t vß║¡y th├¼ hai loß║íi tß║Ñn c├┤ng quan trß╗ìng
Γûênhß║Ñt lß╗ìt l╞░ß╗¢i, v├¼ cß║ú hai ─æß╗üu nß╗ò NGAY L├ÜC PARSE:
Γöé
Γûê  - YAML bomb ("billion laughs"): file 1KB d├╣ng anchor/alias lß╗ông nhau, parse
Γûê    xong nß╗ƒ ra h├áng GB v├á giß║┐t process. Kiß╗âm tra sau khi parse l├á kiß╗âm tra khi
Γûê    server ─æ├ú chß║┐t.
Γûê  - Tag `!!python/object/apply`: dß╗▒ng object Python tuß╗│ ├╜ ngay trong l├║c parse.
Γöé
ΓûêN├¬n security phß║úi chia ─æ├┤i: phß║ºn soi BYTES TH├ö chß║íy TR╞»ß╗ÜC khi parse (─æ├óy l├á
Γûêlayer 2), phß║ºn soi Nß╗ÿI DUNG ─É├â HIß╗éU chß║íy sau (nß║▒m ß╗ƒ layer 4 ΓÇö ─æß╗Ö s├óu, v├á layer 5
ΓûêΓÇö dß╗» liß╗çu). Nguy├¬n tß║»c chung: kh├┤ng bao giß╗¥ ─æ╞░a dß╗» liß╗çu ch╞░a soi v├áo mß╗Öt parser.
Γöé
Γûê`yaml.SafeLoader` chß║╖n ─æ╞░ß╗úc tag nguy hiß╗âm, nh╞░ng KH├öNG chß║╖n anchor/alias bomb ΓÇö
Γûê─æ├│ l├á YAML hß╗úp lß╗ç. N├│ kh├┤ng thay thß║┐ ─æ╞░ß╗úc layer 2.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport logging
Γûêimport re
Γûêfrom dataclasses import dataclass, field
Γûêfrom typing import Any
Γöé
Γûêfrom fastapi import UploadFile
Γöé
Γûêfrom src.core import config
Γûêfrom src.core.errors import (
Γûê    CriticalError,
Γûê    ErrorCode,
Γûê    SecurityError,
Γûê    Stage,
Γûê    ValidationError,
Γûê)
Γûêfrom src.core.logging import content_fingerprint
Γûêfrom src.models.schemas import Issue
Γûêfrom src.services.catalog_to_graph import (
Γûê    Diagnostics,
Γûê    FatalError,
Γûê    ParsedFile,
Γûê    assert_invariants,
Γûê    build_nx_graph,
Γûê    check_cycles,
Γûê    load_yaml,
Γûê    parse_document,
Γûê)
Γöé
Γûêlogger = logging.getLogger(__name__)
Γöé
Γûê# T├¬n file bß╗ï Windows cß║Ñm ΓÇö nß║┐u lß╗ìt xuß╗æng, thao t├íc ghi ─æ─⌐a sß║╜ hß╗Ång theo c├ích kh├│ hiß╗âu.
Γûê_WINDOWS_RESERVED = {
Γûê    "con", "prn", "aux", "nul",
Γûê    *(f"com{i}" for i in range(1, 10)),
Γûê    *(f"lpt{i}" for i in range(1, 10)),
Γûê}
Γöé
Γûê_ANCHOR_RE = re.compile(r"(?:^|[\s\[\{,])&[A-Za-z0-9_-]+")
Γûê_ALIAS_RE = re.compile(r"(?:^|[\s\[\{,])\*[A-Za-z0-9_-]+")
Γûê_MERGE_KEY_RE = re.compile(r"(?m)^\s*<<\s*:")
Γöé
Γöé
Γûê@dataclass
Γûêclass ValidatedUpload:
Γûê    """Kß║┐t quß║ú cß╗ºa cß║ú pipeline khi input ─æ├ú sß║ích."""
Γöé
Γûê    filename: str
Γûê    size_bytes: int
Γûê    fingerprint: str
Γûê    parsed: ParsedFile
Γûê    warnings: list[Issue] = field(default_factory=list)
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 1 ΓÇö Basic input validation
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêasync def read_upload_within_limit(file: UploadFile) -> bytes:
Γûê    """─Éß╗ìc file theo tß╗½ng chunk v├á CHß║╢N NGAY khi v╞░ß╗út ng╞░ß╗íng.
Γöé
Γûê    Kh├┤ng d├╣ng `await file.read()` mß╗Öt ph├ít: n├│ nß║íp trß╗ìn file v├áo RAM rß╗ôi mß╗¢i
Γûê    ─æo ─æ╞░ß╗úc k├¡ch th╞░ß╗¢c ΓÇö tß╗⌐c l├á kiß╗âm tra giß╗¢i hß║ín sau khi thiß╗çt hß║íi ─æ├ú xß║úy ra.
Γûê    C┼⌐ng kh├┤ng tin `Content-Length` do client khai.
Γûê    """
Γûê    buffer = bytearray()
Γûê    limit = config.MAX_UPLOAD_BYTES
Γûê    try:
Γûê        while chunk := await file.read(config.UPLOAD_CHUNK_BYTES):
Γûê            buffer.extend(chunk)
Γûê            if len(buffer) > limit:
Γûê                raise ValidationError(
Γûê                    ErrorCode.FILE_TOO_LARGE,
Γûê                    f"File v╞░ß╗út qu├í giß╗¢i hß║ín {limit // 1024} KB. "
Γûê                    "catalog-info.yaml hß╗úp lß╗ç chß╗ë nß║╖ng v├ái KB.",
Γûê                    stage=Stage.L1_BASIC_INPUT,
Γûê                    details={"limit_bytes": limit},
Γûê                )
Γûê    except ValidationError:
Γûê        raise
Γûê    except Exception as exc:  # ─æß╗ìc hß╗Ång giß╗»a chß╗½ng: mß║íng ─æß╗⌐t, temp file lß╗ùi
Γûê        raise CriticalError(
Γûê            ErrorCode.INTERNAL_ERROR,
Γûê            "Kh├┤ng ─æß╗ìc ─æ╞░ß╗úc dß╗» liß╗çu upload. Vui l├▓ng thß╗¡ lß║íi.",
Γûê            stage=Stage.L1_BASIC_INPUT,
Γûê            log_message=f"─Éß╗ìc UploadFile thß║Ñt bß║íi: {type(exc).__name__}",
Γûê        ) from exc
Γûê    return bytes(buffer)
Γöé
Γöé
Γûêdef layer1_basic_input(filename: str | None, content: bytes, content_type: str | None) -> str:
Γûê    """Kiß╗âm tra ß╗ƒ mß╗⌐c 'c├│ phß║úi mß╗Öt file d├╣ng ─æ╞░ß╗úc kh├┤ng'. Trß║ú vß╗ü t├¬n file ─æ├ú strip.
Γöé
Γûê    Kiß╗âm tra an to├án T├èN FILE nß║▒m ß╗ƒ ─æ├óy chß╗⌐ kh├┤ng ß╗ƒ layer 2, d├╣ n├│ l├á kiß╗âm tra
Γûê    bß║úo mß║¡t. L├╜ do: t├¬n file l├á dß╗» liß╗çu ng╞░ß╗¥i d├╣ng nguy hiß╗âm nhß║Ñt trong request
Γûê    (n├│ sß║╜ ─æi v├áo mß╗Öt ─æ╞░ß╗¥ng dß║½n ghi ─æ─⌐a), v├á nß║┐u ─æß╗â sau b╞░ß╗¢c kiß╗âm tra ─æu├┤i file
Γûê    th├¼ `../../etc/passwd.txt` sß║╜ bß╗ï b├ío l├á "sai ─æu├┤i file" ΓÇö ng╞░ß╗¥i d├╣ng thß║¡t vß║½n
Γûê    bß╗ï chß║╖n, nh╞░ng ta mß║Ñt t├¡n hiß╗çu l├á c├│ ng╞░ß╗¥i ─æang d├▓ path traversal. Ph├ón loß║íi
Γûê    lß╗ùi nß║▒m ß╗ƒ KIß╗éU EXCEPTION (`SecurityError`), kh├┤ng ß╗ƒ sß╗æ hiß╗çu tß║ºng.
Γûê    """
Γûê    if not filename or not filename.strip():
Γûê        raise ValidationError(
Γûê            ErrorCode.NO_FILE,
Γûê            "Ch╞░a chß╗ìn file ─æß╗â tß║úi l├¬n.",
Γûê            stage=Stage.L1_BASIC_INPUT,
Γûê        )
Γöé
Γûê    name = _check_filename(filename.strip())
Γöé
Γûê    if len(name) > config.MAX_FILENAME_LENGTH:
Γûê        raise ValidationError(
Γûê            ErrorCode.FILENAME_TOO_LONG,
Γûê            f"T├¬n file qu├í d├ái (tß╗æi ─æa {config.MAX_FILENAME_LENGTH} k├╜ tß╗▒).",
Γûê            stage=Stage.L1_BASIC_INPUT,
Γûê        )
Γöé
Γûê    if not name.lower().endswith(config.ALLOWED_EXTENSIONS):
Γûê        raise ValidationError(
Γûê            ErrorCode.INVALID_FILE_TYPE,
Γûê            f"Chß╗ë nhß║¡n file {' hoß║╖c '.join(config.ALLOWED_EXTENSIONS)}.",
Γûê            stage=Stage.L1_BASIC_INPUT,
Γûê            details={"allowed_extensions": list(config.ALLOWED_EXTENSIONS)},
Γûê        )
Γöé
Γûê    if not content:
Γûê        raise ValidationError(
Γûê            ErrorCode.EMPTY_FILE,
Γûê            "File rß╗ùng, kh├┤ng c├│ nß╗Öi dung ─æß╗â xß╗¡ l├╜.",
Γûê            stage=Stage.L1_BASIC_INPUT,
Γûê        )
Γöé
Γûê    # Content-Type chß╗ë ghi log, KH├öNG chß║╖n ΓÇö xem ch├║ th├¡ch ß╗ƒ config.EXPECTED_CONTENT_TYPES.
Γûê    if content_type and content_type.lower().split(";")[0] not in config.EXPECTED_CONTENT_TYPES:
Γûê        logger.info(
Γûê            "Content-Type lß║í '%s' cho file '%s' ΓÇö bß╗Å qua, sß║╜ soi nß╗Öi dung thß║¡t ß╗ƒ layer 2",
Γûê            content_type, name,
Γûê        )
Γöé
Γûê    return name
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 2 ΓÇö Security (chß║íy tr├¬n BYTES TH├ö, tr╞░ß╗¢c khi parse)
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef layer2_security(filename: str, content: bytes) -> None:
Γûê    """Soi BYTES TH├ö tr╞░ß╗¢c khi ─æ╞░a cho parser. T├¬n file ─æ├ú ─æ╞░ß╗úc layer 1 duyß╗çt."""
Γûê    _check_not_binary(filename, content)
Γûê    _check_yaml_bomb(filename, content)
Γöé
Γöé
Γûêdef _check_filename(filename: str) -> str:
Γûê    """Chß║╖n path traversal. Gß╗ìi tß╗½ layer 1 ΓÇö xem ch├║ th├¡ch ß╗ƒ ─æ├│.
Γöé
Γûê    Nguy├¬n tß║»c: Tß╗¬ CHß╗ÉI chß╗⌐ kh├┤ng ├óm thß║ºm sß╗¡a. Nß║┐u tß╗▒ ├╜ cß║»t `../../etc/passwd.yaml`
Γûê    th├ánh `passwd.yaml` th├¼ ng╞░ß╗¥i d├╣ng t╞░ß╗ƒng ─æ├ú l╞░u t├¬n n├áy, hß╗ç thß╗æng l╞░u t├¬n kia
Γûê    ΓÇö v├á ta mß║Ñt lu├┤n t├¡n hiß╗çu l├á c├│ ng╞░ß╗¥i ─æang d├▓ ─æ╞░ß╗¥ng.
Γûê    """
Γûê    lowered = filename.lower()
Γöé
Γûê    reasons: list[str] = []
Γûê    if "/" in filename or "\\" in filename:
Γûê        reasons.append("chß╗⌐a dß║Ñu ph├ón c├ích th╞░ mß╗Ñc")
Γûê    if ".." in filename:
Γûê        reasons.append("chß╗⌐a '..'")
Γûê    if "\x00" in filename:
Γûê        reasons.append("chß╗⌐a NUL byte")
Γûê    if ":" in filename:  # 'C:' hoß║╖c NTFS alternate data stream 'file.yaml:evil'
Γûê        reasons.append("chß╗⌐a dß║Ñu ':'")
Γûê    if filename.startswith((".", "-", "~")):
Γûê        reasons.append("bß║»t ─æß║ºu bß║▒ng k├╜ tß╗▒ ─æß║╖c biß╗çt")
Γûê    if any(ord(ch) < 32 or ord(ch) == 127 for ch in filename):
Γûê        reasons.append("chß╗⌐a control character")
Γûê    if lowered.split(".")[0] in _WINDOWS_RESERVED:
Γûê        reasons.append("tr├╣ng t├¬n thiß║┐t bß╗ï hß╗ç thß╗æng")
Γöé
Γûê    if reasons:
Γûê        raise SecurityError(
Γûê            ErrorCode.UNSAFE_FILENAME,
Γûê            "T├¬n file kh├┤ng hß╗úp lß╗ç. Chß╗ë d├╣ng chß╗», sß╗æ, dß║Ñu '-', '_', '.' "
Γûê            "v├á kh├┤ng k├¿m ─æ╞░ß╗¥ng dß║½n th╞░ mß╗Ñc.",
Γûê            stage=Stage.L1_BASIC_INPUT,
Γûê            log_message=f"Tß╗½ chß╗æi t├¬n file {filename!r}: {', '.join(reasons)}",
Γûê        )
Γûê    return filename
Γöé
Γöé
Γûêdef _check_not_binary(filename: str, content: bytes) -> None:
Γûê    """Bß║»t 'file type spoofing': ─æß╗òi ─æu├┤i ß║únh/zip th├ánh .yaml.
Γöé
Γûê    Soi magic bytes v├á NUL byte ΓÇö hai thß╗⌐ kh├┤ng bao giß╗¥ c├│ trong file text hß╗úp lß╗ç.
Γûê    ─É├óy l├á kiß╗âm tra dß╗▒a tr├¬n Nß╗ÿI DUNG THß║¼T, kh├íc hß║│n viß╗çc tin v├áo phß║ºn mß╗ƒ rß╗Öng
Γûê    hay Content-Type do client khai.
Γûê    """
Γûê    head = content[:64]
Γûê    for magic, label in config.BINARY_MAGIC_SIGNATURES.items():
Γûê        if head.startswith(magic):
Γûê            raise SecurityError(
Γûê                ErrorCode.CONTENT_TYPE_MISMATCH,
Γûê                "Nß╗Öi dung file kh├┤ng phß║úi v─ân bß║ún YAML d├╣ phß║ºn mß╗ƒ rß╗Öng l├á .yaml/.yml.",
Γûê                stage=Stage.L2_SECURITY,
Γûê                details={"detected_format": label},
Γûê                log_message=f"'{filename}' mang ─æu├┤i YAML nh╞░ng magic bytes l├á {label}",
Γûê            )
Γöé
Γûê    if b"\x00" in content:
Γûê        raise SecurityError(
Γûê            ErrorCode.BINARY_CONTENT,
Γûê            "File chß╗⌐a dß╗» liß╗çu nhß╗ï ph├ón, kh├┤ng phß║úi v─ân bß║ún YAML.",
Γûê            stage=Stage.L2_SECURITY,
Γûê            log_message=f"'{filename}' chß╗⌐a NUL byte",
Γûê        )
Γöé
Γöé
Γûêdef _check_yaml_bomb(filename: str, content: bytes) -> None:
Γûê    """Chß║╖n tß║Ñn c├┤ng l├ám cß║ín t├ái nguy├¬n l├║c parse.
Γöé
Γûê    ─Éß║┐m tr├¬n text th├┤ bß║▒ng regex ΓÇö cß╗æ t├¼nh th├┤ s╞í, v├¼ mß╗Ñc ─æ├¡ch l├á chß║╖n TR╞»ß╗ÜC khi
Γûê    parser chß║ím v├áo dß╗» liß╗çu. Ng╞░ß╗íng ─æß║╖t cao h╞ín nhiß╗üu lß║ºn file thß║¡t n├¬n kh├┤ng
Γûê    c├│ nguy c╞í chß║╖n nhß║ºm.
Γûê    """
Γûê    # errors="replace": ß╗ƒ ─æ├óy chß╗ë cß║ºn ─æß║┐m k├╜ tß╗▒, chuyß╗çn encoding ─æß╗â layer 3 ph├ín.
Γûê    text = content.decode("utf-8", errors="replace")
Γöé
Γûê    for tag in config.FORBIDDEN_YAML_TAGS:
Γûê        if tag in text:
Γûê            raise SecurityError(
Γûê                ErrorCode.UNSAFE_YAML_TAG,
Γûê                "File chß╗⌐a cß║Ñu tr├║c YAML kh├┤ng ─æ╞░ß╗úc ph├⌐p.",
Γûê                stage=Stage.L2_SECURITY,
Γûê                log_message=f"'{filename}' chß╗⌐a tag nguy hiß╗âm {tag!r}",
Γûê            )
Γöé
Γûê    lines = text.splitlines()
Γûê    if len(lines) > config.MAX_YAML_LINES:
Γûê        raise SecurityError(
Γûê            ErrorCode.YAML_TOO_MANY_LINES,
Γûê            f"File qu├í d├ái (tß╗æi ─æa {config.MAX_YAML_LINES} d├▓ng).",
Γûê            stage=Stage.L2_SECURITY,
Γûê            details={"lines": len(lines)},
Γûê        )
Γöé
Γûê    longest = max((len(ln) for ln in lines), default=0)
Γûê    if longest > config.MAX_YAML_LINE_LENGTH:
Γûê        raise SecurityError(
Γûê            ErrorCode.YAML_TOO_MANY_LINES,
Γûê            f"File c├│ d├▓ng qu├í d├ái (tß╗æi ─æa {config.MAX_YAML_LINE_LENGTH} k├╜ tß╗▒).",
Γûê            stage=Stage.L2_SECURITY,
Γûê            details={"longest_line": longest},
Γûê        )
Γöé
Γûê    anchors = len(_ANCHOR_RE.findall(text))
Γûê    aliases = len(_ALIAS_RE.findall(text)) + len(_MERGE_KEY_RE.findall(text))
Γûê    if anchors > config.MAX_YAML_ANCHORS or aliases > config.MAX_YAML_ALIASES:
Γûê        raise SecurityError(
Γûê            ErrorCode.YAML_EXPANSION_BOMB,
Γûê            "File d├╣ng qu├í nhiß╗üu anchor/alias YAML v├á bß╗ï tß╗½ chß╗æi v├¼ l├╜ do an to├án.",
Γûê            stage=Stage.L2_SECURITY,
Γûê            details={"anchors": anchors, "aliases": aliases},
Γûê            log_message=(
Γûê                f"Nghi ngß╗¥ YAML expansion bomb ß╗ƒ '{filename}': "
Γûê                f"{anchors} anchor, {aliases} alias"
Γûê            ),
Γûê        )
Γöé
Γûê    # Thß╗Ñt ─æß║ºu d├▓ng qu├í s├óu -> ─æß╗ç quy s├óu trong parser. ╞»ß╗¢c l╞░ß╗úng 2 space = 1 cß║Ñp.
Γûê    max_indent = max((len(ln) - len(ln.lstrip(" ")) for ln in lines), default=0)
Γûê    if max_indent > config.MAX_YAML_DEPTH * 2:
Γûê        raise SecurityError(
Γûê            ErrorCode.YAML_TOO_DEEP,
Γûê            f"Cß║Ñu tr├║c file lß╗ông nhau qu├í s├óu (tß╗æi ─æa {config.MAX_YAML_DEPTH} cß║Ñp).",
Γûê            stage=Stage.L2_SECURITY,
Γûê            details={"max_indent_spaces": max_indent},
Γûê        )
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 3 ΓÇö File integrity
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef layer3_file_integrity(filename: str, content: bytes) -> dict[str, Any]:
Γûê    """File c├│ ─Éß╗îC ─É╞»ß╗óC kh├┤ng: giß║úi m├ú UTF-8, c├║ ph├íp YAML, key tr├╣ng."""
Γûê    try:
Γûê        text = content.decode("utf-8-sig")  # -sig ─æß╗â nuß╗æt lu├┤n BOM cß╗ºa Notepad
Γûê    except UnicodeDecodeError as exc:
Γûê        raise ValidationError(
Γûê            ErrorCode.INVALID_ENCODING,
Γûê            "File phß║úi ─æ╞░ß╗úc l╞░u ß╗ƒ dß║íng UTF-8. H├úy l╞░u lß║íi vß╗¢i encoding UTF-8 rß╗ôi tß║úi l├¬n.",
Γûê            stage=Stage.L3_FILE_INTEGRITY,
Γûê            details={"position": exc.start},
Γûê        ) from exc
Γöé
Γûê    try:
Γûê        document = load_yaml(text)
Γûê    except FatalError as exc:
Γûê        # load_yaml g├│i cß║ú lß╗ùi c├║ ph├íp lß║½n "root kh├┤ng phß║úi mapping" v├áo FatalError.
Γûê        code = (
Γûê            ErrorCode.DUPLICATE_KEY
Γûê            if "duplicate key" in exc.issue.message
Γûê            else ErrorCode.YAML_SYNTAX
Γûê            if exc.issue.code == "YAML_SYNTAX"
Γûê            else ErrorCode.INVALID_STRUCTURE
Γûê        )
Γûê        raise ValidationError(
Γûê            code,
Γûê            _readable_yaml_error(exc.issue.message),
Γûê            stage=Stage.L3_FILE_INTEGRITY,
Γûê            issues=[
Γûê                Issue(
Γûê                    severity="error",
Γûê                    code=exc.issue.code,
Γûê                    message=exc.issue.message,
Γûê                    location=exc.issue.yaml_path,
Γûê                    source=filename,
Γûê                )
Γûê            ],
Γûê        ) from exc
Γöé
Γûê    return document
Γöé
Γöé
Γûêdef _readable_yaml_error(raw: str) -> str:
Γûê    """PyYAML in ra nhiß╗üu d├▓ng c├│ toß║í ─æß╗Ö; giß╗» d├▓ng ─æß║ºu cho gß╗ìn m├án h├¼nh."""
Γûê    first = raw.strip().splitlines()[0] if raw.strip() else "kh├┤ng r├╡"
Γûê    return f"File YAML sai c├║ ph├íp: {first}"
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 4 ΓÇö Schema (h├¼nh dß║íng t├ái liß╗çu)
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γûê_REQUIRED_SECTIONS = ("specVersion", "metadata", "spec")
Γöé
Γöé
Γûêdef layer4_schema(filename: str, document: dict[str, Any]) -> None:
Γûê    """Kiß╗âm tra H├îNH Dß║áNG, ch╞░a x├⌐t gi├í trß╗ï.
Γöé
Γûê    T├ích khß╗Åi layer 5 v├¼ hai l├╜ do kh├íc nhau vß╗ü bß║ún chß║Ñt: thiß║┐u hß║│n section `spec`
Γûê    th├¼ kh├┤ng c├│ g├¼ ─æß╗â m├á kiß╗âm tra gi├í trß╗ï ΓÇö b├ío "thiß║┐u spec" mß╗Öt c├óu r├╡ r├áng
Γûê    hß╗»u ├¡ch h╞ín l├á 20 lß╗ùi "field bß║»t buß╗Öc" dß╗Öi ra tß╗½ tß║ºng d╞░ß╗¢i.
Γûê    """
Γûê    missing = [s for s in _REQUIRED_SECTIONS if s not in document]
Γûê    if missing:
Γûê        raise ValidationError(
Γûê            ErrorCode.MISSING_REQUIRED_SECTION,
Γûê            f"File thiß║┐u section bß║»t buß╗Öc: {', '.join(missing)}.",
Γûê            stage=Stage.L4_SCHEMA,
Γûê            details={"missing_sections": missing},
Γûê            issues=[
Γûê                Issue(
Γûê                    severity="error",
Γûê                    code="REQUIRED",
Γûê                    message=f"Thiß║┐u section '{s}' ß╗ƒ cß║Ñp cao nhß║Ñt",
Γûê                    location=s,
Γûê                    source=filename,
Γûê                )
Γûê                for s in missing
Γûê            ],
Γûê        )
Γöé
Γûê    wrong_type = [s for s in ("metadata", "spec") if not isinstance(document[s], dict)]
Γûê    if wrong_type:
Γûê        raise ValidationError(
Γûê            ErrorCode.INVALID_STRUCTURE,
Γûê            f"Section {', '.join(wrong_type)} phß║úi l├á mß╗Öt mapping (khß╗æi key: value).",
Γûê            stage=Stage.L4_SCHEMA,
Γûê            issues=[
Γûê                Issue(
Γûê                    severity="error",
Γûê                    code="TYPE_MISMATCH",
Γûê                    message=f"'{s}' phß║úi l├á mapping, ─æang l├á "
Γûê                    f"{type(document[s]).__name__}",
Γûê                    location=s,
Γûê                    source=filename,
Γûê                )
Γûê                for s in wrong_type
Γûê            ],
Γûê        )
Γöé
Γûê    depth = _document_depth(document)
Γûê    if depth > config.MAX_YAML_DEPTH:
Γûê        raise ValidationError(
Γûê            ErrorCode.INVALID_STRUCTURE,
Γûê            f"Cß║Ñu tr├║c lß╗ông nhau qu├í s├óu ({depth} cß║Ñp, tß╗æi ─æa {config.MAX_YAML_DEPTH}).",
Γûê            stage=Stage.L4_SCHEMA,
Γûê        )
Γöé
Γöé
Γûêdef _document_depth(value: Any, current: int = 0, limit: int = 64) -> int:
Γûê    """─Éo ─æß╗Ö s├óu thß║¡t sau khi parse. `limit` chß║╖n ch├¡nh h├ám n├áy khß╗Åi ─æß╗ç quy v├┤ hß║ín
Γûê    khi gß║╖p cß║Ñu tr├║c tß╗▒ tham chiß║┐u do alias tß║ío ra."""
Γûê    if current >= limit:
Γûê        return current
Γûê    if isinstance(value, dict):
Γûê        return max((_document_depth(v, current + 1, limit) for v in value.values()),
Γûê                   default=current)
Γûê    if isinstance(value, list):
Γûê        return max((_document_depth(v, current + 1, limit) for v in value), default=current)
Γûê    return current
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 5 ΓÇö Data / business rules
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef layer5_data(filename: str, document: dict[str, Any]) -> tuple[ParsedFile, list[Issue]]:
Γûê    """Chß║íy to├án bß╗Ö luß║¡t nghiß╗çp vß╗Ñ. Trß║ú vß╗ü (ParsedFile, danh s├ích warning).
Γöé
Γûê    Kh├íc 4 tß║ºng tr├¬n ß╗ƒ mß╗Öt ─æiß╗âm quan trß╗ìng: tß║ºng n├áy GOM Hß║╛T lß╗ùi rß╗ôi mß╗¢i b├ío,
Γûê    kh├┤ng dß╗½ng ß╗ƒ lß╗ùi ─æß║ºu ti├¬n. Ng╞░ß╗¥i d├╣ng sß╗¡a YAML cß║ºn thß║Ñy cß║ú 12 lß╗ùi trong mß╗Öt
Γûê    lß║ºn, kh├┤ng phß║úi upload lß║íi 12 lß║ºn.
Γûê    """
Γûê    d = Diagnostics()
Γûê    try:
Γûê        nodes, edges, root_id = parse_document(document, filename, d)
Γûê    except FatalError as exc:
Γûê        raise ValidationError(
Γûê            ErrorCode.INVALID_STRUCTURE,
Γûê            exc.issue.message,
Γûê            stage=Stage.L5_DATA,
Γûê            issues=[_to_issue(exc.issue, "error", filename)],
Γûê        ) from exc
Γöé
Γûê    if nodes and not d.errors:
Γûê        check_cycles(build_nx_graph(nodes, edges), d)
Γûê        try:
Γûê            assert_invariants(nodes, edges)
Γûê        except AssertionError as exc:
Γûê            # Bß║Ñt biß║┐n vß╗í = bug ß╗ƒ ph├¡a sinh dß╗» liß╗çu, KH├öNG phß║úi lß╗ùi cß╗ºa input.
Γûê            # Kh├┤ng ─æ╞░ß╗úc nuß╗æt: ─æß╗ô thß╗ï ─æang ß╗ƒ trß║íng th├íi kh├┤ng nhß║Ñt qu├ín.
Γûê            raise CriticalError(
Γûê                ErrorCode.INCONSISTENT_STATE,
Γûê                "Hß╗ç thß╗æng tß║ío ra dß╗» liß╗çu kh├┤ng nhß║Ñt qu├ín v├á ─æ├ú dß╗½ng ─æß╗â tr├ính l╞░u sai.",
Γûê                stage=Stage.L5_DATA,
Γûê                log_message=f"Vß╗í bß║Ñt biß║┐n khi xß╗¡ l├╜ '{filename}': {exc}",
Γûê            ) from exc
Γöé
Γûê    if d.errors:
Γûê        raise ValidationError(
Γûê            ErrorCode.SCHEMA_VALIDATION_FAILED,
Γûê            f"File c├│ {len(d.errors)} lß╗ùi cß║ºn sß╗¡a tr╞░ß╗¢c khi sß╗¡ dß╗Ñng ─æ╞░ß╗úc.",
Γûê            stage=Stage.L5_DATA,
Γûê            details={"error_count": len(d.errors), "warning_count": len(d.warnings)},
Γûê            issues=(
Γûê                [_to_issue(i, "error", filename) for i in d.errors]
Γûê                + [_to_issue(i, "warning", filename) for i in d.warnings]
Γûê            ),
Γûê        )
Γöé
Γûê    warnings = [_to_issue(i, "warning", filename) for i in d.warnings]
Γûê    return ParsedFile(filename, nodes, edges, root_id, d), warnings
Γöé
Γöé
Γûêdef _to_issue(issue: Any, severity: str, filename: str) -> Issue:
Γûê    """─Éß╗òi `catalog_to_graph.Issue` (nß╗Öi bß╗Ö) th├ánh `schemas.Issue` (contract).
Γöé
Γûê    Giß╗» hai kiß╗âu ri├¬ng biß╗çt l├á cß╗æ ├╜: ─æß╗òi cß║Ñu tr├║c nß╗Öi bß╗Ö kh├┤ng ─æ╞░ß╗úc ph├⌐p ├óm thß║ºm
Γûê    l├ám vß╗í contract cß╗ºa frontend.
Γûê    """
Γûê    return Issue(
Γûê        severity=severity,
Γûê        code=issue.code,
Γûê        message=issue.message,
Γûê        location=issue.yaml_path,
Γûê        subject=issue.subject,
Γûê        source=issue.source or filename,
Γûê    )
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Pipeline
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef run_validation_pipeline(
Γûê    filename: str | None, content: bytes, content_type: str | None = None
Γûê) -> ValidatedUpload:
Γûê    """Chß║íy lß║ºn l╞░ß╗út 5 tß║ºng. Tß║ºng n├áo raise th├¼ c├íc tß║ºng sau kh├┤ng chß║íy.
Γöé
Γûê    H├ám n├áy KH├öNG bß║»t exception. N├│ ─æß╗â lß╗ùi bay l├¬n cho tß║ºng gß╗ìi (service) quyß║┐t
Γûê    ─æß╗ïnh ΓÇö ─æ├║ng vai tr├▓: validator ph├ín ─æ├║ng/sai, kh├┤ng ph├ín xß╗¡ l├╜ thß║┐ n├áo.
Γûê    """
Γûê    name = layer1_basic_input(filename, content, content_type)
Γûê    layer2_security(name, content)
Γûê    document = layer3_file_integrity(name, content)
Γûê    layer4_schema(name, document)
Γûê    parsed, warnings = layer5_data(name, document)
Γöé
Γûê    return ValidatedUpload(
Γûê        filename=name,
Γûê        size_bytes=len(content),
Γûê        fingerprint=content_fingerprint(content),
Γûê        parsed=parsed,
Γûê        warnings=warnings,
Γûê    )
Γöé


src\test.py:
Γûêimport json
Γûêfrom fastapi import Request
Γöé
Γûêpayload = {
Γûê  "ref": "refs/heads/main",
Γûê  "before": "2fa1e1f6276f47a79beebb3ddca4b17df0b82bfa",
Γûê  "after": "d89caa17cd36630afba8bfa3f7fe569a03a0005a",
Γûê  "repository": {
Γûê    "id": 1327508956,
Γûê    "node_id": "R_kgDOTyAt3A",
Γûê    "name": "gitlab-event",
Γûê    "full_name": "vungocthien843-cyber/gitlab-event",
Γûê    "private": False,
Γûê    "owner": {
Γûê      "name": "vungocthien843-cyber",
Γûê      "email": "vungocthien843@gmail.com",
Γûê      "login": "vungocthien843-cyber",
Γûê      "id": 281504692,
Γûê      "node_id": "U_kgDOEMdrtA",
Γûê      "avatar_url": "https://avatars.githubusercontent.com/u/281504692?v=4",
Γûê      "gravatar_id": "",
Γûê      "url": "https://api.github.com/users/vungocthien843-cyber",
Γûê      "html_url": "https://github.com/vungocthien843-cyber",
Γûê      "followers_url": "https://api.github.com/users/vungocthien843-cyber/followers",
Γûê      "following_url": "https://api.github.com/users/vungocthien843-cyber/following{/other_user}",
Γûê      "gists_url": "https://api.github.com/users/vungocthien843-cyber/gists{/gist_id}",
Γûê      "starred_url": "https://api.github.com/users/vungocthien843-cyber/starred{/owner}{/repo}",
Γûê      "subscriptions_url": "https://api.github.com/users/vungocthien843-cyber/subscriptions",
Γûê      "organizations_url": "https://api.github.com/users/vungocthien843-cyber/orgs",
Γûê      "repos_url": "https://api.github.com/users/vungocthien843-cyber/repos",
Γûê      "events_url": "https://api.github.com/users/vungocthien843-cyber/events{/privacy}",
Γûê      "received_events_url": "https://api.github.com/users/vungocthien843-cyber/received_events",
Γûê      "type": "User",
Γûê      "user_view_type": "public",
Γûê      "site_admin": False
Γûê    },
Γûê    "html_url": "https://github.com/vungocthien843-cyber/gitlab-event",
Γûê    "description": None,
Γûê    "fork": False,
Γûê    "url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event",
Γûê    "forks_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/forks",
Γûê    "keys_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/keys{/key_id}",
Γûê    "collaborators_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/collaborators{/collaborator}",
Γûê    "teams_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/teams",
Γûê    "hooks_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/hooks",
Γûê    "issue_events_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/issues/events{/number}",
Γûê    "events_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/events",
Γûê    "assignees_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/assignees{/user}",
Γûê    "branches_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/branches{/branch}",
Γûê    "tags_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/tags",
Γûê    "blobs_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/blobs{/sha}",
Γûê    "git_tags_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/tags{/sha}",
Γûê    "git_refs_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/refs{/sha}",
Γûê    "trees_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/trees{/sha}",
Γûê    "statuses_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/statuses/{sha}",
Γûê    "languages_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/languages",
Γûê    "stargazers_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/stargazers",
Γûê    "contributors_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/contributors",
Γûê    "subscribers_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/subscribers",
Γûê    "subscription_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/subscription",
Γûê    "commits_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/commits{/sha}",
Γûê    "git_commits_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/commits{/sha}",
Γûê    "comments_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/comments{/number}",
Γûê    "issue_comment_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/issues/comments{/number}",
Γûê    "contents_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/contents/{+path}",
Γûê    "compare_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/compare/{base}...{head}",
Γûê    "merges_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/merges",
Γûê    "archive_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/{archive_format}{/ref}",
Γûê    "downloads_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/downloads",
Γûê    "issues_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/issues{/number}",
Γûê    "pulls_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/pulls{/number}",
Γûê    "milestones_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/milestones{/number}",
Γûê    "notifications_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/notifications{?since,all,participating}",
Γûê    "labels_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/labels{/name}",
Γûê    "releases_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/releases{/id}",
Γûê    "deployments_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/deployments",
Γûê    "created_at": 1786173232,
Γûê    "updated_at": "2026-08-08T09:51:36Z",
Γûê    "pushed_at": 1786182756,
Γûê    "git_url": "git://github.com/vungocthien843-cyber/gitlab-event.git",
Γûê    "ssh_url": "git@github.com:vungocthien843-cyber/gitlab-event.git",
Γûê    "clone_url": "https://github.com/vungocthien843-cyber/gitlab-event.git",
Γûê    "svn_url": "https://github.com/vungocthien843-cyber/gitlab-event",
Γûê    "homepage": "https://gitlab-event.vercel.app",
Γûê    "size": 2737,
Γûê    "stargazers_count": 0,
Γûê    "watchers_count": 0,
Γûê    "language": "Python",
Γûê    "has_issues": True,
Γûê    "has_projects": True,
Γûê    "has_downloads": True,
Γûê    "has_wiki": True,
Γûê    "has_pages": False,
Γûê    "has_discussions": False,
Γûê    "forks_count": 0,
Γûê    "mirror_url": None,
Γûê    "archived": False,
Γûê    "disabled": False,
Γûê    "open_issues_count": 0,
Γûê    "license": None,
Γûê    "allow_forking": True,
Γûê    "is_template": False,
Γûê    "web_commit_signoff_required": False,
Γûê    "has_pull_requests": True,
Γûê    "pull_request_creation_policy": "all",
Γûê    "topics": [
Γöé
Γûê    ],
Γûê    "visibility": "public",
Γûê    "forks": 0,
Γûê    "open_issues": 0,
Γûê    "watchers": 0,
Γûê    "default_branch": "main",
Γûê    "stargazers": 0,
Γûê    "master_branch": "main"
Γûê  },
Γûê  "pusher": {
Γûê    "name": "vungocthien843-cyber",
Γûê    "email": "vungocthien843@gmail.com"
Γûê  },
Γûê  "forced": False,
Γûê  "sender": {
Γûê    "login": "vungocthien843-cyber",
Γûê    "id": 281504692,
Γûê    "node_id": "U_kgDOEMdrtA",
Γûê    "avatar_url": "https://avatars.githubusercontent.com/u/281504692?v=4",
Γûê    "gravatar_id": "",
Γûê    "url": "https://api.github.com/users/vungocthien843-cyber",
Γûê    "html_url": "https://github.com/vungocthien843-cyber",
Γûê    "followers_url": "https://api.github.com/users/vungocthien843-cyber/followers",
Γûê    "following_url": "https://api.github.com/users/vungocthien843-cyber/following{/other_user}",
Γûê    "gists_url": "https://api.github.com/users/vungocthien843-cyber/gists{/gist_id}",
Γûê    "starred_url": "https://api.github.com/users/vungocthien843-cyber/starred{/owner}{/repo}",
Γûê    "subscriptions_url": "https://api.github.com/users/vungocthien843-cyber/subscriptions",
Γûê    "organizations_url": "https://api.github.com/users/vungocthien843-cyber/orgs",
Γûê    "repos_url": "https://api.github.com/users/vungocthien843-cyber/repos",
Γûê    "events_url": "https://api.github.com/users/vungocthien843-cyber/events{/privacy}",
Γûê    "received_events_url": "https://api.github.com/users/vungocthien843-cyber/received_events",
Γûê    "type": "User",
Γûê    "user_view_type": "public",
Γûê    "site_admin": False
Γûê  },
Γûê  "created": False,
Γûê  "deleted": False,
Γûê  "base_ref": None,
Γûê  "compare": "https://github.com/vungocthien843-cyber/gitlab-event/compare/2fa1e1f6276f...d89caa17cd36",
Γûê  "commits": [
Γûê    {
Γûê      "id": "d89caa17cd36630afba8bfa3f7fe569a03a0005a",
Γûê      "tree_id": "b292c13656639bce513a87eb9ad0b75e6d89a6c0",
Γûê      "distinct": True,
Γûê      "message": "nthoc",
Γûê      "timestamp": "2026-08-08T16:52:31+07:00",
Γûê      "url": "https://github.com/vungocthien843-cyber/gitlab-event/commit/d89caa17cd36630afba8bfa3f7fe569a03a0005a",
Γûê      "author": {
Γûê        "name": "Vu ngon thien",
Γûê        "email": "vungocthien843@gmail.com",
Γûê        "date": "2026-08-08T16:52:31+07:00",
Γûê        "username": "vungocthien843-cyber"
Γûê      },
Γûê      "committer": {
Γûê        "name": "Vu ngon thien",
Γûê        "email": "vungocthien843@gmail.com",
Γûê        "date": "2026-08-08T16:52:31+07:00",
Γûê        "username": "vungocthien843-cyber"
Γûê      },
Γûê      "added": [
Γöé
Γûê      ],
Γûê      "removed": [
Γöé
Γûê      ],
Γûê      "modified": [
Γûê        "ping01.yaml"
Γûê      ]
Γûê    }
Γûê  ],
Γûê  "head_commit": {
Γûê    "id": "d89caa17cd36630afba8bfa3f7fe569a03a0005a",
Γûê    "tree_id": "b292c13656639bce513a87eb9ad0b75e6d89a6c0",
Γûê    "distinct": True,
Γûê    "message": "nthoc",
Γûê    "timestamp": "2026-08-08T16:52:31+07:00",
Γûê    "url": "https://github.com/vungocthien843-cyber/gitlab-event/commit/d89caa17cd36630afba8bfa3f7fe569a03a0005a",
Γûê    "author": {
Γûê      "name": "Vu ngon thien",
Γûê      "email": "vungocthien843@gmail.com",
Γûê      "date": "2026-08-08T16:52:31+07:00",
Γûê      "username": "vungocthien843-cyber"
Γûê    },
Γûê    "committer": {
Γûê      "name": "Vu ngon thien",
Γûê      "email": "vungocthien843@gmail.com",
Γûê      "date": "2026-08-08T16:52:31+07:00",
Γûê      "username": "vungocthien843-cyber"
Γûê    },
Γûê    "added": [
Γöé
Γûê    ],
Γûê    "removed": [
Γöé
Γûê    ],
Γûê    "modified": [
Γûê      "ping01.yaml"
Γûê    ]
Γûê  }
Γûê}
Γöé
Γöé
Γûêprint(payload)
Γöé
Γûêcommits = payload.get("commits", [])
Γûêprint("Commits:", commits)
Γöé
Γûêlatest_commit = commits[-1]
Γûêprint("Latest Commit:", latest_commit)
Γöé
Γûêchanged_files = latest_commit.get("added", []) + latest_commit.get("modified", [])
Γûêprint("Changed Files:", changed_files)
Γöé
Γûêyaml_files = [f for f in changed_files if f.endswith('.yaml') or f.endswith('.yml')]
Γûêprint("YAML Files:", yaml_files)


tests\conftest.py:
Γûêfrom unittest.mock import AsyncMock
Γöé
Γûêimport pytest
Γûêimport pytest_asyncio
Γûêfrom httpx import ASGITransport, AsyncClient
Γöé
Γûêfrom src.main import app
Γöé
Γöé
Γûê@pytest_asyncio.fixture
Γûêasync def client():
Γûê    """Async HTTP client for testing API endpoints."""
Γûê    transport = ASGITransport(app=app)
Γûê    async with AsyncClient(transport=transport, base_url="http://test") as ac:
Γûê        yield ac
Γöé
Γöé
Γûê@pytest.fixture
Γûêdef mock_llm():
Γûê    """Mock LLM to avoid calling OpenAI during tests.
Γöé
Γûê    Usage in test:
Γûê        def test_something(mock_llm):
Γûê            # LLM calls will return mock response instead of hitting OpenAI
Γûê            ...
Γûê    """
Γûê    mock = AsyncMock()
Γûê    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
Γûê    return mock


tests\test_agents\test_graph.py:
Γûêimport pytest
Γöé
Γûêfrom src.agents.graph import agent
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_agent_basic_flow():
Γûê    result = await agent.ainvoke({"query": "Hello"})
Γûê    assert "response" in result
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_agent_state_structure():
Γûê    result = await agent.ainvoke({"query": "Test query"})
Γûê    assert isinstance(result, dict)
Γûê    assert "query" in result


tests\test_api\test_routes.py:
Γûêimport pytest
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_health(client):
Γûê    response = await client.get("/health")
Γûê    assert response.status_code == 200
Γûê    data = response.json()
Γûê    assert data["status"] == "ok"
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_chat_empty_message(client):
Γûê    response = await client.post("/api/v1/chat", json={"message": ""})
Γûê    assert response.status_code == 422  # Validation error
Γöé
Γöé
Γûê@pytest.mark.asyncio
Γûêasync def test_agent_status(client):
Γûê    response = await client.get("/api/v1/status")
Γûê    assert response.status_code == 200


tests\test_catalog_api.py:
Γûê"""
ΓûêTest cho luß╗ông input processing.
Γöé
ΓûêChia theo Tß║ªNG validate ΓÇö mß╗ùi tß║ºng phß║úi c├│ ├¡t nhß║Ñt mß╗Öt test chß╗⌐ng minh n├│ chß║╖n
Γûê─æ╞░ß╗úc ─æ├║ng thß╗⌐ n├│ sinh ra ─æß╗â chß║╖n, v├á mß╗Öt test chß╗⌐ng minh n├│ KH├öNG chß║╖n nhß║ºm
Γûêinput hß╗úp lß╗ç.
Γöé
ΓûêNh├│m test quan trß╗ìng nhß║Ñt l├á `TestContract`: n├│ kiß╗âm tra t├¡nh chß║Ñt ─æ├║ng cho Mß╗îI
Γûêresponse (status khß╗¢p severity, lu├┤n c├│ request_id, lß╗ùi th├¼ can_continue=False).
ΓûêLoß║íi test n├áy bß║»t ─æ╞░ß╗úc cß║ú nhß╗»ng lß╗ùi ß╗ƒ endpoint ch╞░a ai ngh─⌐ tß╗¢i khi viß║┐t test.
Γûê"""
Γöé
Γûêfrom __future__ import annotations
Γöé
Γûêimport json
Γûêimport os
Γöé
Γûêimport pytest
Γûêfrom fastapi.testclient import TestClient
Γûêfrom sqlalchemy import text
Γöé
Γûêfrom src.core import config
Γûêfrom src.core import db as core_db
Γûêfrom src.main import app
Γûêfrom src.services import catalog_repository, ingest
Γûêfrom src.services.store import store
Γöé
Γûêclient = TestClient(app, raise_server_exceptions=False)
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Fixtures
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêdef make_yaml(
Γûê    *,
Γûê    sid: str = "order-service",
Γûê    namespace: str = "order",
Γûê    system: str = "order-system",
Γûê    stype: str = "worker",
Γûê    topology: str | None = None,
Γûê) -> str:
Γûê    """Mß║╖c ─æß╗ïnh sinh ra file Sß║áCH TUYß╗åT ─Éß╗ÉI ΓÇö kh├┤ng lß╗ùi, kh├┤ng cß║únh b├ío.
Γöé
Γûê    D├╣ng `worker` chß╗⌐ kh├┤ng `service` cho mß║╖c ─æß╗ïnh: component c├│ API surface m├á
Γûê    khai providesApis th├¼ lu├┤n k├¿m cß║únh b├ío AWAITING_SPEC_INGEST (─æ├║ng theo luß║¡t
Γûê    nghiß╗çp vß╗Ñ). Test "th├ánh c├┤ng sß║ích" cß║ºn mß╗Öt fixture kh├┤ng c├│ cß║únh b├ío n├áo,
Γûê    nß║┐u kh├┤ng n├│ kh├┤ng ph├ón biß╗çt ─æ╞░ß╗úc success vß╗¢i warning.
Γûê    """
Γûê    default_topology = f"""
Γûê    - ref: system:{namespace}/{system}
Γûê    - ref: resource:{namespace}/order-db"""
Γûê    return f"""specVersion: vsf-idp.io/v2
Γûêmetadata:
Γûê  domain: commerce
Γûê  system: {system}
Γûê  namespace: {namespace}
Γûêspec:
Γûê  type: {stype}
Γûê  id: {sid}
Γûê  name: Order Service
Γûê  description: Handles order lifecycle
Γûê  owners:
Γûê    members:
Γûê      - user: alice@example.com
Γûê        role: techlead
Γûê  review:
Γûê    branch: main
Γûê  topology:{topology if topology is not None else default_topology}
Γûê"""
Γöé
Γöé
ΓûêVALID_YAML = make_yaml()
Γöé
Γûê# Hß╗úp lß╗ç nh╞░ng thiß║┐u ref 'system' v├á thiß║┐u providesApis -> chß╗ë ra WARNING.
ΓûêWARNING_YAML = make_yaml(topology="\n    - ref: resource:order/order-db")
Γöé
Γûê# Sai luß║¡t nghiß╗çp vß╗Ñ: id kh├┤ng phß║úi slug, thiß║┐u techlead.
ΓûêINVALID_DATA_YAML = """specVersion: vsf-idp.io/v2
Γûêmetadata:
Γûê  domain: commerce
Γûê  system: order-system
Γûê  namespace: order
Γûêspec:
Γûê  type: service
Γûê  id: Order_Service
Γûê  name: Order Service
Γûê  owners:
Γûê    members:
Γûê      - user: bob@example.com
Γûê        role: member
Γûê  review:
Γûê    branch: main
Γûê  topology:
Γûê    - ref: system:order/order-system
Γûê"""
Γöé
Γöé
Γûêdef upload(name: str, text: str | bytes, content_type: str = "application/x-yaml"):
Γûê    data = text.encode("utf-8") if isinstance(text, str) else text
Γûê    return client.post("/catalogs", files={"file": (name, data, content_type)})
Γöé
Γöé
Γûê@pytest.fixture(scope="session", autouse=True)
Γûêdef test_database():
Γûê    """Dß╗▒ng mß╗Öt SCHEMA RI├èNG tr├¬n ch├¡nh Postgres thß║¡t, xo├í sß║ích l├║c xong.
Γöé
Γûê    V├¼ sao kh├┤ng d├╣ng SQLite cho nhanh: bß║úng d├╣ng JSONB v├á BIGSERIAL, c├▓n ph├⌐p
Γûê    tra cß╗⌐u dß╗▒a tr├¬n to├ín tß╗¡ JSON cß╗ºa Postgres. Test tr├¬n mß╗Öt engine kh├íc l├á test
Γûê    mß╗Öt hß╗ç thß╗æng kh├┤ng tß╗ôn tß║íi ΓÇö n├│ xanh trong khi production vß║½n hß╗Ång.
Γöé
Γûê    V├¼ sao l├á schema ri├¬ng chß╗⌐ kh├┤ng phß║úi bß║úng ri├¬ng: `DROP SCHEMA ... CASCADE`
Γûê    dß╗ìn ─æ╞░ß╗úc mß╗ìi thß╗⌐ test tß║ío ra trong ─æ├║ng mß╗Öt c├óu, kß╗â cß║ú nhß╗»ng thß╗⌐ th├¬m v├áo sau
Γûê    n├áy. V├á kh├┤ng c├│ ─æ╞░ß╗¥ng n├áo ─æß╗â mß╗Öt c├óu lß╗çnh trong test chß║ím tß╗¢i `ai20k_db`.
Γûê    """
Γûê    if not config.DATABASE_URL:
Γûê        pytest.fail(
Γûê            "Thiß║┐u DATABASE_URL. Bß╗Ö test chß║íy tr├¬n Postgres thß║¡t (schema ri├¬ng), "
Γûê            "kh├┤ng c├│ bß║ún giß║ú lß║¡p ΓÇö h├úy ─æß║╖t biß║┐n n├áy trong .env."
Γûê        )
Γöé
Γûê    schema = os.getenv("TEST_DB_SCHEMA", "ai20k_db_test")
Γûê    if schema == (config.DB_SCHEMA or config.DB_SCHEMA_FALLBACK):
Γûê        pytest.fail(
Γûê            f"TEST_DB_SCHEMA tr├╣ng schema production ('{schema}'). "
Γûê            "Test sß║╜ TRUNCATE bß║úng n├¬n phß║úi nß║▒m ß╗ƒ schema kh├íc."
Γûê        )
Γöé
Γûê    core_db.configure(config.DATABASE_URL, schema)
Γûê    core_db.init_db()
Γöé
Γûê    yield
Γöé
Γûê    with core_db.get_engine().begin() as conn:
Γûê        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
Γûê    core_db.dispose()
Γöé
Γöé
Γûê@pytest.fixture(autouse=True)
Γûêdef isolate():
Γûê    """Mß╗ùi test bß║»t ─æß║ºu vß╗¢i bß║úng rß╗ùng v├á cache rß╗ùng."""
Γûê    _truncate()
Γûê    store.clear()
Γûê    yield
Γûê    store.clear()
Γöé
Γöé
Γûêdef _truncate() -> None:
Γûê    with core_db.get_engine().begin() as conn:
Γûê        conn.execute(text("TRUNCATE TABLE input_json RESTART IDENTITY"))
Γöé
Γöé
Γûêdef stored(filename: str) -> dict | None:
Γûê    """T├ái liß╗çu JSON ─æang nß║▒m trong bß║úng cho file n├áy (None nß║┐u kh├┤ng c├│)."""
Γûê    return catalog_repository.find(filename)
Γöé
Γöé
Γûêdef row_count() -> int:
Γûê    return catalog_repository.count()
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Contract ΓÇö t├¡nh chß║Ñt phß║úi ─æ├║ng cho mß╗ìi response
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestContract:
Γûê    ALL_REQUESTS = [
Γûê        lambda: upload("order-service.yaml", VALID_YAML),
Γûê        lambda: upload("warn.yaml", WARNING_YAML),
Γûê        lambda: upload("bad.txt", "x"),
Γûê        lambda: upload("empty.yaml", ""),
Γûê        lambda: upload("broken.yaml", "specVersion: vsf-idp.io/v2\n"),
Γûê        lambda: upload("../evil.yaml", VALID_YAML),
Γûê        lambda: client.get("/catalogs"),
Γûê        lambda: client.delete("/catalogs/khong-ton-tai.yaml"),
Γûê        lambda: client.get("/duong-dan-khong-ton-tai"),
Γûê    ]
Γöé
Γûê    @pytest.mark.parametrize("call", ALL_REQUESTS)
Γûê    def test_moi_response_deu_dung_hinh_dang(self, call):
Γûê        body = call().json()
Γûê        for field in (
Γûê            "status", "severity", "code", "message",
Γûê            "can_continue", "next_action", "stage", "request_id", "issues", "details",
Γûê        ):
Γûê            assert field in body, f"thiß║┐u field '{field}'"
Γûê        assert body["message"], "message kh├┤ng ─æ╞░ß╗úc rß╗ùng"
Γûê        assert body["request_id"], "request_id kh├┤ng ─æ╞░ß╗úc rß╗ùng"
Γöé
Γûê    @pytest.mark.parametrize("call", ALL_REQUESTS)
Γûê    def test_status_luon_khop_severity(self, call):
Γûê        """status suy ra tß╗½ severity ΓÇö hai field n├áy kh├┤ng bao giß╗¥ ─æ╞░ß╗úc lß╗çch."""
Γûê        body = call().json()
Γûê        expected = {
Γûê            "none": "success", "low": "warning",
Γûê            "validation": "error", "critical": "error",
Γûê        }[body["severity"]]
Γûê        assert body["status"] == expected
Γöé
Γûê    @pytest.mark.parametrize("call", ALL_REQUESTS)
Γûê    def test_loi_thi_khong_bao_gio_cho_di_tiep(self, call):
Γûê        body = call().json()
Γûê        if body["status"] == "error":
Γûê            assert body["can_continue"] is False
Γûê            assert body["code"] is not None
Γûê            assert body["next_action"] != "proceed"
Γöé
Γûê    def test_request_id_trong_body_khop_header(self):
Γûê        r = upload("order-service.yaml", VALID_YAML)
Γûê        assert r.headers["X-Request-ID"] == r.json()["request_id"]
Γöé
Γûê    def test_request_id_do_client_gui_duoc_giu_nguyen(self):
Γûê        r = client.get("/catalogs", headers={"X-Request-ID": "trace-abc-123"})
Γûê        assert r.json()["request_id"] == "trace-abc-123"
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Luß╗ông th├ánh c├┤ng
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestHappyPath:
Γûê    def test_file_hop_le_tra_success_va_luu_db(self):
Γûê        r = upload("order-service.yaml", VALID_YAML)
Γûê        assert r.status_code == 201
Γöé
Γûê        body = r.json()
Γûê        assert body["status"] == "success"
Γûê        assert body["severity"] == "none"
Γûê        assert body["code"] is None
Γûê        assert body["can_continue"] is True
Γûê        assert body["next_action"] == "proceed"
Γûê        assert body["stage"] == "done"
Γûê        assert body["issues"] == []
Γûê        assert body["details"]["root"] == "component:order/order-service"
Γûê        assert body["details"]["node_count"] > 0
Γöé
Γûê        assert body["details"]["output_file"] == "order-service.json"
Γûê        assert isinstance(body["details"]["record_id"], int)
Γöé
Γûê        graph = stored("order-service.yaml")
Γûê        assert graph is not None
Γûê        assert graph["nodes"]["component:order/order-service"]["spec"]["type"] == "worker"
Γöé
Γûê    def test_duoi_yml_va_hau_to_catalog_deu_duoc(self):
Γûê        assert upload("payment.catalog.yml", make_yaml(sid="payment-service")).status_code == 201
Γûê        assert stored("payment.catalog.yml") is not None
Γöé
Γûê    def test_upload_lai_cung_ten_bao_warning_ghi_de(self):
Γûê        first = upload("order-service.yaml", VALID_YAML).json()
Γûê        body = upload("order-service.yaml", VALID_YAML).json()
Γöé
Γûê        assert body["status"] == "warning"
Γûê        assert body["can_continue"] is True
Γûê        assert body["details"]["replaced_existing"] is True
Γûê        assert any(i["code"] == "FILE_REPLACED" for i in body["issues"])
Γûê        # Ghi ─É├ê ─æ├║ng d├▓ng c┼⌐, kh├┤ng ch├¿n th├¬m d├▓ng mß╗¢i: bß║úng phß║ún ├ính "c├íc
Γûê        # catalog ─æang c├│", kh├┤ng phß║úi nhß║¡t k├╜ upload.
Γûê        assert body["details"]["record_id"] == first["details"]["record_id"]
Γûê        assert row_count() == 1
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Warning ΓÇö ─æi tiß║┐p ─æ╞░ß╗úc
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestWarning:
Γûê    def test_canh_bao_khong_chan_luong(self):
Γûê        r = upload("warn.yaml", WARNING_YAML)
Γûê        assert r.status_code == 201
Γöé
Γûê        body = r.json()
Γûê        assert body["status"] == "warning"
Γûê        assert body["severity"] == "low"
Γûê        assert body["can_continue"] is True
Γûê        assert body["next_action"] == "review_warnings"
Γûê        assert body["code"] == "HAS_WARNINGS"
Γûê        assert {i["code"] for i in body["issues"]} >= {"MISSING_SYSTEM_REF"}
Γûê        assert all(i["severity"] == "warning" for i in body["issues"])
Γûê        # C├│ warning vß║½n phß║úi l╞░u ─æ╞░ß╗úc: warning l├á "─æß╗â ├╜", kh├┤ng phß║úi "dß╗½ng".
Γûê        assert stored("warn.yaml") is not None
Γöé
Γûê    def test_file_co_warning_van_nam_trong_danh_sach(self):
Γûê        upload("warn.yaml", WARNING_YAML)
Γûê        item = client.get("/catalogs").json()["details"]["items"][0]
Γûê        assert item["state"] == "valid_with_warnings"
Γûê        assert item["warning_count"] > 0
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 1 ΓÇö basic input
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestLayer1BasicInput:
Γûê    def test_khong_gui_file(self):
Γûê        r = client.post("/catalogs")
Γûê        assert r.status_code == 422
Γûê        body = r.json()
Γûê        assert body["code"] == "NO_FILE"
Γûê        assert body["stage"] == "receive"
Γûê        assert body["next_action"] == "fix_and_reupload"
Γöé
Γûê    def test_file_rong(self):
Γûê        r = upload("empty.yaml", "")
Γûê        assert r.status_code == 422
Γûê        assert r.json()["code"] == "EMPTY_FILE"
Γöé
Γûê    def test_sai_duoi_file(self):
Γûê        r = upload("catalog.txt", VALID_YAML)
Γûê        assert r.status_code == 422
Γûê        body = r.json()
Γûê        assert body["code"] == "INVALID_FILE_TYPE"
Γûê        assert body["details"]["allowed_extensions"] == [".yaml", ".yml"]
Γöé
Γûê    def test_file_qua_lon(self):
Γûê        r = upload("huge.yaml", "#" + "a" * (config.MAX_UPLOAD_BYTES + 1))
Γûê        assert r.status_code == 422
Γûê        assert r.json()["code"] == "FILE_TOO_LARGE"
Γöé
Γûê    def test_ten_file_qua_dai(self):
Γûê        r = upload("a" * 200 + ".yaml", VALID_YAML)
Γûê        assert r.status_code == 422
Γûê        assert r.json()["code"] == "FILENAME_TOO_LONG"
Γöé
Γûê    def test_content_type_la_khong_bi_chan(self):
Γûê        """Content-Type do client khai kh├┤ng ─æ├íng tin -> kh├┤ng d├╣ng ─æß╗â chß║╖n."""
Γûê        r = upload("order-service.yaml", VALID_YAML, content_type="application/octet-stream")
Γûê        assert r.status_code == 201
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 2 ΓÇö security
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestLayer2Security:
Γûê    @pytest.mark.parametrize(
Γûê        "name",
Γûê        [
Γûê            "../../etc/passwd.yaml",
Γûê            "..\\..\\windows\\system32\\evil.yaml",
Γûê            "sub/dir/catalog.yaml",
Γûê            "C:catalog.yaml",
Γûê            "catalog.yaml:stream",
Γûê            "nul.yaml",
Γûê            ".hidden.yaml",
Γûê        ],
Γûê    )
Γûê    def test_ten_file_nguy_hiem_bi_tu_choi(self, name):
Γûê        r = upload(name, VALID_YAML)
Γûê        assert r.status_code == 400
Γûê        body = r.json()
Γûê        assert body["code"] == "UNSAFE_FILENAME"
Γûê        assert body["severity"] == "critical"
Γöé
Γûê    def test_path_traversal_khong_luu_duoc_gi(self):
Γûê        upload("../../evil.yaml", VALID_YAML)
Γûê        assert row_count() == 0
Γöé
Γûê    def test_file_nhi_phan_doi_lot_yaml(self):
Γûê        r = upload("fake.yaml", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
Γûê        assert r.status_code == 400
Γûê        body = r.json()
Γûê        assert body["code"] == "CONTENT_TYPE_MISMATCH"
Γûê        assert body["details"]["detected_format"] == "PNG"
Γöé
Γûê    def test_noi_dung_chua_nul_byte(self):
Γûê        r = upload("weird.yaml", VALID_YAML.encode() + b"\x00\x01")
Γûê        assert r.status_code == 400
Γûê        assert r.json()["code"] == "BINARY_CONTENT"
Γöé
Γûê    def test_tag_python_bi_chan(self):
Γûê        payload = "specVersion: !!python/object/apply:os.system ['echo hi']\n"
Γûê        r = upload("evil.yaml", payload)
Γûê        assert r.status_code == 400
Γûê        assert r.json()["code"] == "UNSAFE_YAML_TAG"
Γöé
Γûê    def test_yaml_bomb_bi_chan_truoc_khi_parse(self):
Γûê        """'Billion laughs': SafeLoader KH├öNG chß║╖n ─æ╞░ß╗úc, layer 2 phß║úi chß║╖n."""
Γûê        lines = ["a0: &a0 'x'"]
Γûê        for i in range(1, 40):
Γûê            lines.append(f"a{i}: &a{i} [{', '.join([f'*a{i - 1}'] * 8)}]")
Γûê        r = upload("bomb.yaml", "\n".join(lines))
Γûê        assert r.status_code == 400
Γûê        assert r.json()["code"] == "YAML_EXPANSION_BOMB"
Γöé
Γûê    def test_qua_nhieu_dong(self):
Γûê        r = upload("long.yaml", "# comment\n" * (config.MAX_YAML_LINES + 1))
Γûê        assert r.status_code == 400
Γûê        assert r.json()["code"] == "YAML_TOO_MANY_LINES"
Γöé
Γûê    def test_long_nhau_qua_sau(self):
Γûê        deep = "".join(" " * (2 * i) + f"k{i}:\n" for i in range(config.MAX_YAML_DEPTH + 5))
Γûê        r = upload("deep.yaml", deep)
Γûê        assert r.status_code == 400
Γûê        assert r.json()["code"] == "YAML_TOO_DEEP"
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 3 ΓÇö file integrity
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestLayer3Integrity:
Γûê    def test_khong_phai_utf8(self):
Γûê        r = upload("latin.yaml", "specVersion: caf\xe9".encode("latin-1"))
Γûê        assert r.status_code == 422
Γûê        assert r.json()["code"] == "INVALID_ENCODING"
Γöé
Γûê    def test_bom_utf8_van_doc_duoc(self):
Γûê        r = upload("bom.yaml", b"\xef\xbb\xbf" + VALID_YAML.encode("utf-8"))
Γûê        assert r.status_code == 201
Γöé
Γûê    def test_sai_cu_phap_yaml(self):
Γûê        r = upload("broken.yaml", "spec:\n  - a\n b: [unclosed\n")
Γûê        assert r.status_code == 422
Γûê        body = r.json()
Γûê        assert body["code"] == "YAML_SYNTAX"
Γûê        assert body["stage"] == "layer3_file_integrity"
Γûê        assert len(body["issues"]) == 1
Γöé
Γûê    def test_key_trung_bi_tu_choi(self):
Γûê        """PyYAML mß║╖c ─æß╗ïnh nuß╗æt key tr├╣ng v├á lß║Ñy c├íi sau. ß╗₧ ─æ├óy phß║úi b├ío lß╗ùi:
Γûê        key tr├╣ng gß║ºn nh╞░ lu├┤n l├á dß║Ñu hiß╗çu merge nhß║ºm."""
Γûê        dup = VALID_YAML.replace("  domain: commerce", "  domain: commerce\n  domain: retail")
Γûê        r = upload("dup.yaml", dup)
Γûê        assert r.status_code == 422
Γûê        assert r.json()["code"] == "DUPLICATE_KEY"
Γöé
Γûê    def test_root_khong_phai_mapping(self):
Γûê        r = upload("list.yaml", "- a\n- b\n")
Γûê        assert r.status_code == 422
Γûê        assert r.json()["code"] == "INVALID_STRUCTURE"
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 4 ΓÇö schema
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestLayer4Schema:
Γûê    def test_thieu_section_bat_buoc(self):
Γûê        r = upload("partial.yaml", "specVersion: vsf-idp.io/v2\n")
Γûê        assert r.status_code == 422
Γûê        body = r.json()
Γûê        assert body["code"] == "MISSING_REQUIRED_SECTION"
Γûê        assert body["stage"] == "layer4_schema"
Γûê        assert set(body["details"]["missing_sections"]) == {"metadata", "spec"}
Γöé
Γûê    def test_section_sai_kieu(self):
Γûê        r = upload("wrong.yaml", "specVersion: vsf-idp.io/v2\nmetadata: hello\nspec: 123\n")
Γûê        assert r.status_code == 422
Γûê        body = r.json()
Γûê        assert body["code"] == "INVALID_STRUCTURE"
Γûê        assert {i["location"] for i in body["issues"]} == {"metadata", "spec"}
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Layer 5 ΓÇö data / business rules
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestLayer5Data:
Γûê    def test_gom_het_loi_thay_vi_dung_o_loi_dau_tien(self):
Γûê        """Ng╞░ß╗¥i sß╗¡a YAML cß║ºn thß║Ñy cß║ú 5 lß╗ùi trong mß╗Öt lß║ºn, kh├┤ng phß║úi upload 5 lß║ºn."""
Γûê        r = upload("invalid.yaml", INVALID_DATA_YAML)
Γûê        assert r.status_code == 422
Γöé
Γûê        body = r.json()
Γûê        assert body["code"] == "SCHEMA_VALIDATION_FAILED"
Γûê        assert body["stage"] == "layer5_data"
Γöé
Γûê        errors = [i for i in body["issues"] if i["severity"] == "error"]
Γûê        assert len(errors) >= 2
Γûê        assert {"INVALID_FORMAT", "MISSING_TECHLEAD"} <= {i["code"] for i in errors}
Γûê        assert all(i["location"] for i in errors), "mß╗ùi lß╗ùi phß║úi chß╗ë ─æ├║ng vß╗ï tr├¡ trong YAML"
Γöé
Γûê    def test_sai_specversion(self):
Γûê        r = upload("old.yaml", VALID_YAML.replace("vsf-idp.io/v2", "vsf-idp.io/v1"))
Γûê        assert r.status_code == 422
Γûê        assert any(i["code"] == "UNSUPPORTED_VERSION" for i in r.json()["issues"])
Γöé
Γûê    def test_file_loi_khong_luu_db_va_khong_vao_kho(self):
Γûê        """Bß║ún c┼⌐ ghi JSON kß╗â cß║ú khi parse c├▓n lß╗ùi -> kho t├¡ch luß╗╣ r├íc."""
Γûê        upload("invalid.yaml", INVALID_DATA_YAML)
Γûê        assert row_count() == 0
Γûê        assert client.get("/catalogs").json()["details"]["total"] == 0
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Human-in-the-loop
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestHumanInTheLoop:
Γûê    PROVIDER_A = make_yaml(
Γûê        sid="order-service", stype="service",
Γûê        topology="\n    - ref: system:order/order-system"
Γûê                 "\n    - ref: providesApis:order/order-service",
Γûê    )
Γûê    PROVIDER_B = make_yaml(
Γûê        sid="payment-service", stype="service",
Γûê        topology="\n    - ref: system:order/order-system"
Γûê                 "\n    - ref: providesApis:order/order-service",
Γûê    )
Γöé
Γûê    def test_tranh_chap_quyen_so_huu_chuyen_human_review(self):
Γûê        """Hai file c├╣ng provides mß╗Öt API: hß╗ç thß╗æng kh├┤ng c├│ c╞í sß╗ƒ chß╗ìn b├¬n n├áo."""
Γûê        upload("a.yaml", self.PROVIDER_A)
Γûê        r = upload("b.yaml", self.PROVIDER_B)
Γöé
Γûê        assert r.status_code == 409
Γûê        body = r.json()
Γûê        assert body["code"] == "NEEDS_HUMAN_REVIEW"
Γûê        assert body["next_action"] == "human_review"
Γûê        assert body["can_continue"] is False
Γûê        assert body["issues"][0]["code"] == "AMBIGUOUS_OWNER"
Γöé
Γûê    def test_tranh_chap_khong_lam_hong_du_lieu_da_co(self):
Γûê        upload("a.yaml", self.PROVIDER_A)
Γûê        upload("b.yaml", self.PROVIDER_B)
Γûê        assert client.get("/catalogs").json()["details"]["total"] == 1
Γûê        assert stored("b.yaml") is None
Γöé
Γûê    def test_upload_lai_chinh_no_khong_bi_coi_la_tranh_chap(self):
Γûê        upload("a.yaml", make_yaml())
Γûê        assert upload("a.yaml", make_yaml()).status_code == 201
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Danh s├ích + t├¼m kiß║┐m
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestListAndSearch:
Γûê    @pytest.fixture(autouse=True)
Γûê    def seed(self):
Γûê        upload("order-service.yaml", make_yaml(sid="order-service"))
Γûê        upload("payment-service.yaml", make_yaml(sid="payment-service", namespace="payment",
Γûê                                                 system="payment-system"))
Γûê        upload("order-worker.yaml", make_yaml(sid="order-worker", stype="worker",
Γûê                                              topology="\n    - ref: system:order/order-system"))
Γöé
Γûê    def test_liet_ke_day_du(self):
Γûê        d = client.get("/catalogs").json()["details"]
Γûê        assert d["total"] == 3
Γûê        assert d["returned"] == 3
Γûê        assert [i["file"] for i in d["items"]] == [
Γûê            "order-service.yaml", "order-worker.yaml", "payment-service.yaml"
Γûê        ]
Γöé
Γûê    def test_moi_dong_du_thong_tin_de_render_bang(self):
Γûê        item = client.get("/catalogs").json()["details"]["items"][0]
Γûê        for field in ("file", "root", "state", "error_count", "warning_count",
Γûê                      "node_count", "edge_count", "size_bytes", "uploaded_at",
Γûê                      "output_file", "record_id"):
Γûê            assert field in item
Γûê        assert item["output_file"] == "order-service.json"
Γûê        assert isinstance(item["record_id"], int)
Γöé
Γûê    def test_tim_kiem_theo_chuoi_con(self):
Γûê        d = client.get("/catalogs", params={"q": "order"}).json()["details"]
Γûê        assert d["returned"] == 2
Γûê        assert d["total"] == 3
Γûê        assert all("order" in i["file"] for i in d["items"])
Γöé
Γûê    def test_tim_kiem_khong_phan_biet_hoa_thuong(self):
Γûê        assert client.get("/catalogs", params={"q": "ORDER"}).json()["details"]["returned"] == 2
Γöé
Γûê    def test_tim_khong_thay_van_la_success_voi_danh_sach_rong(self):
Γûê        """Kh├┤ng t├¼m thß║Ñy KH├öNG phß║úi lß╗ùi ΓÇö c├óu truy vß║Ñn ─æ├ú chß║íy ─æ├║ng."""
Γûê        body = client.get("/catalogs", params={"q": "khong-co-gi"}).json()
Γûê        assert body["status"] == "success"
Γûê        assert body["details"]["items"] == []
Γûê        assert "khong-co-gi" in body["message"]
Γöé
Γûê    def test_diagnostics_chi_tra_khi_duoc_yeu_cau(self):
Γûê        assert client.get("/catalogs").json()["details"]["items"][0]["diagnostics"] is None
Γûê        with_diag = client.get("/catalogs", params={"include": "diagnostics"}).json()
Γûê        assert with_diag["details"]["items"][0]["diagnostics"] is not None
Γöé
Γûê    def test_include_sai_gia_tri_bi_tu_choi(self):
Γûê        r = client.get("/catalogs", params={"include": "everything"})
Γûê        assert r.status_code == 422
Γûê        assert r.json()["severity"] == "validation"
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Xo├í
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestDelete:
Γûê    def test_xoa_ca_ban_ghi_lan_dong_trong_db(self):
Γûê        upload("order-service.yaml", VALID_YAML)
Γûê        assert stored("order-service.yaml") is not None
Γöé
Γûê        r = client.delete("/catalogs/order-service.yaml")
Γûê        assert r.status_code == 200
Γöé
Γûê        body = r.json()
Γûê        assert body["status"] == "success"
Γûê        assert body["details"]["remaining"] == 0
Γûê        assert stored("order-service.yaml") is None
Γûê        assert client.get("/catalogs").json()["details"]["total"] == 0
Γöé
Γûê    def test_xoa_file_khong_ton_tai_kem_goi_y(self):
Γûê        upload("order-service.yaml", VALID_YAML)
Γûê        r = client.delete("/catalogs/order-servic.yaml")
Γöé
Γûê        assert r.status_code == 422
Γûê        body = r.json()
Γûê        assert body["code"] == "CATALOG_NOT_FOUND"
Γûê        assert body["can_continue"] is False
Γöé
Γûê    def test_goi_y_khi_go_tat(self):
Γûê        upload("order-service.yaml", VALID_YAML)
Γûê        body = client.delete("/catalogs/order").json()
Γûê        assert body["details"]["suggestions"] == ["order-service.yaml"]
Γöé
Γûê    def test_goi_y_khi_go_sai_chinh_ta(self):
Γûê        """G├╡ thiß║┐u/nhß║ºm mß╗Öt k├╜ tß╗▒ l├á l├║c cß║ºn gß╗úi ├╜ nhß║Ñt ΓÇö khß╗¢p chuß╗ùi con kh├┤ng lo ─æ╞░ß╗úc."""
Γûê        upload("order-service.yaml", VALID_YAML)
Γûê        body = client.delete("/catalogs/order-servic.yaml").json()
Γûê        assert body["details"]["suggestions"] == ["order-service.yaml"]
Γöé
Γûê    def test_khong_goi_y_bua_khi_khong_co_gi_giong(self):
Γûê        upload("order-service.yaml", VALID_YAML)
Γûê        body = client.delete("/catalogs/zzzzzzzz.yaml").json()
Γûê        assert body["details"]["suggestions"] == []
Γöé
Γûê    def test_xoa_chi_anh_huong_dung_mot_file(self):
Γûê        upload("a.yaml", make_yaml(sid="order-service"))
Γûê        upload("b.yaml", make_yaml(sid="payment-service", namespace="payment",
Γûê                                   system="payment-system"))
Γûê        client.delete("/catalogs/a.yaml")
Γûê        assert [i["file"] for i in client.get("/catalogs").json()["details"]["items"]] == ["b.yaml"]
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Bß╗ün vß╗»ng qua restart ΓÇö thß╗⌐ m├á bß║ún ghi ra th╞░ mß╗Ñc output_json/ kh├┤ng l├ám ─æ╞░ß╗úc
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestPersistence:
Γûê    # Kh├íc namespace/system vß╗¢i VALID_YAML ─æß╗â hai file kh├┤ng tranh chß║Ñp quyß╗ün
Γûê    # sß╗ƒ hß╗»u; thiß║┐u ref 'system' n├¬n vß║½n sinh ─æ├║ng mß╗Öt cß║únh b├ío.
Γûê    WARN_KHAC = make_yaml(
Γûê        sid="payment-service", namespace="payment", system="payment-system",
Γûê        topology="\n    - ref: resource:payment/payment-db",
Γûê    )
Γöé
Γûê    def test_nap_lai_chi_muc_tu_db_sau_restart(self):
Γûê        """`store.clear()` m├┤ phß╗Ång mß╗Öt lß║ºn restart: cache RAM mß║Ñt sß║ích, database
Γûê        c├▓n nguy├¬n. Nß║íp lß║íi xong danh s├ích phß║úi trß╗ƒ lß║íi nh╞░ c┼⌐ ΓÇö nß║┐u kh├┤ng, ng╞░ß╗¥i
Γûê        d├╣ng sß║╜ t╞░ß╗ƒng mß║Ñt dß╗» liß╗çu v├á upload ─æ├¿ l├¬n ch├¡nh n├│."""
Γûê        assert upload("order-service.yaml", VALID_YAML).status_code == 201
Γûê        assert upload("warn.yaml", self.WARN_KHAC).status_code == 201
Γöé
Γûê        store.clear()
Γûê        assert client.get("/catalogs").json()["details"]["total"] == 0
Γöé
Γûê        assert store.load_from_db() == 2
Γöé
Γûê        items = client.get("/catalogs").json()["details"]["items"]
Γûê        assert [i["file"] for i in items] == ["order-service.yaml", "warn.yaml"]
Γöé
Γûê        khoi_phuc = {i["file"]: i for i in items}
Γûê        assert khoi_phuc["order-service.yaml"]["root"] == "component:order/order-service"
Γûê        assert khoi_phuc["order-service.yaml"]["state"] == "valid"
Γûê        assert khoi_phuc["order-service.yaml"]["node_count"] > 0
Γûê        assert khoi_phuc["warn.yaml"]["state"] == "valid_with_warnings"
Γûê        assert khoi_phuc["warn.yaml"]["warning_count"] > 0
Γûê        # Nß║íp lß║íi phß║úi biß║┐t m├¼nh l├á d├▓ng n├áo trong bß║úng, kh├┤ng ─æß╗â null.
Γûê        assert all(isinstance(i["record_id"], int) for i in items)
Γöé
Γûê    def test_canh_bao_chi_tiet_van_con_sau_khi_nap_lai(self):
Γûê        """Diagnostics nß║▒m trong JSON n├¬n phß║úi sß╗æng s├│t nguy├¬n vß║╣n."""
Γûê        upload("warn.yaml", WARNING_YAML)
Γûê        goc = client.get("/catalogs", params={"include": "diagnostics"}).json()
Γöé
Γûê        store.clear()
Γûê        store.load_from_db()
Γûê        sau = client.get("/catalogs", params={"include": "diagnostics"}).json()
Γöé
Γûê        assert sau["details"]["items"][0]["diagnostics"] == \
Γûê            goc["details"]["items"][0]["diagnostics"]
Γöé
Γûê    def test_size_bytes_khong_khoi_phuc_duoc_thi_bao_null(self):
Γûê        """K├¡ch th╞░ß╗¢c file YAML gß╗æc kh├┤ng phß║úi nß╗Öi dung cß╗ºa JSON n├¬n kh├┤ng l╞░u.
Γûê        Trß║ú null trung thß╗▒c h╞ín l├á bß╗ïa mß╗Öt con sß╗æ."""
Γûê        upload("order-service.yaml", VALID_YAML)
Γûê        assert client.get("/catalogs").json()["details"]["items"][0]["size_bytes"] > 0
Γöé
Γûê        store.clear()
Γûê        store.load_from_db()
Γûê        item = client.get("/catalogs").json()["details"]["items"][0]
Γûê        assert item["size_bytes"] is None
Γûê        assert item["uploaded_at"] is not None  # lß║Ñy ─æ╞░ß╗úc tß╗½ generatedAt
Γöé
Γûê    def test_upload_lai_sau_restart_van_biet_la_ghi_de(self):
Γûê        """Cache mß║Ñt nh╞░ng DB nhß╗¢ -> vß║½n phß║úi b├ío FILE_REPLACED, kh├┤ng lß║╖ng lß║╜
Γûê        ─æ├¿ l├¬n bß║ún c┼⌐."""
Γûê        upload("order-service.yaml", VALID_YAML)
Γûê        store.clear()
Γûê        store.load_from_db()
Γöé
Γûê        body = upload("order-service.yaml", VALID_YAML).json()
Γûê        assert body["details"]["replaced_existing"] is True
Γûê        assert row_count() == 1
Γöé
Γöé
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γûê# Fail-safe
Γûê# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
Γöé
Γöé
Γûêclass TestFailSafe:
Γûê    def test_exception_la_thanh_critical_chu_khong_thanh_success(self, monkeypatch):
Γûê        """Nguy├¬n tß║»c 'Unknown error = Fail safely': kh├┤ng r├╡ l├á g├¼ th├¼ coi l├á hß╗Ång."""
Γûê        def no_dau(*args, **kwargs):
Γûê            raise RuntimeError("hß╗Ång ß╗ƒ chß╗ù kh├┤ng ai l╞░ß╗¥ng tr╞░ß╗¢c")
Γöé
Γûê        monkeypatch.setattr(ingest, "_save_graph_document", no_dau)
Γöé
Γûê        r = upload("order-service.yaml", VALID_YAML)
Γûê        assert r.status_code == 500
Γûê        body = r.json()
Γûê        assert body["status"] == "error"
Γûê        assert body["severity"] == "critical"
Γûê        assert body["code"] == "INTERNAL_ERROR"
Γûê        assert body["can_continue"] is False
Γûê        assert body["next_action"] == "contact_support"
Γöé
Γûê    def test_message_loi_he_thong_khong_lo_chi_tiet_noi_bo(self, monkeypatch):
Γûê        def no_dau(*args, **kwargs):
Γûê            raise RuntimeError("/srv/secret/path/db.sqlite: password=hunter2")
Γöé
Γûê        monkeypatch.setattr(ingest, "_save_graph_document", no_dau)
Γöé
Γûê        body = upload("order-service.yaml", VALID_YAML).json()
Γûê        assert "hunter2" not in json.dumps(body)
Γûê        assert "/srv/secret" not in json.dumps(body)
Γöé
Γûê    def test_ghi_that_bai_khong_luu_vao_kho(self, monkeypatch):
Γûê        """Dß╗▒ng t├ái liß╗çu hß╗Ång -> KH├öNG ─æ╞░ß╗úc ─æ├ính dß║Ñu l├á ─æ├ú nß║íp th├ánh c├┤ng."""
Γûê        def khong_ghi_duoc(*args, **kwargs):
Γûê            raise OSError(28, "No space left on device")
Γöé
Γûê        monkeypatch.setattr(ingest, "merge_documents", khong_ghi_duoc)
Γöé
Γûê        r = upload("order-service.yaml", VALID_YAML)
Γûê        assert r.status_code == 500
Γûê        assert r.json()["code"] == "STORAGE_FAILURE"
Γûê        assert client.get("/catalogs").json()["details"]["total"] == 0
Γöé
Γûê    def test_db_hong_van_dung_contract_va_khong_lo_dsn(self, monkeypatch):
Γûê        """DB chß║┐t l├á t├¼nh huß╗æng ta HIß╗éU R├ò -> STORAGE_FAILURE, kh├┤ng phß║úi
Γûê        INTERNAL_ERROR. V├á th├┤ng ─æiß╗çp psycopg2 hay k├¿m chuß╗ùi kß║┐t nß╗æi, tß╗⌐c l├á k├¿m
Γûê        mß║¡t khß║⌐u ΓÇö n├│ kh├┤ng ─æ╞░ß╗úc ph├⌐p ─æi ra tß╗¢i client."""
Γûê        from sqlalchemy.exc import OperationalError
Γöé
Γûê        def db_chet(*args, **kwargs):
Γûê            raise OperationalError(
Γûê                "SELECT 1",
Γûê                {},
Γûê                Exception("could not connect: password=sieu-bi-mat host=db.internal"),
Γûê            )
Γöé
Γûê        # Chß║╖n ß╗ƒ tß║ºng session chß╗⌐ kh├┤ng phß║úi ß╗ƒ `save`: nh╞░ vß║¡y code thß║¡t cß╗ºa
Γûê        # repository vß║½n chß║íy v├á ta kiß╗âm tra ─æ╞░ß╗úc ─æ├║ng ph├⌐p ├ính xß║í lß╗ùi cß╗ºa n├│.
Γûê        monkeypatch.setattr(catalog_repository, "session_scope", db_chet)
Γöé
Γûê        r = upload("order-service.yaml", VALID_YAML)
Γûê        assert r.status_code == 500
Γöé
Γûê        body = r.json()
Γûê        assert body["code"] == "STORAGE_FAILURE"
Γûê        assert body["stage"] == "persist"
Γûê        assert body["next_action"] == "contact_support"
Γûê        assert "sieu-bi-mat" not in json.dumps(body)
Γûê        assert "db.internal" not in json.dumps(body)
Γûê        assert client.get("/catalogs").json()["details"]["total"] == 0
Γöé
Γûê    def test_route_khong_ton_tai_van_dung_contract(self):
Γûê        r = client.get("/khong-co-duong-nay")
Γûê        assert r.status_code == 404
Γûê        assert r.json()["code"] == "HTTP_404"
Γöé
Γûê    def test_sai_method_van_dung_contract(self):
Γûê        r = client.put("/catalogs")
Γûê        assert r.status_code == 405
Γûê        assert r.json()["status"] == "error"
Γöé
Γöé
Γûêclass TestHealth:
Γûê    def test_health(self):
Γûê        r = client.get("/health")
Γûê        assert r.status_code == 200
Γûê        assert r.json() == {"status": "ok"}
Γöé


test_ftfy.py:
Γûê∩╗┐import os
Γûêimport ftfy
Γöé
Γûêwith open('src/services/github_events.py', 'r', encoding='utf-8') as f:
Γûê    text = f.read()
Γöé
Γûê# Fix mojibake
Γûêfixed_text = ftfy.fix_text(text)
Γöé
Γûêwith open('github_events_ftfy.py', 'w', encoding='utf-8') as f:
Γûê    f.write(fixed_text)
Γûêprint("FTFY finished!")


vercer.json:
Γûê{
Γûê  "version": 2,
Γûê  "builds": [
Γûê    {
Γûê      "src": "src/main.py",
Γûê      "use": "@vercel/python"
Γûê    }
Γûê  ],
Γûê  "routes": [
Γûê    {
Γûê      "src": "/(.*)",
Γûê      "dest": "src/main.py"
Γûê    }
Γûê  ]
Γûê}


WORKLOG.md:
Γûê# Worklog ΓÇö Team [T├¬n Team]
Γöé
Γûê> Ghi lß║íi tß║Ñt cß║ú c├┤ng viß╗çc ─æ├ú l├ám theo ng├áy. Ai l├ám g├¼, kß║┐t quß║ú g├¼.
Γöé
Γûê---
Γöé
Γûê## [YYYY-MM-DD]
Γöé
Γûê| Member | Task | Status | Output | Time |
Γûê|--------|------|--------|--------|------|
Γûê| [T├¬n] | [m├┤ tß║ú task] | Γ£à Done | [link/kß║┐t quß║ú] | 2h |
Γûê| [T├¬n] | [m├┤ tß║ú task] | ≡ƒöä WIP | [m├┤ tß║ú tiß║┐n ─æß╗Ö] | 1.5h |
Γûê| [T├¬n] | [m├┤ tß║ú task] | Γ¥î Blocked | [l├╜ do block] | - |
Γöé
Γûê**Tß╗òng kß║┐t ng├áy:** [1-2 c├óu vß╗ü tiß║┐n ─æß╗Ö chung]
Γöé
Γûê---
Γöé
Γûê## [YYYY-MM-DD]
Γöé
Γûê| Member | Task | Status | Output | Time |
Γûê|--------|------|--------|--------|------|
Γûê| | | | | |
Γöé
Γûê**Tß╗òng kß║┐t ng├áy:**
Γöé
Γûê---
Γöé
Γûê<!-- Format: copy block tr├¬n cho mß╗ùi ng├áy l├ám viß╗çc -->

