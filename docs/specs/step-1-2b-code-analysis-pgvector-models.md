# 📄 Technical Specification: Code Analysis & pgvector Vector Models + Alembic Migrations

> **Step ID**: `1.2b`  
> **Target Module**: `backend/app/models/` & `backend/alembic/`  
> **Git Feature Branch**: `feat/step-1-2b-code-analysis-pgvector-models`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-10-26  

---

## 1. Executive Summary

This specification completes **Milestone 1.2: Database Models & Migrations** by implementing the codebase static analysis and vector evidence schema for **RepoDefense**. It introduces SQLAlchemy 2.0 models for parsed code files (`AnalyzedFile`), AST symbols (`CodeSymbol`), external packages (`Dependency`), extracted interview proof points (`Evidence`), and vector embeddings (`CodeEmbedding`) equipped with a 384-dimensional `pgvector.sqlalchemy.Vector(384)` column and HNSW cosine similarity index (`vector_cosine_ops`). It initializes Alembic with asynchronous `asyncpg` execution, establishes the initial database migration, and verifies vector persistence and similarity querying (`<=>`) against Supabase PostgreSQL 17.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - Step 1.2a (SQLAlchemy 2.0 engine, `Base`, and core tenancy models `User`, `Project`, `RepositorySnapshot`).
  - PostgreSQL 17 with `vector` extension enabled on Supabase.
