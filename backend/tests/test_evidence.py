import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.analyzers.evidence import extract_and_persist_evidence, extract_evidence
from app.models.analysis import AnalyzedFile, CodeSymbol, Dependency, Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceResponse, EvidenceType


def test_evidence_schemas():
    """Verifies EvidenceBase, EvidenceCreate, and EvidenceResponse validation."""
    project_id, ev_id = uuid.uuid4(), uuid.uuid4()
    create_data = EvidenceCreate(
        project_id=project_id,
        evidence_type=EvidenceType.FRAMEWORK,
        title="FastAPI Web Framework",
        description="Async web framework for building APIs.",
        file_path="requirements.txt",
        start_line=1,
        end_line=1,
    )
    assert create_data.project_id == project_id
    assert create_data.evidence_type == EvidenceType.FRAMEWORK

    orm_instance = Evidence(
        id=ev_id,
        project_id=project_id,
        evidence_type="framework",
        title="FastAPI Web Framework",
        description="Async web framework for building APIs.",
        file_path="requirements.txt",
        start_line=1,
        end_line=1,
    )
    resp = EvidenceResponse.model_validate(orm_instance)
    assert resp.id == ev_id
    assert resp.evidence_type == EvidenceType.FRAMEWORK


def test_extract_framework_and_database_dependencies():
    """Verifies framework and database dependencies generate correct evidence items."""
    project_id = uuid.uuid4()
    deps = [
        Dependency(
            id=uuid.uuid4(),
            project_id=project_id,
            name="fastapi",
            version="^0.115.0",
            source_file="pyproject.toml",
            is_dev=False,
        ),
        Dependency(
            id=uuid.uuid4(),
            project_id=project_id,
            name="sqlalchemy",
            version=">=2.0.0",
            source_file="pyproject.toml",
            is_dev=False,
        ),
        Dependency(
            id=uuid.uuid4(),
            project_id=project_id,
            name="pgvector",
            version="0.3.6",
            source_file="pyproject.toml",
            is_dev=False,
        ),
    ]

    items = extract_evidence(project_id, files=[], symbols=[], dependencies=deps)
    assert len(items) == 3
    types = {item.evidence_type for item in items}
    assert EvidenceType.FRAMEWORK in types
    assert EvidenceType.DATABASE in types
    titles = {item.title for item in items}
    assert "FastAPI Web Framework" in titles
    assert "SQLAlchemy Database ORM" in titles
    assert "pgvector Vector Extension" in titles


def test_extract_auth_and_queue_dependencies():
    """Verifies auth and background queue dependencies generate correct evidence items."""
    project_id = uuid.uuid4()
    deps = [
        Dependency(
            id=uuid.uuid4(),
            project_id=project_id,
            name="@supabase/supabase-js",
            version="^2.45.0",
            source_file="package.json",
            is_dev=False,
        ),
        Dependency(
            id=uuid.uuid4(),
            project_id=project_id,
            name="arq",
            version="0.26.1",
            source_file="requirements.txt",
            is_dev=False,
        ),
    ]

    items = extract_evidence(project_id, files=[], symbols=[], dependencies=deps)
    assert len(items) == 2
    type_map = {item.title: item.evidence_type for item in items}
    assert type_map["Supabase JS Client & Auth"] == EvidenceType.AUTH
    assert type_map["ARQ Asyncio Job Queue"] == EvidenceType.QUEUE


def test_extract_ast_endpoints_and_models():
    """Verifies endpoint and model symbols are correctly classified with line ranges."""
    project_id, file_id = uuid.uuid4(), uuid.uuid4()
    test_file = AnalyzedFile(
        id=file_id,
        snapshot_id=uuid.uuid4(),
        path="app/api/v1/projects.py",
        language="python",
        total_lines=120,
        size_bytes=3400,
    )
    sym_endpoint = CodeSymbol(
        id=uuid.uuid4(),
        file_id=file_id,
        name="create_project",
        symbol_type="endpoint",
        start_line=35,
        end_line=60,
        signature="@router.post('', response_model=ProjectResponse)",
    )
    sym_model = CodeSymbol(
        id=uuid.uuid4(),
        file_id=file_id,
        name="Project",
        symbol_type="class",
        start_line=10,
        end_line=30,
        signature="class Project(Base):",
    )

    items = extract_evidence(
        project_id=project_id,
        files=[test_file],
        symbols=[sym_endpoint, sym_model],
        dependencies=[],
    )
    assert len(items) == 2
    ep = next(it for it in items if it.evidence_type == EvidenceType.API_ENDPOINT)
    assert ep.title == "API Route: create_project"
    assert ep.file_path == "app/api/v1/projects.py"
    assert ep.start_line == 35 and ep.end_line == 60
    md = next(it for it in items if it.evidence_type == EvidenceType.DATABASE)
    assert md.title == "Data Model: Project"
    assert md.start_line == 10 and md.end_line == 30


