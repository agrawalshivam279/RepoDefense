# Technical Specification: Step 1.7a — Tree-sitter Base Engine & Python AST Symbol Extractor

> **Milestone**: 1.7 AST Parsing & Symbol Extraction  
> **Feature Branch**: `feat/step-1-7a-ast-python-parser`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.7a is to construct the multi-language Tree-sitter AST parsing infrastructure in `backend/app/analyzers/ast/` and implement the deterministic Python symbol extractor. 

In RepoDefense, AI defense evaluations and architectural stress-tests are grounded in mathematical code evidence. Rather than relying on fuzzy heuristics or LLM prompt guessing, the system uses deterministic Tree-sitter syntax trees to extract every function, method, class, decorator, and docstring with exact 1-indexed line ranges (`start_line`, `end_line`) and signatures. These symbols are persisted as `CodeSymbol` rows in PostgreSQL 17 linked to their parent `AnalyzedFile`.

---

## 2. Invariants & Security Guardrails

1. **Zero Arbitrary Code Execution**: Exclusively parse static code bytes into Tree-sitter concrete syntax trees (`CST`). Never invoke `eval()`, `exec()`, or import user modules.
2. **Deterministic Symbol Boundaries**: Every extracted symbol must report exact 1-indexed `start_line` and `end_line` coordinates corresponding to the full definition block (including decorators and body).
3. **Resilient AST Parsing**: Malformed code, syntax errors, or incomplete files must not crash the parser; Tree-sitter's error-tolerant parser recovers and extracts all valid surrounding nodes.
4. **Relational Traceability**: Every `CodeSymbol` row must foreign-key link to `AnalyzedFile.id` with `CASCADE` deletion.
5. **Strict 5-Gate Goldilocks Compliance**:
   - $\le 4$ target source files modified/created.
   - $\le 300$ LOC per file.
   - Single architectural concern: Tree-sitter infrastructure, Python AST symbol extraction, and database persistence.
   - Complete hermetic test verification.

---

## 3. Target Files & Component Specifications

### 1. `backend/app/analyzers/ast/base.py` (New File, $\le 80$ LOC)
- `class SymbolMetadata(BaseModel)`:
  - `name: str` (Identifier name, e.g. `"create_project"`)
  - `symbol_type: str` (`"function"`, `"async_function"`, `"class"`, `"method"`)
  - `start_line: int` (1-indexed start line)
  - `end_line: int` (1-indexed end line)
  - `signature: Optional[str]` (Parameter list and return type)
  - `docstring: Optional[str]` (Cleaned docstring string if present)
  - `decorators: list[str]` (List of decorator strings attached to the symbol)
- `class BaseASTParser(ABC)`:
  - `@abstractmethod def parse(self, code_bytes: bytes) -> list[SymbolMetadata]`

### 2. `backend/app/analyzers/ast/python.py` (New File, $\le 180$ LOC)
- `class PythonASTParser(BaseASTParser)`:
  - Initializes `Language(tree_sitter_python.language())` and `Parser`.
  - Defines pre-compiled Tree-sitter S-expression queries (`Query` and `QueryCursor`):
    - Function definitions (`function_definition`, `async def` handling)
    - Class definitions (`class_definition`) and member methods
    - Parameter extraction, type annotations, and docstrings
    - Attached decorators (`decorated_definition`)
  - Extracts clean signatures: e.g. `def func(a: int) -> bool` or `class Service(Base)`
  - Returns list of `SymbolMetadata` ordered by `start_line`.

### 3. `backend/app/analyzers/ast/__init__.py` (New File, $\le 60$ LOC)
- Parser registry mapping canonical language names to parser instances (`{"Python": PythonASTParser()}`).
- `def extract_code_symbols(code_bytes: bytes, language: str) -> list[SymbolMetadata]`:
  - Dispatches to registered language parser; returns empty list if parser not yet implemented.
- `async def persist_code_symbols(session: AsyncSession, file_id: uuid.UUID, symbols: Sequence[SymbolMetadata]) -> list[CodeSymbol]`:
  - Batch inserts `CodeSymbol` entities linked to `file_id`.
  - Flushes session and returns created records.

### 4. `backend/pyproject.toml` (Edit Existing File)
- Declare `tree-sitter>=0.24.0` and `tree-sitter-python>=0.23.0` in project dependencies.

---

## 4. Verification Plan

### Automated Test Suite: `backend/tests/test_ast_python.py`
1. **Function & Async Function Extraction Test**:
   - Parses functions with typed parameters and return type annotations.
   - Verifies `name`, `symbol_type`, `start_line`, `end_line`, `signature`, and `docstring`.
2. **Class & Method Extraction Test**:
   - Parses classes with inheritance and nested methods (`__init__`, instance methods).
   - Verifies class `docstring` and methods distinguished as `symbol_type="method"`.
3. **Decorator Extraction Test**:
   - Parses functions and routes decorated with FastAPI decorators (e.g. `@router.post('/login')`).
   - Asserts decorators list is correctly populated.
4. **Syntax Error Tolerance Test**:
   - Parses Python files with partial syntax errors; asserts parser extracts valid neighboring symbols without throwing unhandled exceptions.
5. **Database Persistence Integration Test**:
   - Creates test user, project, snapshot, and analyzed file in PostgreSQL 17 test DB.
   - Calls `persist_code_symbols` and verifies rows in `code_symbols` table.
   - Verifies cascade deletion when the parent `AnalyzedFile` is deleted.

### Acceptance Criteria
- Ruff linter passing clean with zero warnings or errors.
- Full backend pytest suite passing (`pytest backend/tests`).
- Frontend Next.js 15 production build unbroken.
- Maximum 300 LOC limit observed across all files.
- Zero arbitrary code execution maintained.
