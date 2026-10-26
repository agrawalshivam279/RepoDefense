# 📄 Technical Specification: Step 1.11: Deterministic Evidence Extractor & Worker Pipeline

> **Step ID**: `Step 1.11`  
> **Feature Title**: Deterministic Evidence Extractor & Worker Pipeline  
> **Target Module**: `backend/app/analyzers/evidence.py`, `backend/app/schemas/evidence.py`, `backend/app/workers/cloner.py`  
> **Git Feature Branch**: `feat/step-1-11-evidence-extractor`  
> **Status**: 📋 Ready for Implementation  
> **Created**: 2026-10-27  

---

## 1. Executive Summary

Per **Gemini.md** (Section 1, 4 & 5), RepoDefense's foundational principle is **"Evidence over hallucination"**: every technical interview question and evaluation must be mathematically grounded in the actual codebase. A candidate's claims are verified against extracted architectural evidence rather than generic quiz templates.

Milestone 1.11 implements the **Deterministic Evidence Extractor**, a high-precision static analyzer that mines cataloged `AnalyzedFile`, `CodeSymbol`, and `Dependency` records to identify load-bearing architectural components (web frameworks, databases/ORMs, authentication middleware, API endpoints, job queues, and infrastructure configurations). Extracted items are classified into standardized evidence categories, bound to exact file paths and line ranges, persisted in PostgreSQL 17 as `Evidence` records, and integrated directly into the ARQ repository ingestion worker pipeline (`backend/app/workers/cloner.py`).

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Milestone 1.2b`: `Evidence` model in `backend/app/models/analysis.py` with `project_id`, `evidence_type`, `title`, `description`, `file_path`, `start_line`, `end_line`.
  - `Milestone 1.6`: `AnalyzedFile` records cataloged per repository snapshot.
  - `Milestone 1.7`: `CodeSymbol` records extracted via Tree-sitter (functions, classes, endpoints, decorators).
  - `Milestone 1.8`: `Dependency` records parsed from Python/Node manifests and Docker/Compose/CI configs.
  - `Milestone 1.9`: `RepositorySnapshot.summary` aggregation pattern in `backend/app/workers/cloner.py`.
- **Blocked by**: None.
- **Tech Stack Invariant**: Zero new external libraries. Adheres strictly to **Gemini.md** (FastAPI, SQLAlchemy 2.0 asyncpg, PostgreSQL 17, ARQ, structlog).

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Static classification only. Operates purely on database records (`CodeSymbol`, `Dependency`, `AnalyzedFile`) and cached metadata without executing user scripts or importing user modules.
- [x] **Deterministic Grounding**: Every generated `Evidence` record references a concrete `file_path` and 1-indexed `start_line` / `end_line` range. No hallucinated or floating evidence items.
- [x] **Path Traversal Defense**: All file paths are validated against POSIX relative path invariants (`Path(path).is_absolute() is False` and no `..` traversal).
- [x] **Parameterized SQL**: Database persistence leverages SQLAlchemy 2.0 `select()` and async ORM sessions with foreign key integrity.

---

## 4. 🧠 Sequential Thinking Strategy

Evidence extraction must deterministically filter hundreds of symbols and dependencies into a curated set of **10–30 high-signal architectural anchor points** that an AI Principal Engineer persona can challenge:

1. **Classification Priority**:
   - **Frameworks**: Primary web/application frameworks (`fastapi`, `next`, `express`, `django`, `flask`) derived from dependencies or entrypoint symbols.
   - **Database & Storage**: ORMs, vector extensions, drivers (`sqlalchemy`, `prisma`, `pgvector`, `redis`, `mongoose`).
   - **Authentication & Security**: Custom auth middleware, JWT verifiers, session guards, decorators (`get_current_user`, `@login_required`, `verify_token`).
   - **API Endpoints**: Public route handlers and RPC definitions (`@router.get`, `@app.post`, Express router calls).
   - **Queue & Async Jobs**: Background workers and message queues (`arq`, `celery`, `bullmq`).
   - **Infrastructure**: Container configurations (`Dockerfile`, `docker-compose.yml`, GitHub Actions CI).
2. **Deduplication & Granularity**:
   - Avoid creating 500 evidence rows for 500 minor helper functions.
   - Group related dependencies (e.g. `fastapi` + `uvicorn` into a unified framework evidence item or distinct key dependencies).
   - Prioritize load-bearing endpoints and classes with decorators or docstrings.
3. **Graceful Fallbacks**:
   - If a repository has minimal dependencies, fall back to file tree structure (e.g. detecting single-file scripts or static sites).

---

## 5. Data Contracts & Interfaces

### 5.1 Pydantic Schemas (`backend/app/schemas/evidence.py`)

```python
import uuid
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class EvidenceType(str, Enum):
    """Canonical classification for load-bearing architectural evidence."""

    FRAMEWORK = "framework"
    DATABASE = "database"
    AUTH = "auth"
    API_ENDPOINT = "api_endpoint"
    QUEUE = "queue"
    INFRASTRUCTURE = "infrastructure"
    ARCHITECTURE = "architecture"


