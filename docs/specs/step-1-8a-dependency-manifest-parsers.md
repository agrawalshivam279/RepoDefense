# Technical Specification: Step 1.8a — Python & Node.js Manifest Parsers & Database Persistence

> **Milestone**: 1.8 Dependency & Config Extraction  
> **Feature Branch**: `feat/step-1-8a-dependency-manifest-parsers`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.8a is to initiate **Milestone 1.8** by:
1. Creating a modular dependency extraction subsystem in `backend/app/analyzers/dependencies/`.
2. Implementing deterministic static parsers for Python (`requirements.txt`, `pyproject.toml`) and Node.js (`package.json`) package manifests without code execution.
3. Classifying dependencies by name, version/version constraint, source file path, and runtime vs. development flag (`is_dev`).
4. Providing batch database persistence for `Dependency` records attached to `Project` in PostgreSQL 17 with cascading foreign key integrity.

---

## 2. Invariants & Security Guardrails

1. **Zero Arbitrary Code Execution**: Manifests are analyzed using static text, regex, and structured standard library parsers (`tomllib` for TOML, `json` for JSON). Never run `pip`, `npm`, or `python setup.py`.
2. **Standard Library Only**: Use Python 3.11+ built-in `tomllib` and `json` for format parsing, preventing unnecessary external dependencies.
3. **Robust Sanitization of Requirement Lines**:
   - Strip inline and block comments (`#`).
   - Ignore pip directives (`-r`, `-f`, `-i`, `--index-url`, `--extra-index-url`, `-e`).
   - Strip environment markers (`sys_platform == 'win32'`) and extras (`package[extra]>=1.0`).
4. **Relational Database Integrity**: Every `Dependency` row is linked to `Project.id` with `ondelete="CASCADE"`.
5. **Strict 5-Gate Goldilocks Compliance**:
   - $\le 4$ target source files modified/created.
   - $\le 300$ LOC per file.
   - Single architectural concern: Language manifest parsing and persistence.
   - Complete hermetic test verification.

---

## 3. Target Files & Component Specifications

### 1. `backend/app/analyzers/dependencies/base.py` (New File, $\le 50$ LOC)
- `class DependencyMetadata(BaseModel)`:
  - `name: str`: Normalized lowercase package name.
  - `version: str`: Pinned version or semver constraint string (defaults to `*` if unpinned).
  - `source_file: str`: Relative path of the manifest file.
  - `is_dev: bool`: Flag indicating development/test dependency.
- `class BaseDependencyParser(ABC)`:
  - `@abstractmethod def parse(self, content_str: str, file_path: str) -> list[DependencyMetadata]`

### 2. `backend/app/analyzers/dependencies/python.py` (New File, $\le 160$ LOC)
- `parse_requirements_txt(content: str, file_path: str = "requirements.txt") -> list[DependencyMetadata]`:
  - Parses lines splitting on operators (`==`, `>=`, `<=`, `~=`, `!=`, `<`, `>`).
  - Flags `is_dev=True` if filename matches dev patterns (`*dev*.txt`, `*test*.txt`).
- `parse_pyproject_toml(content: str, file_path: str = "pyproject.toml") -> list[DependencyMetadata]`:
  - Parses `[project.dependencies]` (runtime, `is_dev=False`).
  - Parses `[project.optional-dependencies]` (dev/test groups, `is_dev=True`).
  - Parses `[tool.poetry.dependencies]` (excluding python version) and `[tool.poetry.group.*.dependencies]` (`is_dev=True`).
- `class PythonDependencyParser(BaseDependencyParser)`:
  - Dispatches to requirements or pyproject parser based on file name.

### 3. `backend/app/analyzers/dependencies/node.py` (New File, $\le 90$ LOC)
- `parse_package_json(content: str, file_path: str = "package.json") -> list[DependencyMetadata]`:
  - Parses `dependencies` (`is_dev=False`).
  - Parses `devDependencies` (`is_dev=True`).
  - Parses `peerDependencies` (`is_dev=False`).
- `class NodeDependencyParser(BaseDependencyParser)`:
  - Wraps `parse_package_json`.

### 4. `backend/app/analyzers/dependencies/__init__.py` (New File, $\le 110$ LOC)
- Central manifest parser registry:
  - Maps `requirements*.txt`, `pyproject.toml`, `package.json`.
- `extract_file_dependencies(file_path: Union[Path, str], content_bytes: bytes) -> list[DependencyMetadata]`.
- `persist_dependencies(session: AsyncSession, project_id: uuid.UUID, dependencies: Sequence[DependencyMetadata]) -> list[Dependency]`:
  - Batch inserts `Dependency` records into PostgreSQL 17.

---

## 4. Verification Plan

### Automated Test Suite: `backend/tests/test_dependencies.py`
1. **Python `requirements.txt` Test**:
   - Pinned versions (`fastapi==0.115.0`), ranged versions (`pydantic>=2.8.0,<3.0.0`), unpinned (`requests`), extras (`uvicorn[standard]>=0.30.0`), comments, and pip flags.
2. **Python `pyproject.toml` Test**:
   - PEP 621 `[project.dependencies]` and `[project.optional-dependencies]`.
   - Poetry `[tool.poetry.dependencies]` and `[tool.poetry.group.dev.dependencies]`.
3. **Node.js `package.json` Test**:
   - `dependencies` (runtime), `devDependencies` (dev flag), `peerDependencies`.
4. **Manifest Dispatch Router Test**:
   - Correctly matches filenames and extracts dependencies.
5. **Database Persistence Test**:
   - Batch inserts records into PostgreSQL 17, verifies queries by `project_id`, and confirms cascade deletion on project removal.

### Acceptance Criteria
- `ruff check backend` passing with 0 warnings/errors.
- Full pytest suite passing (`pytest backend/tests -v`).
- All files strictly under 300 LOC limit.
- Zero arbitrary code execution maintained.
