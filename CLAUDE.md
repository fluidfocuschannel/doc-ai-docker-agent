# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This repository currently contains only planning documents (`docs/`) — no application code has been written yet. Before implementing, read the docs below in order; they are the source of truth for architecture and scope decisions. Do not invent alternative stacks or scope — follow what's specified unless the user directs otherwise.

- `docs/PRD.md` — product requirements, scope, and out-of-scope list
- `docs/TECHNICAL_DESIGN.md` — architecture, API contracts, data model, config
- `docs/WBS.md` — build order and task breakdown (build in this dependency order: scaffolding → Docker → app shell → ingestion → embedding/vector store → generation → API → frontend → integration testing → docs)

## What This Project Is

A locally-hosted RAG (Retrieval-Augmented Generation) document Q&A app, built as a teaching example for a Udemy course on Claude Code. A user uploads a single PDF or TXT document and asks questions about it in a chat UI. Everything runs in Docker with no external API keys — Ollama provides both chat and embedding models, ChromaDB is the vector store.

Key scope constraints to preserve when implementing or extending:
- **Single document at a time** — uploading a new file replaces the current one (Chroma collection is reset on each upload), not appended to a multi-doc corpus.
- **Fully local** — no cloud LLM fallback (Anthropic/OpenAI); this is intentional, not a gap to fill in.
- **No auth, no multi-user, no streaming** — explicitly out of scope for v1 per the PRD.

## Architecture (target, per `docs/TECHNICAL_DESIGN.md`)

Three Docker Compose services on a shared network, addressed by service name:
- `app` — FastAPI backend + static HTML/JS frontend (no frontend framework/build step)
- `ollama` — local LLM serving chat (`OLLAMA_CHAT_MODEL`) and embeddings (`OLLAMA_EMBED_MODEL`)
- `chromadb` — vector store, single collection `current_document`

Request flow:
```
POST /upload → extract text (pypdf/plain read) → chunk → embed via Ollama → reset + upsert into Chroma
POST /ask    → embed question → retrieve top-k chunks from Chroma → below SIMILARITY_THRESHOLD? hedge : build prompt → Ollama chat → answer
```

Module responsibilities (see `docs/TECHNICAL_DESIGN.md` §3 for full contracts):
- `app/main.py` — FastAPI routes (`/`, `/health`, `/upload`, `/ask`) and static file mounting
- `app/config.py` — all tunables (chunk size/overlap, top-k, similarity threshold, model names) loaded from env vars — change behavior here, not via hardcoded values in other modules
- `app/ingest.py` — text extraction + chunking (pure functions, no I/O to Ollama/Chroma)
- `app/rag.py` — all Ollama and Chroma calls: embedding, storage/reset, retrieval, answer generation
- `app/static/` — plain HTML/CSS/JS frontend, no build step

Since retrieval scores gate whether the LLM is even called (see `SIMILARITY_THRESHOLD` in config), avoid "fixing" perceived hallucination by just prompting harder — the intended fix is tuning the threshold or chunking, not the prompt.

## Development Process: TDD is Mandatory

Every backend story (any leaf item in `docs/WBS.md` with a "TDD steps" block) must be implemented red → green → refactor:
1. Write a failing test in `tests/unit/` or `tests/` (or a `tests/integration/` test for Phase 9 items) that captures the story's acceptance criteria — before writing implementation code.
2. Write the minimal implementation to make it pass.
3. Refactor while keeping the suite green.
4. Update that story's status in `docs/WBS.md` (`⬜ → ✅`) in the same change. Do not batch WBS status updates until the end of a phase — update per story as it completes.

Items marked `N/A` in the WBS (Docker/YAML config, frontend JS, static markup) don't get a pytest cycle — verify those manually per the WBS notes instead of skipping verification entirely.

Mocking rules (see `docs/TECHNICAL_DESIGN.md` §9): unit and API-layer tests must never require the Docker stack to be running — mock Ollama HTTP calls and use Chroma's in-memory client, not `HttpClient`. Only `tests/integration/` (marked `@pytest.mark.integration`) talks to the real `docker compose` stack.

## Commands

No code exists yet, so there is nothing to run yet. Once implemented per the WBS, the expected commands are:

```bash
docker compose up --build                               # start app, ollama, chromadb
docker compose exec ollama ollama pull <chat-model>      # one-time model pull
docker compose exec ollama ollama pull <embed-model>     # one-time model pull

pytest -m "not integration"                              # fast unit/API loop, no Docker required
pytest tests/unit/test_ingest.py::test_chunk_text         # run a single test
pytest -m integration                                    # full stack must be running via docker compose first
```
