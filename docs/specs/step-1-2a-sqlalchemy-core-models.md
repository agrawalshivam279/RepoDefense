# 📄 Technical Specification: SQLAlchemy 2.0 Async Engine & Core Tenancy Models

> **Step ID**: `1.2a`  
> **Target Module**: `backend/app/core/` & `backend/app/models/`  
> **Git Feature Branch**: `feat/step-1-2a-sqlalchemy-core-models`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-10-26  

---

## 1. Executive Summary

This specification establishes the asynchronous database architecture for **RepoDefense** using SQLAlchemy 2.0 and `asyncpg`. It defines the connection engine, session factory, and FastAPI dependency in `backend/app/core/database.py` configured with connection pool parameters optimized for Supabase. It implements the declarative model foundation (`backend/app/models/base.py`) and authors the core domain tenancy models: `User` (linking Supabase auth identity), `Project` (GitHub repository records, URL, default branch), and `RepositorySnapshot` (point-in-time analysis snapshot). Automated integration tests verify schema creation, session isolation, and entity relationships against PostgreSQL 17.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - Step 1.1a (`Settings` in `backend/app/core/config.py`).
  - Step 1.1b (`DATABASE_URL` in `.env` configured for Supabase PostgreSQL 17).
- **Blocked by**: None (database connectivity verified).
- **Tech Stack Invariant**:
  - SQLAlchemy 2.0+ (using `Mapped`, `mapped_column`, and DeclarativeBase).
  - `asyncpg` async driver.
  - PostgreSQL 17 (Supabase cloud).
  - Adheres strictly to [Gemini.md](file:///d:/RepoDefense/Gemini.md) without introducing microservices or unapproved ORMs.

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Raw SQL String Concatenation**: 100% of database operations use SQLAlchemy 2.0 parameterized expressions or ORM models.
- [x] **Referential Integrity**: Foreign keys enforce cascade constraints (`ondelete="CASCADE"`) preventing orphaned records.
- [x] **UUID Primary Keys**: Uses `uuid4` string/UUID identifiers to prevent sequential ID enumeration attacks.
- [x] **File Length Limit**: Every target file strictly maintains $\le 300$ LOC.

---

## 4. 🧠 Sequential Thinking Strategy

- **Complexity Evaluation**: Standard SQLAlchemy 2.0 async engine and relational model authoring. Sequential Thinking MCP is **Skipped** for this step as no complex AST algorithms or state machines are present.

---

## 5. Data Contracts & Interfaces

### 5.1 Database Engine & Session Factory (`backend/app/core/database.py`)

```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    url=settings.DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_recycle=300,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### 5.2 Core Tenancy Models (`backend/app/models/project.py`)

- **`User`**:
  - `id`: `UUID` (Primary Key, Supabase Auth user reference)
  - `email`: `String(255)`, unique, indexed
  - `created_at`: `DateTime(timezone=True)`
  - `updated_at`: `DateTime(timezone=True)`
  - Relationship: `projects` (`Project`, back_populates="user", cascade="all, delete-orphan")

- **`Project`**:
  - `id`: `UUID` (Primary Key)
  - `user_id`: `UUID` (ForeignKey to `users.id`, indexed)
  - `name`: `String(255)` (e.g. "RepoDefense")
  - `github_url`: `String(500)` (e.g. "https://github.com/user/repo")
  - `default_branch`: `String(100)` (default: "main")
  - `status`: `String(50)` (default: "pending")
  - `created_at`, `updated_at`: `DateTime(timezone=True)`
  - Relationship: `snapshots` (`RepositorySnapshot`, back_populates="project", cascade="all, delete-orphan")

- **`RepositorySnapshot`**:
  - `id`: `UUID` (Primary Key)
  - `project_id`: `UUID` (ForeignKey to `projects.id`, indexed)
  - `commit_hash`: `String(40)` (Git SHA)
  - `summary`: `JSON` or `Text` (AI high-level summary)
  - `created_at`: `DateTime(timezone=True)`

---

## 6. Step-by-Step Implementation Sequence

### Phase A: Database Session & Engine
1. **Implement `backend/app/core/database.py`**:
   - Create asynchronous engine using `settings.DATABASE_URL`.
   - Setup `async_sessionmaker`.
   - Define FastAPI `get_db` dependency.

### Phase B: Base Model & Common Mixins
2. **Implement `backend/app/models/base.py`**:
   - Define `Base(DeclarativeBase)`.
   - Define `TimestampMixin` with timezone-aware `created_at` and `updated_at`.

### Phase C: Core Tenancy Models
3. **Implement `backend/app/models/project.py`**:
   - Define `User`, `Project`, and `RepositorySnapshot` using modern SQLAlchemy 2.0 mapped columns.
   - Configure relationships and cascading deletes.

### Phase D: Automated Tests & Verification
4. **Implement `backend/tests/test_database.py`**:
   - Connect to database using `engine`.
   - Create core tables using `Base.metadata.create_all`.
   - Test inserting a `User`, a `Project`, and a `RepositorySnapshot`.
   - Test query filtering and relationship retrieval.
   - Clean up test records.

---

## 7. Verification & Acceptance Criteria

### Automated Tests
```bash
python -m pytest backend/tests/test_database.py -v
```

### Acceptance Checklist
- [ ] SQLAlchemy 2.0 async engine cleanly connects to PostgreSQL 17.
- [ ] Core tables (`users`, `projects`, `repository_snapshots`) create and execute CRUD.
- [ ] Foreign keys cascade cleanly.
- [ ] All files $\le 300$ LOC.
