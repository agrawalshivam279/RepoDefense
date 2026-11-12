# Technical Specification: Step 3.7a — Backend Performance Analytics Aggregation Service & REST API

## 1. Metadata & Branch
- **Step ID**: `3.7a` (Sub-slice of Milestone 3.7: Enhanced Analytics & Visualizations)
- **Feature Slug**: `step-3-7a-analytics-backend`
- **Git Branch**: `feat/step-3-7a-analytics-backend`
- **Scope**: Backend Schema, Service Aggregation Layer, FastAPI Router, Unit/Integration Tests (`<= 300 LOC/file`)
- **Specialized Skills Active**: `security_auditor` (tenant isolation / IDOR 404 semantics, parameterized SQLAlchemy queries, zero code execution)

---

## 2. Objective & Architecture

Provide a deterministic, low-latency REST analytics layer aggregating candidate performance across all 6 RepoDefense interview & defense modes alongside static repository ground truth (`AnalyzedFile` language breakdown, `calculate_project_coverage` module heatmaps, and `audit_project_technology` health scores).

### Endpoints
1. `GET /api/v1/analytics/workspace`
   - Aggregates cross-mode defense session performance across all `Project` records owned by `current_user`.
2. `GET /api/v1/analytics/projects/{project_id}`
   - Returns detailed analytics for a single user-owned project, or HTTP `404` if missing or owned by a different user.

### Target Files (`<= 4` Primary Modules + Router Mount)
1. `backend/app/schemas/analytics.py` (`~140` LOC)
2. `backend/app/services/analytics.py` (`~245` LOC)
3. `backend/app/api/v1/analytics.py` (`~75` LOC) + mount in `backend/app/main.py`
4. `backend/tests/test_analytics.py` (`~240` LOC)

---

## 3. Data Contracts (`app/schemas/analytics.py`)

- **`DefenseModeKey`**: `"core_defense" | "pr_defense" | "commit_defense" | "stress_test" | "incident_simulation" | "arch_defense"`
- **`ModePerformanceMetric`**: `mode`, `label`, `sessions_total`, `sessions_completed`, `avg_score_pct` (`0.0..100.0 | None`), `best_score_pct`, `pass_rate_pct`
- **`ScoreTrendPoint`**: `session_id`, `mode`, `label`, `score_pct` (`0.0..100.0`), `timestamp`, `topic_or_title`
- **`CategorySkillMetric`**: `category`, `confidence_pct` (`0.0..100.0`), `evaluations_count`
- **`LanguageDistributionItem`**: `language`, `file_count`, `total_lines`, `line_share_pct`
- **`ModuleCoveragePoint`**: `module_path`, `coverage_pct`, `tested_files`, `total_files`
- **`ProjectAnalyticsResponse`**: `project_id`, `project_name`, `overall_readiness_pct`, `total_sessions`, `completed_sessions`, `file_coverage_pct`, `evidence_coverage_pct`, `tech_health_score`, `mode_breakdown`, `category_skills`, `score_trend`, `language_distribution`, `module_coverage`
- **`WorkspaceAnalyticsSummary`**: `total_projects`, `analyzed_projects`, `total_sessions`, `completed_sessions`, `avg_readiness_pct`, `mode_breakdown`, `recent_trend`

### Score Normalization Standard
- Core / PR / Commit Defense (`overall_score`: `1.0..10.0`), Stress Test (`overall_score`: `1..10`), Architecture Defense (`overall_score`: `1..10`) are multiplied by `10.0` and clamped to `[0.0, 100.0]`.
- Incident Simulation (`overall_score`: `0.0..100.0`) is clamped directly to `[0.0, 100.0]`.
- Pass threshold across modes: normalized score `>= 70.0`.

---

## 4. Security & Invariants Checklist
- [x] Zero arbitrary repository code execution (pure database metadata + session metric aggregation).
- [x] Strict parameterized SQLAlchemy ORM queries only (no raw interpolated SQL).
- [x] Tenant ownership enforced on every project lookup (`Project.user_id == current_user.id`) returning HTTP `404` for unauthorized or absent resources.
- [x] Workspace aggregation restricts in-memory store scans strictly to `project_ids` owned by `current_user.id`.
- [x] Non-fatal graceful degradation if optional coverage/tech audit metadata raises on unanalyzed projects.

---

## 5. Verification Plan
- `python -m ruff check backend/app backend/tests`
- `python -m pytest backend/tests/test_analytics.py -v --cov=app.schemas.analytics --cov=app.services.analytics --cov=app.api.v1.analytics --cov-report=term-missing --cov-branch`
