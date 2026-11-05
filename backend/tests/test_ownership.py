"""Hermetic unit and integration tests for git blame parsing and ownership attribution."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.analyzers.blame import (
    compute_range_attribution,
    parse_file_blame,
    parse_line_porcelain_output,
)
from app.models.analysis import AnalyzedFile, CodeSymbol, Evidence
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.ownership import OwnershipStatus
from app.services.ownership import calculate_project_ownership

PORCELAIN_DATA = """d11b4db7d164ace6f252212160268d4cea477283 1 1 1
author Alice Dev
author-mail <alice@example.com>
summary Add auth
filename auth.py
\tdef authenticate_user():
59a6c9c769341d144d92dcddb9a77ac005e6e939 2 2 1
author Bob Teammate
author-mail <bob@example.com>
summary Fix token
filename auth.py
\t    token = create_jwt()
59a6c9c769341d144d92dcddb9a77ac005e6e939 3 3 1
author Bob Teammate
author-mail <bob@example.com>
summary Fix token
filename auth.py
\t    return token
"""


def test_parse_line_porcelain_output():
    """Validates deterministic parsing of git blame --line-porcelain output."""
    lines_map = parse_line_porcelain_output(PORCELAIN_DATA)
    assert len(lines_map) == 3
    assert lines_map[1].author_name == "Alice Dev"
    assert lines_map[1].author_email == "alice@example.com"
    assert lines_map[2].author_name == "Bob Teammate"


def test_compute_range_attribution():
    """Validates author share calculation and candidate attribution classification."""
    lines_map = parse_line_porcelain_output(PORCELAIN_DATA)

    # Bob authored 2/3 (66.7%) -> Collaborator
    cand_pct, prim_auth, status, authors = compute_range_attribution(
        lines_map=lines_map, start_line=1, end_line=3, candidate_email="bob@example.com"
    )
    assert cand_pct == 66.7
    assert prim_auth == "Bob Teammate"
    assert status == OwnershipStatus.COLLABORATOR
    assert len(authors) == 2

    # Alice authored 1/3 (33.3%) -> Collaborator
    cand_pct_a, _, status_a, _ = compute_range_attribution(
        lines_map=lines_map, start_line=1, end_line=3, candidate_email="alice@example.com"
    )
    assert cand_pct_a == 33.3
    assert status_a == OwnershipStatus.COLLABORATOR

    # Charlie authored 0% -> Unowned
    cand_pct_c, _, status_c, _ = compute_range_attribution(
        lines_map=lines_map, start_line=1, end_line=3, candidate_email="charlie@example.com"
    )
    assert cand_pct_c == 0.0
    assert status_c == OwnershipStatus.UNOWNED

    # Alice solo on line 1 -> Primary
    cand_pct_1, prim_1, status_1, _ = compute_range_attribution(
        lines_map=lines_map, start_line=1, end_line=1, candidate_email="alice@example.com"
    )
    assert cand_pct_1 == 100.0
    assert prim_1 == "Alice Dev"
    assert status_1 == OwnershipStatus.PRIMARY


@pytest.mark.anyio
async def test_parse_file_blame_security_path_traversal(tmp_path: Path):
    """Verifies that path traversal attacks outside repository root are safely blocked."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    assert await parse_file_blame(repo_dir, "../../etc/passwd") is None


def _create_mock_db(
    project: Optional[Project],
    user: Optional[User],
    snapshot: Optional[RepositorySnapshot],
    files: list[AnalyzedFile],
    symbols: list[CodeSymbol],
    evidence: list[Evidence],
) -> AsyncMock:
    """Builds a mock AsyncSession returning test domain objects."""
    mock_db = AsyncMock()

    async def mock_get(entity, entity_id):
        if entity is Project and project and entity_id == project.id:
            return project
        if entity is User and user and entity_id == user.id:
            return user
        return None

    mock_db.get.side_effect = mock_get

    def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "from repository_snapshots" in stmt_str:
            res.scalars.return_value.first.return_value = snapshot
        elif "from analyzed_files" in stmt_str:
            res.scalars.return_value.all.return_value = files
        elif "from code_symbols" in stmt_str:
            res.scalars.return_value.all.return_value = symbols
        elif "from evidence" in stmt_str:
            res.scalars.return_value.all.return_value = evidence
        else:
            res.scalars.return_value.all.return_value = []
            res.scalars.return_value.first.return_value = None
        return res

    mock_db.execute.side_effect = mock_execute
    return mock_db


