def test_root_serves_index_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text.lower()


def test_health_returns_ok(client, mocker):
    mocker.patch("app.main.check_ollama", return_value=True)
    mocker.patch("app.main.check_chroma", return_value=True)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ollama"] is True
    assert body["chroma"] is True


def test_health_reports_dependency_down(client, mocker):
    mocker.patch("app.main.check_ollama", return_value=False)
    mocker.patch("app.main.check_chroma", return_value=True)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["ollama"] is False
