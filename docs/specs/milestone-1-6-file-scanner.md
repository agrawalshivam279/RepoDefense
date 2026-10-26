# Technical Specification: Milestone 1.6 — File Scanning & Language Detection Engine

> **Milestone**: 1.6 File Scanning & Language Detection  
> **Feature Branch**: `feat/milestone-1-6-file-scanner`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Milestone 1.6 is to bridge static security sanitization (Milestone 1.5) and AST parsing / semantic vectorization (Milestones 1.7 & 1.8). Once a repository has been shallowly cloned and sanitized in an isolated workspace, RepoDefense must catalog every valid source code file, deterministically classify its programming language, extract quantitative structural metadata (total lines, byte size, canonical relative path), and persist `AnalyzedFile` records linked to the `RepositorySnapshot` in PostgreSQL 17.

This foundation enables:
1. Deterministic file routing to language-specific Tree-sitter parsers (Python, TypeScript, JavaScript, Go, Java) in Milestone 1.7.
2. Accurate codebase composition metrics for candidate repositories (e.g. language breakdown percentage, total lines of code).
3. Relational traceability linking every downstream AST symbol (`CodeSymbol`) and code vector embedding (`CodeEmbedding`) back to its parent `AnalyzedFile`.

---

## 2. Invariants & Security Guardrails

1. **Zero Arbitrary Code Execution**: Static file inspection only. Never execute, import, or run interpreter/compiler binaries against candidate files.
2. **Path Sanitization & POSIX Standardization**: All cataloged paths stored in `AnalyzedFile.path` must be POSIX-normalized relative paths (using forward slashes `/`), strictly preventing absolute system paths or directory traversal sequences from leaking into the database.
3. **Safe File Decoding**: Files must be opened with encoding fallback handling (`utf-8` with `errors="replace"`), ensuring files with non-UTF8 byte sequences do not crash the scanning pipeline.
4. **Relational Integrity & Cascading**: Every `AnalyzedFile` row must belong to a valid `RepositorySnapshot` via `snapshot_id` with foreign key cascade deletion.
5. **Strict 5-Gate Goldilocks Sizing**:
   - $\le 4$ target source files modified/created.
   - $\le 300$ LOC per file.
   - Single architectural concern: Repository cataloging, language classification, and metadata persistence.
   - Complete hermetic test verification.

---

## 3. Target Files & Component Specifications

### 1. `backend/app/analyzers/languages.py` (New File, $\le 90$ LOC)
- Canonical Language Registry:
  - Maps file extensions to programming languages:
    - `.py`, `.pyw`, `.pyi` $\rightarrow$ `Python`
    - `.ts`, `.tsx` $\rightarrow$ `TypeScript`
    - `.js`, `.jsx`, `.mjs`, `.cjs` $\rightarrow$ `JavaScript`
    - `.go` $\rightarrow$ `Go`
    - `.java` $\rightarrow$ `Java`
    - `.rs` $\rightarrow$ `Rust`
    - `.c`, `.h` $\rightarrow$ `C`
    - `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx` $\rightarrow$ `C++`
    - `.cs` $\rightarrow$ `C#`
    - `.rb` $\rightarrow$ `Ruby`
    - `.php` $\rightarrow$ `PHP`
    - `.swift` $\rightarrow$ `Swift`
    - `.kt`, `.kts` $\rightarrow$ `Kotlin`
    - `.scala` $\rightarrow$ `Scala`
    - `.sql` $\rightarrow$ `SQL`
    - `.html`, `.htm` $\rightarrow$ `HTML`
    - `.css`, `.scss`, `.sass`, `.less` $\rightarrow$ `CSS`
    - `.json` $\rightarrow$ `JSON`
    - `.yaml`, `.yml` $\rightarrow$ `YAML`
    - `.toml` $\rightarrow$ `TOML`
    - `.md`, `.markdown` $\rightarrow$ `Markdown`
    - `.sh`, `.bash`, `.zsh` $\rightarrow$ `Shell`
  - Maps special exact filenames:
    - `dockerfile` $\rightarrow$ `Dockerfile`
    - `makefile` $\rightarrow$ `Makefile`
    - `gemfile` $\rightarrow$ `Ruby`
    - `procfile` $\rightarrow$ `Procfile`
