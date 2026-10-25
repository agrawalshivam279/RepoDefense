from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify that the root endpoint returns service identification and docs link."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert data["docs"] == f"{settings.API_V1_STR}/docs"


def test_health_check_endpoint():
    """Verify that GET /api/health returns HTTP 200 with valid health schema."""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert "timestamp" in data


def test_cors_preflight():
    """Verify that CORS middleware responds appropriately to allowed origins."""
    response = client.options(
        f"{settings.API_V1_STR}/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
