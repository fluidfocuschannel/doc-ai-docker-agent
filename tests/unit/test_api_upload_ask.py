import io

from app import ingest, rag


def test_upload_success(client, mocker):
    mocker.patch("app.ingest.extract_text", return_value="some extracted text")
    mocker.patch("app.ingest.chunk_text", return_value=["chunk one", "chunk two"])
    mocker.patch("app.rag.store_chunks")

    response = client.post(
        "/upload",
        files={"file": ("sample.txt", io.BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["filename"] == "sample.txt"
    assert body["chunks_stored"] == 2


def test_upload_rejects_unsupported_type(client, mocker):
    mocker.patch(
        "app.ingest.extract_text",
        side_effect=ingest.UnsupportedFileTypeError("nope"),
    )

    response = client.post(
        "/upload",
        files={"file": ("sample.docx", io.BytesIO(b"hello"), "application/octet-stream")},
    )

    assert response.status_code == 400


def test_upload_rejects_oversized_file(client, mocker):
    mocker.patch("app.main.settings.MAX_UPLOAD_MB", 0)

    response = client.post(
        "/upload",
        files={"file": ("sample.txt", io.BytesIO(b"hello world"), "text/plain")},
    )

    assert response.status_code == 413


def test_upload_rejects_empty_document(client, mocker):
    mocker.patch(
        "app.ingest.extract_text",
        side_effect=ingest.EmptyDocumentError("empty"),
    )

    response = client.post(
        "/upload",
        files={"file": ("empty.txt", io.BytesIO(b"   "), "text/plain")},
    )

    assert response.status_code == 422


def test_upload_returns_502_when_store_fails(client, mocker):
    mocker.patch("app.ingest.extract_text", return_value="text")
    mocker.patch("app.ingest.chunk_text", return_value=["chunk"])
    mocker.patch("app.rag.store_chunks", side_effect=ConnectionError("boom"))

    response = client.post(
        "/upload",
        files={"file": ("sample.txt", io.BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 502


def test_ask_success(client, mocker):
    chunk = rag.RetrievedChunk(text="Refunds within 30 days.", score=0.9, chunk_index=0)
    mocker.patch("app.rag.has_document", return_value=True)
    mocker.patch("app.rag.retrieve", return_value=[chunk])
    mocker.patch("app.rag.generate_answer", return_value="You get a refund within 30 days.")

    response = client.post("/ask", json={"question": "What is the refund window?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "You get a refund within 30 days."
    assert body["grounded"] is True
    assert body["sources"][0]["chunk_index"] == 0


def test_ask_rejects_empty_question(client):
    response = client.post("/ask", json={"question": "   "})

    assert response.status_code == 400


def test_ask_rejects_when_no_document_uploaded(client, mocker):
    mocker.patch("app.rag.has_document", return_value=False)

    response = client.post("/ask", json={"question": "What is the refund window?"})

    assert response.status_code == 400


def test_ask_returns_502_when_dependency_unreachable(client, mocker):
    mocker.patch("app.rag.has_document", return_value=True)
    mocker.patch("app.rag.retrieve", side_effect=ConnectionError("boom"))

    response = client.post("/ask", json={"question": "What is the refund window?"})

    assert response.status_code == 502


def test_get_document_status_when_none_uploaded(client, mocker):
    mocker.patch("app.rag.get_document_status", return_value={"filename": None, "chunk_count": 0})

    response = client.get("/document")

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] is None
    assert body["chunk_count"] == 0


def test_get_document_status_when_uploaded(client, mocker):
    mocker.patch(
        "app.rag.get_document_status",
        return_value={"filename": "sample.txt", "chunk_count": 3},
    )

    response = client.get("/document")

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "sample.txt"
    assert body["chunk_count"] == 3


def test_delete_document_clears_current_document(client, mocker):
    mock_clear = mocker.patch("app.rag.clear_document")

    response = client.delete("/document")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_clear.assert_called_once()


def test_delete_document_returns_502_when_dependency_unreachable(client, mocker):
    mocker.patch("app.rag.clear_document", side_effect=ConnectionError("boom"))

    response = client.delete("/document")

    assert response.status_code == 502
