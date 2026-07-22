# Work Breakdown Structure: Local RAG Document Q&A Agent

Reference: [PRD.md](./PRD.md), [TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md)

Each task is scoped to be demonstrable as a discrete step in the Udemy course (i.e., a natural point to show a Claude Code command/workflow).

## Status Legend

`⬜ Not Started` · `🔄 In Progress` · `✅ Done` · `N/A` (not code — no TDD cycle applies, e.g. pure config/YAML/docs tasks)

**Definition of Done for any story with a TDD cycle** (see `docs/TECHNICAL_DESIGN.md` §9.5): a failing test was written first, the implementation makes it pass, refactors kept it green, and this file's status was updated in the same change. Non-code tasks are marked `✅ Done` once verified manually (e.g. "containers start cleanly").

## Progress Summary

| Phase | Status |
|-------|--------|
| 1. Project Scaffolding | ✅ Done |
| 2. Docker Infrastructure | ✅ Done |
| 3. Backend Core — App Shell | ✅ Done |
| 4. Document Ingestion Pipeline | ✅ Done |
| 5. Embedding + Vector Store Integration | ✅ Done |
| 6. Answer Generation | ✅ Done |
| 7. API Endpoints | ✅ Done |
| 8. Frontend UI | ✅ Done |
| 9. Integration & Manual Testing | ✅ Done (manual; automated `@pytest.mark.integration` suite is a follow-up) |
| 10. Documentation & Course Packaging | ⬜ Not Started |

---

## 1. Project Scaffolding

### 1.1 Initialize project folder structure (`app/`, `docs/`, `app/static/`, `tests/`)
- Status: ✅ Done (N/A — structural task)

### 1.2 Create `requirements.txt` with pinned core + dev dependencies
- Status: ✅ Done (N/A — config task)
- Includes: fastapi, uvicorn, chromadb, pypdf, httpx (or ollama client), pytest, pytest-mock

### 1.3 Create `.env.example`
- Status: ✅ Done (N/A — config task)
- OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL, OLLAMA_EMBED_MODEL, CHROMA_HOST, CHROMA_PORT, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, SIMILARITY_THRESHOLD, MAX_UPLOAD_MB

### 1.4 Create `.gitignore`
- Status: ✅ Done (N/A — config task)

### 1.5 Write initial `README.md` skeleton
- Status: ✅ Done (N/A — docs task)

**Deliverable:** empty-but-runnable project skeleton, no app logic yet.

---

## 2. Docker Infrastructure

### 2.1 Write `Dockerfile` for the FastAPI app
- Status: ✅ Done (N/A — infra config)

### 2.2 Write `docker-compose.yml` (app, ollama, chromadb, shared network, volumes)
- Status: ✅ Done (N/A — infra config)

### 2.3 Verify `docker compose up --build` starts all three containers cleanly
- Status: ✅ Done (N/A — manual verification; confirmed all three containers running and `/health` returns `ollama: true, chroma: true` — fixed a real bug found here: Chroma's heartbeat endpoint is `/api/v2/heartbeat`, not `/api/v1/`)

### 2.4 Document one-time model pull step
- Status: ✅ Done (N/A — docs task; documented in README, verified live with `nomic-embed-text` + `phi3`)

**Deliverable:** `docker compose up` brings up all services; containers can reach each other by service name.

---

## 3. Backend Core — App Shell

### 3.1 `app/main.py` app shell + static mount + `GET /`
- Status: ✅ Done
- TDD steps: 1) `tests/unit/test_api.py` — failing test asserting `GET /` returns 200 and serves the index page. 2) Implement route + static mount. 3) Refactor.

### 3.2 `GET /health` route
- Status: ✅ Done
- TDD steps: 1) Failing test asserting `GET /health` returns 200 with expected shape (mock Ollama/Chroma pings). 2) Implement. 3) Refactor.

### 3.3 Centralized config loading (`app/config.py`)
- Status: ✅ Done
- TDD steps: 1) Failing test asserting env vars override defaults (e.g. set `CHUNK_SIZE` env, assert config reflects it). 2) Implement settings loader. 3) Refactor.

### 3.4 Basic logging setup
- Status: ✅ Done (N/A — no meaningful behavior to assert; verified manually via log output)

**Deliverable:** app boots in Docker, serves a blank page, health check passes.

---

## 4. Document Ingestion Pipeline

### 4.1 PDF text extraction
- Status: ✅ Done
- TDD steps: 1) Failing test: `extract_text(pdf_bytes, "sample.pdf")` returns expected known text from `tests/fixtures/sample.pdf`. 2) Implement via `pypdf`. 3) Refactor.

