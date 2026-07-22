from app.rag import RetrievedChunk, build_prompt, generate_answer, format_response


def test_build_prompt_includes_context_and_question():
    chunks = [
        RetrievedChunk(text="Refunds within 30 days.", score=0.9, chunk_index=0),
        RetrievedChunk(text="Support hours are 9-5.", score=0.8, chunk_index=1),
    ]

    prompt = build_prompt("What is the refund window?", chunks)

    assert "[chunk 0]" in prompt
    assert "Refunds within 30 days." in prompt
    assert "[chunk 1]" in prompt
    assert "What is the refund window?" in prompt


def test_generate_answer_calls_ollama_chat(mocker):
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"message": {"content": "You get a refund within 30 days."}}
    mock_response.raise_for_status = mocker.Mock()
    mock_post = mocker.patch("app.rag.httpx.post", return_value=mock_response)

    chunks = [RetrievedChunk(text="Refunds within 30 days.", score=0.9, chunk_index=0)]

    answer = generate_answer("What is the refund window?", chunks)

    assert answer == "You get a refund within 30 days."
    mock_post.assert_called_once()


def test_generate_answer_hedges_when_no_chunks_meet_threshold(mocker):
    mock_post = mocker.patch("app.rag.httpx.post")

    answer = generate_answer("What is the refund window?", [])

    mock_post.assert_not_called()
    assert "don't" in answer.lower() or "couldn't find" in answer.lower()


def test_format_response_grounded():
    chunks = [RetrievedChunk(text="Refunds within 30 days.", score=0.9, chunk_index=0)]

    response = format_response("You get a refund within 30 days.", chunks, grounded=True)

    assert response["answer"] == "You get a refund within 30 days."
    assert response["grounded"] is True
    assert response["sources"][0]["chunk_index"] == 0
    assert response["sources"][0]["score"] == 0.9
    assert response["sources"][0]["excerpt"] == "Refunds within 30 days."


def test_format_response_not_grounded_has_no_sources():
    response = format_response("I couldn't find that in the document.", [], grounded=False)

    assert response["grounded"] is False
    assert response["sources"] == []
