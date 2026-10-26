import uuid

import pytest
from sqlalchemy import select

from app.analyzers.dependencies import (
    DependencyMetadata,
    extract_file_dependencies,
    persist_dependencies,
)
from app.analyzers.dependencies.node import parse_package_json
from app.analyzers.dependencies.python import (
    parse_pyproject_toml,
    parse_requirements_txt,
)
from app.core.database import AsyncSessionLocal, engine
from app.models.analysis import Dependency
from app.models.project import Project, User


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test runs."""
    yield
    await engine.dispose()


def test_parse_requirements_txt_pinned_and_ranged():
    """Verifies parsing of pinned versions, version ranges, extras, and comments."""
    content = """
# Production requirements
fastapi==0.115.0
pydantic>=2.8.0,<3.0.0
uvicorn[standard]>=0.30.0
requests  # inline comment
pytest~=8.0.0; sys_platform == 'linux'
-r base.txt
--extra-index-url https://example.com/pypi
"""
    deps = parse_requirements_txt(content, file_path="requirements.txt")
    assert len(deps) == 5

    dep_map = {d.name: d for d in deps}
    assert dep_map["fastapi"].version == "0.115.0"
    assert dep_map["fastapi"].is_dev is False

    assert dep_map["pydantic"].version == ">=2.8.0,<3.0.0"
    assert dep_map["uvicorn"].version == ">=0.30.0"
    assert dep_map["requests"].version == "*"
    assert dep_map["pytest"].version == "~=8.0.0"


def test_parse_requirements_txt_dev_file():
    """Verifies that requirements-dev.txt sets is_dev flag to True."""
    content = "pytest>=8.0.0\nruff==0.6.0\n"
    deps = parse_requirements_txt(content, file_path="requirements-dev.txt")
    assert len(deps) == 2
    assert all(d.is_dev for d in deps)


def test_parse_pyproject_toml_pep621():
    """Verifies parsing of standard PEP 621 dependencies and optional-dependencies."""
    content = """
[project]
name = "sample-app"
version = "0.1.0"
dependencies = [
    "fastapi>=0.115.0",
    "sqlalchemy==2.0.30",
    "structlog",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "ruff",
]
test = [
    "pytest-asyncio>=0.23.0",
]
"""
    deps = parse_pyproject_toml(content, file_path="pyproject.toml")
    assert len(deps) == 6

    dep_map = {d.name: d for d in deps}
    assert dep_map["fastapi"].is_dev is False
    assert dep_map["fastapi"].version == ">=0.115.0"
    assert dep_map["sqlalchemy"].version == "2.0.30"
    assert dep_map["structlog"].version == "*"

    assert dep_map["pytest"].is_dev is True
    assert dep_map["ruff"].is_dev is True
    assert dep_map["pytest-asyncio"].is_dev is True


def test_parse_pyproject_toml_poetry():
    """Verifies Poetry style dependencies and dependency groups."""
    content = """
[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115.0"
redis = {version = "^5.0.0", optional = true}

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
"""
    deps = parse_pyproject_toml(content, file_path="pyproject.toml")
    names = [d.name for d in deps]
    assert "python" not in names
    assert "fastapi" in names
    assert "redis" in names
    assert "pytest" in names

    dep_map = {d.name: d for d in deps}
    assert dep_map["fastapi"].is_dev is False
    assert dep_map["fastapi"].version == "^0.115.0"
    assert dep_map["redis"].is_dev is True
    assert dep_map["pytest"].is_dev is True


def test_parse_package_json():
    """Verifies parsing of dependencies, devDependencies, and peerDependencies in package.json."""
    content = """{
  "name": "repodefense-frontend",
  "dependencies": {
    "next": "15.5.28",
    "react": "^19.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "tailwindcss": "^3.4.0"
  },
  "peerDependencies": {
    "react-dom": "^19.0.0"
  }
}"""
    deps = parse_package_json(content, file_path="package.json")
    assert len(deps) == 5

    dep_map = {d.name: d for d in deps}
    assert dep_map["next"].version == "15.5.28"
    assert dep_map["next"].is_dev is False

    assert dep_map["react"].version == "^19.0.0"
    assert dep_map["react"].is_dev is False

    assert dep_map["typescript"].is_dev is True
    assert dep_map["tailwindcss"].is_dev is True

    assert dep_map["react-dom"].is_dev is False


def test_extract_file_dependencies_dispatch():
    """Verifies high-level router dispatches by file name and ignores unsupported files."""
    req_bytes = b"fastapi==0.115.0\n"
    deps_req = extract_file_dependencies("requirements.txt", req_bytes)
    assert len(deps_req) == 1
    assert deps_req[0].name == "fastapi"

    pkg_bytes = b'{"dependencies": {"react": "^19.0.0"}}'
    deps_pkg = extract_file_dependencies("package.json", pkg_bytes)
    assert len(deps_pkg) == 1
    assert deps_pkg[0].name == "react"

    empty = extract_file_dependencies("README.md", b"# Documentation\n")
    assert empty == []


@pytest.mark.anyio
async def test_persist_dependencies_in_database():
    """Verifies database batch insertion and cascading deletion for Dependency rows."""
    test_email = f"dep_test_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="dependency-test-repo",
            github_url="https://github.com/test/dep-repo",
            default_branch="main",
            status="cloned",
        )
        session.add(user)
        session.add(project)
        await session.commit()

    metadata_list = [
        DependencyMetadata(
            name="fastapi",
            version="0.115.0",
            source_file="backend/requirements.txt",
            is_dev=False,
        ),
        DependencyMetadata(
            name="pytest",
            version=">=8.0.0",
            source_file="backend/requirements-dev.txt",
            is_dev=True,
        ),
        DependencyMetadata(
            name="next",
            version="15.5.28",
            source_file="frontend/package.json",
            is_dev=False,
        ),
    ]

    try:
        async with AsyncSessionLocal() as session:
            records = await persist_dependencies(session, project_id, metadata_list)
            assert len(records) == 3
            await session.commit()

        # Verify DB records
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Dependency)
                .where(Dependency.project_id == project_id)
                .order_by(Dependency.name)
            )
            db_deps = (await session.execute(stmt)).scalars().all()
            assert len(db_deps) == 3

            dep_dict = {d.name: d for d in db_deps}
            assert dep_dict["fastapi"].version == "0.115.0"
            assert dep_dict["fastapi"].source_file == "backend/requirements.txt"
            assert dep_dict["fastapi"].is_dev is False

            assert dep_dict["pytest"].version == ">=8.0.0"
            assert dep_dict["pytest"].is_dev is True

            assert dep_dict["next"].version == "15.5.28"
            assert dep_dict["next"].is_dev is False

        # Verify cascade deletion on Project delete
        async with AsyncSessionLocal() as session:
            p = await session.get(Project, project_id)
            assert p is not None
            await session.delete(p)
            await session.commit()

            stmt_check = select(Dependency).where(Dependency.project_id == project_id)
            remaining = (await session.execute(stmt_check)).scalars().all()
            assert len(remaining) == 0

    finally:
        async with AsyncSessionLocal() as session:
            u = await session.get(User, user_id)
            if u:
                await session.delete(u)
                await session.commit()
