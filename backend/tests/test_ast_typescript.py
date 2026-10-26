import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.analyzers.ast import extract_code_symbols
from app.analyzers.ast.typescript import TypeScriptASTParser
from app.core.database import AsyncSessionLocal, engine
from app.models.analysis import AnalyzedFile, CodeSymbol
from app.models.project import Project, RepositorySnapshot, User
from app.workers.cloner import clone_and_sanitize_repository


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test runs."""
    yield
    await engine.dispose()


def test_parse_typescript_functions():
    """Verifies extraction of exported and internal TypeScript functions."""
    parser = TypeScriptASTParser()
    code = b"""
export async function calculateMetrics(a: number, b: number): Promise<number> {
    return a + b;
}
export function greet(name: string): string {
    return "Hello " + name;
}
function internalHelper(): void {
    console.log("helper");
}
"""
    symbols = parser.parse(code)
    assert len(symbols) == 3
    assert symbols[0].name == "calculateMetrics"
    assert symbols[0].symbol_type == "async_function"
    assert symbols[0].start_line == 2
    assert symbols[0].end_line == 4
    assert "async function calculateMetrics" in symbols[0].signature

    assert symbols[1].name == "greet"
    assert symbols[1].symbol_type == "function"
    assert symbols[1].start_line == 5
    assert symbols[1].end_line == 7

    assert symbols[2].name == "internalHelper"
    assert symbols[2].symbol_type == "function"
    assert symbols[2].start_line == 8
    assert symbols[2].end_line == 10


def test_parse_typescript_arrow_functions_and_components():
    """Verifies React functional components and arrow function declarations."""
    parser = TypeScriptASTParser()
    code = b"""
export const UserCard: React.FC<Props> = ({ user }) => {
    return <div className="card">{user.name}</div>;
};
export const fetchSummary = async () => {
    return "summary";
};
const multiply = function(a: number, b: number): number {
    return a * b;
};
"""
    symbols = parser.parse(code)
    assert len(symbols) == 3

    assert symbols[0].name == "UserCard"
    assert symbols[0].symbol_type == "function"
    assert ": React.FC<Props>" in symbols[0].signature
    assert "({ user }) => ..." in symbols[0].signature

    assert symbols[1].name == "fetchSummary"
    assert symbols[1].symbol_type == "async_function"
    assert "async () => ..." in symbols[1].signature

    assert symbols[2].name == "multiply"
    assert symbols[2].symbol_type == "function"
    assert "multiply" in symbols[2].signature


def test_parse_typescript_classes_and_methods():
    """Verifies class definitions, extends clauses, decorators, and member methods."""
    parser = TypeScriptASTParser()
    code = b"""
@Injectable()
export class AuthService extends BaseService implements IAuth {
    private token: string;
    /**
     * Authenticates the user token.
     */
    @LogCall
    async authenticate(token: string): Promise<boolean> {
        return token.length > 0;
    }
    public logout(): void {
        this.token = "";
    }
}
"""
    symbols = parser.parse(code)
    assert len(symbols) == 3

    assert symbols[0].name == "AuthService"
    assert symbols[0].symbol_type == "class"
    assert symbols[0].start_line == 2
    assert symbols[0].signature == "class AuthService extends BaseService implements IAuth"
    assert symbols[0].decorators == ["@Injectable()"]

    assert symbols[1].name == "authenticate"
    assert symbols[1].symbol_type == "method"
    assert symbols[1].start_line == 8
    assert symbols[1].decorators == ["@LogCall"]
    assert symbols[1].signature == "async authenticate(token: string) : Promise<boolean>"
    assert symbols[1].docstring == "Authenticates the user token."

    assert symbols[2].name == "logout"
    assert symbols[2].symbol_type == "method"
    assert symbols[2].signature == "logout() : void"


def test_parse_typescript_interfaces():
    """Verifies interface declarations and extends clauses."""
    parser = TypeScriptASTParser()
    code = b"""
export interface UserProfile extends BaseProfile {
    id: string;
    email: string;
}
interface LocalConfig {
    debug: boolean;
}
"""
    symbols = parser.parse(code)
    assert len(symbols) == 2
    assert symbols[0].name == "UserProfile"
    assert symbols[0].symbol_type == "interface"
    assert symbols[0].signature == "interface UserProfile extends BaseProfile"

    assert symbols[1].name == "LocalConfig"
    assert symbols[1].symbol_type == "interface"
    assert symbols[1].signature == "interface LocalConfig"


def test_parse_javascript_and_jsx():
    """Verifies that plain JavaScript and JSX syntax are supported seamlessly."""
    parser = TypeScriptASTParser()
    code = b"""
