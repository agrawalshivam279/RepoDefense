# Technical Specification: Step 4.6a — Backend Senior Benchmark Engine, Skill Gap Aggregator & REST API

## 1. Overview & Context
RepoDefense Milestone 4.6 introduces **Skill Gap Analysis**, comparing candidate interview performance and proficiency scores against standard Senior and Staff/Principal Engineer competency expectations.
Step 4.6a implements the backend evaluation engine, benchmark profiles, category deficit calculators, remediation ranker, and authenticated REST API endpoint.

## 2. Industry Benchmark Profiles
We define standard competency baselines across core architectural domains:
- `SYSTEM_ARCHITECTURE`: Scalability, modularity, system boundaries, distributed patterns.
- `DATABASE_DESIGN`: Indexing, query tuning, connection management, consistency vs availability.
- `CONCURRENCY_PERFORMANCE`: Race conditions, locking, thread safety, event-driven primitives.
- `SECURITY_ISOLATION`: Multi-tenant isolation, authorization, sanitization, threat boundaries.
- `RELIABILITY_OBSERVABILITY`: Fault tolerance, circuit breakers, structured telemetry, health probes.
- `API_CONTRACT_DESIGN`: Schema idempotency, backward compatibility, error taxonomy.

Profiles:
- `MID_LEVEL`: Core baseline (~65 average).
- `SENIOR_ENGINEER`: Senior production bar (~80-85 average).
- `STAFF_PRINCIPAL`: Staff/Principal architectural bar (~90-95 average).

## 3. Data Contracts (`backend/app/schemas/skill_gap.py`)
- `TargetRoleBenchmark`: Enum (`mid_level`, `senior_engineer`, `staff_principal`).
- `CategoryGapMetric`:
  - `category`: String / Domain enum.
  - `current_score`: Float [0, 100].
  - `benchmark_score`: Float [0, 100].
  - `gap_deficit`: Float ($max(0.0, benchmark - current)$).
  - `status`: Enum (`surpassed`, `met`, `moderate_gap`, `critical_gap`).
  - `weight`: Float.
  - `percentile_estimate`: Float [0, 99.9].
- `RemediationRecommendation`:
  - `topic`: String.
  - `category`: String.
  - `priority`: Enum (`critical`, `high`, `medium`, `low`).
  - `rationale`: String.
  - `unresolved_weakness_count`: Integer.
  - `suggested_action`: String.
- `SkillGapAnalysisResponse`:
  - `target_role`: TargetRoleBenchmark.
  - `overall_candidate_score`: Float [0, 100].
  - `overall_benchmark_score`: Float [0, 100].
  - `overall_readiness_pct`: Float [0, 100].
  - `categories`: List[CategoryGapMetric].
  - `recommendations`: List[RemediationRecommendation].
  - `strengths`: List[str].
  - `critical_gaps`: List[str].
  - `analyzed_at`: Datetime.

## 4. Business Logic (`backend/app/services/skill_gap.py`)
- Reads `UserSkill` rows for `user_id` (and optionally filtered by project via weaknesses).
- Aggregates proficiency scores by category. Default unassessed categories receive baseline score `50.0` or `0.0` (flagged unassessed).
- Calculates weighted overall readiness:
  $$\text{readiness\_pct} = \min(100.0, \frac{\text{candidate\_weighted\_score}}{\text{benchmark\_weighted\_score}} \times 100)$$
- Queries active `CandidateWeakness` records (`is_resolved=False`) to prioritize actionable remediation items.
- Sorts recommendations by gap severity and active weakness density.

## 5. REST API Router (`backend/app/api/v1/skill_gap.py`)
- `GET /api/v1/skills/gap-analysis`:
  - Query params: `target_role: TargetRoleBenchmark = TargetRoleBenchmark.SENIOR_ENGINEER`, `project_id: UUID | None = None`.
  - Auth: Supabase JWT Bearer token required. Enforces tenant isolation (`current_user.id`).
  - Responses: 200 OK (`SkillGapAnalysisResponse`), 401 Unauthorized, 422 Unprocessable.

## 6. Acceptance Criteria & Guardrails
- **File Limit**: All authored/modified files strictly $\le 300$ LOC (`Gemini.md`).
- **Security**: Zero code execution, parameterized queries via SQLAlchemy 2.0 async session, IDOR enforcement.
- **Coverage**: 100% test coverage with hermetic unit tests in `backend/tests/test_skill_gap.py`.
- **Quality**: `ruff check` passes with 0 warnings, `pytest` passes with 0 regressions.
