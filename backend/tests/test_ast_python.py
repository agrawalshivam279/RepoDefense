import uuid

import pytest
from sqlalchemy import select

from app.analyzers.ast import extract_code_symbols, persist_code_symbols
from app.analyzers.ast.base import SymbolMetadata
from app.analyzers.ast.python import PythonASTParser
from app.core.database import AsyncSessionLocal, engine
from app.models.analysis import AnalyzedFile, CodeSymbol
from app.models.project import Project, RepositorySnapshot, User


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test runs."""
    yield
    await engine.dispose()


# --- Unit Tests: Python AST Parser ---


def test_parse_standard_function():
    """Verifies parsing of standard Python functions, parameters, and return types."""
    parser = PythonASTParser()
    code = b'''
def calculate_metrics(values: list[float], precision: int = 2) -> float:
    """Calculates the standard statistical metric."""
    return round(sum(values) / len(values), precision)
'''
    symbols = parser.parse(code)
    assert len(symbols) == 1
    sym = symbols[0]

    assert sym.name == "calculate_metrics"
    assert sym.symbol_type == "function"
    assert sym.start_line == 2
    assert sym.end_line == 4
    assert sym.signature == (
        "def calculate_metrics(values: list[float], precision: int = 2) -> float"
    )
    assert sym.docstring == "Calculates the standard statistical metric."
    assert sym.decorators == []


def test_parse_async_function_with_decorators():
    """Verifies extraction of async functions with multiple decorators and signatures."""
    parser = PythonASTParser()
    code = b'''
@router.post("/auth/login", response_model=TokenResponse)
@rate_limit(max_requests=10)
async def login_user(credentials: LoginRequest) -> TokenResponse:
    """Authenticates the user and returns tokens."""
    return TokenResponse(token="xyz")
'''
    symbols = parser.parse(code)
    assert len(symbols) == 1
    sym = symbols[0]

    assert sym.name == "login_user"
    assert sym.symbol_type == "async_function"
    assert sym.start_line == 2  # Begins at top decorator
    assert sym.end_line == 6
    assert len(sym.decorators) == 2
    assert '@router.post("/auth/login", response_model=TokenResponse)' in sym.decorators
    assert "@rate_limit(max_requests=10)" in sym.decorators
    assert sym.signature == "async def login_user(credentials: LoginRequest) -> TokenResponse"
    assert sym.docstring == "Authenticates the user and returns tokens."


def test_parse_class_and_nested_methods():
    """Verifies class definitions, docstrings, and member methods extraction."""
    parser = PythonASTParser()
    code = b'''
class RepositoryManager(BaseManager, metaclass=Singleton):
    """Manages repository cloning and snapshot lifecycles."""

    def __init__(self, workspace_path: str):
        self.workspace = workspace_path

    @cached
    async def get_snapshot(self, snapshot_id: str) -> dict:
        """Fetches snapshot metadata."""
        return {}
'''
    symbols = parser.parse(code)
    assert len(symbols) == 3

    # 1. Class
    class_sym = symbols[0]
    assert class_sym.name == "RepositoryManager"
    assert class_sym.symbol_type == "class"
    assert class_sym.start_line == 2
    assert class_sym.end_line == 11
    assert class_sym.signature == "class RepositoryManager(BaseManager, metaclass=Singleton)"
    assert class_sym.docstring == "Manages repository cloning and snapshot lifecycles."

    # 2. Init method
    init_sym = symbols[1]
    assert init_sym.name == "__init__"
    assert init_sym.symbol_type == "method"
    assert init_sym.start_line == 5
    assert init_sym.end_line == 6
    assert init_sym.signature == "def __init__(self, workspace_path: str)"

    # 3. Async cached method
    method_sym = symbols[2]
    assert method_sym.name == "get_snapshot"
    assert method_sym.symbol_type == "method"
    assert method_sym.start_line == 8  # Includes @cached decorator
    assert method_sym.end_line == 11
    assert method_sym.decorators == ["@cached"]
    assert method_sym.docstring == "Fetches snapshot metadata."


def test_parse_syntax_error_tolerance():
    """Verifies that the Tree-sitter parser gracefully recovers from syntax errors."""
    parser = PythonASTParser()
    code = b'''
def first_valid():
    return 1

# Syntax error in between
def broken_fn(:
    invalid_syntax +++

def second_valid():
    return 2
'''
    symbols = parser.parse(code)
    names = [s.name for s in symbols]
    assert "first_valid" in names
    assert "second_valid" in names


def test_extract_code_symbols_dispatch():
    """Verifies high-level dispatch router maps Python and handles unmapped languages."""
    py_code = b"def test_dispatch(): pass"
    symbols = extract_code_symbols(py_code, "Python")
    assert len(symbols) == 1
    assert symbols[0].name == "test_dispatch"

    unmapped = extract_code_symbols(b"fn main() {}", "Rust")
    assert unmapped == []


# --- Integration Tests: Database Persistence ---


@pytest.mark.anyio
async def test_persist_code_symbols_in_database():
    """Verifies batch persistence and cascade deletion of CodeSymbol rows in PostgreSQL 17."""
    test_email = f"ast_test_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="ast-project",
            github_url="https://github.com/test/ast-project",
            default_branch="main",
            status="cloned",
        )
        snapshot = RepositorySnapshot(
            id=snapshot_id,
            project_id=project_id,
            commit_hash="a" * 40,
            summary="AST test snapshot",
        )
        analyzed_file = AnalyzedFile(
            id=file_id,
            snapshot_id=snapshot_id,
            path="app/services.py",
            language="Python",
            total_lines=50,
            size_bytes=1024,
        )
        session.add(user)
        session.add(project)
        session.add(snapshot)
        session.add(analyzed_file)
        await session.commit()

    symbols = [
        SymbolMetadata(
            name="BaseService",
            symbol_type="class",
            start_line=1,
            end_line=20,
            signature="class BaseService",
            docstring="Service base class.",
        ),
        SymbolMetadata(
            name="execute_job",
            symbol_type="async_function",
            start_line=22,
            end_line=30,
            signature="async def execute_job(job_id: str) -> bool",
            docstring="Executes background job.",
            decorators=["@app.task"],
        ),
    ]

    try:
        async with AsyncSessionLocal() as session:
            records = await persist_code_symbols(session, file_id, symbols)
            assert len(records) == 2
            await session.commit()

        # Verify DB rows
        async with AsyncSessionLocal() as session:
            stmt = (
                select(CodeSymbol)
                .where(CodeSymbol.file_id == file_id)
                .order_by(CodeSymbol.start_line)
            )
            db_symbols = (await session.execute(stmt)).scalars().all()
            assert len(db_symbols) == 2

            assert db_symbols[0].name == "BaseService"
            assert db_symbols[0].symbol_type == "class"
            assert db_symbols[0].start_line == 1
            assert db_symbols[0].end_line == 20
            assert db_symbols[0].docstring == "Service base class."

            assert db_symbols[1].name == "execute_job"
            assert db_symbols[1].symbol_type == "async_function"
            assert db_symbols[1].signature == "async def execute_job(job_id: str) -> bool"

        # Verify cascade deletion
        async with AsyncSessionLocal() as session:
            file_record = await session.get(AnalyzedFile, file_id)
            assert file_record is not None
            await session.delete(file_record)
            await session.commit()

            # Confirm symbols were cascade deleted
            stmt = select(CodeSymbol).where(CodeSymbol.file_id == file_id)
            remaining_symbols = (await session.execute(stmt)).scalars().all()
            assert len(remaining_symbols) == 0

    finally:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                await session.delete(user)
                await session.commit()