- `def detect_language(file_path: Path | str) -> str`:
  - Resolves file name and extension in lowercase.
  - Returns canonical language name or `"Plain Text"` as safe default.

### 2. `backend/app/analyzers/scanner.py` (New File, $\le 160$ LOC)
- `class FileMetadata(BaseModel)`:
  - `path: str` (POSIX relative path)
  - `language: str`
  - `total_lines: int`
  - `size_bytes: int`
- `def extract_file_metadata(file_path: Path, base_dir: Path) -> FileMetadata`:
  - Calculates relative POSIX path `file_path.relative_to(base_dir).as_posix()`.
  - Determines language with `detect_language`.
  - Obtains `size_bytes = file_path.stat().st_size`.
  - Counts non-empty or total lines via stream reading.
- `def scan_workspace_files(base_dir: Path, file_paths: list[Path] | None = None) -> list[FileMetadata]`:
  - Iterates over valid files provided or runs `sanitize_workspace(base_dir)`.
  - Computes `FileMetadata` for every valid file.
- `async def persist_analyzed_files(session: AsyncSession, snapshot_id: uuid.UUID, files_meta: list[FileMetadata]) -> list[AnalyzedFile]`:
  - Instantiates `AnalyzedFile` entities.
  - Batch inserts via `session.add_all(...)`.
  - Flushes or commits session.
  - Returns created records.

### 3. `backend/app/analyzers/__init__.py` (New File, $\le 30$ LOC)
- Exposes `detect_language`, `extract_file_metadata`, `scan_workspace_files`, `persist_analyzed_files`, `FileMetadata`.

### 4. `backend/app/workers/cloner.py` (Edit Existing File, $\le 200$ LOC)
- Integrates scanning step into `clone_and_sanitize_repository`:
  - After `sanitization = sanitize_workspace(temp_dir)`:
  - Runs `files_meta = scan_workspace_files(temp_dir, sanitization.valid_files)`.
  - Within database session:
    - Creates `RepositorySnapshot`.
    - Persists `AnalyzedFile` records via `persist_analyzed_files(session, snapshot.id, files_meta)`.
    - Updates snapshot summary with language distribution breakdown.

---

## 4. Verification Plan

### Automated Test Suite: `backend/tests/test_file_scanner.py`
1. **Language Detection Unit Tests**:
   - Asserts standard file extensions map to correct languages (Python, TypeScript, Go, Java, Rust, SQL, Markdown, etc.).
   - Asserts special filenames (`Dockerfile`, `Makefile`) map correctly.
   - Asserts unknown extensions fall back to `"Plain Text"`.
2. **Metadata Extraction Unit Tests**:
   - Tests file line counting (including empty lines, multi-line blocks, single line).
   - Tests byte size computation and POSIX relative path calculation.
3. **Workspace Scanning Unit Tests**:
   - Creates a temporary directory structure with nested directories and diverse languages.
   - Verifies all valid files are extracted with correct metadata.
4. **Database Persistence Integration Tests**:
   - Creates test user, project, and snapshot in live PostgreSQL 17 test database.
   - Calls `persist_analyzed_files` and queries `analyzed_files` table.
   - Asserts rows match expected counts, paths, line counts, and foreign key cascades.
5. **Cloner Worker Integration Test**:
   - Verifies end-to-end `clone_and_sanitize_repository` creates both `RepositorySnapshot` and `AnalyzedFile` rows.

### Acceptance Criteria
- Ruff linter passing with zero warnings or formatting errors.
- Full backend pytest suite passing (`pytest backend/tests -v`).
- Next.js 15 frontend production build (`npm run build`) passing without errors.
- Max 300 LOC limit respected across all source files.
- Zero arbitrary code execution maintained.
