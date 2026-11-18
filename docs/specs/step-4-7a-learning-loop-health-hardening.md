# Technical Specification: Step 4.7a — Backend Learning Loop Telemetry Hardening, Diagnostic Health Probe & Synthesis Benchmark API

## 1. Overview & Context
RepoDefense Milestone 4.7 introduces **Phase 4 Polish & Learning Loop Hardening**.
Following the delivery of the complete Phase 4 Learning Loop (Weakness Tracking, Mentor Mode, Mini Challenges, Progress Telemetry, Targeted Re-Testing, and Senior Skill Gap Analysis), Step 4.7a establishes backend operational resilience, comprehensive diagnostic health monitoring, and defensive hardening across all Phase 4 services.

Following the architectural precedent established in Step 3.8a (`/api/v1/health/simulations`), this step introduces a dedicated diagnostic probe `GET /api/v1/health/learning-loop` that validates the live operational readiness of every learning loop subsystem without arbitrary code execution.

## 2. Specialized Skills Directives
- **`doctor`**: Verifies backend Python environment, database connectivity, and CI workflow readiness before execution.
- **`security_auditor`**: Enforces strict zero arbitrary code execution, parameterized queries via SQLAlchemy 2.0 asyncpg, safe dependency override restoration, and read-only diagnostic safety.
- **`code_reviewer`**: Enforces strict $\le 300$ LOC limit per file, Pydantic v2 schemas with extra fields forbidden, and structured `structlog` logging.

## 3. Data Contracts (`backend/app/schemas/learning_health.py`)
- `ComponentHealthStatus`: Enum (`healthy`, `degraded`, `unhealthy`).
- `DatabaseModelsHealth`:
  - `status`: ComponentHealthStatus
  - `user_skills_accessible`: bool
  - `candidate_weaknesses_accessible`: bool
  - `total_user_skills`: int
  - `total_candidate_weaknesses`: int
  - `detail`: str | None
- `BenchmarkProfilesHealth`:
  - `status`: ComponentHealthStatus
  - `configured_tiers`: list[str]
  - `total_categories`: int
  - `tier_integrity_verified`: bool
  - `detail`: str | None
- `MentorServiceHealth`:
  - `status`: ComponentHealthStatus
  - `fallbacks_ready`: bool
  - `supported_fallback_topics`: list[str]
  - `detail`: str | None
- `RetestServiceHealth`:
  - `status`: ComponentHealthStatus
  - `cache_active`: bool
  - `cached_question_count`: int
  - `max_cache_capacity`: int
  - `detail`: str | None
- `LearningLoopHealthResponse`:
  - `status`: ComponentHealthStatus
  - `database_models`: DatabaseModelsHealth
  - `benchmark_profiles`: BenchmarkProfilesHealth
  - `mentor_service`: MentorServiceHealth
  - `retest_service`: RetestServiceHealth
  - `timestamp`: datetime
  - `version`: str

## 4. Business Logic & Diagnostic Engine (`backend/app/services/learning_health.py`)
- `inspect_learning_loop_health(db: AsyncSession) -> LearningLoopHealthResponse`:
  1. **Database Models Health**:
     - Queries `select(func.count(UserSkill.id))` and `select(func.count(CandidateWeakness.id))` with timeout and graceful exception catching.
     - Sets `healthy` if counts resolve, `unhealthy` if queries fail.
  2. **Benchmark Profiles Health**:
     - Validates `BENCHMARK_PROFILES` in `app/services/skill_gap.py` ensuring all 3 tiers (`mid_level`, `senior_engineer`, `staff_principal`) are populated with non-zero weights and targets in [0, 100].
  3. **Mentor Service Health**:
     - Inspects deterministic fallback catalog in `app/ai/mentor_prompts.py` (`OFFLINE_EXPLANATIONS`) confirming critical topics (`database connection pooling`, `concurrency lost updates`, `cache stampedes`, `domain decoupling`) are available for zero-crash degradation.
  4. **Retest Service Health**:
     - Inspects `retest_service._question_cache` checking active state, current item count, and maximum 1000-item FIFO capacity.
  5. **Overall Status Aggregation**:
     - If all components are `healthy`, returns `healthy`.
     - If mentor fallbacks or retest cache have warnings, returns `degraded`.
     - If database models are inaccessible, returns `unhealthy`.

## 5. REST API Router (`backend/app/api/v1/health.py`)
- Mounts `GET /api/v1/health/learning-loop` on existing health router.
- Returns 200 OK with `LearningLoopHealthResponse` when healthy or degraded.
- Returns 503 Service Unavailable when overall status is `unhealthy`.

## 6. Acceptance Criteria & Verification
- **File Limit**: All files strictly $\le 300$ LOC (`Gemini.md`).
- **Security**: Zero arbitrary code execution, read-only SQL aggregation, parameterized asyncpg queries.
- **Coverage**: 100% test coverage with hermetic unit tests in `backend/tests/test_learning_health.py`.
- **Command**: `python -m pytest backend/tests/test_learning_health.py` passes 100%, `python -m ruff check backend/app` is clean.
