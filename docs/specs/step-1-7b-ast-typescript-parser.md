# Technical Specification: Step 1.7b — TypeScript/JavaScript AST Parser & Cloner Worker Pipeline

> **Milestone**: 1.7 AST Parsing & Symbol Extraction  
> **Feature Branch**: `feat/step-1-7b-ast-typescript-parser`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.7b is to complete Milestone 1.7 by:
1. Implementing a deterministic Tree-sitter AST parser for **TypeScript**, **TSX**, **JavaScript**, and **JSX** in `backend/app/analyzers/ast/typescript.py`.
2. Extracting functions, arrow functions in variable declarations (including React functional components), classes, class methods, interfaces, and JSDoc docstrings.
3. Registering `TypeScript` and `JavaScript` in the central AST dispatch registry (`backend/app/analyzers/ast/__init__.py`).
4. Integrating the AST symbol extraction pipeline directly into the ARQ clone worker (`backend/app/workers/cloner.py`), ensuring that every cataloged `AnalyzedFile` is parsed into `CodeSymbol` records stored in PostgreSQL 17 upon repository cloning.

---

## 2. Invariants & Security Guardrails

1. **Zero Arbitrary Code Execution**: Tree-sitter AST parsing only. No evaluation, bundling, or execution of user TS/JS code.
2. **Unified TSX Parser**: Use `tree_sitter_typescript.language_tsx()` to reliably parse TypeScript, TSX, standard JavaScript, and JSX syntax under a unified syntax grammar.
3. **Deterministic 1-Indexed Line Ranges**: Ensure `start_line` and `end_line` accurately reflect symbol boundaries, including `export` statements and decorators.
4. **Relational Foreign Key Integrity**: Every `CodeSymbol` row is attached to its parent `AnalyzedFile.id` with `CASCADE` deletion.
5. **Strict 5-Gate Goldilocks Compliance**:
   - $\le 4$ target source files modified/created.
   - $\le 300$ LOC per file.
   - Single architectural concern: TS/JS AST symbol extraction and worker pipeline integration.
   - Complete hermetic test verification.

---

## 3. Target Files & Component Specifications

### 1. `backend/app/analyzers/ast/typescript.py` (New File, $\le 190$ LOC)
- `class TypeScriptASTParser(BaseASTParser)`:
  - Initializes `Language(tree_sitter_typescript.language_tsx())` and `Parser`.
  - Traverses AST nodes, unwrapping `export_statement`:
    - `function_declaration`: Extracts function name, parameter types, return types, and docstrings.
    - `variable_declarator` with `arrow_function` or `function_expression`: Extracts name and callable signature (React components, arrow handlers).
    - `class_declaration`: Extracts class name, extends clauses, docstrings, and nested `method_definition` members.
    - `interface_declaration`: Extracts interface name and line boundaries.
  - Extracts JSDoc leading comments (`/** ... */`) and cleans comment delimiters.
  - Returns list of `SymbolMetadata` sorted by `start_line`.

### 2. `backend/app/analyzers/ast/__init__.py` (Edit Existing File, $\le 90$ LOC)
- Registers `"TypeScript": TypeScriptASTParser()`, `"JavaScript": TypeScriptASTParser()` in `_PARSER_REGISTRY`.
- Exposes `extract_and_persist_file_symbols(session, file, file_path) -> list[CodeSymbol]`.

### 3. `backend/app/workers/cloner.py` (Edit Existing File, $\le 210$ LOC)
- Updates `clone_and_sanitize_repository`:
  - After `created_files = await persist_analyzed_files(...)`:
  - Iterates over `created_files` and calls `extract_and_persist_file_symbols(session, file, temp_dir / file.path)`.
  - Calculates total symbol count and enriches `RepositorySnapshot.summary`.

### 4. `backend/pyproject.toml` (Edit Existing File)
- Adds `tree-sitter-typescript>=0.23.0` and `tree-sitter-javascript>=0.23.0` to dependencies.

---

## 4. Verification Plan

### Automated Test Suite: `backend/tests/test_ast_typescript.py`
1. **TypeScript Functions & Arrow Functions Test**:
   - Parses exported functions with typed parameters and return type annotations.
   - Parses exported arrow functions (`const UserCard: React.FC<Props> = ...`).
2. **TypeScript Classes & Interfaces Test**:
   - Parses `class AuthService extends BaseService` with `async authenticate(token: string): Promise<boolean>` methods.
   - Parses `interface UserProps` definitions.
3. **JavaScript / JSX Parsing Test**:
   - Parses standard JavaScript function declarations and JSX component syntax.
4. **JSDoc Docstring Extraction Test**:
   - Asserts `/** Formats user name */` is extracted and stripped cleanly.
5. **Cloner Worker Pipeline Integration Test**:
   - End-to-end test executing `clone_and_sanitize_repository` with Python and TypeScript mock files.
   - Asserts `RepositorySnapshot`, `AnalyzedFile` rows, AND `CodeSymbol` rows are created and verified in live PostgreSQL 17 database.

### Acceptance Criteria
- Ruff linter passing clean with zero warnings or errors.
- Full backend pytest suite passing (`pytest backend/tests`).
- Next.js 15 production build unbroken.
- Maximum 300 LOC limit observed across all files.
- Zero arbitrary code execution maintained.
