import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.core.redis import enqueue_clone_job, get_redis_settings
from app.models.project import Project, RepositorySnapshot, User
from app.workers.cloner import (
    clone_and_sanitize_repository,
    run_git_shallow_clone,
    sanitize_git_branch,
)
from app.workers.main import WorkerSettings


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test runs."""
    yield
    await engine.dispose()


# --- Unit Tests: Branch Sanitization ---


def test_sanitize_git_branch_valid():
    """Verifies that legitimate git branch names pass validation."""
    valid_branches = [
        "main",
        "master",
        "feature/add-login",
        "release_v1.0.0",
        "fix/issue-123.4",
        "v2.1.0-rc1",
    ]
    for branch in valid_branches:
        assert sanitize_git_branch(branch) == branch


def test_sanitize_git_branch_invalid():
    """Verifies that malicious or malformed branch names are rejected."""
    invalid_branches = [
        "",  # Empty
        "   ",  # Whitespace only
        "--upload-pack=evil",  # Leading dash argument injection
        "-f",  # Short flag
        "feature/../main",  # Path traversal
        "branch with spaces",  # Spaces
        "branch;rm -rf /",  # Semicolon injection
        "branch`whoami`",  # Backtick command substitution
        "branch$FOO",  # Dollar variable expansion
    ]
    for branch in invalid_branches:
        with pytest.raises(ValueError):
            sanitize_git_branch(branch)


# --- Unit Tests: Git Subprocess Execution ---


@pytest.mark.anyio
async def test_run_git_shallow_clone_success():
    """Verifies git clone and rev-parse subprocess invocation returns commit hash."""
    mock_clone_proc = AsyncMock()
    mock_clone_proc.returncode = 0
    mock_clone_proc.communicate.return_value = (b"", b"")

    mock_rev_proc = AsyncMock()
    mock_rev_proc.returncode = 0
    mock_rev_proc.communicate.return_value = (
        b"4b825dc642cb6eb9a060e54bf8d69288fbee4904\n",
        b"",
    )

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_clone_proc, mock_rev_proc]):
        with tempfile.TemporaryDirectory() as td:
            commit = await run_git_shallow_clone(
                github_url="https://github.com/fastapi/fastapi",
                branch="master",
                target_dir=Path(td),
            )
            assert commit == "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


@pytest.mark.anyio
async def test_run_git_shallow_clone_clone_error():
    """Verifies that git clone failure raises RuntimeError with stderr message."""
    mock_clone_proc = AsyncMock()
    mock_clone_proc.returncode = 128
    mock_clone_proc.communicate.return_value = (
        b"",
        b"fatal: repository 'https://github.com/nonexistent/repo' not found",
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_clone_proc):
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(
                RuntimeError,
                match="repository 'https://github.com/nonexistent/repo' not found",
            ):
                await run_git_shallow_clone(
                    github_url="https://github.com/nonexistent/repo",
                    branch="main",
                    target_dir=Path(td),
                )


@pytest.mark.anyio
async def test_run_git_shallow_clone_rev_parse_error():
    """Verifies that rev-parse failure raises RuntimeError."""
    mock_clone_proc = AsyncMock()
    mock_clone_proc.returncode = 0
    mock_clone_proc.communicate.return_value = (b"", b"")

    mock_rev_proc = AsyncMock()
    mock_rev_proc.returncode = 1
    mock_rev_proc.communicate.return_value = (b"", b"fatal: not a git repository")

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_clone_proc, mock_rev_proc]):
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(RuntimeError, match="git rev-parse HEAD failed"):
                await run_git_shallow_clone(
                    github_url="https://github.com/test/repo",
                    branch="main",
                    target_dir=Path(td),
                )


# --- Integration Tests: Worker Task Execution ---


@pytest.mark.anyio
async def test_clone_and_sanitize_repository_success():
    """Tests full clone, sanitize, and snapshot workflow on a database project."""
    test_email = f"worker_test_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="test-repo",
            github_url="https://github.com/test/test-repo",
            default_branch="main",
            status="pending",
        )
        session.add(user)
        session.add(project)
        await session.commit()

    test_commit_hash = "abc1234567890def1234567890abcdef12345678"

    # Side-effect to write a mock file into target_dir when clone is called
    async def mock_clone(url, branch, target_dir, timeout=120.0):
        (target_dir / "main.py").write_text("print('hello')", encoding="utf-8")
        return test_commit_hash

    try:
        with patch("app.workers.cloner.run_git_shallow_clone", side_effect=mock_clone):
            result = await clone_and_sanitize_repository({}, str(project_id))
            assert result["status"] == "cloned"
            assert result["commit_hash"] == test_commit_hash
            assert result["file_count"] >= 1

        # Verify DB state
        async with AsyncSessionLocal() as session:
            db_project = await session.get(Project, project_id)
            assert db_project is not None
            assert db_project.status == "cloned"

            stmt = select(RepositorySnapshot).where(RepositorySnapshot.project_id == project_id)
            snapshot = (await session.execute(stmt)).scalar_one_or_none()
            assert snapshot is not None
            assert snapshot.commit_hash == test_commit_hash
            assert "Cloned commit abc1234" in snapshot.summary

    finally:
        # Cleanup
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                await session.delete(user)
                await session.commit()


@pytest.mark.anyio
async def test_clone_and_sanitize_repository_failure_updates_status():
    """Verifies that an error in git clone transitions Project.status to 'failed'."""
    test_email = f"worker_fail_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="fail-repo",
            github_url="https://github.com/fail/fail-repo",
            default_branch="main",
            status="pending",
        )
        session.add(user)
        session.add(project)
        await session.commit()

    try:
        with patch(
            "app.workers.cloner.run_git_shallow_clone",
            side_effect=RuntimeError("fatal: clone timeout"),
        ):
            result = await clone_and_sanitize_repository({}, str(project_id))
            assert result["status"] == "failed"
            assert "fatal: clone timeout" in result["error"]

        async with AsyncSessionLocal() as session:
            db_project = await session.get(Project, project_id)
            assert db_project is not None
            assert db_project.status == "failed"

    finally:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                await session.delete(user)
                await session.commit()


@pytest.mark.anyio
async def test_clone_and_sanitize_nonexistent_project():
    """Verifies graceful handling when the project UUID is not found in database."""
    random_id = str(uuid.uuid4())
    result = await clone_and_sanitize_repository({}, random_id)
    assert result["status"] == "failed"
    assert "not found" in result["error"]


def test_arq_worker_settings():
    """Verifies WorkerSettings exposes required functions and config."""
    assert clone_and_sanitize_repository in WorkerSettings.functions
    assert WorkerSettings.job_timeout == 300
    assert WorkerSettings.max_jobs == 10
    settings_obj = get_redis_settings()
    assert settings_obj is not None


@pytest.mark.anyio
async def test_enqueue_clone_job_offline_graceful():
    """Verifies that enqueue_clone_job returns None gracefully when Redis is offline."""
    with patch("app.core.redis.get_arq_redis_pool", return_value=None):
        job_id = await enqueue_clone_job(uuid.uuid4())
        assert job_id is None
