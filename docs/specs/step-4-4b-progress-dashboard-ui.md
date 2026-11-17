# Specification: Step 4.4b — Next.js 15 Progress Dashboard UI & Interactive Learning Timeline Visualizer

## 1. Overview
Step 4.4b builds the candidate-facing Progress & Skill Improvement Dashboard in Next.js 15 App Router. It consumes the telemetry and aggregation REST endpoints delivered in Step 4.4a (`/api/v1/progress/overview`, `/timeline`, `/categories`) and renders an interactive learning timeline, weakness remediation velocity metrics, category mastery scorecards, and focused topic recommendations with one-click navigation to targeted re-testing.

## 2. Architecture & Invariants
- **Framework**: Next.js 15 (App Router, Client & Server Component separation) + TypeScript + Tailwind CSS.
- **File Length Limit**: Strictly $\le 300$ LOC per file (`Gemini.md`).
- **Zero Execution Security**: Read-only display of candidate skill history and telemetry data.
- **Design System**: Dark-themed, principal-engineer telemetry styling with clean SVG-based data visualization, responsive layouts, and accessible ARIA attributes.

## 3. Component Architecture
1. **Types (`frontend/src/types/progress.ts`)**:
   - `ProficiencyTrendPoint`, `WeaknessVelocityMetric`, `CategoryProgressDelta`, `TopicMasteryItem`, `UserProgressOverviewResponse`.
2. **API Client (`frontend/src/lib/progressApi.ts`)**:
   - `fetchProgressOverview()`, `fetchProgressTimeline(days?: number)`, `fetchProgressCategories()`.
3. **Domain Components (`frontend/src/components/domain/`)**:
   - `LearningTimelineChart.tsx`: Interactive SVG timeline curve with date filters (7d, 14d, 30d, all), hover tooltips, and evaluations count indicators.
   - `WeaknessVelocityCard.tsx`: Visual breakdown of resolution rates, severity resolution breakdown (critical, major, minor), and average remediation turnaround hours.
   - `CategoryMasteryGrid.tsx`: Progress cards for each technical category (security, architecture, scalability, concurrency, etc.) displaying proficiency progress bars, pass rates, and mastery status badges (`mastered`, `proficient`, `improving`, `needs_focus`).
   - `FocusTopicsPanel.tsx`: Side-by-side list comparing top improved topics and areas needing focus.
4. **App Page (`frontend/src/app/dashboard/progress/page.tsx`)**:
   - Full page view linking overview metrics, timeline chart, velocity analytics, and mastery grid.
   - Includes navigation header back to `/dashboard`.

## 4. Testing & Verification Plan
- Unit tests for `progressApi.ts` with mocked `fetch`.
- Component tests for `LearningTimelineChart`, `WeaknessVelocityCard`, and `CategoryMasteryGrid`.
- Lint & Typecheck: `tsc --noEmit` and `npm test`.
