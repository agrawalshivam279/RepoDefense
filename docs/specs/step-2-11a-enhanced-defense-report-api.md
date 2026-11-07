# Technical Specification: Step 2.11a — Backend Enhanced Defense Report Aggregation Service & REST API

## 1. Overview
Step 2.11a builds the backend data contracts, aggregation service, and REST API for the Enhanced Defense Report. It bridges the oral interview defense debrief with codebase ground truth by unifying evaluation scores, verified resume claims, detected architectural topology patterns, Mermaid flowcharts, and dependency health audits into a single comprehensive evaluation payload.

## 2. Requirements & Acceptance Criteria
- **Data Model (`backend/app/schemas/report.py`)**:
  - `EnhancedDefenseReportResponse` extending `DefenseReportResponse`:
    - Base fields: `session_id`, `project_id`, `overall_score`, `verdict`, `summary`, `category_scores`, `key_strengths`, `critical_blind_spots`, `actionable_recommendations`, `total_questions`, `completed_at`.
    - Enhanced fields:
      - `architecture_primary_pattern`: Optional[str]
      - `architecture_confidence_tier`: Optional[str]
      - `diagram_mermaid_code`: Optional[str]
      - `tech_health_score`: Optional[int]
      - `tech_flagged_count`: Optional[int]
      - `tech_total_dependencies`: Optional[int]
      - `claims_verified_count`: Optional[int]
      - `claims_total_count`: Optional[int]
- **Domain Aggregation Service (`backend/app/services/enhanced_report.py`)**:
  - Function: `generate_enhanced_defense_report(session: DefenseSessionState, db: AsyncSession) -> EnhancedDefenseReportResponse`
  - Leverages `generate_defense_report(session)` for core Principal Engineer evaluation.
  - Queries `Project` record from DB.
  - Safely extracts and merges architectural pattern data, Mermaid diagram syntax, and technology health audit metrics with graceful fallbacks if sub-analyses are not populated.
- **REST API Endpoint (`backend/app/api/v1/defense.py`)**:
  - `GET /defense/sessions/{session_id}/enhanced-report`
  - Protected with Supabase JWT Bearer token authentication via `get_current_user`.
  - Multi-tenant isolation: enforces `project.user_id == current_user.id`.
  - Guards against incomplete sessions (`400 Bad Request` if `session.status != DefenseStage.SESSION_COMPLETED`).
- **Hermetic Tests (`backend/tests/test_enhanced_report.py`)**:
  - Schema serialization and default value tests.
  - Service unit test with mock session, project, and analyzers.
  - API endpoint integration test: 200 OK, 404 Not Found, 403 Forbidden, 400 Bad Request.
- **Constraints**:
  - Strictly $\le 300$ LOC per file across all touched files.
  - Zero arbitrary code execution.
  - Complete compliance with `ruff check` and `tsc --noEmit`.
