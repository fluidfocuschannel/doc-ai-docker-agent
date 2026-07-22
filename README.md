# doc-ai-docker-agent

A locally-hosted RAG (Retrieval-Augmented Generation) document Q&A app. Upload a single PDF or TXT document and ask questions about it — everything runs in Docker, with no external API keys required (Ollama for chat + embeddings, ChromaDB for the vector store).

This project is a teaching example for a Udemy course on using Claude Code.

See `docs/PRD.md`, `docs/TECHNICAL_DESIGN.md`, and `docs/WBS.md` for full requirements, architecture, and build status.

## Setup & Run

1. Copy `.env.example` to `.env` (defaults work out of the box).
2. Build and start the stack:
   ```bash
   docker compose up --build
   ```
3. One-time model pull (first run only — models persist in the `ollama_data` volume):
   ```bash
   docker compose exec ollama ollama pull nomic-embed-text
   docker compose exec ollama ollama pull llama3.1   # or a smaller model, e.g. phi3 — set OLLAMA_CHAT_MODEL in .env to match
   ```
4. Open http://localhost:8000, upload a PDF or TXT file, then ask questions about it.

Check `http://localhost:8000/health` to confirm the app can reach both Ollama and Chroma.

## Development

This project follows TDD: every backend story is implemented red → green → refactor. See `docs/TECHNICAL_DESIGN.md` §9 and `CLAUDE.md` for the testing setup.

```bash
pytest -m "not integration"   # fast unit/API test loop, no Docker required
pytest -m integration         # requires the full docker-compose stack running
```
