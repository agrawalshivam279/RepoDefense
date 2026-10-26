import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.analyzers.languages import detect_language
from app.analyzers.scanner import (
    FileMetadata,
    count_file_lines,
    extract_file_metadata,
    persist_analyzed_files,
    scan_workspace_files,
)
from app.core.database import AsyncSessionLocal, engine
from app.models.analysis import AnalyzedFile
from app.models.project import Project, RepositorySnapshot, User
from app.workers.cloner import clone_and_sanitize_repository


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test runs."""
    yield
    await engine.dispose()


# --- Unit Tests: Language Detection ---


def test_detect_language_standard_extensions():
    """Verifies standard extensions map to expected canonical language names."""
    cases = [
        ("main.py", "Python"),
        ("types.pyi", "Python"),
        ("app.ts", "TypeScript"),
        ("Component.tsx", "TypeScript"),
        ("index.js", "JavaScript"),
        ("util.cjs", "JavaScript"),
        ("server.go", "Go"),
        ("Main.java", "Java"),
        ("lib.rs", "Rust"),
        ("schema.sql", "SQL"),
        ("README.md", "Markdown"),
        ("script.sh", "Shell"),
        ("config.yaml", "YAML"),
        ("package.json", "JSON"),
    ]
    for filename, expected_lang in cases:
        assert detect_language(filename) == expected_lang


def test_detect_language_special_filenames():
    """Verifies exact filenames without extensions are mapped correctly."""
    cases = [
        ("Dockerfile", "Dockerfile"),
        ("dockerfile", "Dockerfile"),
        ("Makefile", "Makefile"),
        ("makefile", "Makefile"),
        ("Gemfile", "Ruby"),
        ("Procfile", "Procfile"),
    ]
    for filename, expected_lang in cases:
        assert detect_language(filename) == expected_lang


def test_detect_language_unknown_fallback():
    """Verifies that unmapped extensions fall back safely to Plain Text."""
    cases = ["archive.customext", "notes.random", "no_extension_file"]
    for filename in cases:
        assert detect_language(filename) == "Plain Text"


# --- Unit Tests: Metadata & Line Counting ---


def test_count_file_lines(tmp_path: Path):
    """Verifies accurate line counting for empty, single, and multiline files."""
    # 1. Empty file
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    assert count_file_lines(empty_file) == 0

    # 2. Multiline file with trailing newline
    multi_file = tmp_path / "multi.py"
    multi_file.write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    assert count_file_lines(multi_file) == 3

    # 3. File without trailing newline
    no_trailing = tmp_path / "no_trailing.py"
    no_trailing.write_text("line1\nline2", encoding="utf-8")
    assert count_file_lines(no_trailing) == 2


def test_extract_file_metadata(tmp_path: Path):
    """Verifies that relative POSIX path, size, and language are extracted accurately."""
    src_dir = tmp_path / "src" / "services"
    src_dir.mkdir(parents=True)
    target = src_dir / "auth.ts"
    target.write_text("export function login() {\n  return true;\n}\n", encoding="utf-8")

    meta = extract_file_metadata(target, tmp_path)
    assert meta.path == "src/services/auth.ts"
    assert meta.language == "TypeScript"
    assert meta.total_lines == 3
    assert meta.size_bytes > 0


def test_scan_workspace_files(tmp_path: Path):
    """Verifies scanning a workspace correctly skips ignored directories and categorizes files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create files
    (workspace / "main.py").write_text("print('hello')", encoding="utf-8")
    (workspace / "README.md").write_text("# Project\nOverview", encoding="utf-8")
    (workspace / "Dockerfile").write_text("FROM alpine:latest", encoding="utf-8")

    # Create ignored directory and binary file
    (workspace / "node_modules").mkdir()
    (workspace / "node_modules" / "test.js").write_text("console.log()", encoding="utf-8")
    (workspace / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")

    results = scan_workspace_files(workspace)
    paths = [m.path for m in results]

    assert paths == ["Dockerfile", "README.md", "main.py"]
    langs = {m.path: m.language for m in results}
    assert langs["Dockerfile"] == "Dockerfile"
    assert langs["README.md"] == "Markdown"
    assert langs["main.py"] == "Python"


# --- Integration Tests: Database Persistence ---


@pytest.mark.anyio
async def test_persist_analyzed_files_in_database():
    """Tests batch persistence of AnalyzedFile records linked to a RepositorySnapshot."""
    test_email = f"scanner_test_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="scan-repo",
            github_url="https://github.com/scan/scan-repo",
            default_branch="main",
            status="pending",
        )
        snapshot = RepositorySnapshot(
            id=snapshot_id,
            project_id=project_id,
            commit_hash="f" * 40,
            summary="Initial snapshot",
        )
        session.add(user)
        session.add(project)
        session.add(snapshot)
        await session.commit()

    meta_batch = [
        FileMetadata(path="app/main.py", language="Python", total_lines=45, size_bytes=1024),
        FileMetadata(path="app/types.ts", language="TypeScript", total_lines=20, size_bytes=512),
        FileMetadata(path="README.md", language="Markdown", total_lines=15, size_bytes=350),
    ]

    try:
        async with AsyncSessionLocal() as session:
            records = await persist_analyzed_files(session, snapshot_id, meta_batch)
            assert len(records) == 3
            await session.commit()

        # Verify DB rows
        async with AsyncSessionLocal() as session:
            stmt = select(AnalyzedFile).where(AnalyzedFile.snapshot_id == snapshot_id)
            db_files = (await session.execute(stmt)).scalars().all()
            assert len(db_files) == 3

            path_map = {f.path: f for f in db_files}
            assert "app/main.py" in path_map
            assert path_map["app/main.py"].language == "Python"
            assert path_map["app/main.py"].total_lines == 45
            assert path_map["app/types.ts"].language == "TypeScript"

    finally:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                await session.delete(user)
                await session.commit()


@pytest.mark.anyio
async def test_cloner_worker_catalogs_analyzed_files():
    """Verifies that the full worker execution persists AnalyzedFile entities alongside snapshot."""
    test_email = f"cloner_scan_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="full-scan-repo",
            github_url="https://github.com/test/full-scan-repo",
            default_branch="main",
            status="pending",
        )
        session.add(user)
        session.add(project)
        await session.commit()

    commit_hash = "11223344556677889900aabbccddeeff11223344"

    async def mock_clone(url, branch, target_dir, timeout=120.0):
        (target_dir / "index.ts").write_text("console.log('hi');\n", encoding="utf-8")
        (target_dir / "models.py").write_text("class Item:\n    pass\n", encoding="utf-8")
        return commit_hash

    try:
        with patch("app.workers.cloner.run_git_shallow_clone", side_effect=mock_clone):
            result = await clone_and_sanitize_repository({}, str(project_id))
            assert result["status"] == "cloned"
            assert result["file_count"] == 2
            assert result["total_lines"] >= 3

        async with AsyncSessionLocal() as session:
            db_project = await session.get(Project, project_id)
            assert db_project is not None
            assert db_project.status == "cloned"

            stmt = select(RepositorySnapshot).where(RepositorySnapshot.project_id == project_id)
            snapshot = (await session.execute(stmt)).scalar_one_or_none()
            assert snapshot is not None
            assert "Languages:" in snapshot.summary

            file_stmt = select(AnalyzedFile).where(AnalyzedFile.snapshot_id == snapshot.id)
            files = (await session.execute(file_stmt)).scalars().all()
            assert len(files) == 2
            file_paths = [f.path for f in files]
            assert "index.ts" in file_paths
            assert "models.py" in file_paths

    finally:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                await session.delete(user)
                await session.commit()
