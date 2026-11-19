# Technical Specification: Step 5.2b — Next.js 15 GitHub App Installation Flow & Private Repository Selector UI

## 1. Overview & Goal
Milestone 5.2 enables candidates and engineering teams to defend private repositories using a dedicated GitHub App. With the backend infrastructure (Step 5.2a) completed and verified, Step 5.2b delivers the complete candidate-facing UI in Next.js 15 App Router:
1. **GitHub App Status & Setup Link**: Automatically inspect whether the GitHub App is configured on the backend (`/api/v1/github-app/status`) and present a direct "Install / Configure GitHub App" action button.
2. **Auto-Detection of Post-Install Callback**: Detect `installation_id` from URL query parameters when GitHub redirects back to `/dashboard?installation_id=...&setup_action=install`.
3. **Interactive Private Repository Selector**: Query `/api/v1/github-app/installations/{id}/repositories`, render accessible repositories with search filtering, default branch tags, and private visibility indicators.
4. **One-Click Project Import**: Enable 1-click registration via `POST /api/v1/github-app/projects` with real-time import state and error handling (403 unauthorized, 409 conflict, 503 service unavailable).
5. **Add Project Modal Integration**: Enhance `AddProjectModal.tsx` on the `/dashboard` page with a tabbed interface ("Public Repository URL" vs "Private GitHub App").

## 2. Invariants & Guardrails
- **Tech Stack Compliance**: Next.js 15 (App Router), React 19, TypeScript strict mode, Tailwind CSS, Lucide icons.
- **Strict LOC Limit**: All `.ts` and `.tsx` files must strictly remain $\le 300$ LOC.
- **Zero Arbitrary Code Execution**: Untrusted repository names, branches, and URLs are sanitized and never evaluated.
- **Credential Protection**: Installation access tokens are handled entirely backend-side; the frontend only exchanges Supabase JWTs and numeric installation IDs.
- **Specialized Domain Skill Directive**:
  - `security_auditor`: Validate that all private repository requests carry the Supabase Bearer token and that installation ID tampering returns graceful 403 / 404 UI error notifications.

## 3. Architecture & Data Contracts

### 3.1 TypeScript Contracts (`frontend/src/types/githubApp.ts`)
- `GitHubAppStatusResponse`:
  - `configured: boolean`
  - `app_id: string | null`
  - `app_slug: string | null`
  - `install_url: string | null`
- `GitHubAppRepoItem`:
  - `id: number`
  - `name: string`
  - `full_name: string`
  - `private: boolean`
  - `default_branch: string`
  - `description: string | null`
  - `clone_url: string`
  - `html_url: string`
- `GitHubAppRepoListResponse`:
  - `installation_id: number`
  - `total_count: number`
  - `repositories: GitHubAppRepoItem[]`
- `PrivateRepoProjectCreate`:
  - `full_name: string`
  - `installation_id: number`
  - `default_branch?: string`

### 3.2 Typed REST API Client (`frontend/src/lib/githubAppApi.ts`)
- `getGitHubAppStatus(): Promise<GitHubAppStatusResponse>`
- `getInstallationRepositories(installationId: number, token?: string): Promise<GitHubAppRepoListResponse>`
- `createPrivateProject(data: PrivateRepoProjectCreate, token?: string): Promise<Project>`

### 3.3 Domain Components
1. `frontend/src/components/domain/GitHubAppRepoSelector.tsx`:
   - State: `installationIdInput`, `selectedInstallationId`, `repositories`, `searchQuery`, `loading`, `importingRepo`, `error`.
   - Renders GitHub App status indicator, installation action link, search input, repository list, and "Import" buttons.
2. `frontend/src/components/domain/AddProjectModal.tsx`:
   - Dual-tab selector: "Public Repo URL" (existing URL input form) and "Private GitHub App" (`GitHubAppRepoSelector`).
   - Seamlessly dispatches `onProjectAdded` callback to refresh the project grid on the dashboard.

## 4. Verification Plan
- Unit tests in `frontend/src/lib/__tests__/githubAppApi.test.ts` validating:
  1. `getGitHubAppStatus` success and failure handling.
  2. `getInstallationRepositories` query format, headers, and error parsing.
  3. `createPrivateProject` payload serialization and 403/409/503 error handling.
- TypeScript compilation: `cd frontend && npx tsc --noEmit`.
- Next.js 15 production build: `cd frontend && npm run build`.
- File line count audit: All files strictly $\le 300$ LOC.
