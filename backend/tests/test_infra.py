from pathlib import Path

from app.core.redis import _redact_redis_url

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


def test_redact_redis_url_masks_password():
    """Verify that _redact_redis_url strips embedded credentials including unescaped '#'."""
    masked = _redact_redis_url("rediss://default:super-secret-token@upstash.io:6379")
    assert "super-secret-token" not in masked
    assert "upstash.io:6379" in masked
    assert _redact_redis_url("redis://localhost:6379/0") == "redis://localhost:6379/0"

    hash_masked = _redact_redis_url("redis://default:abc123#xyz789@redis.example:6379/0")
    assert "abc123" not in hash_masked and "xyz789" not in hash_masked
    assert "redis.example:6379/0" in hash_masked

    no_colon_hash = _redact_redis_url("redis://prefixSecret#suffixSecret@redis.example:6379/0")
    assert "prefixSecret" not in no_colon_hash and "suffixSecret" not in no_colon_hash


def test_get_arq_redis_pool_failure_logs_redacted_url():
    """Verify connection failure warning logs never expose password prefix/suffix around '#'."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    import app.core.redis as redis_mod

    saved_pool = redis_mod._arq_redis_pool
    redis_mod._arq_redis_pool = None
    mock_logger = MagicMock()
    try:
        for bad_dsn, prefix, suffix in [
            ("redis://default:abcPrefix#xyzSuffix@redis.example:6379/0", "abcPrefix", "xyzSuffix"),
            ("redis://onlyPrefix#onlySuffix@redis.example:6379/0", "onlyPrefix", "onlySuffix"),
        ]:
            with (
                patch.object(redis_mod.settings, "REDIS_URL", bad_dsn),
                patch.object(redis_mod, "create_pool", AsyncMock(side_effect=OSError("conn err"))),
                patch.object(redis_mod, "logger", mock_logger),
            ):
                pool = asyncio.run(redis_mod.get_arq_redis_pool())
                assert pool is None
            logged_kwargs = mock_logger.warning.call_args.kwargs
            assert prefix not in logged_kwargs["redis_url"]
            assert suffix not in logged_kwargs["redis_url"]
    finally:
        redis_mod._arq_redis_pool = saved_pool
