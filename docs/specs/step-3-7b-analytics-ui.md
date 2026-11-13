# Technical Specification: Next.js 15 Enhanced Analytics & Visualizations Dashboard UI

> **Step ID**: `3.7b`  
> **Target Module**: `frontend/src/types/analytics.ts`, `frontend/src/lib/analyticsApi.ts`, `frontend/src/components/domain/AnalyticsCharts.tsx`, `frontend/src/components/domain/AnalyticsGroundTruthPanels.tsx`, `frontend/src/app/projects/[id]/analytics/page.tsx`, `frontend/src/components/domain/ProjectNavHeader.tsx`, `frontend/src/lib/__tests__/analyticsApi.test.ts`  
> **Git Feature Branch**: `feat/step-3-7b-analytics-ui`  
> **Status**: Ready for Implementation  
> **Created**: 2026-11-12

---

## 1. Executive Summary

Step 3.7b delivers the Next.js 15 App Router Performance Analytics & Visualizations Dashboard (`/projects/[id]/analytics`), completing Milestone 3.7. It consumes the backend cross-mode analytics API introduced in Step 3.7a (`/api/v1/analytics/projects/{project_id}` and `/api/v1/analytics/workspace`) to visualize readiness scores, chronological trends, category skill radars, per-mode pass/best/average breakdowns across all 6 RepoDefense modes, static codebase language composition, and directory-level defense coverage heatmaps.

---

## 2. Dependencies & Prerequisites

- **Depends on**: Step 3.7a (`backend/app/schemas/analytics.py`, `backend/app/api/v1/analytics.py`), existing `ProjectNavHeader.tsx`, `projectApi.ts`, and Supabase browser auth (`supabase.ts`).
- **Blocked by**: None.
- **Tech Stack Invariant**: Strictly uses Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS + `lucide-react` (zero extra npm dependencies; accessible custom SVG charts replace external React 19-incompatible charting libraries).

---

## 3. Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Frontend exclusively renders static/historical JSON analytics metrics; no arbitrary repository code execution.
- [x] **Runtime Payload Validation & Safe Rendering**: `analyticsApi.ts` narrows `unknown` JSON responses, rejects non-finite numbers (`NaN` / `Infinity`), distinguishes explicit `null` coverage/health metrics (`"Unavailable"`) from `0.0%`, URL-encodes `projectId`, and avoids `dangerouslySetInnerHTML`.
- [x] **Multi-Tenant Auth**: All analytics requests send Supabase `access_token` Bearer headers; missing sessions redirect cleanly to `/login`.
- [x] **File Size Cap**: Every created or modified file strictly adheres to `<= 300 LOC`.

### Specialized Skills Directive
- **Active Skill(s)**: None required beyond standard UI verification (`typecheck`, `next build`, `node --test`, `/code_reviewer`) — no backend DB migrations, AST parsers, ingestion workers, or LLM prompts are modified.

---

## 4. Data Contracts & Interfaces

### 4.1 TypeScript Data Contracts (`frontend/src/types/analytics.ts`)

1:1 mirror of `backend/app/schemas/analytics.py`:

```ts
export type DefenseModeKey =
  | "core_defense"
  | "pr_defense"
  | "commit_defense"
  | "stress_test"
  | "incident_simulation"
  | "arch_defense";

export interface ModePerformanceMetric {
  mode: DefenseModeKey;
  label: string;
  sessions_total: number;
  sessions_completed: number;
  avg_score_pct: number | null;
  best_score_pct: number | null;
  pass_rate_pct: number | null;
}

export interface ScoreTrendPoint {
  session_id: string;
  mode: DefenseModeKey;
  label: string;
  score_pct: number;
  timestamp: string;
  topic_or_title: string;
}

export interface CategorySkillMetric {
  category: string;
  confidence_pct: number;
  evaluations_count: number;
}

export interface LanguageDistributionItem {
  language: string;
  file_count: number;
  total_lines: number;
  line_share_pct: number;
}

export interface ModuleCoveragePoint {
  module_path: string;
  coverage_pct: number;
  tested_files: number;
  total_files: number;
}

export interface ProjectAnalyticsResponse {
  project_id: string;
  project_name: string;
  overall_readiness_pct: number | null;
  total_sessions: number;
  completed_sessions: number;
  file_coverage_pct: number | null;
  evidence_coverage_pct: number | null;
  tech_health_score: number | null;
  mode_breakdown: ModePerformanceMetric[];
  category_skills: CategorySkillMetric[];
  score_trend: ScoreTrendPoint[];
  language_distribution: LanguageDistributionItem[];
  module_coverage: ModuleCoveragePoint[];
}

export interface WorkspaceAnalyticsSummary {
  total_projects: number;
  analyzed_projects: number;
  total_sessions: number;
  completed_sessions: number;
  avg_readiness_pct: number | null;
  mode_breakdown: ModePerformanceMetric[];
  recent_trend: ScoreTrendPoint[];
}
```

---

## 5. Step-by-Step Implementation Sequence

1. **Phase A: Types, Validated API Client & Unit Tests**
   - [ ] Author `frontend/src/types/analytics.ts` (`<= 90` LOC).
   - [ ] Author `frontend/src/lib/analyticsApi.ts` (`<= 230` LOC) implementing `getProjectAnalytics`, `getWorkspaceAnalytics`, finite nullable checks, and FastAPI error extraction.
   - [ ] Author `frontend/src/lib/__tests__/analyticsApi.test.ts` (`<= 170` LOC) covering happy-path parsing, `null` coverage preservation, `NaN` rejection, `AbortSignal`, and error propagation.
2. **Phase B: Modular SVG Visualizations & Ground Truth Panels**
   - [ ] Author `frontend/src/components/domain/AnalyticsCharts.tsx` (`<= 280` LOC) exporting `ReadinessTrendChart`, `SkillRadarChart`, and `ModePerformanceBars`.
   - [ ] Author `frontend/src/components/domain/AnalyticsGroundTruthPanels.tsx` (`<= 220` LOC) exporting `LanguageBreakdownCard`, `ModuleCoverageList`, and `WorkspaceBenchmarkCard`.
3. **Phase C: Dashboard Page & Navigation Tab**
   - [ ] Author `frontend/src/app/projects/[id]/analytics/page.tsx` (`<= 250` LOC) integrating `ProjectNavHeader`, `AbortController` + monotonic request guards, KPI cards, mode filter, charts, and ground-truth panels.
   - [ ] Update `frontend/src/components/domain/ProjectNavHeader.tsx` (`<= 220` LOC) adding `"analytics"` tab and navigation link.

---

## 6. Verification & Acceptance Criteria

### Automated Checks (Executed later in `/verify_step`)
```bash
cd frontend
npm run typecheck
npm run lint
npm run build
node --experimental-strip-types --test src/lib/__tests__/analyticsApi.test.ts
```

### Acceptance Checklist
- [ ] `npm run typecheck` and `npm run build` succeed with 0 errors
- [ ] Hermetic `node --test` tests pass for `analyticsApi.ts`
- [ ] Every created/modified file is `<= 300 LOC`
- [ ] Nullable backend metrics (`null` coverage/health/readiness) render `"Unavailable"` instead of `0%`
- [ ] Interactive trend tooltip, skill radar, mode drill-down links, language bar, and module coverage bars render cleanly with zero unsafe HTML injection
