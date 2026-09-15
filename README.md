# doc-ai-docker-agent

A locally-hosted RAG (Retrieval-Augmented Generation) document Q&A app. Upload a single PDF or TXT document and ask questions about it — everything runs in Docker, with no external API keys required (Ollama for chat + embeddings, ChromaDB for the vector store).

This project is a teaching example for a Udemy course on using Claude Code.

See `docs/PRD.md`, `docs/TECHNICAL_DESIGN.md`, and `docs/WBS.md` for full requirements, architecture, and build status.

## Architecture

Three services run on a shared Docker Compose network, addressed by service name:

| Service    | Image                    | Port (host)                | Role                                   |
|------------|--------------------------|-----------------------------|-----------------------------------------|
| `app`      | built from `Dockerfile`  | `8000` → `8000`             | FastAPI backend + static frontend      |
| `ollama`   | `ollama/ollama:latest`   | `11434` → `11434`           | Local chat + embedding model serving   |
| `chromadb` | `chromadb/chroma:latest` | `8001` → `8000` (container) | Vector store (single collection)       |

Request flow:

```
POST /upload → extract text (pypdf/plain read) → chunk → embed via Ollama → reset + upsert into Chroma
POST /ask    → embed question → retrieve top-k chunks from Chroma → below SIMILARITY_THRESHOLD? hedge : build prompt → Ollama chat → answer
```

The app is **single-document**: uploading a new file replaces whatever was previously loaded (the Chroma collection is reset each time), rather than adding to a multi-document corpus.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2) installed and running
- ~4–8 GB free disk space for model weights, depending on which chat model you pull
- No GPU required — the default models run fine on CPU, though a GPU will speed up responses if Docker has access to one

## Getting Started

### 1. Clone and configure environment variables

```bash
git clone <repo-url>
cd doc-ai-docker-agent
cp .env.example .env
```

The defaults in `.env.example` work out of the box:

```bash
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_CHAT_MODEL=qwen2.5:0.5b
OLLAMA_EMBED_MODEL=nomic-embed-text

CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_COLLECTION=current_document

CHUNK_SIZE=800
CHUNK_OVERLAP=100
TOP_K=4
SIMILARITY_THRESHOLD=0.35
MAX_UPLOAD_MB=20
```

You only need to edit `.env` if you want a different chat model (see [Choosing a chat model](#choosing-a-chat-model) below) or different chunking/retrieval tuning.

### 2. Build and start the stack

```bash
docker compose up --build
```

This builds the `app` image and starts all three containers. Leave it running in the foreground, or add `-d` to run detached:

```bash
docker compose up --build -d
```

Check everything is up:

```bash
docker compose ps
```

You should see `app`, `ollama`, and `chromadb` all in the `Up` state.

### 3. Pull the Ollama models (one-time, first run only)

The `ollama` container starts empty — it doesn't ship with any models baked in. Pull the embedding model and a chat model matching `OLLAMA_CHAT_MODEL` in your `.env`:

```bash
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull qwen2.5:0.5b
```

Models are stored in the `ollama_data` Docker volume, so this is a one-time step — they persist across `docker compose down` / `up` cycles (they only disappear if you remove the volume with `docker compose down -v`).

Verify the pull worked:

```bash
docker compose exec ollama ollama list
```

#### Choosing a chat model

`OLLAMA_CHAT_MODEL` in `.env` must exactly match a model you've pulled, or `/ask` will fail with a `502` ("Ollama or Chroma unreachable") — the error is generic, but the most common cause is a model-name mismatch, not an actual connectivity problem. Options, smallest to largest:

| Model              | Approx. size | Notes                                      |
|---------------------|-------------|---------------------------------------------|
| `qwen2.5:0.5b`       | ~400 MB     | Smallest/fastest, weaker reasoning quality   |
| `llama3.2:1b`        | ~1.3 GB     | Good quality-to-size ratio                   |
| `gemma2:2b`          | ~1.6 GB     | Stronger quality, still lightweight          |
| `phi3`               | ~2.2 GB     | Solid general-purpose default                |
| `llama3.1`           | ~4.7 GB     | Larger, better quality, slower on CPU        |

Pull whichever you choose the same way as above (`docker compose exec ollama ollama pull <model>`), then set `OLLAMA_CHAT_MODEL` in `.env` to match and restart the `app` service so it picks up the change:

```bash
docker compose up -d app
```

### 4. Open the app

Go to **http://localhost:8000** in a browser. Upload a `.pdf` or `.txt` file, then ask questions about it in the chat panel.

### 5. Confirm health

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "ollama": true, "chroma": true}
```

If `status` is `"degraded"`, check which of `ollama`/`chroma` is `false` and inspect that service's logs (`docker compose logs ollama` or `docker compose logs chromadb`).

## API Reference

All endpoints are served by the `app` container on port `8000`.

| Method | Path        | Description                                                        |
|--------|-------------|----------------------------------------------------------------------|
| GET    | `/`         | Serves the static frontend                                          |
| GET    | `/health`   | Reports whether Ollama and Chroma are reachable                     |
| POST   | `/upload`   | Uploads a PDF/TXT file; extracts, chunks, embeds, and stores it (replaces any existing document) |
| GET    | `/document` | Returns the currently loaded document's filename and chunk count (`null`/`0` if none uploaded) |
| DELETE | `/document` | Clears the currently loaded document without uploading a replacement |
| POST   | `/ask`      | Asks a question about the currently loaded document                 |

Examples:

```bash
# Upload a document
curl -X POST http://localhost:8000/upload -F "file=@sample.pdf"

# Check what's currently loaded
curl http://localhost:8000/document

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?"}'

# Clear the current document
curl -X DELETE http://localhost:8000/document
```

## Everyday Commands

```bash
docker compose up --build          # rebuild and start all services
docker compose up -d                # start in background
docker compose down                 # stop and remove containers (keeps volumes, i.e. models/vectors)
docker compose down -v              # stop and also wipe volumes (re-pull models next time)
docker compose logs -f app          # tail app logs
docker compose ps                   # list running services
docker compose restart app          # restart just the app (e.g. after editing .env)
```

## Troubleshooting

**"Ollama or Chroma unreachable" on `/ask`**
This 502 is a generic catch-all in `app/main.py`. In practice it usually means one of:
- `OLLAMA_CHAT_MODEL` doesn't match a pulled model — check with `docker compose exec ollama ollama list` and pull the missing one.
- The `ollama` or `chromadb` container isn't running — check with `docker compose ps` and `docker compose logs ollama` / `docker compose logs chromadb`.
- You changed `.env` but didn't restart the `app` container — run `docker compose up -d app`.

**Upload fails with "Unsupported file type"**
Only `.pdf` and `.txt` files are supported per the PRD scope — this is intentional, not a bug.

**Answers feel ungrounded or hallucinated**
Check `SIMILARITY_THRESHOLD` and `CHUNK_SIZE`/`CHUNK_OVERLAP` in `.env` first — retrieval quality is gated by these, not the prompt. See `docs/TECHNICAL_DESIGN.md` for tuning guidance.

**Ports already in use**
If `8000`, `8001`, or `11434` are taken by another process, stop that process or change the host-side port mapping in `docker-compose.yml`.

## Development

This project follows TDD: every backend story is implemented red → green → refactor. See `docs/TECHNICAL_DESIGN.md` §9 and `CLAUDE.md` for the testing setup.

```bash
pytest -m "not integration"   # fast unit/API test loop, no Docker required
pytest -m integration         # requires the full docker-compose stack running
```
