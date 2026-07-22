# Technical Design Document: Local RAG Document Q&A Agent

Reference: [PRD.md](./PRD.md), [WBS.md](./WBS.md)

## 1. Overview

A locally-hosted Retrieval-Augmented Generation (RAG) app for single-document Q&A, built entirely from open, self-hostable components (FastAPI, Ollama, ChromaDB) orchestrated with Docker Compose. No external API keys are required.

## 2. System Architecture

```
┌───────────────────────────────────────────────────────────┐
│                        Docker network                     │
│                                                             │
│   ┌─────────────┐      ┌─────────────┐    ┌─────────────┐  │
│   │   app       │      │   ollama    │    │  chromadb   │  │
│   │ (FastAPI)   │◄────►│ (chat +     │    │ (vector DB) │  │
│   │ port 8000   │      │  embeddings)│    │ port 8000   │  │
│   │             │◄─────┴─────────────┴───►│ internal    │  │
│   └──────┬──────┘      port 11434          port 8000     │
│          │                                                 │
└──────────┼─────────────────────────────────────────────────┘
           │  (host port mapping, e.g. 8000:8000)
           ▼
       Browser (static HTML/JS UI)
```

- `app` is the only service exposed meaningfully to the user (serves UI + API).
- `ollama` and `chromadb` are internal-only in typical use; their ports can optionally be published to the host for debugging.
- All three services join a single Compose-defined bridge network and address each other by service name (`http://ollama:11434`, `http://chromadb:8000`).

## 3. Component Design

### 3.1 `app/main.py` (FastAPI app)

Routes:

| Method | Path       | Purpose                                      |
|--------|-----------|-----------------------------------------------|
| GET    | `/`        | Serves `static/index.html`                   |
| GET    | `/health`  | Liveness + dependency check (Ollama, Chroma)  |
| POST   | `/upload`  | Accepts a document, triggers ingestion        |
| POST   | `/ask`     | Accepts a question, returns a grounded answer |

FastAPI mounts `app/static` for JS/CSS/HTML assets via `StaticFiles`.

### 3.2 `app/config.py`

Centralized settings loaded from environment variables (with defaults), e.g. via `pydantic-settings` or a plain dataclass:

```python
OLLAMA_BASE_URL: str = "http://ollama:11434"
OLLAMA_CHAT_MODEL: str = "llama3.1"
OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
CHROMA_HOST: str = "chromadb"
CHROMA_PORT: int = 8000
CHROMA_COLLECTION: str = "current_document"
CHUNK_SIZE: int = 800          # characters
CHUNK_OVERLAP: int = 100       # characters
TOP_K: int = 4
MAX_UPLOAD_MB: int = 20
SIMILARITY_THRESHOLD: float = 0.35   # below this, treat retrieval as "no relevant context"
```

### 3.3 `app/ingest.py`

```python
def extract_text(file_bytes: bytes, filename: str) -> str: ...
def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]: ...
```

- PDF: `pypdf.PdfReader`, concatenate `page.extract_text()` per page, join with `\n`.
- TXT: decode as UTF-8 (fallback latin-1 on failure).
- Chunking: sliding-window character splitter respecting paragraph/sentence boundaries where possible (split on `\n\n` first, then hard-wrap long paragraphs at `CHUNK_SIZE` with `CHUNK_OVERLAP` overlap).
- Reject empty extracted text (e.g., scanned/image-only PDFs) with a clear error surfaced to the API layer.

### 3.4 `app/rag.py`

```python
def embed_text(text: str) -> list[float]: ...        # calls Ollama /api/embeddings
def reset_collection() -> None: ...                    # drop + recreate Chroma collection
def store_chunks(chunks: list[str], source: str) -> None: ...
def retrieve(question: str, top_k: int) -> list[RetrievedChunk]: ...
def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str: ...  # calls Ollama /api/chat
```

`RetrievedChunk` = `{text: str, score: float, chunk_index: int}`.

