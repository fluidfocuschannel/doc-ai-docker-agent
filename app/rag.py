from dataclasses import dataclass

import chromadb
import httpx

from app.config import settings

COLLECTION_METADATA = {"hnsw:space": "cosine"}


@dataclass
class RetrievedChunk:
    text: str
    score: float
    chunk_index: int


def get_chroma_client():
    return chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)


def _create_collection(client):
    return client.get_or_create_collection(settings.CHROMA_COLLECTION, metadata=COLLECTION_METADATA)


def get_collection(client=None):
    client = client or get_chroma_client()
    return _create_collection(client)


def reset_collection(client=None):
    client = client or get_chroma_client()
    try:
        client.delete_collection(settings.CHROMA_COLLECTION)
    except Exception:
        pass
    return _create_collection(client)


def _ping(url: str, timeout: float = 2.0) -> bool:
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def check_ollama() -> bool:
    return _ping(f"{settings.OLLAMA_BASE_URL}/api/tags")


def check_chroma() -> bool:
    return _ping(f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}/api/v2/heartbeat")


def _ollama_post(path: str, payload: dict, timeout: float) -> dict:
    response = httpx.post(f"{settings.OLLAMA_BASE_URL}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def embed_text(text: str) -> list[float]:
    body = _ollama_post(
        "/api/embeddings",
        {"model": settings.OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=30.0,
    )
    return body["embedding"]


def store_chunks(chunks: list[str], source: str, client=None):
    collection = reset_collection(client)

    if not chunks:
        return collection

    ids = [f"{source}-{i}" for i in range(len(chunks))]
    embeddings = [embed_text(chunk) for chunk in chunks]
    metadatas = [{"filename": source, "chunk_index": i} for i in range(len(chunks))]

    collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    return collection


def has_document(client=None) -> bool:
    return get_collection(client).count() > 0


def get_document_status(client=None) -> dict:
    collection = get_collection(client)
    count = collection.count()
    if count == 0:
        return {"filename": None, "chunk_count": 0}

    stored = collection.get(limit=1)
    filename = stored["metadatas"][0]["filename"]
    return {"filename": filename, "chunk_count": count}


def clear_document(client=None):
    return reset_collection(client)


def retrieve(question: str, top_k: int, client=None) -> list[RetrievedChunk]:
    collection = get_collection(client)
    query_embedding = embed_text(question)

    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    retrieved = []
    for text, distance, metadata in zip(
        results["documents"][0], results["distances"][0], results["metadatas"][0]
    ):
        retrieved.append(
            RetrievedChunk(text=text, score=1.0 - distance, chunk_index=metadata["chunk_index"])
        )

    return retrieved


HEDGE_RESPONSE = "I couldn't find anything about that in the uploaded document."

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions using ONLY the "
    "provided document excerpts. If the excerpts do not contain the answer, "
    "say so clearly instead of guessing."
)


def is_grounded(chunks: list[RetrievedChunk]) -> bool:
    return bool(chunks) and chunks[0].score >= settings.SIMILARITY_THRESHOLD


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(f"[chunk {c.chunk_index}] {c.text}" for c in chunks)
    return (
        f"System: {SYSTEM_PROMPT}\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    if not is_grounded(chunks):
        return HEDGE_RESPONSE

    prompt = build_prompt(question, chunks)
    body = _ollama_post(
        "/api/chat",
        {
            "model": settings.OLLAMA_CHAT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=60.0,
    )
    return body["message"]["content"]


def format_response(answer: str, chunks: list[RetrievedChunk], grounded: bool) -> dict:
    return {
        "answer": answer,
        "grounded": grounded,
        "sources": [
            {"chunk_index": c.chunk_index, "score": c.score, "excerpt": c.text}
            for c in chunks
        ]
        if grounded
        else [],
    }
