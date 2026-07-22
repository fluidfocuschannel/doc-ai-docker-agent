# PRD: Local RAG Document Q&A Agent (Docker)

## Context

This project is a teaching example for a Udemy course on using Claude Code. The project is a greenfield build. The primary goal is **not** to ship a production RAG product; it's to give students a realistic, moderately-sized project they can watch get built (or build themselves) using Claude Code commands — plan mode, subagents, memory, incremental edits, etc. The app itself must still genuinely work: upload a document, ask questions about it, get grounded answers.

Everything runs locally via Docker so students don't need any API keys or cloud accounts to follow along.

## Product Summary

A single-page web app where a user:
1. Uploads one document (PDF or TXT).
2. Waits briefly while it's chunked, embedded, and stored.
3. Asks natural-language questions about that document in a chat-style box.
4. Gets answers grounded in the document's content, with the underlying local LLM doing the generation.

Uploading a new document replaces the current one (single-document scope — no multi-doc management, no auth, no persistence across container restarts required for v1).

## Architecture

**Stack:**
- Backend: Python + FastAPI
- Frontend: Simple static HTML/CSS/JS (no framework) served by FastAPI — file upload widget + chat box
- LLM: Ollama (local model, e.g. `llama3.1` or `phi3` — pick a small model that runs reasonably on CPU) for both embeddings (via an Ollama embedding model like `nomic-embed-text`) and answer generation
- Vector store: ChromaDB, running as its own Docker service
- Orchestration: `docker-compose.yml` with 3 services: `app` (FastAPI), `ollama`, `chromadb`

**Flow:**
```
Browser --(upload file)--> FastAPI /upload
   -> extract text (pypdf for PDF, plain read for TXT)
   -> chunk text (simple recursive/character splitter)
   -> embed chunks via Ollama embedding model
   -> upsert into ChromaDB collection (clear collection first, since single-doc scope)

Browser --(question)--> FastAPI /ask
   -> embed question via Ollama
   -> query ChromaDB for top-k similar chunks
   -> build prompt (context + question) -> send to Ollama chat model
   -> return answer to browser, render in chat UI
```

## Key Components / Files

- `docker-compose.yml` — defines `app`, `ollama`, `chromadb` services, volumes for Ollama model cache and Chroma persistence, network between them
- `app/main.py` — FastAPI app, routes: `GET /` (serves frontend), `POST /upload`, `POST /ask`
- `app/ingest.py` — text extraction (PDF/TXT) + chunking logic
- `app/rag.py` — embedding calls, Chroma client setup/query, prompt construction, Ollama chat call
- `app/static/index.html` + `app/static/app.js` — upload form + chat UI, calls `/upload` and `/ask` via fetch
- `requirements.txt` — fastapi, uvicorn, chromadb (client), pypdf, httpx (or ollama python client)
- `.env.example` — Ollama base URL, model names, Chroma host/port (all defaulted for local Docker network)
- `README.md` — setup/run instructions (`docker compose up`), and a short note framing this as a Claude Code course example
- `tests/` — pytest suite (unit tests with mocked Ollama/Chroma, plus integration tests against the real docker-compose stack)

## Development Process: Test-Driven Development

Every story in `docs/WBS.md` must be implemented TDD-style: write a failing test that captures the story's acceptance criteria, write the minimal code to make it pass, then refactor with tests green. This is itself part of the course narrative — the red/green/refactor loop is something students should see demonstrated via Claude Code.

- Unit tests mock Ollama (HTTP calls) and Chroma (client) so the test loop is fast and doesn't require Docker.
- A smaller set of integration tests run against the real `docker compose` stack and cover the end-to-end flows in the Verification Plan below.
- A WBS story is only marked `✅ Done` once its tests are written and passing. See `docs/TECHNICAL_DESIGN.md` §9 for the test setup and `docs/WBS.md` for per-story status tracking.

## Out of Scope (v1)

- Authentication / multi-user support
- Multiple simultaneous documents or document history
- Streaming responses (can be a stretch goal)
- Cloud LLM fallback (Anthropic/OpenAI) — explicitly local-only for this version

## Verification Plan

1. `docker compose up --build` brings up all 3 services with no errors.
2. Confirm Ollama has pulled/has access to the chosen chat + embedding models (may need a one-time `docker compose exec ollama ollama pull <model>` documented in README).
3. Open the frontend in a browser, upload a sample PDF and a sample TXT file (separately) — confirm each replaces the prior document in Chroma.
4. Ask a question with a factual answer clearly present in the uploaded doc — confirm the answer reflects that content (not hallucinated).
5. Ask a question unrelated to the doc's content — confirm the app either says it doesn't know or clearly hedges, rather than confidently inventing an answer.
6. Restart the `app` container only — confirm Chroma (separate service/volume) retains the last uploaded document's embeddings.
