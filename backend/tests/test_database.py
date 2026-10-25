import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, engine
from app.models.base import Base
from app.models.project import Project, RepositorySnapshot, User


@pytest.fixture(scope="module", autouse=True)
async def setup_database():
    """Ensure required tables exist in the database before running tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup tables after test module completes
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.anyio
async def test_database_engine_connection():
    """Verify that the async engine connects and executes a test probe."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(1))
        assert result.scalar() == 1


@pytest.mark.anyio
async def test_user_project_snapshot_crud_lifecycle():
    """Verify full CRUD lifecycle and cascade deletion across User -> Project -> Snapshot."""
    test_email = f"test_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        # 1. Create User
        user = User(
            id=user_id,
            email=test_email,
        )
        session.add(user)
        await session.commit()

        # 2. Create Project
        project = Project(
            id=project_id,
            user_id=user_id,
            name="test-repo",
            github_url="https://github.com/test/test-repo",
            default_branch="main",
            status="pending",
        )
        session.add(project)
        await session.commit()

        # 3. Create RepositorySnapshot
        snapshot = RepositorySnapshot(
            id=snapshot_id,
            project_id=project_id,
            commit_hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            summary="Initial test architecture snapshot",
        )
        session.add(snapshot)
        await session.commit()

    # 4. Verify Retrieval and Relationships
    async with AsyncSessionLocal() as session:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.projects).selectinload(Project.snapshots)
            )
        )
        retrieved_user = (await session.execute(stmt)).scalar_one_or_none()
        assert retrieved_user is not None
        assert retrieved_user.email == test_email
        assert len(retrieved_user.projects) == 1

        retrieved_project = retrieved_user.projects[0]
        assert retrieved_project.id == project_id
        assert retrieved_project.name == "test-repo"
        assert len(retrieved_project.snapshots) == 1
        assert retrieved_project.snapshots[0].id == snapshot_id

    # 5. Verify Cascade Deletion
    async with AsyncSessionLocal() as session:
        user_to_delete = await session.get(User, user_id)
        assert user_to_delete is not None
        await session.delete(user_to_delete)
        await session.commit()

        # Confirm Project and Snapshot were also deleted
        deleted_project = await session.get(Project, project_id)
        deleted_snapshot = await session.get(RepositorySnapshot, snapshot_id)
        assert deleted_project is None
        assert deleted_snapshot is None