class EvidenceBase(BaseModel):
    """Base payload for architectural evidence."""

    evidence_type: EvidenceType = Field(..., description="Classification category")
    title: str = Field(..., max_length=255, description="Concise human-readable evidence title")
    description: str = Field(..., description="Detailed explanation of the architectural significance")
    file_path: str = Field(..., max_length=1000, description="Repository-relative file path")
    start_line: int = Field(..., ge=1, description="1-indexed starting line")
    end_line: int = Field(..., ge=1, description="1-indexed ending line")


class EvidenceCreate(EvidenceBase):
    """Payload for creating a new evidence record."""

    project_id: uuid.UUID = Field(..., description="Owning project UUID")


class EvidenceResponse(EvidenceBase):
    """API response model for an evidence record."""

    id: uuid.UUID = Field(..., description="Unique evidence UUID")
    project_id: uuid.UUID = Field(..., description="Owning project UUID")

    model_config = ConfigDict(from_attributes=True)
```

---

## 6. Implementation Logic

### 6.1 Evidence Extraction Rules Engine (`backend/app/analyzers/evidence.py`)

- **Signature**:
  ```python
  def extract_evidence(
      project_id: uuid.UUID,
      files: Sequence[AnalyzedFile],
      symbols: Sequence[CodeSymbol],
      dependencies: Sequence[Dependency],
  ) -> list[EvidenceCreate]
  ```

- **Extraction Rules**:
  1. **Framework Rule**:
     - Check `dependencies` for known frameworks: `fastapi`, `starlette`, `django`, `flask`, `next`, `react`, `express`, `nest`, `@nestjs/core`, `koa`, `gin`, `fiber`.
     - Map to `EvidenceType.FRAMEWORK` with source file from `Dependency.source_file`.
  2. **Database & ORM Rule**:
     - Check `dependencies` for `sqlalchemy`, `alembic`, `pgvector`, `psycopg`, `asyncpg`, `prisma`, `typeorm`, `drizzle-orm`, `mongoose`, `redis`, `ioredis`.
     - Check `symbols` for classes inheriting `Base` or models.
     - Map to `EvidenceType.DATABASE`.
  3. **Auth & Security Rule**:
     - Check `dependencies` for `supabase`, `@supabase/supabase-js`, `jsonwebtoken`, `jose`, `passlib`, `bcrypt`, `next-auth`, `@auth/core`.
     - Check `symbols` for functions/classes with names matching `auth`, `login`, `token`, `jwt`, `current_user`, `permission`, `guard`, or decorators with `auth`/`protect`.
     - Map to `EvidenceType.AUTH`.
  4. **API Endpoint Rule**:
     - Check `symbols` for `symbol_type == "endpoint"` or decorators containing `@app.`, `@router.`, `@api.`.
     - Map to `EvidenceType.API_ENDPOINT` with symbol line boundaries.
  5. **Queue & Background Task Rule**:
     - Check `dependencies` for `arq`, `celery`, `bullmq`, `redis`, `rq`.
     - Check `symbols` for workers or task definitions (e.g. `worker`, `WorkerSettings`, `@task`).
     - Map to `EvidenceType.QUEUE`.
  6. **Infrastructure Rule**:
     - Check `files` for `Dockerfile`, `docker-compose.yml`, `compose.yaml`, `.github/workflows/*.yml`.
     - Map to `EvidenceType.INFRASTRUCTURE` with line range 1 to `min(50, file.total_lines)`.

### 6.2 Database Persistence Function (`backend/app/analyzers/evidence.py`)

- **Signature**:
  ```python
  async def extract_and_persist_evidence(
      session: AsyncSession,
      project_id: uuid.UUID,
      snapshot_id: Optional[uuid.UUID] = None,
  ) -> list[Evidence]
  ```
- **Flow**:
  1. Fetch `AnalyzedFile` and `CodeSymbol` records for the snapshot (or latest project snapshot).
  2. Fetch `Dependency` records for the project.
  3. Run deterministic `extract_evidence(...)`.
  4. Deduplicate items by `(evidence_type, title, file_path)`.
  5. Delete any existing `Evidence` records for `project_id` (idempotent re-runs).
  6. Bulk persist new `Evidence` ORM records.
  7. Return persisted `Evidence` instances.

### 6.3 ARQ Worker Integration (`backend/app/workers/cloner.py`)

- Update `clone_and_sanitize_repository`:
  ```python
  # 4. Deterministic Architectural Evidence Extraction
  evidence_items = await extract_and_persist_evidence(session, project.id, snapshot.id)
  total_evidence = len(evidence_items)
  ```
- Update `snapshot.summary` to include `{total_evidence} evidence items`.
- Include `evidence_count: total_evidence` in return dictionary and structured logger.

---

## 7. Step-by-Step Implementation Sequence

1. **Step A: Pydantic Schema Definition**
   - Create `backend/app/schemas/evidence.py` (`EvidenceType`, `EvidenceBase`, `EvidenceCreate`, `EvidenceResponse`).
   - Register schema exports in `backend/app/schemas/__init__.py`.

2. **Step B: Evidence Extraction Engine & DB Persistence**
   - Implement `backend/app/analyzers/evidence.py` with `extract_evidence` and `extract_and_persist_evidence`.
   - Export in `backend/app/analyzers/__init__.py`.

3. **Step C: Cloner Background Worker Integration**
   - Wire `extract_and_persist_evidence` into `backend/app/workers/cloner.py`.
   - Update snapshot summary string and logger metrics.

4. **Step D: Hermetic Test Suite**
   - Create `backend/tests/test_evidence.py` covering:
     - Framework, database, auth, endpoint, queue, and infrastructure rules.
     - Line boundary preservation.
     - Database persistence and idempotent re-runs.
     - Worker pipeline integration with mocked DB sessions.

---

## 8. Verification & Acceptance Criteria

### Automated Test Command
```bash
pytest backend/tests/test_evidence.py -v
```

### Acceptance Checklist
- [ ] `extract_evidence` correctly identifies frameworks (`fastapi`, `next`), databases (`sqlalchemy`, `prisma`), auth patterns (`jwt`, `current_user`), API endpoints, queues (`arq`, `celery`), and infra configs (`Dockerfile`).
- [ ] Every extracted `Evidence` has non-null, valid `file_path`, `start_line`, and `end_line`.
- [ ] Database persistence correctly links records to `project_id`.
- [ ] ARQ worker executes evidence extraction cleanly without errors.
- [ ] All code files strictly adhere to $\le 300$ LOC.
- [ ] Zero code execution invariant preserved 100%.
- [ ] Full backend test suite passes cleanly (`pytest backend/tests/`).
