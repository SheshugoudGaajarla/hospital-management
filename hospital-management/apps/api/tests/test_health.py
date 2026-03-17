from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers.get("x-request-id")


def test_metrics_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "hospital_http_requests_total" in response.text
    assert "hospital_http_request_duration_seconds" in response.text
