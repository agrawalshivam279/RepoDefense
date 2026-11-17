# Feature Spec: Step 4.3b — Next.js 15 Mini Challenge Interactive Sandbox & Solution Evaluation UI

## 1. Context & Objectives
- **Phase**: Phase 4 — Learning Loop & Weakness Tracking
- **Milestone**: Milestone 4.3 — Mentor Mode: Mini Challenges
- **Step**: Step 4.3b (Frontend Implementation)
- **Goal**: Build the Next.js 15 App Router interactive mini-challenge workspace and solution evaluation interface. Candidates can load targeted challenges (optionally grounded in recorded weaknesses or chosen topics), inspect flawed starter code, formulate solutions in an accessible code editor, submit them to the backend evaluation engine (`POST /api/v1/mentor/challenges/evaluate`), and receive comprehensive architectural grading, strengths, missing elements, critique, and canonical model reference solutions.

---

## 2. Core Invariants & Architecture Compliance
- **Strict LOC Limit**: All files must strictly maintain $\le 300$ LOC.
- **No Arbitrary Code Execution**: All evaluations are static analysis and LiteLLM prompt reasoning; no code execution runs in the browser or server.
- **Authentication**: All API calls use Supabase Auth Bearer JWT tokens.
- **Multi-Tenant Isolation**: Weakness IDs and challenges are scoped to authenticated users.
- **Accessible & Responsive UX**: Tailwind CSS dark-mode theme, keyboard accessible, loading states, and error retries.

---

## 3. Deliverables & Component Layout

### A. Data Contracts (`frontend/src/types/challenge.ts`)
- TypeScript interfaces matching backend Pydantic models:
  - `MiniChallengeDifficulty`: `"foundational" | "intermediate" | "advanced"`
  - `MiniChallengeResponse`: `challenge_id`, `category`, `topic`, `difficulty`, `title`, `scenario`, `starter_code`, `language`, `requirements`, `hints`, `generated_at`
  - `GenerateChallengeRequest`: `weakness_id`, `topic`, `category`, `difficulty`, `language`, `code_context`
  - `SubmitChallengeSolutionRequest`: `challenge_id`, `weakness_id`, `category`, `topic`, `scenario`, `requirements`, `candidate_solution`, `language`
  - `ChallengeEvaluationResponse`: `evaluation_id`, `challenge_id`, `passed`, `score`, `strengths`, `missing_elements`, `critique`, `model_solution`, `weakness_updated`, `evaluated_at`

### B. Typed REST API Client (`frontend/src/lib/challengeApi.ts`)
- `generateMiniChallenge(token, req)`: calls `POST /api/v1/mentor/challenges/generate`
- `fetchWeaknessChallenge(token, weaknessId)`: calls `GET /api/v1/mentor/challenges/weakness/{id}`
- `submitChallengeSolution(token, req)`: calls `POST /api/v1/mentor/challenges/evaluate`
- Runtime response validators and error message extractions.

### C. Domain Components
- `MiniChallengeCard.tsx`: Displays challenge title, difficulty badge, problem scenario, criteria checklist with check toggles, and progressive Socratic hints accordion.
- `ChallengeEditor.tsx`: Starter code editor with line numbers, code reset, character/line count, submit action, and loading spinner.
- `SolutionEvaluationViewer.tsx`: Evaluation scorecard with score gauge, pass/fail status, strengths list, missing requirements, mentor critique, and toggleable canonical model solution.
- `MentorChallengeSandbox.tsx`: Orchestrates active challenge state, generation forms, solution submission, evaluation results, and weakness resolution notifications.

### D. Page Integration (`frontend/src/app/projects/[id]/mentor/page.tsx`)
- Tabbed switcher between:
  1. `Remediation Guide`: Root cause analysis and before/after code diffs.
  2. `Challenge Sandbox`: Interactive mini-challenge editor and grading engine.

---

## 4. Verification Checklist
- `npm run typecheck --prefix frontend` clean (0 errors)
- `npm run build --prefix frontend` clean (all routes compiled)
- `npx tsx --test frontend/src/lib/__tests__/challengeApi.test.ts` (100% passing)
- Line count verified $\le 300$ LOC across all new and touched files.
