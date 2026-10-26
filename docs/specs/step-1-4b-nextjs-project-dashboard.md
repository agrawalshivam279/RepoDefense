# Technical Specification: Step 1.4b — Next.js 15 Project Dashboard & Add Repository Form

> **Milestone**: 1.4 Project Creation & GitHub URL Input  
> **Feature Branch**: `feat/step-1-4b-nextjs-project-dashboard`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.4b is to complete Milestone 1.4 by delivering the repository dashboard and project creation UI in Next.js 15 (App Router). This allows authenticated users to:
1. View a list of all repositories registered under their account (`/dashboard`).
2. Add a new GitHub repository URL via an interactive modal dialog with client-side URL validation and automatic name slug preview.
3. Authenticate requests to the backend FastAPI endpoints (`/api/v1/projects`) using their Supabase JWT Bearer token.
4. Delete repositories with cascading cleanup.
5. Seamlessly navigate between the public landing page and the authenticated candidate dashboard.

---

## 2. Invariants & Guardrails

1. **Strict Auth Protection**: The `/dashboard` route checks for an active Supabase session; unauthenticated visitors are gracefully redirected to `/login`.
2. **Bearer Token API Integration**: All communications with FastAPI (`GET /api/v1/projects`, `POST /api/v1/projects`, `DELETE /api/v1/projects/{id}`) include `Authorization: Bearer <session.access_token>`.
3. **Optimistic & Error Resilient**: Displays accessible error states for 409 Conflict ("Repository already registered") and 422 Unprocessable Entity.
4. **Max 300 LOC Constraint**: All target components and pages must remain strictly under 300 lines of code.
5. **Clean Type Checking**: Must pass `npm run build` and `npm run typecheck` (`tsc --noEmit`) with 0 errors.

---

## 3. Target Files & Component Specifications

### 1. `frontend/src/types/project.ts` (New File, $\le 30$ LOC)
- `Project`: TypeScript interface matching backend `ProjectResponse` (`id`, `user_id`, `name`, `github_url`, `default_branch`, `status`, `created_at`, `updated_at`).
- `ProjectCreate`: Interface for request payload (`github_url`, `name`, `default_branch`).

### 2. `frontend/src/components/domain/ProjectCard.tsx` (New File, $\le 110$ LOC)
- Displays project title, GitHub repository URL with external link, branch tag, and status pill.
- Action button: "Start Defense" linking to `/interview/[id]` (ready for Phase 3/4).
- Action button: "Delete" icon button triggering delete confirmation callback.

### 3. `frontend/src/components/domain/AddProjectModal.tsx` (New File, $\le 160$ LOC)
- Modal dialog with form:
  - GitHub URL input with live regex format validation.
  - Project name input (auto-populated with repository slug if left empty).
  - Branch input (defaults to `main`).
- Handles API submission to `${API_URL}/api/v1/projects` using active Supabase token.
- Handles duplicate conflict (409) and validation errors (422) with in-modal error banners.

### 4. `frontend/src/app/dashboard/page.tsx` (New File, $\le 170$ LOC)
- `"use client"` dashboard page.
- Resolves active Supabase session and fetches user projects.
- Shows empty state when no repositories exist with "Add Repository" prompt.
- Renders responsive grid of `ProjectCard` components when repositories are present.

### 5. `frontend/src/components/domain/AuthStatus.tsx` (Update, $\le 90$ LOC)
- When authenticated, render a "Dashboard" navigation button linking to `/dashboard`.

---

## 4. Acceptance Criteria

1. Navigating to `/dashboard` loads authenticated user projects or redirects unauthenticated visitors to `/login`.
2. Submitting a valid GitHub URL in the Add Repository modal creates a project via the FastAPI backend and adds it to the grid.
3. Submitting an invalid or duplicate GitHub URL surfaces appropriate inline error messages.
4. Deleting a project removes it from the list and calls `DELETE /api/v1/projects/{id}`.
5. Full `npm run build` and `npm run typecheck` pass with 0 errors.
