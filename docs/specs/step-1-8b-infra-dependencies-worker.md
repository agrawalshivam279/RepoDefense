# Technical Specification: Step 1.8b — Container, Infrastructure & CI/CD Config Extraction & Cloner Worker Pipeline

> **Milestone**: 1.8 Dependency & Config Extraction  
> **Feature Branch**: `feat/step-1-8b-infra-dependencies-worker`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.8b is to complete **Milestone 1.8** by:
1. Implementing deterministic static parsers for container, infrastructure, and CI/CD configurations:
   - `Dockerfile` (base images, tags, multi-stage targets)
   - `docker-compose.yml` (services, images, local builds)
   - `.github/workflows/*.yml` (GitHub Actions workflow steps and actions)
2. Unifying language manifest parsers (from Step 1.8a) and infrastructure parsers under a central analyzer dispatcher.
3. Integrating full dependency extraction directly into the ARQ clone background worker (`backend/app/workers/cloner.py`), ensuring that every ingested repository snapshot catalogs both code symbols and third-party / infrastructure dependencies in PostgreSQL 17 upon cloning.
4. Tracking dependency metrics in `RepositorySnapshot.summary`.

---

## 2. Invariants & Security Guardrails

1. **Zero Arbitrary Code Execution**: Configurations are parsed strictly via static text analysis and `yaml.safe_load`. Never run `docker`, `docker compose`, or container commands on user code.
2. **Safe YAML Parsing**: Mandate `yaml.safe_load()` to prevent YAML object deserialization exploits.
3. **Multi-Stage Build Handling**: Accurately tag intermediate build stages (`AS builder`, `AS test`) as `is_dev=True`.
4. **Relational Database Integrity**: Every `Dependency` row is linked to `Project.id` with `ondelete="CASCADE"`.
5. **Strict 5-Gate Goldilocks Compliance**:
   - $\le 4$ target source files modified/created.
   - $\le 300$ LOC per file.
   - Single architectural concern: Infrastructure dependency extraction and worker integration.
   - Complete hermetic test verification.

---

## 3. Target Files & Component Specifications

### 1. `backend/app/analyzers/dependencies/infra.py` (New File, $\le 160$ LOC)
- `parse_dockerfile(content: str, file_path: str = "Dockerfile") -> list[DependencyMetadata]`:
  - Parses `FROM <image>[:<tag>] [AS <stage>]` lines.
  - Image name: normalized to lowercase (e.g. `python`, `node`, `pgvector/pgvector`).
  - Version: extracted tag (e.g. `3.12-slim`, `20-alpine`, `pg17`, default `latest`).
  - `is_dev`: True if stage name contains `build`, `test`, `dev`, `lint`, else False.
- `parse_docker_compose(content: str, file_path: str = "docker-compose.yml") -> list[DependencyMetadata]`:
  - Parses `services.*.image` (service images and tags).
  - Handles local build targets `services.*.build` (`version="local-build"`).
  - Sets `is_dev=False`.
- `parse_github_actions_workflow(content: str, file_path: str) -> list[DependencyMetadata]`:
  - Parses `jobs.*.steps[].uses` actions (e.g. `actions/checkout@v4`).
  - Name: action identifier (e.g. `actions/checkout`).
  - Version: action tag / commit hash (e.g. `v4`, `v5`).
  - Sets `is_dev=True` (CI actions are test/pipeline tools).
- `class InfraDependencyParser(BaseDependencyParser)`:
  - Dispatches to Dockerfile, docker-compose, or GitHub Actions parser based on filename.

### 2. `backend/app/analyzers/dependencies/__init__.py` (Edit Existing File, $\le 130$ LOC)
- Registers `InfraDependencyParser` in `get_dependency_parser`:
  - `Dockerfile*`, `containerfile*`
  - `docker-compose*.yml`, `docker-compose*.yaml`, `compose*.yml`, `compose*.yaml`
  - `.github/workflows/*.yml`, `.github/workflows/*.yaml`
- Re-exports `InfraDependencyParser`, `parse_dockerfile`, `parse_docker_compose`, `parse_github_actions_workflow`.

### 3. `backend/app/workers/cloner.py` (Edit Existing File, $\le 240$ LOC)
- In `clone_and_sanitize_repository`:
  - After AST symbol extraction:
  - Iterates through `created_files`:
    - If `get_dependency_parser(af.path)` is not None:
      - Reads file content from `temp_dir / af.path`.
      - Calls `extract_file_dependencies(af.path, content_bytes)`.
      - Calls `persist_dependencies(session, project.id, deps)`.
      - Increments `total_deps`.
  - Enriches `snapshot.summary`:
    - `Cloned commit {hash} with {files} files ({lines} lines, {size} MB, {symbols} symbols, {deps} dependencies).`
  - Returns `dependency_count` in worker return dictionary.

### 4. `backend/pyproject.toml` (Edit Existing File)
- Adds `"pyyaml>=6.0.0"` to dependencies.

---

## 4. Verification Plan

### Automated Test Suite: `backend/tests/test_infra_dependencies.py`
1. **Dockerfile Parsing Test**:
   - Multi-stage Dockerfile: `FROM node:20-alpine AS builder`, `FROM node:20-alpine AS runner`.
   - Asserts intermediate stage classified as `is_dev=True` and final stage as `is_dev=False`.
2. **Docker Compose Parsing Test**:
   - Parses services with remote images (`pgvector/pgvector:pg17`, `redis:7-alpine`) and local build context (`backend`).
3. **GitHub Actions Workflow Parsing Test**:
   - Parses `.github/workflows/ci.yml` steps (`actions/checkout@v4`, `actions/setup-python@v5`).
   - Asserts `is_dev=True`.
4. **End-to-End Cloner Worker Pipeline Test**:
   - Mock shallow clone creating a repository with Python code, TypeScript code, `requirements.txt`, `package.json`, `Dockerfile`, and `docker-compose.yml`.
   - Runs `clone_and_sanitize_repository`.
   - Asserts:
     - `RepositorySnapshot` created with summary mentioning both symbols and dependencies.
     - `AnalyzedFile` rows created in PostgreSQL 17.
     - `CodeSymbol` rows created in PostgreSQL 17.
     - `Dependency` rows created in PostgreSQL 17 for all manifests and infrastructure configs.

### Acceptance Criteria
- `ruff check backend` passing with 0 warnings/errors.
- Full pytest suite passing (`pytest backend/tests -v`).
- Next.js 15 production build passing cleanly.
- All files strictly under 300 LOC limit.
- Zero arbitrary code execution maintained.