**Ollama calls:** use plain `httpx` POST requests to `{OLLAMA_BASE_URL}/api/embeddings` and `{OLLAMA_BASE_URL}/api/chat` (or the `ollama` Python client if preferred) — avoids extra dependency surface for a teaching example.

**Chroma calls:** `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`, single collection `CHROMA_COLLECTION`. Because scope is single-document, `reset_collection()` deletes and recreates the collection on every successful upload before inserting new chunks.

### 3.5 API Contracts

**`POST /upload`** (multipart/form-data, field `file`)

Success `200`:
```json
{
  "status": "ok",
  "filename": "syllabus.pdf",
  "chunks_stored": 42
}
```

Errors:
- `400` — unsupported file type (only `.pdf`/`.txt` accepted)
- `413` — file exceeds `MAX_UPLOAD_MB`
- `422` — no extractable text (e.g., scanned image PDF)
- `502` — Ollama or Chroma unreachable during embedding/storage

**`POST /ask`** (`application/json`)
```json
{ "question": "What is the refund policy?" }
```

Success `200`:
```json
{
  "answer": "According to the document, ...",
  "sources": [
    { "chunk_index": 3, "score": 0.81, "excerpt": "Refunds are available within..." }
  ],
  "grounded": true
}
```

- If the best retrieval score is below `SIMILARITY_THRESHOLD`, `grounded: false` and `answer` is a hedge (e.g., "I couldn't find anything about that in the uploaded document.") — the LLM is not called with weak/irrelevant context, avoiding hallucination.

Errors:
- `400` — empty question or no document uploaded yet
- `502` — Ollama or Chroma unreachable

### 3.6 Prompt Template (for `/ask`)

```
System: You are a helpful assistant that answers questions using ONLY the
provided document excerpts. If the excerpts do not contain the answer,
say so clearly instead of guessing.

Context:
{{ retrieved chunks, each prefixed with [chunk N] }}

Question: {{ user question }}

Answer:
```

### 3.7 Frontend (`app/static/`)

- `index.html`: upload `<form>` (file input + submit), status banner, chat message list (`<div id="messages">`), question input + send button.
- `app.js`:
  - `handleUpload(event)` — `fetch('/upload', {method:'POST', body: formData})`, on success enable chat input and show filename/chunk count.
  - `handleAsk(event)` — `fetch('/ask', {method:'POST', body: JSON.stringify({question})})`, append user + assistant messages to the DOM.
  - Simple loading indicators (disable inputs while awaiting response).
- No frontend framework/build step — plain JS keeps the teaching example easy to read top-to-bottom.

## 4. Data Model

Chroma collection `current_document`, one entry per chunk:

| Field       | Type          | Notes                                  |
|-------------|---------------|-----------------------------------------|
| `id`        | string        | `f"{filename}-{chunk_index}"`           |
| `embedding` | float[]       | from Ollama embedding model             |
| `document`  | string        | raw chunk text                          |
| `metadata`  | dict          | `{filename, chunk_index}`               |

No separate relational database — Chroma is the single source of truth for the current document's state (existence of any entries implies a document has been uploaded).

## 5. Docker Compose Sketch

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [ollama, chromadb]

  ollama:
    image: ollama/ollama:latest
    volumes: ["ollama_data:/root/.ollama"]
    ports: ["11434:11434"]   # optional, for host-side debugging/model pulls

  chromadb:
    image: chromadb/chroma:latest
    volumes: ["chroma_data:/chroma/chroma"]
    ports: ["8001:8000"]     # optional, for host-side debugging

volumes:
  ollama_data:
  chroma_data:
