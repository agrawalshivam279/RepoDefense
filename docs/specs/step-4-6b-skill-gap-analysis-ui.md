# Technical Specification: Step 4.6b — Next.js 15 Senior Benchmark Radar Visualizer & Skill Gap Matrix UI

## 1. Overview & Context
Following Step 4.6a's backend gap analysis REST API, Step 4.6b builds the candidate-facing interactive visualization suite for **Milestone 4.6: Skill Gap Analysis**.
It enables candidates to visualize how their architectural competencies compare against Senior and Staff/Principal Engineer baselines via a custom SVG Radar Chart, Category Comparison Matrix, and prioritized Remediation Roadmap.

## 2. TypeScript Contracts (`frontend/src/types/skillGap.ts`)
Mirrors backend Pydantic models:
- `TargetRoleBenchmark`: `'mid_level' | 'senior_engineer' | 'staff_principal'`
- `GapStatus`: `'surpassed' | 'met' | 'moderate_gap' | 'critical_gap'`
- `RemediationPriority`: `'critical' | 'high' | 'medium' | 'low'`
- `CategoryGapMetric`, `RemediationRecommendation`, `SkillGapAnalysisResponse`
- Styling and label helper functions (`getGapStatusBadge`, `getPriorityBadge`).

## 3. Typed API Client (`frontend/src/lib/skillGapApi.ts`)
- `fetchSkillGapAnalysis(token: string, targetRole?: TargetRoleBenchmark, projectId?: string | null): Promise<SkillGapAnalysisResponse>`
- Runtime assertions with `unknown` type safety, non-finite score rejection, and error message extraction.

## 4. Domain Components (`frontend/src/components/domain/`)
- `SkillRadarChart.tsx`: Clean mathematical SVG radar visualizer plotting both Candidate and Benchmark polygons across the 6 axes (`system_architecture`, `database_design`, `concurrency_performance`, `security_isolation`, `reliability_observability`, `api_contract_design`) with grid rings, vertex points, and hover legend.
- `BenchmarkComparisonMatrix.tsx`: Detailed category scorecard displaying current vs target scores, gap deficits, status badges, and estimated percentiles.
- `SkillGapRemediationsCard.tsx`: Prioritized remediation items with priority indicators, explanation rationales, and targeted actions.

## 5. Dashboard Page (`frontend/src/app/dashboard/skill-gap/page.tsx`)
- Role benchmark switcher (`Senior Engineer`, `Staff/Principal`, `Mid-Level`).
- Overall readiness gauge and score dials.
- Integrated radar visualization, matrix, and remediation action cards.
- Multi-tenant auth token handling with refresh resilience.

## 6. Acceptance Criteria
- Strict $\le 300$ LOC per file (`Gemini.md`).
- Zero arbitrary code execution.
- 100% typecheck (`tsc --noEmit`), Next.js 15 production build (`next build`), and client unit tests passing.
