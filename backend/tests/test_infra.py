from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_env_example_presence_and_keys():
    """Verify that .env.example exists and contains all required architectural keys."""
    env_file = REPO_ROOT / ".env.example"
    assert env_file.exists(), ".env.example file must exist at project root"

    content = env_file.read_text(encoding="utf-8")
    expected_keys = [
        "PROJECT_NAME",
        "VERSION",
        "DATABASE_URL",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "REDIS_URL",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "FREELLMAPI_BASE_URL",
        "FREELLMAPI_API_KEY",
    ]

    for key in expected_keys:
        assert f"{key}=" in content, f"Missing required configuration key {key} in .env.example"


def test_docker_compose_structure_and_services():
    """Verify that docker-compose.yml properly declares postgres (pgvector), redis, and backend."""
    compose_file = REPO_ROOT / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml must exist at project root"

    content = compose_file.read_text(encoding="utf-8")

    # Assert services
    assert "postgres:" in content
    assert "image: pgvector/pgvector:pg17" in content
    assert "5432:5432" in content
    assert "pg_isready" in content

    assert "redis:" in content
    assert "image: redis:7-alpine" in content
    assert "6379:6379" in content
    assert "redis-cli" in content

    assert "backend:" in content
    assert "dockerfile: Dockerfile" in content
    assert "8000:8000" in content

    # Assert named volumes
    assert "postgres_data:" in content
    assert "redis_data:" in content


def test_dockerfile_security_and_non_root():
    """Verify that backend/Dockerfile enforces Python 3.12 and non-root execution."""
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    assert dockerfile.exists(), "backend/Dockerfile must exist"

    content = dockerfile.read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in content
    assert "USER appuser" in content
    assert "EXPOSE 8000" in content
    assert "uvicorn" in content