### 4.2 TXT text extraction
- Status: ✅ Done
- TDD steps: 1) Failing test: `extract_text(txt_bytes, "sample.txt")` returns decoded text, including a case needing latin-1 fallback. 2) Implement. 3) Refactor.

### 4.3 File type validation/rejection
- Status: ✅ Done
- TDD steps: 1) Failing test: unsupported extension raises the expected error/exception type. 2) Implement validation. 3) Refactor.

### 4.4 Chunking function (size + overlap, paragraph-aware)
- Status: ✅ Done
- TDD steps: 1) Failing tests: known input text + chunk_size/overlap produces expected chunk boundaries and count. 2) Implement `chunk_text`. 3) Refactor.

### 4.5 Empty/unextractable text handling
- Status: ✅ Done
- TDD steps: 1) Failing test: empty extracted text raises a clear, catchable error. 2) Implement. 3) Refactor.

**Deliverable:** given a file path, `ingest.py` returns a list of clean text chunks; fully covered by unit tests, no Docker required.

---

## 5. Embedding + Vector Store Integration

### 5.1 Ollama embedding client wrapper
- Status: ✅ Done
- TDD steps: 1) Failing test: `embed_text("hello")` calls the (mocked) Ollama HTTP endpoint with expected payload and returns the mocked vector. 2) Implement. 3) Refactor.

### 5.2 Chroma client setup (get-or-create collection)
- Status: ✅ Done
- TDD steps: 1) Failing test using Chroma's in-memory client: collection is created if absent. 2) Implement. 3) Refactor.

### 5.3 Reset-collection logic (single-doc replace)
- Status: ✅ Done
- TDD steps: 1) Failing test: after `store_chunks` for doc A then doc B, only doc B's chunks are present. 2) Implement `reset_collection` + upsert flow. 3) Refactor.

### 5.4 Upsert chunks + embeddings + metadata
- Status: ✅ Done
- TDD steps: 1) Failing test: stored entries have expected `id`, `document`, `metadata` fields. 2) Implement. 3) Refactor.

### 5.5 Retrieval (top-k query)
- Status: ✅ Done
- TDD steps: 1) Failing test: given known stored chunks (in-memory Chroma), `retrieve(question, top_k)` returns expected chunks ordered by score. 2) Implement. 3) Refactor.

**Deliverable:** chunks from an uploaded file are embedded and retrievable by similarity; unit-testable via in-memory Chroma + mocked Ollama, no containers required.

---

## 6. Answer Generation

### 6.1 Prompt template construction
- Status: ✅ Done
- TDD steps: 1) Failing test: given question + retrieved chunks, `build_prompt(...)` produces expected string structure (system instructions, numbered context, question). 2) Implement. 3) Refactor.

### 6.2 Ollama chat completion call wrapper
- Status: ✅ Done
- TDD steps: 1) Failing test: `generate_answer(...)` calls the (mocked) Ollama chat endpoint with the built prompt and returns its response text. 2) Implement. 3) Refactor.

### 6.3 "No relevant context" hedging logic
- Status: ✅ Done
- TDD steps: 1) Failing test: retrieval score below `SIMILARITY_THRESHOLD` → `generate_answer` returns the hedge response without calling Ollama chat (assert mock not called). 2) Implement gating. 3) Refactor.

### 6.4 Response formatting to API layer
- Status: ✅ Done
- TDD steps: 1) Failing test: formatted response includes `answer`, `sources`, `grounded` fields matching the API contract. 2) Implement. 3) Refactor.

**Deliverable:** given a question + retrieved chunks, the app returns a grounded answer string; fully unit-tested with mocked Ollama.

---

## 7. API Endpoints

### 7.1 `POST /upload`
- Status: ✅ Done
- TDD steps: 1) Failing tests via `TestClient` (rag.py/ingest.py mocked): success case returns 200 + expected shape; unsupported type → 400; oversized file → 413; unextractable text → 422. 2) Implement route. 3) Refactor.

### 7.2 `POST /ask`
- Status: ✅ Done
- TDD steps: 1) Failing tests via `TestClient` (rag.py mocked): success case returns 200 + expected shape; empty question or no document uploaded → 400. 2) Implement route. 3) Refactor.

### 7.3 Dependency-failure error handling (Ollama/Chroma unreachable → 502)
- Status: ✅ Done
- TDD steps: 1) Failing test: mocked rag.py call raises connection error → route returns 502 with clear message. 2) Implement try/except translation. 3) Refactor.