def test_extract_auth_symbols():
    """Verifies security and auth symbols generate EvidenceType.AUTH."""
    project_id, file_id = uuid.uuid4(), uuid.uuid4()
    test_file = AnalyzedFile(
        id=file_id,
        snapshot_id=uuid.uuid4(),
        path="app/core/security.py",
        language="python",
        total_lines=95,
        size_bytes=2500,
    )
    sym_auth = CodeSymbol(
        id=uuid.uuid4(),
        file_id=file_id,
        name="get_current_user",
        symbol_type="function",
        start_line=20,
        end_line=45,
        signature="async def get_current_user(token: str) -> User",
    )

    items = extract_evidence(
        project_id=project_id,
        files=[test_file],
        symbols=[sym_auth],
        dependencies=[],
    )
    assert len(items) == 1
    assert items[0].evidence_type == EvidenceType.AUTH
    assert items[0].title == "Authentication Logic: get_current_user"
    assert items[0].start_line == 20 and items[0].end_line == 45


def test_extract_infrastructure_files():
    """Verifies Dockerfile, compose, and CI workflows generate INFRASTRUCTURE evidence."""
    project_id = uuid.uuid4()
    files = [
        AnalyzedFile(
            id=uuid.uuid4(),
            snapshot_id=uuid.uuid4(),
            path="Dockerfile",
            language="dockerfile",
            total_lines=42,
            size_bytes=1200,
        ),
        AnalyzedFile(
            id=uuid.uuid4(),
            snapshot_id=uuid.uuid4(),
            path="docker-compose.yml",
            language="yaml",
            total_lines=60,
            size_bytes=1800,
        ),
        AnalyzedFile(
            id=uuid.uuid4(),
            snapshot_id=uuid.uuid4(),
            path=".github/workflows/ci.yml",
            language="yaml",
            total_lines=75,
            size_bytes=2100,
        ),
    ]

    items = extract_evidence(project_id=project_id, files=files, symbols=[], dependencies=[])
    assert len(items) == 3
    titles = {it.title for it in items}
    assert "Docker Containerization: Dockerfile" in titles
    assert "Docker Compose Multi-Service Orchestration" in titles
    assert "CI/CD Pipeline: ci.yml" in titles


def test_extract_evidence_deduplication():
    """Verifies duplicate dependencies do not produce duplicate evidence."""
    project_id = uuid.uuid4()
    deps = [
        Dependency(id=uuid.uuid4(), project_id=project_id, name="fastapi", version="0.115.0", source_file="pyproject.toml"),
        Dependency(id=uuid.uuid4(), project_id=project_id, name="fastapi", version="0.115.0", source_file="pyproject.toml"),
    ]
    items = extract_evidence(project_id, files=[], symbols=[], dependencies=deps)
    assert len(items) == 1


def test_extract_and_persist_evidence_db():
    """Verifies extract_and_persist_evidence clears prior evidence and bulk persists."""
    import asyncio

    async def _run():
        project_id, snapshot_id, file_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        af = AnalyzedFile(id=file_id, snapshot_id=snapshot_id, path="app/main.py", language="python", total_lines=50, size_bytes=1200)
        sym = CodeSymbol(id=uuid.uuid4(), file_id=file_id, name="root_health", symbol_type="endpoint", start_line=15, end_line=25, signature="@app.get('/health')")
        dep = Dependency(id=uuid.uuid4(), project_id=project_id, name="fastapi", version="0.115.0", source_file="requirements.txt")

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_result_files, mock_result_syms, mock_result_deps = MagicMock(), MagicMock(), MagicMock()
        mock_result_files.scalars.return_value.all.return_value = [af]
        mock_result_syms.scalars.return_value.all.return_value = [sym]
        mock_result_deps.scalars.return_value.all.return_value = [dep]

        mock_session.execute.side_effect = [
            mock_result_files,
            mock_result_syms,
            mock_result_deps,
            MagicMock(),  # delete
        ]

        records = await extract_and_persist_evidence(mock_session, project_id, snapshot_id)
        assert len(records) == 2
        mock_session.commit.assert_awaited_once()
        assert mock_session.add.call_count == 2

    asyncio.run(_run())
