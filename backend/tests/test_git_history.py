import subprocess
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.analyzers.git import (
    DELIMITER,
    _parse_git_log_output,
    extract_git_history,
)
from app.core.database import AsyncSessionLocal, engine
from app.models.project import Project, RepositorySnapshot, User
from app.workers.cloner import clone_and_sanitize_repository


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test runs."""
    yield
    await engine.dispose()


def _init_git_repo(path: Path) -> None:
    """Helper to initialize a local git repo with standard test user configs."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test Committer"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@repodefense.dev"],
        check=True,
    )


def _create_commit(
    path: Path,
    filename: str,
    content: str,
    message: str,
    author_name: str,
    author_email: str,
) -> None:
    """Helper to author a git commit with specific author metadata."""
    file_path = path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", filename], check=True, capture_output=True)
    author_flag = f"{author_name} <{author_email}>"
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", message, f"--author={author_flag}"],
        check=True,
        capture_output=True,
    )


# --- Unit Tests: Git Log Output Parser ---


def test_parse_git_log_output_multicommit():
    """Verifies delimited parsing of git log outputs with files changed."""
    c1 = (
        f"c111111111111111111111111111111111111111{DELIMITER}Alice Smith{DELIMITER}"
        f"alice@example.com{DELIMITER}2026-10-25T14:30:00+00:00{DELIMITER}Add auth service\n"
        "app/auth.py\n"
        "tests/test_auth.py\n\n"
    )
    c2 = (
        f"c222222222222222222222222222222222222222{DELIMITER}Bob Jones{DELIMITER}"
        f"bob@example.com{DELIMITER}2026-10-24T10:15:00+00:00{DELIMITER}Setup database schema\n"
        "app/models.py\n\n"
    )
    c3 = (
        f"c333333333333333333333333333333333333333{DELIMITER}Alice Smith{DELIMITER}"
        f"alice@example.com{DELIMITER}2026-10-23T09:00:00+00:00{DELIMITER}"
        "Initial scaffold: fast & robust\n"
        "README.md\n"
    )
    raw = c1 + c2 + c3

    summary = _parse_git_log_output(raw)
    assert summary.total_commits == 3
    assert len(summary.commits) == 3
    assert summary.primary_author == "Alice Smith"

    # Commit 0 (latest)
    c0 = summary.commits[0]
    assert c0.commit_hash == "c111111111111111111111111111111111111111"
    assert c0.author_name == "Alice Smith"
    assert c0.author_email == "alice@example.com"
    assert c0.message == "Add auth service"
    assert c0.files_changed == ["app/auth.py", "tests/test_auth.py"]

    # Commit 2
    c2_obj = summary.commits[2]
    assert c2_obj.commit_hash == "c333333333333333333333333333333333333333"
    assert c2_obj.message == "Initial scaffold: fast & robust"
    assert c2_obj.files_changed == ["README.md"]

    # Contributor aggregates
    assert len(summary.contributors) == 2
    top = summary.contributors[0]
    assert top.name == "Alice Smith"
    assert top.email == "alice@example.com"
    assert top.commit_count == 2
    assert top.percentage == 66.7
    assert top.files_touched_count == 3  # app/auth.py, tests/test_auth.py, README.md

    second = summary.contributors[1]
    assert second.name == "Bob Jones"
    assert second.email == "bob@example.com"
    assert second.commit_count == 1
    assert second.percentage == 33.3
    assert second.files_touched_count == 1


def test_parse_git_log_output_empty():
    """Verifies that empty or whitespace-only log output returns empty summary."""
    summary = _parse_git_log_output("")
    assert summary.total_commits == 0
    assert summary.commits == []
    assert summary.contributors == []
    assert summary.primary_author is None


# --- Integration Tests: Live Git Repository Analysis ---


