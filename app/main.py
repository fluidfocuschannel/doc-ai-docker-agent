import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import ingest, rag
from app.config import settings
from app.rag import check_chroma, check_ollama

STATIC_DIR = Path(__file__).parent / "static"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("doc_ai_agent")

app = FastAPI(title="Doc AI Agent")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    ollama_ok = check_ollama()
    chroma_ok = check_chroma()
    return {
        "status": "ok" if ollama_ok and chroma_ok else "degraded",
        "ollama": ollama_ok,
        "chroma": chroma_ok,
    }


class AskRequest(BaseModel):
    question: str


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds maximum upload size.")

    try:
        text = ingest.extract_text(contents, file.filename)
    except ingest.UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ingest.EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    chunks = ingest.chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)

    try:
        rag.store_chunks(chunks, source=file.filename)
    except Exception:
        logger.exception("Failed to store chunks for %s", file.filename)
        raise HTTPException(status_code=502, detail="Vector store or embedding service unreachable.")

    return {"status": "ok", "filename": file.filename, "chunks_stored": len(chunks)}


@app.post("/ask")
def ask(request: AskRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        if not rag.has_document():
            raise HTTPException(status_code=400, detail="No document has been uploaded yet.")

        chunks = rag.retrieve(question, settings.TOP_K)
        grounded = rag.is_grounded(chunks)
        answer = rag.generate_answer(question, chunks)
        return rag.format_response(answer, chunks, grounded)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to answer question")
        raise HTTPException(status_code=502, detail="Ollama or Chroma unreachable.")