- **Blocked by**: None (`pgvector` and `alembic` installed).
- **Tech Stack Invariant**:
  - PostgreSQL 17 + `pgvector`
  - SQLAlchemy 2.0+ & `pgvector.sqlalchemy`
  - Alembic 1.20+ with asyncpg template
  - Vector dimensionality: exactly 384 dimensions (`all-MiniLM-L6-v2` compatibility)
  - Adheres strictly to [Gemini.md](file:///d:/RepoDefense/Gemini.md).

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Pure static analysis data representation. No executing or evaluating user code.
- [x] **Evidence Grounding Foundation**: `Evidence` and `CodeEmbedding` tables store direct line numbers (`start_line`, `end_line`) and symbol references ensuring 100% verifiable citations for the AI interviewer.
- [x] **Vector Dimensions Locked**: Strict 384-dimensional vector constraint prevents dimension mismatch errors during cosine distance calculations.
- [x] **Cascade Safety**: Analysis entities cascade on snapshot/project deletion (`ondelete="CASCADE"`).
- [x] **File Length Limit**: Every target file strictly maintains $\le 300$ LOC.

---

## 4. 🧠 Sequential Thinking Strategy

- **Vector Dimension & Indexing**:
  - Embeddings use `Vector(384)` aligned with local `all-MiniLM-L6-v2` outputs.
  - HNSW index uses `vector_cosine_ops` with parameters `m=16` and `ef_construction=64` for optimal recall and sub-5ms query latency.
  - Cosine distance operator (`<=>`) used for semantic search: `1 - (embedding <=> query_vector)`.

---

## 5. Data Contracts & Interfaces

### 5.1 Analysis & Evidence Entities (`backend/app/models/analysis.py`)

- **`AnalyzedFile`**:
  - `id`: `UUID` (Primary Key)
  - `snapshot_id`: `UUID` (FK $\rightarrow$ `repository_snapshots.id`, ondelete="CASCADE", indexed)
  - `path`: `String(1000)` (e.g. `backend/app/main.py`)
  - `language`: `String(50)` (e.g. `python`, `typescript`)
  - `total_lines`: `Integer`
  - `size_bytes`: `Integer`
  - `created_at`: `DateTime(timezone=True)`
  - Relationships: `symbols`, `embeddings`

- **`CodeSymbol`**:
  - `id`: `UUID` (Primary Key)
  - `file_id`: `UUID` (FK $\rightarrow$ `analyzed_files.id`, ondelete="CASCADE", indexed)
  - `name`: `String(255)` (e.g. `get_db`, `HealthResponse`)
  - `symbol_type`: `String(50)` (e.g. `function`, `class`, `endpoint`, `import`)
  - `start_line`: `Integer`, `end_line`: `Integer`
  - `signature`: `Text` (optional)
  - `docstring`: `Text` (optional)

- **`Dependency`**:
  - `id`: `UUID` (Primary Key)
  - `project_id`: `UUID` (FK $\rightarrow$ `projects.id`, ondelete="CASCADE", indexed)
  - `name`: `String(255)` (e.g. `fastapi`, `next`)
  - `version`: `String(100)` (e.g. `^15.5.0`)
  - `source_file`: `String(255)` (e.g. `package.json`, `pyproject.toml`)
  - `is_dev`: `Boolean` (default: False)

- **`Evidence`**:
  - `id`: `UUID` (Primary Key)
  - `project_id`: `UUID` (FK $\rightarrow$ `projects.id`, ondelete="CASCADE", indexed)
  - `evidence_type`: `String(50)` (e.g. `Architecture`, `Dependency`, `KeyFunction`, `ApiEndpoint`)
  - `title`: `String(255)`
  - `description`: `Text`
  - `file_path`: `String(1000)`
  - `start_line`: `Integer`, `end_line`: `Integer`

- **`CodeEmbedding`**:
  - `id`: `UUID` (Primary Key)
  - `file_id`: `UUID` (FK $\rightarrow$ `analyzed_files.id`, ondelete="CASCADE", indexed)
  - `symbol_id`: `UUID` (FK $\rightarrow$ `code_symbols.id`, ondelete="SET NULL", nullable=True, indexed)
  - `chunk_content`: `Text`
  - `embedding`: `Vector(384)` (indexed with HNSW `vector_cosine_ops`)
  - `token_count`: `Integer`
  - `created_at`: `DateTime(timezone=True)`

---

## 6. Step-by-Step Implementation Sequence

### Phase A: Analysis Models & Vector Columns
1. **Author `backend/app/models/analysis.py`**:
   - Define `AnalyzedFile`, `CodeSymbol`, `Dependency`, `Evidence`, and `CodeEmbedding` using SQLAlchemy 2.0.
   - Configure `Vector(384)` column from `pgvector.sqlalchemy`.
   - Configure HNSW cosine index `idx_code_embeddings_hnsw`.
2. **Update `backend/app/models/__init__.py`**:
   - Re-export all models for Alembic autogeneration and application access.

### Phase B: Alembic Async Migration Scaffolding
3. **Initialize & Configure Alembic**:
   - Create `backend/alembic.ini` and `backend/alembic/env.py`.
   - Wire `env.py` to import `Base.metadata` and use `settings.DATABASE_URL` with asyncpg.
   - Ensure migration script runs `CREATE EXTENSION IF NOT EXISTS vector;`.
4. **Generate Initial Migration**:
   - Generate initial migration creating all Phase 1 tables and indexes.

### Phase C: Automated Tests & Verification
5. **Author `backend/tests/test_analysis_models.py`**:
   - Verify table creation.
   - Insert code file, symbols, and dependencies.
   - Insert a 384-dimensional test embedding.
   - Query embedding using cosine distance operator (`<=>`).
   - Verify cascading deletions.

---

## 7. Verification & Acceptance Criteria

### Automated Tests
```bash
python -m pytest backend/tests/test_analysis_models.py -v
```

### Acceptance Checklist
- [ ] All analysis models (`AnalyzedFile`, `CodeSymbol`, `Dependency`, `Evidence`, `CodeEmbedding`) defined $\le 300$ LOC.
- [ ] 384-dimensional vector column and HNSW cosine index configured.
- [ ] Alembic async migration environment functional.
- [ ] Cosine similarity search verified against Supabase PostgreSQL 17.
- [ ] All tests pass with 0 errors.
