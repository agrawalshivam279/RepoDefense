# Technical Specification: Step 4.5b — Next.js 15 Targeted Re-Test Workspace & Interactive Evaluation UI

## 1. Context & Objective
In Step 4.5a, we built and deployed the backend targeted re-testing engine (`/api/v1/retest`) which synthesizes production scenarios targeting a candidate's past architectural weaknesses and automatically resolves weaknesses and boosts skill proficiencies upon passing.
Step 4.5b completes Milestone 4.5 by providing an interactive Next.js 15 App Router workspace where candidates can:
1. Review their active, unresolved weaknesses with severity indicators.
2. Select specific weaknesses to initiate a targeted re-test session.
3. Defend their system design decisions against realistic architectural constraints.
4. Receive immediate, grounded grading, rubric feedback, and verify their weakness resolution in real time.

## 2. Technical Stack & Invariants
- **Frontend**: Next.js 15 (App Router) + React 19 + TypeScript (Strict Mode) + Tailwind CSS + shadcn/ui.
- **Backend API**: FastAPI at `/api/v1/retest` (`/weaknesses`, `/session`, `/evaluate`).
- **Safety Invariants**:
  - Zero arbitrary code execution (100% static analysis and prompt grounding).
  - Multi-tenant IDOR isolation using Supabase Auth JWT.
  - Strict `<= 300 LOC` limit per file.
  - Graceful loading states, error boundaries, and empty state fallbacks.

## 3. Component Architecture & File Layout
1. `frontend/src/types/retest.ts`:
   - Data contracts for eligible weaknesses, sessions, questions, submissions, and evaluation results.
   - Helper badge styling functions for severity and category.
2. `frontend/src/lib/retestApi.ts`:
   - Typed client for `/api/v1/retest` endpoints with error normalization and parameter serialization.
3. `frontend/src/components/domain/RetestWeaknessSelector.tsx`:
   - Multi-select weakness catalog with category filtering, severity indicators, and session launch action.
4. `frontend/src/components/domain/RetestSessionCard.tsx`:
   - Active question presentation with architectural constraints banner and collapsible rubric.
5. `frontend/src/components/domain/RetestDefenseEditor.tsx`:
   - Defense text input with word counter, minimum guidance hint, and submission loading states.
6. `frontend/src/components/domain/RetestEvaluationModal.tsx`:
   - Post-turn grading card with score meter, pass/fail status, skill proficiency delta, and improvement tags.
7. `frontend/src/app/projects/[id]/retest/page.tsx`:
   - Complete re-test workspace page connecting navigation, state machine, and multi-turn flow.
8. `frontend/src/components/domain/ProjectNavHeader.tsx`:
   - Register "Targeted Re-Test" navigation button.

## 4. Verification Acceptance Criteria
- `npm run typecheck` passes with 0 errors.
- `npm run build` succeeds generating static route for `/projects/[id]/retest`.
- All files $\le 300$ LOC.
