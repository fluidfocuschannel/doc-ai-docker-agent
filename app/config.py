from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_CHAT_MODEL: str = "qwen2.5:0.5b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "current_document"

    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K: int = 4
    SIMILARITY_THRESHOLD: float = 0.35
    MAX_UPLOAD_MB: int = 20


settings = Settings()
