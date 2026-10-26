import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.embeddings import (
    DEFAULT_MODEL_NAME,
    EMBEDDING_DIM,
    embed_and_persist_workspace_chunks,
    generate_embeddings,
    retrieve_relevant_chunks,
    set_embedding_model,
)
from app.models.analysis import AnalyzedFile, CodeEmbedding
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.embedding import RetrievalQuery, RetrievedChunk
from app.workers.cloner import clone_and_sanitize_repository


class DummyEmbeddingModel:
    """Mock SentenceTransformer model returning deterministic 384-dim vectors."""

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True):
        return [[float(abs(hash(t)) % 1000) / 1000.0] * EMBEDDING_DIM for t in texts]


@pytest.fixture(autouse=True)
def mock_embedding_model():
    """Ensure tests run hermetically with dummy model unless explicitly overridden."""
    dummy = DummyEmbeddingModel()
    set_embedding_model(dummy)
    yield dummy
    set_embedding_model(None)


def test_embedding_constants_and_schemas():
    """Validates default embedding parameters and Pydantic schema constraints."""
    assert DEFAULT_MODEL_NAME == "all-MiniLM-L6-v2" and EMBEDDING_DIM == 384
    proj_id, file_id, chunk_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    query = RetrievalQuery(project_id=proj_id, query="connection pooling", top_k=3)
    assert query.project_id == proj_id and query.top_k == 3 and query.file_id is None

    retrieved = RetrievedChunk(
        id=chunk_id,
        file_id=file_id,
        file_path="app/db.py",
        symbol_id=None,
        chunk_content="def get_db(): pass",
        similarity=0.9124,
        token_count=12,
    )
    assert retrieved.similarity == 0.9124 and retrieved.file_path == "app/db.py"


def test_generate_embeddings_empty_and_dummy():
    """Tests embedding generation with dummy model and empty inputs."""
    assert generate_embeddings([]) == []
    texts = ["def auth(u): pass", "class Repo: pass"]
    vectors = generate_embeddings(texts)
    assert len(vectors) == 2 and len(vectors[0]) == 384 and len(vectors[1]) == 384


