import importlib

from app import config


def test_defaults_when_env_not_set(monkeypatch):
    for var in [
        "OLLAMA_BASE_URL",
        "OLLAMA_CHAT_MODEL",
        "OLLAMA_EMBED_MODEL",
        "CHROMA_HOST",
        "CHROMA_PORT",
        "CHROMA_COLLECTION",
        "CHUNK_SIZE",
        "CHUNK_OVERLAP",
        "TOP_K",
        "SIMILARITY_THRESHOLD",
        "MAX_UPLOAD_MB",
    ]:
        monkeypatch.delenv(var, raising=False)

    importlib.reload(config)
    settings = config.Settings()

    assert settings.OLLAMA_BASE_URL == "http://ollama:11434"
    assert settings.OLLAMA_CHAT_MODEL == "llama3.1"
    assert settings.OLLAMA_EMBED_MODEL == "nomic-embed-text"
    assert settings.CHROMA_HOST == "chromadb"
    assert settings.CHROMA_PORT == 8000
    assert settings.CHUNK_SIZE == 800
    assert settings.CHUNK_OVERLAP == 100
    assert settings.TOP_K == 4
    assert settings.SIMILARITY_THRESHOLD == 0.35
    assert settings.MAX_UPLOAD_MB == 20


def test_env_vars_override_defaults(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "500")
    monkeypatch.setenv("OLLAMA_CHAT_MODEL", "phi3")

    settings = config.Settings()

    assert settings.CHUNK_SIZE == 500
    assert settings.OLLAMA_CHAT_MODEL == "phi3"