@pytest.mark.anyio
async def test_calculate_project_ownership_empty():
    """Validates report calculation on a newly created project with zero snapshots."""
    user_id, proj_id = uuid.uuid4(), uuid.uuid4()
    now = datetime.now(timezone.utc)
    user = User(id=user_id, email="dev@example.com")
    project = Project(
        id=proj_id, user_id=user_id, name="EmptyRepo",
        github_url="https://github.com/test/empty", created_at=now, updated_at=now
    )
    mock_db = _create_mock_db(project, user, None, [], [], [])

    report = await calculate_project_ownership(proj_id, user_id, mock_db)
    assert report.project_name == "EmptyRepo"
    assert report.candidate_email == "dev@example.com"
    assert report.total_symbols_analyzed == 0
    assert report.candidate_authored_symbols == 0
    assert report.candidate_overall_ownership_percentage == 0.0


@pytest.mark.anyio
async def test_calculate_project_ownership_multi_tenant():
    """Verifies that accessing another user's project ownership raises 403 Forbidden."""
    owner_id, other_id, proj_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    now = datetime.now(timezone.utc)
    project = Project(
        id=proj_id, user_id=owner_id, name="PrivateProject",
        github_url="https://github.com/test/private", created_at=now, updated_at=now
    )
    mock_db = _create_mock_db(project, None, None, [], [], [])

    with pytest.raises(HTTPException) as exc_info:
        await calculate_project_ownership(proj_id, other_id, mock_db)
    assert exc_info.value.status_code == 403


@pytest.mark.anyio
async def test_calculate_project_ownership_with_symbols(tmp_path: Path):
    """Validates full ownership calculation with code symbols, evidence, and mocked blame."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    user_id, proj_id, snap_id, file_id = (uuid.uuid4() for _ in range(4))
    now = datetime.now(timezone.utc)
    user = User(id=user_id, email="alice@example.com")
    project = Project(
        id=proj_id, user_id=user_id, name="AuthModule",
        github_url="https://github.com/test/auth", created_at=now, updated_at=now
    )
    snapshot = RepositorySnapshot(
        id=snap_id,
        project_id=proj_id,
        commit_hash="d11b4db7d164ace6f252212160268d4cea477283",
        created_at=now,
    )
    file_record = AnalyzedFile(
        id=file_id, snapshot_id=snap_id, path="backend/auth.py",
        language="Python", total_lines=3, size_bytes=120
    )
    sym_auth = CodeSymbol(
        id=uuid.uuid4(), file_id=file_id, name="authenticate_user",
        symbol_type="function", start_line=1, end_line=1
    )
    sym_token = CodeSymbol(
        id=uuid.uuid4(), file_id=file_id, name="create_jwt",
        symbol_type="function", start_line=2, end_line=3
    )
    ev = Evidence(
        id=uuid.uuid4(), project_id=proj_id, file_path="backend/auth.py",
        evidence_type="auth", title="JWT Auth Service",
        description="Core JWT authentication pipeline", start_line=2, end_line=3
    )

    mock_db = _create_mock_db(project, user, snapshot, [file_record], [sym_auth, sym_token], [ev])
    mock_blame = parse_line_porcelain_output(PORCELAIN_DATA)

    with patch("app.services.ownership.parse_file_blame", new=AsyncMock(return_value=mock_blame)):
        report = await calculate_project_ownership(
            project_id=proj_id, user_id=user_id, candidate_email="alice@example.com",
            db=mock_db, repo_dir=repo_dir
        )

    assert report.total_symbols_analyzed == 2
    assert report.candidate_email == "alice@example.com"
    assert report.candidate_authored_symbols == 1
    assert len(report.symbols) == 2

    # Verify flagged unowned evidence: sym_token is lines 2-3 (ev type auth), Alice authored 0%
    assert len(report.flagged_unowned_symbols) == 1
    flagged = report.flagged_unowned_symbols[0]
    assert flagged.symbol_name == "create_jwt"
    assert flagged.candidate_status == OwnershipStatus.UNOWNED
    assert flagged.is_architectural_evidence is True
    assert flagged.evidence_type == "auth"
