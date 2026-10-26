import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.analyzers.dependencies import extract_file_dependencies
from app.analyzers.dependencies.infra import (
    parse_docker_compose,
    parse_dockerfile,
    parse_github_actions_workflow,
)
from app.core.database import AsyncSessionLocal, engine
from app.models.analysis import Dependency
from app.models.project import Project, RepositorySnapshot, User
from app.workers.cloner import clone_and_sanitize_repository


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test runs."""
    yield
    await engine.dispose()


def test_parse_dockerfile_multi_stage():
    """Verifies Dockerfile multi-stage builds and dev stage classification."""
    content = """
FROM --platform=linux/amd64 node:20-alpine AS builder
WORKDIR /app
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/dist ./dist

FROM scratch
"""
    deps = parse_dockerfile(content, file_path="Dockerfile")
    assert len(deps) == 2

    builder_dep = deps[0]
    assert builder_dep.name == "node"
    assert builder_dep.version == "20-alpine"
    assert builder_dep.is_dev is True

    runner_dep = deps[1]
    assert runner_dep.name == "node"
    assert runner_dep.version == "20-alpine"
    assert runner_dep.is_dev is False


def test_parse_dockerfile_single_stage():
    """Verifies standard single-stage Dockerfile parsing."""
    content = "FROM python:3.12-slim\nEXPOSE 8000\n"
    deps = parse_dockerfile(content, file_path="backend/Dockerfile")
    assert len(deps) == 1
    assert deps[0].name == "python"
    assert deps[0].version == "3.12-slim"
    assert deps[0].is_dev is False


def test_parse_docker_compose():
    """Verifies parsing of remote images and local build context in docker-compose.yml."""
    content = """
services:
  postgres:
    image: pgvector/pgvector:pg17
    ports:
      - "5432:5432"
  redis:
    image: redis:7-alpine
  backend:
    build: ./backend
"""
    deps = parse_docker_compose(content, file_path="docker-compose.yml")
    assert len(deps) == 3

    dep_map = {d.name: d for d in deps}
    assert dep_map["pgvector/pgvector"].version == "pg17"
    assert dep_map["pgvector/pgvector"].is_dev is False

    assert dep_map["redis"].version == "7-alpine"
    assert dep_map["redis"].is_dev is False

    assert dep_map["backend"].version == "local-build"
    assert dep_map["backend"].is_dev is False


def test_parse_github_actions_workflow():
    """Verifies extraction and de-duplication of GitHub Actions workflow uses clauses."""
    content = """
name: CI
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
"""
    deps = parse_github_actions_workflow(content, file_path=".github/workflows/ci.yml")
    assert len(deps) == 3

    names = [d.name for d in deps]
    assert names == ["actions/checkout", "actions/setup-python", "docker/build-push-action"]
    assert all(d.is_dev for d in deps)


def test_infra_dispatch():
    """Verifies that high-level dispatcher routes Docker, Compose, and Actions files."""
    df_bytes = b"FROM python:3.12-slim\n"
    deps_df = extract_file_dependencies("Dockerfile", df_bytes)
    assert len(deps_df) == 1
    assert deps_df[0].name == "python"

    dc_bytes = b"services:\n  redis:\n    image: redis:7\n"
    deps_dc = extract_file_dependencies("docker-compose.yml", dc_bytes)
    assert len(deps_dc) == 1
    assert deps_dc[0].name == "redis"

    ga_bytes = b"jobs:\n  build:\n    steps:\n      - uses: actions/checkout@v4\n"
    deps_ga = extract_file_dependencies(".github/workflows/ci.yml", ga_bytes)
    assert len(deps_ga) == 1
    assert deps_ga[0].name == "actions/checkout"


@pytest.mark.anyio
async def test_cloner_worker_infra_and_manifest_pipeline():
    """Verifies end-to-end repository cloning with AST and multi-ecosystem dependency extraction."""
    test_email = f"cloner_full_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="full-ecosystem-repo",
            github_url="https://github.com/test/full-eco-repo",
            default_branch="main",
            status="pending",
        )
        session.add(user)
        session.add(project)
        await session.commit()

    test_commit_hash = "9d1234567890abcdef1234567890abcdef123456"

    async def mock_clone(url, branch, target_dir, timeout=120.0):
        # 1. Source files
        (target_dir / "main.py").write_text("def start(): pass\n", encoding="utf-8")
        # 2. Python manifest
        (target_dir / "requirements.txt").write_text("fastapi==0.115.0\n", encoding="utf-8")
        # 3. Node manifest
        (target_dir / "package.json").write_text(
            '{"dependencies": {"next": "15.5.28"}}',
            encoding="utf-8",
        )
        # 4. Infrastructure configs
        (target_dir / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
        (target_dir / "docker-compose.yml").write_text(
            "services:\n  redis:\n    image: redis:7-alpine\n",
            encoding="utf-8",
        )
        return test_commit_hash

    try:
        with patch("app.workers.cloner.run_git_shallow_clone", side_effect=mock_clone):
            result = await clone_and_sanitize_repository({}, str(project_id))
            assert result["status"] == "cloned"
            assert result["commit_hash"] == test_commit_hash
            assert result["dependency_count"] >= 4

        # Verify DB records
        async with AsyncSessionLocal() as session:
            stmt = select(RepositorySnapshot).where(RepositorySnapshot.project_id == project_id)
            snapshot = (await session.execute(stmt)).scalar_one()
            assert "dependencies" in snapshot.summary

            stmt_deps = select(Dependency).where(Dependency.project_id == project_id)
            db_deps = (await session.execute(stmt_deps)).scalars().all()
            dep_names = [d.name for d in db_deps]

            assert "fastapi" in dep_names
            assert "next" in dep_names
            assert "python" in dep_names
            assert "redis" in dep_names

    finally:
        async with AsyncSessionLocal() as session:
            u = await session.get(User, user_id)
            if u:
                await session.delete(u)
                await session.commit()
