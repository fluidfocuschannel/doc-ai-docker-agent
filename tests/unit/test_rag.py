from app import rag


def test_embed_text_calls_ollama_with_expected_payload(mocker):
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
    mock_response.raise_for_status = mocker.Mock()
    mock_post = mocker.patch("app.rag.httpx.post", return_value=mock_response)

    vector = rag.embed_text("hello world")

    assert vector == [0.1, 0.2, 0.3]
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["prompt"] == "hello world"


def test_get_collection_creates_if_absent(memory_client):
    collection = rag.get_collection(client=memory_client)

    assert collection.name == rag.settings.CHROMA_COLLECTION
    assert collection.count() == 0


def test_get_collection_uses_cosine_space(memory_client):
    collection = rag.get_collection(client=memory_client)

    assert collection.metadata["hnsw:space"] == "cosine"


def test_store_chunks_replaces_previous_document(memory_client, mocker):
    mocker.patch("app.rag.embed_text", side_effect=lambda text: [len(text), 0.0])

    rag.store_chunks(["doc A chunk one", "doc A chunk two"], source="a.txt", client=memory_client)
    collection = rag.store_chunks(["doc B chunk one"], source="b.txt", client=memory_client)

    assert collection.count() == 1
    stored = collection.get()
    assert stored["metadatas"][0]["filename"] == "b.txt"


def test_store_chunks_sets_expected_ids_and_metadata(memory_client, mocker):
    mocker.patch("app.rag.embed_text", side_effect=lambda text: [len(text), 0.0])

    collection = rag.store_chunks(["chunk zero", "chunk one"], source="doc.txt", client=memory_client)

    stored = collection.get()
    assert set(stored["ids"]) == {"doc.txt-0", "doc.txt-1"}
    assert {"filename": "doc.txt", "chunk_index": 0} in stored["metadatas"]
    assert {"filename": "doc.txt", "chunk_index": 1} in stored["metadatas"]


def test_retrieve_returns_top_k_ordered_by_similarity(memory_client, mocker):
    def fake_embed(text):
        if "cat" in text:
            return [1.0, 0.0]
        if "dog" in text:
            return [0.0, 1.0]
        return [0.5, 0.5]

    mocker.patch("app.rag.embed_text", side_effect=fake_embed)

    rag.store_chunks(["all about cats", "all about dogs"], source="pets.txt", client=memory_client)

    results = rag.retrieve("tell me about cat", top_k=1, client=memory_client)

    assert len(results) == 1
    assert "cat" in results[0].text
    assert results[0].score is not None