function calculateTotal(items) {
    return items.reduce((acc, item) => acc + item.price, 0);
}
const ItemCard = ({ title }) => {
    return <div className="item">{title}</div>;
};
"""
    symbols = parser.parse(code)
    assert len(symbols) == 2
    assert symbols[0].name == "calculateTotal"
    assert symbols[0].symbol_type == "function"
    assert symbols[1].name == "ItemCard"
    assert symbols[1].symbol_type == "function"


def test_jsdoc_extraction():
    """Verifies clean extraction and stripping of multi-line JSDoc comments."""
    parser = TypeScriptASTParser()
    code = b"""
/**
 * Processes incoming webhook payload.
 *
 * @param payload Event payload
 * @returns Status string
 */
export async function processWebhook(payload: any): Promise<string> {
    return "ok";
}
"""
    symbols = parser.parse(code)
    assert len(symbols) == 1
    expected_doc = (
        "Processes incoming webhook payload.\n\n"
        "@param payload Event payload\n"
        "@returns Status string"
    )
    assert symbols[0].docstring == expected_doc


def test_extract_code_symbols_dispatch_ts_and_js():
    """Verifies router dispatches TypeScript, TSX, and JavaScript correctly."""
    symbols_ts = extract_code_symbols(b"export function testTS(): void {}", "TypeScript")
    assert len(symbols_ts) == 1
    assert symbols_ts[0].name == "testTS"

    symbols_js = extract_code_symbols(b"function testJS() {}", "JavaScript")
    assert len(symbols_js) == 1
    assert symbols_js[0].name == "testJS"


# --- Integration Test: Cloner Worker Pipeline with AST Extraction ---


@pytest.mark.anyio
async def test_cloner_worker_ast_symbol_pipeline():
    """Verifies end-to-end repository cloning, AST symbol extraction, and DB persistence."""
    test_email = f"cloner_ast_{uuid.uuid4().hex[:8]}@repodefense.dev"
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=test_email)
        project = Project(
            id=project_id,
            user_id=user_id,
            name="fullstack-repo",
            github_url="https://github.com/test/fullstack-repo",
            default_branch="main",
            status="pending",
        )
        session.add(user)
        session.add(project)
        await session.commit()

    test_commit_hash = "7c1234567890abcdef1234567890abcdef123456"

    async def mock_clone(url, branch, target_dir, timeout=120.0):
        py_dir = target_dir / "backend"
        py_dir.mkdir(parents=True, exist_ok=True)
        (py_dir / "main.py").write_text("def run_server():\n    pass\n", encoding="utf-8")

        ts_dir = target_dir / "frontend" / "src"
        ts_dir.mkdir(parents=True, exist_ok=True)
        ts_code = "export class DataService {\n    getData(): string { return 'data'; }\n}\n"
        (ts_dir / "service.ts").write_text(ts_code, encoding="utf-8")
        (ts_dir / "Widget.tsx").write_text(
            "export const Widget = () => <div>Widget</div>;\n", encoding="utf-8"
        )
        return test_commit_hash

    try:
        with patch("app.workers.cloner.run_git_shallow_clone", side_effect=mock_clone):
            result = await clone_and_sanitize_repository({}, str(project_id))
            assert result["status"] == "cloned"
            assert result["commit_hash"] == test_commit_hash
            assert result["file_count"] == 3
            assert result["symbol_count"] >= 4

        async with AsyncSessionLocal() as session:
            stmt = select(RepositorySnapshot).where(RepositorySnapshot.project_id == project_id)
            snapshot = (await session.execute(stmt)).scalar_one()
            assert "symbols" in snapshot.summary

            stmt_files = select(AnalyzedFile).where(AnalyzedFile.snapshot_id == snapshot.id)
            files = (await session.execute(stmt_files)).scalars().all()
            assert len(files) == 3

            file_ids = [f.id for f in files]
            stmt_symbols = select(CodeSymbol).where(CodeSymbol.file_id.in_(file_ids))
            db_symbols = (await session.execute(stmt_symbols)).scalars().all()
            symbol_names = [s.name for s in db_symbols]

            assert "run_server" in symbol_names
            assert "DataService" in symbol_names
            assert "getData" in symbol_names
            assert "Widget" in symbol_names

    finally:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                await session.delete(user)
                await session.commit()
