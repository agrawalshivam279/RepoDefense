import math
import uuid

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models.analysis import (
    AnalyzedFile,
    CodeEmbedding,
    CodeSymbol,
    Dependency,
    Evidence,
)
from app.models.project import Project, RepositorySnapshot, User


def create_normalized_vector(dim: int = 384, value: float = 0.05) -> list[float]:
    """Generates an L2-normalized test vector of the given dimension."""
    raw = [value] * dim
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


@pytest.fixture(scope="module", autouse=True)
async def setup_analysis_schema():
    """Ensure clean connection pool lifecycle across test modules."""
    yield
    await engine.dispose()


@pytest.mark.anyio
async def test_code_analysis_hierarchy_and_vector_query():
    """Verify full CRUD lifecycle and pgvector cosine distance query."""
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()
    symbol_id = uuid.uuid4()
    dep_id = uuid.uuid4()
    evidence_id = uuid.uuid4()
    embedding_id = uuid.uuid4()

    vector_384 = create_normalized_vector(384, 0.05)

    async with AsyncSessionLocal() as session:
        # 1. Base Tenancy Setup
        user = User(id=user_id, email=f"vector_test_{uuid.uuid4().hex[:6]}@repodefense.dev")
        project = Project(
            id=project_id,
            user_id=user_id,
            name="vector-repo",
            github_url="https://github.com/test/vector-repo",
        )
        snapshot = RepositorySnapshot(
            id=snapshot_id,
            project_id=project_id,
            commit_hash="c0ffee1234567890abcdef1234567890abcdef12",
            summary="Vector test snapshot",
        )
        session.add_all([user, project, snapshot])
        await session.commit()

        # 2. File & Symbol Setup
        analyzed_file = AnalyzedFile(
            id=file_id,
            snapshot_id=snapshot_id,
            path="backend/app/main.py",
            language="python",
            total_lines=50,
            size_bytes=1500,
        )
        code_symbol = CodeSymbol(
            id=symbol_id,
            file_id=file_id,
            name="health_check",
            symbol_type="endpoint",
            start_line=20,
            end_line=30,
            signature="async def health_check() -> HealthResponse",
        )

        # 3. Dependency & Evidence Setup
        dependency = Dependency(
            id=dep_id,
            project_id=project_id,
            name="fastapi",
            version=">=0.115.0",
            source_file="pyproject.toml",
        )
        evidence = Evidence(
            id=evidence_id,
            project_id=project_id,
            evidence_type="ApiEndpoint",
            title="Root Health Probe",
            description="Exposes GET /api/health for system status verification.",
            file_path="backend/app/main.py",
            start_line=20,
            end_line=30,
        )

        # 4. 384-dimensional Code Embedding Setup
        code_embedding = CodeEmbedding(
            id=embedding_id,
            file_id=file_id,
            symbol_id=symbol_id,
            chunk_content="async def health_check(): return {'status': 'ok'}",
            embedding=vector_384,
            token_count=18,
        )

        session.add_all([analyzed_file, code_symbol, dependency, evidence, code_embedding])
        await session.commit()

    # 5. Vector Cosine Distance Query Verification
    async with AsyncSessionLocal() as session:
        query_vector = create_normalized_vector(384, 0.05)
        # Cosine distance operator (<=>) via pgvector
        stmt = (
            select(CodeEmbedding)
            .order_by(CodeEmbedding.embedding.cosine_distance(query_vector))
            .limit(1)
        )
        result = (await session.execute(stmt)).scalar_one_or_none()
        assert result is not None
        assert result.id == embedding_id
        assert result.chunk_content.startswith("async def health_check")
        assert len(result.embedding) == 384

    # 6. Cascade Deletion Verification
    async with AsyncSessionLocal() as session:
        user_to_delete = await session.get(User, user_id)
        assert user_to_delete is not None
        await session.delete(user_to_delete)
        await session.commit()

        # All descendants should be cascade-deleted
        assert (await session.get(Project, project_id)) is None
        assert (await session.get(RepositorySnapshot, snapshot_id)) is None
        assert (await session.get(AnalyzedFile, file_id)) is None
        assert (await session.get(CodeSymbol, symbol_id)) is None
        assert (await session.get(Dependency, dep_id)) is None
        assert (await session.get(Evidence, evidence_id)) is None
        assert (await session.get(CodeEmbedding, embedding_id)) is None
