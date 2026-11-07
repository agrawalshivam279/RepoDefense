# Technical Specification: Step 2.12a — Backend Database Indexing & Query Optimization for Phase 2 Workloads

> **Milestone**: 2.12 (Phase 2 Polish & Optimization)  
> **Step**: 2.12a  
> **Feature Branch**: `feat/step-2-12a-database-indexing-optimization`  
> **Status**: Ready for Implementation  
> **Specialized Skill**: `db_migrator`  
> **Verification Command**: `python -m pytest backend/tests/test_db_indexes.py -v`

---

## 1. Executive Summary & Architectural Motivation

Throughout Phase 2 (Milestones 2.1 through 2.11), RepoDefense introduced several high-frequency query patterns across relational tables:
1. **Technology Health Audit (`Dependency`)**: Filters by `Dependency.project_id` and orders by `Dependency.name.asc()`.
2. **Architecture Pattern & Risk Detection (`Evidence`)**: Filters by `Evidence.project_id` and `Evidence.evidence_type` / category.
3. **Repository Coverage & Directory Heatmaps (`AnalyzedFile`)**: Filters by `AnalyzedFile.snapshot_id` and sorts by `AnalyzedFile.path`.
4. **Code Ownership & Blame Attribution (`CodeSymbol`)**: Queries symbols by `file_id` and `kind`.

While initial schema migrations (`16d48d0545e1_create_initial_schema.py`) provided primary keys and foreign keys, critical composite and filtering B-tree indexes were omitted (e.g., `dependencies` lacked an index on `project_id`, `analyzed_files` lacked an index on `snapshot_id`). 

Step 2.12a implements a dedicated Alembic async migration adding targeted B-tree and composite indexes, updates SQLAlchemy models in `backend/app/models/analysis.py`, tunes database queries, and validates safe reversible upgrades and downgrades under PostgreSQL 17.

---

## 2. Target Files & LOC Budget

| File | Nature | Target LOC | Role |
| :--- | :--- | :--- | :--- |
| `backend/alembic/versions/2a3f8b9c1d2e_add_phase2_performance_indexes.py` | New | ~80 LOC | Asyncpg Alembic migration adding composite and filtering B-tree indexes with reversible `downgrade()`. |
| `backend/app/models/analysis.py` | Modified | ~220 LOC | Declare explicit `Index` constructs on `Dependency`, `Evidence`, `AnalyzedFile`, and `CodeSymbol`. |
| `backend/tests/test_db_indexes.py` | New | ~160 LOC | Hermetic unit & schema tests verifying index creation, metadata reflection, and migration reversibility. |

*Total files*: 3 files ($\le 4$ target file limit).  
*Max file size*: $\le 220$ LOC ($\le 300$ strict LOC limit).

---

## 3. Specialized Domain Skill Directive: `db_migrator`

This step activates the **`db_migrator`** domain skill:
- **Asyncpg Compatibility**: Migration must be compatible with SQLAlchemy asyncpg runtime.
- **Index Definitions**:
  1. `ix_dependencies_project_name`: Composite B-tree index on `(project_id, name)` on `dependencies`.
  2. `ix_analyzed_files_snapshot_path`: Composite B-tree index on `(snapshot_id, path)` on `analyzed_files`.
  3. `ix_evidence_project_type`: Composite B-tree index on `(project_id, evidence_type)` on `evidence`.
  4. `ix_code_symbols_file_kind`: Composite B-tree index on `(file_id, kind)` on `code_symbols`.
- **Reversible Downgrade**: The `downgrade()` function must cleanly drop all four indexes using `op.drop_index()`.
- **Zero Arbitrary Code Execution**: No user code execution; operates strictly at DDL level.

---

## 4. Sequential Thinking MCP Evaluation

- **Algorithmic Complexity**: Low. Standard PostgreSQL B-tree index generation.
- **Risk Assessment**: Safe non-blocking schema migration. All target tables exist and indices do not enforce uniqueness, avoiding constraint violation collisions.
- **Reversibility**: High. `op.drop_index` completely undoes changes.

---

## 5. Implementation Details

### A. Alembic Migration Script
- File: `backend/alembic/versions/<revision>_add_phase2_performance_indexes.py`
- Down revision: `16d48d0545e1`
- `upgrade()`:
  - `op.create_index("ix_dependencies_project_name", "dependencies", ["project_id", "name"], unique=False)`
  - `op.create_index("ix_analyzed_files_snapshot_path", "analyzed_files", ["snapshot_id", "path"], unique=False)`
  - `op.create_index("ix_evidence_project_type", "evidence", ["project_id", "evidence_type"], unique=False)`
  - `op.create_index("ix_code_symbols_file_kind", "code_symbols", ["file_id", "kind"], unique=False)`
- `downgrade()`:
  - Drops the created indexes cleanly in reverse order.

### B. SQLAlchemy Model Declarations (`backend/app/models/analysis.py`)
- Add `__table_args__` with `Index(...)` constructs matching the Alembic indexes to keep SQLAlchemy declarative metadata in 100% sync with the database schema.

### C. Hermetic Unit & Schema Tests (`backend/tests/test_db_indexes.py`)
- Test metadata reflection of composite indexes in SQLAlchemy models.
- Test migration module syntax and functions (`upgrade` and `downgrade` definitions).
- Test mock query plan / compilation with composite index filters.

---

## 6. Verification Checklist

- [ ] Stage 0: `python -m ruff check backend/app backend/tests` passes with 0 errors.
- [ ] Stage 0.5: `db_migrator` checklist satisfied (reversible downgrade, index definitions, asyncpg safe).
- [ ] Stage 1: `python -m pytest backend/tests/test_db_indexes.py -v` passes 100%.
- [ ] Stage 2: Code review & LOC audit verifies all files $\le 300$ LOC.
