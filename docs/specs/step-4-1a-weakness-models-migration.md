# Technical Specification: Step 4.1a — Backend UserSkill & CandidateWeakness Models, Schemas & Alembic Migration

> **Milestone**: 4.1 (Weakness Tracking System)  
> **Phase**: Phase 4 — Learning Loop  
> **Step**: 4.1a (Backend Sub-slice: Relational Schema, Models & Migration)  
> **Feature Branch**: `feat/step-4-1a-weakness-models-migration`  
> **Status**: Ready for Implementation  
> **Specialized Skills**: `db_migrator`, `security_auditor`  
> **Verification Command**: `python -m pytest backend/tests/test_skill_models.py -v`

---

## 1. Executive Summary & Architectural Motivation

Phase 4 introduces the **Learning Loop** into RepoDefense: taking the candidate from evaluation and stress-testing into structured mentorship, progressive skill growth, and targeted re-testing.

To power this loop, the platform requires persistent tracking of a candidate's architectural proficiencies, recurring knowledge gaps, and specific weaknesses identified across all 6 defense simulation engines (`core_defense`, `pr_defense`, `commit_defense`, `incident_simulation`, `stress_test`, `arch_defense`).

Step 4.1a establishes the foundational relational schema and SQLAlchemy 2.0 async models for:
1. **`UserSkill`**: Aggregates a candidate's proficiency score ($0.0 - 100.0$), total evaluations, and pass/fail track record across categorized technical competencies (e.g., `architecture/database_connection_pooling`, `scalability/cache_invalidation`, `reliability/circuit_breaker`).
2. **`CandidateWeakness`**: Captures explicit observed deficiencies from simulation turns (question prompt, candidate response, mentor feedback, severity tier `critical|major|minor`, simulation mode anchor, resolution state for re-testing, and optional `Vector(384)` topic embedding for semantic matching in Milestone 4.5).
3. **Alembic Migration**: An asyncpg-compatible migration creating `user_skills` and `candidate_weaknesses` tables with composite B-tree indexes, foreign keys with cascading deletes, and mandatory Supabase public schema RLS lockdown (`ENABLE ROW LEVEL SECURITY` + revoking `anon`/`authenticated` table grants).

---

## 2. Target Files & LOC Budget

| Target File | Nature | Target LOC | Role |
| :--- | :--- | :--- | :--- |
| `backend/app/models/skill.py` | New | ~160 LOC | SQLAlchemy 2.0 async models for `UserSkill` and `CandidateWeakness` with `TimestampMixin` and cascading FKs. |
| `backend/app/schemas/skill.py` | New | ~150 LOC | Pydantic v2 schemas for skill proficiencies, weakness items, severity enums, and summary responses. |
| `backend/alembic/versions/4c8d1e2f3a4b_create_user_skills_and_weaknesses.py` | New | ~130 LOC | Async Alembic migration creating both tables, composite indexes, and enforcing Supabase public schema RLS lockdown. |
| `backend/tests/test_skill_models.py` | New | ~180 LOC | Hermetic unit & schema tests validating Pydantic validation, SQLAlchemy model instantiation, cascading deletes, and RLS metadata. |
| `backend/app/models/__init__.py` | Modified | ~30 LOC | Export `UserSkill` and `CandidateWeakness` in public model exports. |
| `backend/app/models/project.py` | Modified | ~150 LOC | Add back-populating relationship fields `skills` and `weaknesses` on `User` and `Project`. |

*Total target files*: 4 core files + 2 lightweight model link modifications ($\le 4$ primary implementation files).  
*Code Volume Gate*: All files strictly $\le 300$ LOC (`Gemini.md` Rule).

---

## 3. Data Contracts & Schema Definitions

### 3.1 SQLAlchemy 2.0 Async Models (`backend/app/models/skill.py`)