**Deliverable:** endpoints fully covered by API-layer tests (no live Docker needed), also testable via curl/Postman.

---

## 8. Frontend UI

### 8.1 `index.html` structure (upload form, status banner, chat panel)
- Status: ✅ Done (N/A — markup; verified via manual browser check)

### 8.2 `app.js` upload handler
- Status: ✅ Done (N/A for unit TDD; verified manually in browser — uploaded sample.txt via file input + click, saw success status message)

### 8.3 `app.js` chat handler
- Status: ✅ Done (N/A — see 8.2; verified via curl against the real `/ask` endpoint using the same request shape the UI sends)

### 8.4 Minimal CSS
- Status: ✅ Done (N/A — styling)

### 8.5 Guard chat input until upload succeeds
- Status: ✅ Done (N/A — verified in browser: question input/Send button were disabled before upload, enabled after success)

**Deliverable:** end-to-end usable UI in the browser. (Frontend JS is intentionally out of the pytest TDD loop for v1 — no JS test runner in scope; correctness is verified manually per Phase 9.)

---

## 9. Integration & Manual Testing

### 9.1 Integration test: upload PDF → ask factual question → grounded answer
- Status: ✅ Done (manually verified live against the real docker-compose stack: uploaded `tests/fixtures/sample.pdf`, asked "How many days is the refund window?", got a grounded answer citing the correct chunk. Automated `@pytest.mark.integration` test still to be written — tracked as follow-up.)

### 9.2 Integration test: upload TXT → ask factual question → grounded answer
- Status: ✅ Done (manually verified live: uploaded `tests/fixtures/sample.txt`, asked "What is the refund policy?", got a grounded answer citing chunk 0 with score 0.76. Automated test still to be written.)

### 9.3 Integration test: replace-document behavior (doc A → doc B)
- Status: ✅ Done (manually verified live: uploaded sample.txt then sample.pdf; subsequent answers only reflected the PDF content, confirming collection reset works against the real server.)

### 9.4 Integration test: out-of-scope question → hedge, not hallucination
- Status: ✅ Done (manually verified live: asked "What is the capital of France?" against the uploaded doc, got the hedge response with `grounded: false`, no Ollama chat call.)

### 9.5 Container restart persistence check
- Status: ✅ Done (N/A for automated TDD — manually verified: `docker compose restart app`, then asked the same question again and got the same grounded answer, confirming the Chroma volume persisted independently of the app container.)

### 9.6 Error-path tests (unsupported type, oversized file, empty question, Ollama down)
- Status: ✅ Done (covered by unit tests in 7.1/7.2/7.3 — `tests/unit/test_api_upload_ask.py`.)

**Note:** a real bug was found and fixed during this manual verification pass — Chroma's collection was being created without `hnsw:space: cosine`, so it defaulted to unbounded L2 distance, making the `1 - distance` similarity score meaningless (grounded answers were incorrectly hedged). Fixed in `app/rag.py::get_collection`, with a regression test (`test_get_collection_uses_cosine_space`) added to `tests/unit/test_rag.py`. Also found and fixed a `chromadb` client/server version mismatch (client 0.5.23 vs. server 1.0.0) and a resulting `fastapi` pin conflict — both corrected in `requirements.txt`.

**Deliverable:** verification checklist from the PRD fully passes, backed by an integration suite runnable with `pytest -m integration` against the live stack.

---

## 10. Documentation & Course Packaging

### 10.1 Finalize `README.md`
- Status: ⬜ Not Started (N/A — docs task)

### 10.2 "How this was built with Claude Code" course narrative notes
- Status: ⬜ Not Started (N/A — docs task)

### 10.3 Final consistency review of PRD/Technical Design/WBS vs. shipped code
- Status: ⬜ Not Started (N/A — docs task)

**Deliverable:** repo is self-contained and ready to be used as a course artifact.

---

## Suggested Build Order (Dependency Chain)

```
1 (Scaffolding) → 2 (Docker) → 3 (App Shell)
                              → 4 (Ingestion) → 5 (Embedding/Vector) → 6 (Generation) → 7 (API)
                                                                                          → 8 (Frontend)
                                                                                          → 9 (Integration testing)
                                                                                          → 10 (Docs)
```

Within phases 3–7, each numbered story is a self-contained TDD cycle (red → green → refactor) — update this file's status inline as each cycle completes rather than batching updates at the end of a phase.