@pytest.mark.anyio
async def test_embed_and_persist_workspace_chunks(tmp_path: Path):
    """Tests chunking files from workspace, generating embeddings, and session add_all."""
    py_file = tmp_path / "service.py"
    py_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    file_id = uuid.uuid4()
    analyzed_file = AnalyzedFile(
        id=file_id,
        snapshot_id=uuid.uuid4(),
        path="service.py",
        language="python",
        size_bytes=40,
        total_lines=2,
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_exec_res = MagicMock()
    mock_exec_res.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_exec_res
    mock_session.flush = AsyncMock()
    mock_session.add_all = MagicMock()

    count = await embed_and_persist_workspace_chunks(
        session=mock_session,
        temp_dir=tmp_path,
        files=[analyzed_file],
        batch_size=10,
    )

    assert count > 0 and mock_session.add_all.called
    added = mock_session.add_all.call_args[0][0]
    assert len(added) == count and isinstance(added[0], CodeEmbedding)
    assert added[0].file_id == file_id and len(added[0].embedding) == 384


@pytest.mark.anyio
async def test_retrieve_relevant_chunks():
    """Tests vector similarity retrieval with query params and mocked DB result."""
    proj_id, file_id, chunk_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    mock_row = MagicMock()
    mock_row.id, mock_row.file_id = chunk_id, file_id
    mock_row.file_path, mock_row.symbol_id = "app/auth.py", None
    mock_row.chunk_content, mock_row.similarity, mock_row.token_count = (
        "def verify_jwt(): pass",
        0.8845,
        15,
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_exec_res = MagicMock()
    mock_exec_res.all.return_value = [mock_row]
    mock_session.execute.return_value = mock_exec_res

    query = RetrievalQuery(project_id=proj_id, query="verify jwt token", top_k=5)
    chunks = await retrieve_relevant_chunks(mock_session, query)

    assert len(chunks) == 1 and chunks[0].id == chunk_id
    assert chunks[0].file_path == "app/auth.py" and chunks[0].similarity == 0.8845


@pytest.mark.anyio
async def test_cloner_worker_embed_pipeline(monkeypatch):
    """Tests that cloner worker executes Stage 5 and records embedding_count."""
    proj_id, user_id = uuid.uuid4(), uuid.uuid4()
    mock_project = MagicMock(spec=Project)
    mock_project.id, mock_project.user_id = proj_id, user_id
    mock_project.github_url = "https://github.com/test-org/test-repo"
    mock_project.default_branch, mock_project.status = "main", "pending"

    mock_session = AsyncMock(spec=AsyncSession)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_project
    mock_res.scalar_one.return_value = mock_project
    mock_session.execute.return_value = mock_res
    mock_session.add, mock_session.commit = MagicMock(), AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.__aenter__.return_value, mock_ctx.__aexit__.return_value = mock_session, None
    monkeypatch.setattr("app.workers.cloner.AsyncSessionLocal", lambda: mock_ctx)

    async def mock_clone(url, branch, d, timeout=120.0):
        return "1111222233334444555566667777888899990000"

    monkeypatch.setattr("app.workers.cloner.run_git_shallow_clone", mock_clone)
    mock_sanitization = MagicMock(total_bytes=2048, valid_files=[])
    monkeypatch.setattr("app.workers.cloner.sanitize_workspace", lambda d: mock_sanitization)
    monkeypatch.setattr("app.workers.cloner.scan_workspace_files", lambda *a, **k: [])

    async def mock_persist_files(s, sid, fm):
        return []

    monkeypatch.setattr("app.workers.cloner.persist_analyzed_files", mock_persist_files)
    mock_hist = MagicMock(contributors=[], total_commits=1, primary_author="Dev <a@b.com>")

    async def mock_git_hist(d, max_commits=100):
        return mock_hist

    monkeypatch.setattr("app.workers.cloner.extract_git_history", mock_git_hist)

    async def mock_evidence(s, pid, sid):
        return []

    monkeypatch.setattr("app.workers.cloner.extract_and_persist_evidence", mock_evidence)

    async def mock_embed_chunks(s, d, f):
        return 42

    monkeypatch.setattr("app.workers.cloner.embed_and_persist_workspace_chunks", mock_embed_chunks)

    result = await clone_and_sanitize_repository({}, str(proj_id))
    assert result["status"] == "cloned" and result["embedding_count"] == 42
    assert mock_project.status == "cloned"


@pytest.mark.anyio
async def test_live_pgvector_cosine_retrieval():
    """Validates real pgvector cosine distance search against PostgreSQL."""
    from app.core.database import AsyncSessionLocal

    user_id, project_id = uuid.uuid4(), uuid.uuid4()
    snapshot_id, file_id = uuid.uuid4(), uuid.uuid4()
    test_email = f"pgvector_test_{uuid.uuid4().hex[:8]}@repodefense.dev"

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="rag-repo",
            github_url="https://github.com/test/rag-repo",
            default_branch="main",
            status="cloned",
        )
        snapshot = RepositorySnapshot(
            id=snapshot_id,
            project_id=project_id,
            commit_hash="abcdef1234567890abcdef1234567890abcdef12",
            summary="Test snapshot",
        )
        analyzed_file = AnalyzedFile(
            id=file_id,
            snapshot_id=snapshot_id,
            path="app/db.py",
            language="python",
            size_bytes=200,
            total_lines=15,
        )
        emb1 = CodeEmbedding(
            file_id=file_id,
            symbol_id=None,
            chunk_content="def connect_db(): pass",
            embedding=[0.5] * EMBEDDING_DIM,
            token_count=10,
        )
        emb2 = CodeEmbedding(
            file_id=file_id,
            symbol_id=None,
            chunk_content="def unrelated_func(): pass",
            embedding=[0.1] * EMBEDDING_DIM,
            token_count=8,
        )

        session.add_all([user, project, snapshot, analyzed_file, emb1, emb2])
        await session.commit()

    try:
        async with AsyncSessionLocal() as session:
            query = RetrievalQuery(project_id=project_id, query="connect database", top_k=2)
            chunks = await retrieve_relevant_chunks(session, query)
            assert len(chunks) == 2
            assert 0.0 <= chunks[0].similarity <= 1.0
            assert chunks[0].similarity >= chunks[1].similarity
    finally:
        async with AsyncSessionLocal() as session:
            db_user = await session.get(User, user_id)
            if db_user:
                await session.delete(db_user)
                await session.commit()
