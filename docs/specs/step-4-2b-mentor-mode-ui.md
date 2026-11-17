# 📋 Technical Specification: Step 4.2b — Next.js 15 Mentor Mode Teaching Visualizer & Interactive Code Remediation Panel

> **Step ID**: `step-4-2b`  
> **Milestone**: 4.2 (Mentor Mode — Teaching Content)  
> **Phase**: Phase 4 — Learning Loop & Weakness Tracking  
> **Git Feature Branch**: `feat/step-4-2b-mentor-mode-ui`  
> **Status**: Ready for Implementation  

---

## 1. Executive Summary & Objective

In **Step 4.2a**, we delivered the backend Mentor Engine, LiteLLM / deterministic fallback orchestrator, and REST endpoints (`POST /api/v1/mentor/explain` and `GET /api/v1/mentor/explanations/{weakness_id}`) with multi-tenant isolation and strict $\le 300$ LOC modularity.

In **Step 4.2b**, we deliver the Next.js 15 App Router interactive user experience for **Mentor Mode**:
1. **TypeScript Contracts** (`frontend/src/types/mentor.ts`): 1:1 typed schemas mirroring the backend contracts (`CodeRemediationSnippet`, `MentorExplanationRequest`, `MentorExplanationResponse`).
2. **Typed REST API Client** (`frontend/src/lib/mentorApi.ts`): Secure client handling Supabase JWT bearer authorization, request payload validation, runtime response narrowing, and `AbortSignal` cancellation.
3. **Interactive Code Remediation Viewer** (`frontend/src/components/domain/CodeRemediationViewer.tsx`): Before-and-After code viewer with Diff/Split vs Unified tabs, syntax-colored vulnerability (rose/red) and remediation (emerald/green) panes, file context pill, copy-to-clipboard actions, and architectural rationale notes.
4. **Mentor Explanation Card** (`frontend/src/components/domain/MentorExplanationCard.tsx`): Comprehensive pedagogical card displaying root cause failure modes, core design principles, mentor walkthrough, code remediations, key takeaways, and Socratic challenge questions.
5. **Reusable Slide-Over Drawer & Project Hub** (`frontend/src/components/domain/MentorDrawer.tsx` & `frontend/src/app/projects/[id]/mentor/page.tsx`): Drawer component for embedding into weakness cards and simulation post-mortems, plus a dedicated `/projects/[id]/mentor` interactive learning arena registered in `ProjectNavHeader.tsx`.
6. **Hermetic Test Suite** (`frontend/src/lib/__tests__/mentorApi.test.ts`): Node test runner validating runtime schema guards, network fallback, error handling, and parameter constraints.

---

## 2. Dependencies & Stack Invariants

- **Next.js 15 App Router** + **React 19** + **TypeScript** + **Tailwind CSS** + **lucide-react**.
- **No unsafe dependencies**: Pure CSS and accessible SVG indicators for visual state.
- **Strict $\le 300$ LOC limit**: Every file created or touched must strictly stay $\le 300$ LOC.
- **Zero Arbitrary Code Execution**: Ingested and remediated code snippets are treated strictly as read-only static text.

---

## 3. Security & Multi-Tenant Invariants

- **Multi-Tenant Protection**: All client requests carry Supabase `access_token` in `Authorization: Bearer <token>`.
- **Safe Rendering**: Zero `dangerouslySetInnerHTML`. Code blocks render within standard `<pre>` and `<code>` elements with text content escaping.
- **Input Sanitization**: Topic and language parameters are validated (`language` $\le 32$ chars, `topic` $\le 128$ chars).

---

## 4. Target Files & LOC Budgets

| File | Purpose | Budget Limit | Target LOC |
| :--- | :--- | :--- | :--- |
| `frontend/src/types/mentor.ts` | TypeScript Interfaces | $\le 300$ LOC | ~80 LOC |
| `frontend/src/lib/mentorApi.ts` | Typed REST API Client & Validators | $\le 300$ LOC | ~160 LOC |
| `frontend/src/components/domain/CodeRemediationViewer.tsx` | Before/After Code Viewer | $\le 300$ LOC | ~190 LOC |
| `frontend/src/components/domain/MentorExplanationCard.tsx` | Full Teaching Session Card | $\le 300$ LOC | ~240 LOC |
| `frontend/src/components/domain/MentorDrawer.tsx` | Slide-Over Teaching Drawer | $\le 300$ LOC | ~150 LOC |
| `frontend/src/app/projects/[id]/mentor/page.tsx` | Mentor Mode Page | $\le 300$ LOC | ~230 LOC |
| `frontend/src/components/domain/ProjectNavHeader.tsx` | Register "Mentor" Tab | $\le 300$ LOC | ~250 LOC |
| `frontend/src/lib/__tests__/mentorApi.test.ts` | Hermetic Client Tests | $\le 300$ LOC | ~140 LOC |

---

## 5. Verification & Acceptance Criteria

1. `npm run typecheck --prefix frontend` passes with 0 errors.
2. `node --test frontend/src/lib/__tests__/mentorApi.test.ts` passes 100%.
3. `npm run build --prefix frontend` builds cleanly without SSR or bundle warnings.
4. `python -m ruff check backend/app backend/tests` remains 100% clean.
5. All touched files strictly conform to the $\le 300$ LOC invariant.