```python
class UserSkill(Base, TimestampMixin):
    __tablename__ = "user_skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    proficiency_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    total_evaluations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_evaluations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_evaluations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "category", "topic", name="uq_user_skills_user_category_topic"),
        Index("ix_user_skills_user_proficiency", "user_id", "proficiency_score"),
    )

class CandidateWeakness(Base, TimestampMixin):
    __tablename__ = "candidate_weaknesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    simulation_mode: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="major", nullable=False)
    question_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    topic_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(384), nullable=True)

    __table_args__ = (
        Index("ix_candidate_weaknesses_user_resolved_severity", "user_id", "resolved", "severity"),
        Index("ix_candidate_weaknesses_project_mode", "project_id", "simulation_mode"),
    )
```

### 3.2 Pydantic v2 Schemas (`backend/app/schemas/skill.py`)

- `WeaknessSeverity`: Enum (`critical`, `major`, `minor`).
- `SkillCategory`: Enum (`architecture`, `scalability`, `reliability`, `security`, `concurrency`, `tradeoffs`, `code_quality`, `devops_sre`).
- `UserSkillResponse`: Serialized representation with clamped proficiency score (`0.0 <= score <= 100.0`).
- `CandidateWeaknessCreate`: Ingestion schema when a defense turn evaluates to a gap.
- `CandidateWeaknessResponse`: Full serialized weakness model with resolution status and metadata.
- `UserSkillsOverviewResponse`: Rollup containing summary counts, average proficiency, top strengths, and unresolved critical weaknesses.

---

## 4. Specialized Domain Skill Directives

### 4.1 `db_migrator` Directive
- **Alembic Down Revision**: Must chain cleanly from current HEAD `3b7c9d4e2f1a`.
- **Asyncpg Compatibility**: DDL execution must use asyncpg-safe syntax (`op.create_table`, `op.create_index`).
- **Reversible Downgrade**: `downgrade()` must cleanly drop both tables and their indexes.
- **Foreign Key Constraints**: Foreign keys pointing to `users.id` and `projects.id` must declare `ondelete="CASCADE"`.

### 4.2 `security_auditor` Directive
- **Supabase Public Schema RLS Lockdown**:
  Both new tables (`user_skills`, `candidate_weaknesses`) must execute:
  ```sql
  ALTER TABLE public."user_skills" ENABLE ROW LEVEL SECURITY;
  ALTER TABLE public."candidate_weaknesses" ENABLE ROW LEVEL SECURITY;
  ```
  And conditionally revoke all privileges from `anon` and `authenticated` roles to eliminate PostgREST direct exposure vulnerabilities.
- **Zero Arbitrary Code Execution**: No user code execution; static SQL schema definitions only.

---

## 5. Verification & Testing Strategy

- **Test Suite**: `backend/tests/test_skill_models.py`
- **Coverage Target**: $\ge 90\%$ statement coverage on `models/skill.py` and `schemas/skill.py`.
- **Key Assertions**:
  1. `test_user_skill_schema_validation`: Validates score clamping, category enums, and required fields.
  2. `test_candidate_weakness_schema_validation`: Validates severity tiers, optional responses, and default values.
  3. `test_user_skill_model_instantiation`: Verifies SQLAlchemy 2.0 column mappings, default UUID primary keys, and timestamp generation.
  4. `test_candidate_weakness_model_instantiation`: Verifies all foreign key references, vector column declaration, and default resolved state.
  5. `test_migration_rls_lockdown_contract`: Confirms both new table names are present in the migration's RLS lockdown configuration.

---

## 6. Acceptance Criteria

- [ ] `backend/app/models/skill.py` defines `UserSkill` and `CandidateWeakness` under 300 LOC.
- [ ] `backend/app/schemas/skill.py` defines all Pydantic v2 schemas and enums under 300 LOC.
- [ ] Alembic migration `4c8d1e2f3a4b_create_user_skills_and_weaknesses.py` created with RLS lockdown and reversible downgrade under 300 LOC.
- [ ] `backend/tests/test_skill_models.py` passes 100% with $\ge 90\%$ coverage.
- [ ] `ruff check backend/app backend/tests` passes with 0 lint errors.
