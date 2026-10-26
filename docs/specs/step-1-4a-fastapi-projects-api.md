# Technical Specification: Step 1.4a — FastAPI Projects API & GitHub URL Validation

> **Milestone**: 1.4 Project Creation & GitHub URL Input  
> **Feature Branch**: `feat/step-1-4a-fastapi-projects-api`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.4a is to implement the backend repository project management API in FastAPI. This enables authenticated users to register GitHub repositories for architectural analysis and defense simulation. Key capabilities:
1. Strict regex-based GitHub URL validation and automatic repository name extraction.
2. `POST /api/v1/projects`: Creates a new `Project` record linked to the authenticated `current_user.id` in PostgreSQL 17, with duplicate prevention (409 Conflict).
3. `GET /api/v1/projects`: Lists all registered repositories belonging to the authenticated user with strict multi-tenant isolation.
4. `GET /api/v1/projects/{project_id}`: Retrieves single project details, ensuring cross-tenant privacy (404 for unauthorized access).
5. `DELETE /api/v1/projects/{project_id}`: Safely removes a project and cascades cleanup across all child snapshots, files, and vector embeddings.

---

## 2. Invariants & Security Guardrails

1. **Zero Code Execution**: We only store the repository URL and metadata. We do not clone or execute code at this stage.
2. **Strict Multi-Tenant Isolation**: Every project query must filter by `Project.user_id == current_user.id`. Users can never view or delete another user's projects.
3. **Aggressive URL Sanitization**: Reject invalid schemes, non-GitHub hosts, command injection attempts, and malformed repo paths using parameterized Pydantic validators.
4. **Referential Integrity**: Project deletions cleanly cascade to all associated child records (`RepositorySnapshot`, `AnalyzedFile`, `Evidence`, `Dependency`, `CodeEmbedding`).
5. **Max 300 LOC Constraint**: Every file strictly adheres to the 300 LOC limit.

---

## 3. Target Files & Component Specifications

### 1. `backend/app/schemas/project.py` (New File, $\le 70$ LOC)
- `ProjectCreate(BaseModel)`:
  - `github_url: str`: Validated with regex `^https?://(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$`.
  - `name: Optional[str] = None`: If omitted, dynamically extracted from repository slug in the URL.
  - `default_branch: str = Field(default="main", max_length=100)`
- `ProjectResponse(BaseModel)`:
  - `id: uuid.UUID`
  - `user_id: uuid.UUID`
  - `name: str`
  - `github_url: str`
  - `default_branch: str`
  - `status: str`
  - `created_at: datetime`
  - `updated_at: datetime`
  - `model_config = ConfigDict(from_attributes=True)`

### 2. `backend/app/api/v1/projects.py` (New File, $\le 110$ LOC)
- Router prefix: `/projects`, tags: `["Projects"]`
- `POST /`:
  - Validates `ProjectCreate`.
  - Checks duplicate `github_url` for `current_user.id` (returns 409 Conflict if duplicate).
  - Creates `Project(id=uuid.uuid4(), user_id=current_user.id, name=..., github_url=..., default_branch=..., status="pending")`.
  - Returns `201 Created` with `ProjectResponse`.
- `GET /`:
  - Lists projects where `user_id == current_user.id` ordered by `created_at.desc()`.
  - Returns `list[ProjectResponse]`.
- `GET /{project_id}`:
  - Retrieves project by ID for `current_user.id`. Returns 404 if not found or unauthorized.
- `DELETE /{project_id}`:
  - Deletes project for `current_user.id`. Returns 204 No Content (or 404 if not found).

### 3. `backend/app/main.py` (Update)
- Register `projects_router` under `f"{settings.API_V1_STR}/v1"`.

### 4. `backend/tests/test_projects.py` (New File, $\le 200$ LOC)
- Test suite with hermetic Supabase database connectivity:
  1. `test_unauthenticated_request_rejected`: 401 Unauthorized without token.
  2. `test_create_project_invalid_url_rejected`: 422 Unprocessable Entity for invalid or non-GitHub URLs.
  3. `test_create_project_success`: Valid GitHub URL creates project with default name extraction, status 201.
  4. `test_create_project_duplicate_conflict`: Same GitHub URL returns 409 Conflict.
  5. `test_list_projects_tenancy_isolation`: User A cannot see User B's projects.
  6. `test_get_project_and_unauthorized_access`: User B receives 404 attempting to view User A's project.
  7. `test_delete_project_lifecycle`: Deletes project and confirms 404 on subsequent lookup.

---

## 4. Acceptance Criteria

1. Non-GitHub and malformed URLs are rejected with HTTP 422.
2. Valid GitHub repository URLs create database `Project` records tied to `current_user.id`.
3. Users only see their own projects in `GET /api/v1/projects`.
4. Full backend test suite passes (all existing 14 tests + new project tests).
5. All files conform to $\le 300$ LOC and 0 `ruff` errors.