@pytest.mark.anyio
async def test_extract_git_history_live_repo():
    """Verifies live git log extraction on an actual initialized git repository."""
    with tempfile.TemporaryDirectory() as td:
        repo_dir = Path(td)
        _init_git_repo(repo_dir)

        _create_commit(
            repo_dir,
            "backend/main.py",
            "print('init')",
            "Initial commit",
            "Carol Danvers",
            "carol@marvel.com",
        )
        _create_commit(
            repo_dir,
            "frontend/app.ts",
            "export const x = 1;",
            "Add frontend app",
            "Tony Stark",
            "tony@stark.com",
        )
        _create_commit(
            repo_dir,
            "backend/api.py",
            "# API",
            "Add API endpoints",
            "Tony Stark",
            "tony@stark.com",
        )

        summary = await extract_git_history(repo_dir, max_commits=10)
        assert summary.total_commits == 3
        assert len(summary.commits) == 3
        assert summary.primary_author == "Tony Stark"

        assert len(summary.contributors) == 2
        tony = summary.contributors[0]
        assert tony.name == "Tony Stark"
        assert tony.commit_count == 2
        assert tony.percentage == 66.7
        assert tony.files_touched_count == 2

        carol = summary.contributors[1]
        assert carol.name == "Carol Danvers"
        assert carol.commit_count == 1
        assert carol.percentage == 33.3
        assert carol.files_touched_count == 1


@pytest.mark.anyio
async def test_extract_git_history_empty_repo():
    """Verifies that an initialized git repository with 0 commits returns empty summary."""
    with tempfile.TemporaryDirectory() as td:
        repo_dir = Path(td)
        _init_git_repo(repo_dir)

        summary = await extract_git_history(repo_dir)
        assert summary.total_commits == 0
        assert summary.commits == []
        assert summary.contributors == []
        assert summary.primary_author is None


@pytest.mark.anyio
async def test_extract_git_history_non_git_directory():
    """Verifies that a plain directory without .git gracefully returns empty summary."""
    with tempfile.TemporaryDirectory() as td:
        plain_dir = Path(td)
        summary = await extract_git_history(plain_dir)
        assert summary.total_commits == 0
        assert summary.commits == []
        assert summary.contributors == []
        assert summary.primary_author is None


@pytest.mark.anyio
async def test_extract_git_history_max_commits_limit():
    """Verifies that max_commits limit restricts the number of returned commits."""
    with tempfile.TemporaryDirectory() as td:
        repo_dir = Path(td)
        _init_git_repo(repo_dir)

        for i in range(5):
            _create_commit(
                repo_dir,
                f"file_{i}.txt",
                f"content {i}",
                f"Commit number {i}",
                "Dev User",
                "dev@example.com",
            )

        summary = await extract_git_history(repo_dir, max_commits=2)
        assert summary.total_commits == 2
        assert len(summary.commits) == 2
        assert summary.commits[0].message == "Commit number 4"
        assert summary.commits[1].message == "Commit number 3"


# --- Worker Pipeline Integration Test ---


@pytest.mark.anyio
async def test_cloner_worker_git_history_pipeline():
    """Verifies that clone_and_sanitize_repository runs git analysis and updates snapshot."""
    test_email = f"git_worker_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="test-git-worker-repo",
            github_url="https://github.com/repodefense/test-git-worker-repo",
            default_branch="main",
            status="pending",
        )
        session.add(user)
        session.add(project)
        await session.commit()

    test_commit_hash = "1111222233334444555566667777888899990000"

    # Mock clone that creates a real git repo inside target_dir
    async def mock_clone(github_url, branch, target_dir, depth=100, timeout=120.0):
        _init_git_repo(target_dir)
        _create_commit(
            target_dir,
            "main.py",
            "print('worker test')",
            "feat: initial core",
            "Lead Architect",
            "lead@company.com",
        )
        return test_commit_hash

    try:
        with patch("app.workers.cloner.run_git_shallow_clone", side_effect=mock_clone):
            result = await clone_and_sanitize_repository({}, str(project_id))
            assert result["status"] == "cloned"
            assert result["total_commits"] == 1
            assert result["contributor_count"] == 1
            assert result["top_contributor"] == "Lead Architect"

        async with AsyncSessionLocal() as session:
            stmt = select(RepositorySnapshot).where(RepositorySnapshot.project_id == project_id)
            snapshot = (await session.execute(stmt)).scalar_one_or_none()
            assert snapshot is not None
            assert "Contributors (1 commits): Lead Architect" in snapshot.summary

    finally:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                await session.delete(user)
                await session.commit()