```

## 6. Error Handling & Resilience

- All outbound calls to Ollama/Chroma wrapped with try/except, translated to `502` API errors with a clear message rather than raw stack traces.
- Startup order: `depends_on` ensures container start order, but not readiness — `rag.py` calls should retry briefly (e.g., 3 attempts with backoff) on first use in case Ollama/Chroma aren't fully warmed up yet.
- Uploads are fully validated (type, size, extractable text) before touching the vector store, so a bad upload never leaves the collection in a partially-updated state (reset happens only after successful extraction+chunking).

## 7. Configuration & Model Choice Notes

- Default chat model (`llama3.1` or `phi3`) and embedding model (`nomic-embed-text`) are chosen for reasonable CPU performance; documented in README as swappable via `.env`.
- `SIMILARITY_THRESHOLD` is a tunable heuristic, not a hard science — README should note it may need adjustment per model/embedding combination.

## 8. Security & Scope Notes (v1)

- No auth — intended for local/course use only, not for exposing beyond localhost.
- No sanitization concerns beyond file-type/size validation, since there's no multi-user data isolation to protect.
- Explicitly out of scope: HTTPS, rate limiting, persistent multi-user sessions (see PRD "Out of Scope").

## 9. Testing Strategy (TDD)

Every story in `docs/WBS.md` is implemented test-first: red (failing test expressing the acceptance criteria) → green (minimal code to pass) → refactor (clean up, tests stay green).

### 9.1 Test layers

| Layer | Scope | Dependencies | Speed |
|-------|-------|---------------|-------|
| Unit | `ingest.py` chunking/extraction, `rag.py` prompt building, response parsing, threshold logic | None — pure functions, or Ollama/Chroma calls mocked | Fast, runs on every save |
| API (unit-level) | FastAPI routes in `main.py` | `rag.py`/`ingest.py` mocked via dependency overrides or monkeypatch | Fast, no Docker needed |
| Integration | Full `/upload` → `/ask` flow | Real `docker compose` stack (ollama + chromadb running) | Slow, run before marking a phase complete and in CI/pre-merge |

Unit and API-layer tests must **not** require Docker to be running — this keeps the red/green loop fast enough to be usable interactively. Only the integration suite talks to real Ollama/Chroma containers.

### 9.2 Structure

```
tests/
  unit/
    test_ingest.py       # extract_text, chunk_text
    test_rag.py          # prompt construction, threshold gating, response parsing (Ollama/Chroma mocked)
    test_api.py           # /upload, /ask, /health via FastAPI TestClient, rag.py mocked
  integration/
    test_end_to_end.py    # real docker-compose stack: upload real PDF/TXT, ask real questions
  fixtures/
    sample.pdf
    sample.txt
  conftest.py              # shared fixtures: TestClient, mock Ollama/Chroma clients, sample chunks
```

### 9.3 Tooling

- `pytest` as the runner, `pytest-mock` (or stdlib `unittest.mock`) for mocking Ollama HTTP calls and the Chroma client
- FastAPI's `TestClient` (`httpx`-based) for route-level tests without a running server
- Integration tests gated behind a marker (e.g. `@pytest.mark.integration`) so they can be skipped when Docker isn't up: `pytest -m "not integration"` for the fast loop, `pytest -m integration` (with the stack running) before closing out a phase
- Add `pytest`, `pytest-mock` to `requirements.txt` (or a separate `requirements-dev.txt`)

### 9.4 Mocking approach

- Ollama calls: `rag.py` functions take an injectable HTTP client or are patched at the module boundary (`embed_text`, `generate_answer`) so unit tests supply canned embeddings/responses instead of hitting the network.
- Chroma calls: use `chromadb`'s in-memory/ephemeral client (`chromadb.Client()` without a server) in unit tests instead of `HttpClient`, or mock the collection object directly — avoids needing the `chromadb` container for fast tests.

### 9.5 Definition of Done (per WBS story)

A story is `✅ Done` only when:
1. A test exists that fails before the implementation (or a documented reason it's not testable, e.g. pure Docker/YAML config tasks).
2. The implementation makes that test pass.
3. Refactoring (if any) is done with the test suite green.
4. `docs/WBS.md` status is updated in the same change.
