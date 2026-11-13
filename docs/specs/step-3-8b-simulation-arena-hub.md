# 📄 Technical Specification: Step 3.8b — Frontend Simulation Arena Hub, Grouped Navigation & Phase 3 UX Polish

> **Step ID**: `Step 3.8b`  
> **Milestone**: `Milestone 3.8: Phase 3 Polish & Deploy`  
> **Target Module**: `frontend/src/components/domain/SimulationArenaGrid.tsx`, `frontend/src/components/domain/ProjectNavHeader.tsx`, `frontend/src/app/projects/[id]/page.tsx`, `frontend/src/components/domain/__tests__/SimulationArenaGrid.test.ts`  
> **Git Feature Branch**: `feat/step-3-8b-simulation-arena-hub`  
> **Status**: 📋 Ready for Implementation  
> **Created**: 2026-11-13  

---

## 1. Executive Summary

Throughout Phase 1, Phase 2, and Phase 3, RepoDefense developed 6 distinct architectural defense simulation engines:
1. **Core Oral Defense** (`/interview/[id]`): Evidence-grounded architectural defense with adaptive follow-ups and AI pushback.
2. **Pull Request Defense** (`/projects/[id]/pr-defense`): Diff-scoped interrogation focusing on why lines were changed in a PR.
3. **Git Commit Defense** (`/projects/[id]/commit-defense`): Single-commit SHA interrogation validating atomic intent and blast radius.
4. **Incident War Room** (`/projects/[id]/incident-simulation`): Production chaos simulation with triage, mitigation & postmortem.
5. **Stress Test & Scaling** (`/projects/[id]/stress-test`): High-concurrency 10x–100x traffic scaling and bottleneck defense.
6. **Architecture Defense** (`/projects/[id]/arch-defense`): Diagram-linked interrogation challenging system topology and module tradeoffs.
7. **Cross-Mode Performance Analytics** (`/projects/[id]/analytics`): Candidate readiness scores, skill confidence radar & chronological trends.

Currently, on the Project Overview page (`/projects/[id]`), there is no centralized Simulation Arena launcher showcasing these engines or guiding candidates on where to start. Furthermore, in `ProjectNavHeader.tsx`, all 12 tabs are displayed in a single flat row, which causes awkward horizontal overflow and wrapping on standard desktop viewports.

**Step 3.8b** delivers the final frontend polish for Phase 3:
- Authors `SimulationArenaGrid.tsx`, an interactive launcher on `/projects/[id]` showcasing all 6 simulation modes plus Analytics with descriptions, focus areas, difficulty/category badges, and direct launch triggers.
- Reorganizes `ProjectNavHeader.tsx` into clean, organized navigation groups (Code Analysis vs Defense Arena vs Analytics) or compact tab layout preventing viewport overflow.
- Integrates the Simulation Arena directly into the Project Overview page (`/projects/[id]/page.tsx`).
- Authors hermetic component tests and verifies full-route compilation via Next.js 15 production build (`npm run build`).
- Concludes **Phase 3: Advanced Defense**!

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Step 3.8a`: Backend Cross-Simulation Session Store Hardening & Readiness API (Merged in PR #68)
  - `Step 3.7b`: Next.js 15 Enhanced Analytics & Visualizations UI
  - `Step 3.6b`: Next.js 15 Architecture Defense UI
  - `Step 3.5b`: Next.js 15 Stress Test UI
  - `Step 3.4b`: Next.js 15 Incident Simulation War Room UI
- **Blocked by**: None.
- **Tech Stack Invariants**:
  - Next.js 15 App Router + TypeScript + Tailwind CSS + Lucide React
  - Zero external UI libraries added
  - Strict $\le 300$ LOC limit per file (Gemini.md invariant)

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Pure presentation components and Next.js client routing; no arbitrary code execution.
- [x] **Strict Input Validation**: Project ID sanitized in URL links; no `dangerouslySetInnerHTML`.
- [x] **Accessible UI**: Semantic HTML (`<nav>`, `<section>`, `<article>`), keyboard navigable launch triggers, and `aria-label` attributes.
- [x] **File Length Gate**: All modified and new files strictly $\le 300$ LOC.

---

## 4. 🩺 Specialized Domain Skill Advisory

### `doctor` Pre-Flight & Production Build Directive
- Verify Next.js 15 build passes cleanly (`npm run build`) with all 19 App Router routes compiling without prerendering errors.
- Ensure TypeScript typecheck (`npm run typecheck`) reports 0 errors.

---

## 5. Component Contracts & Interfaces

### 5.1 Simulation Mode Definition Contract (`frontend/src/components/domain/SimulationArenaGrid.tsx`)

```typescript
export interface SimulationModeCard {
  id: string;
  title: string;
  category: "core" | "git" | "chaos" | "scale" | "arch" | "telemetry";
  badgeText: string;
  badgeColor: string;
  focusArea: string;
  description: string;
  hrefTemplate: (projectId: string) => string;
  Icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
  recommendedRole: string;
}
```

---

## 6. Target Files & LOC Budget

| File | Status | Target LOC | Role |
| :--- | :--- | :--- | :--- |
| `frontend/src/components/domain/SimulationArenaGrid.tsx` | `[NEW]` | ~180 LOC | Interactive Simulation Arena launcher card grid for all 6 defense modes + Analytics. |
| `frontend/src/components/domain/ProjectNavHeader.tsx` | `[MODIFY]` | ~230 LOC | Reorganize 12 tabs with responsive category grouping and clean layout. |
| `frontend/src/app/projects/[id]/page.tsx` | `[MODIFY]` | ~240 LOC | Embed SimulationArenaGrid component into Project Overview page. |
| `frontend/src/components/domain/__tests__/SimulationArenaGrid.test.ts` | `[NEW]` | ~120 LOC | Hermetic contract and route generation tests for all simulation modes. |

*Total files*: 4 files ($\le 4$ target file limit).  
*Max file size*: $\le 240$ LOC (strictly within 300 LOC limit).

---

## 7. Step-by-Step Implementation Sequence

1. **Phase A: Simulation Arena Grid Component (`SimulationArenaGrid.tsx`)**
   - Define catalog of 6 defense simulation engines + Analytics with icons, badges, descriptions, and route builders.
   - Author responsive grid layout (1 col mobile, 2 col tablet, 3 col desktop).
   - Add "Launch Simulation" primary action buttons and "Learn More" tooltips.

2. **Phase B: Responsive Nav Header Organization (`ProjectNavHeader.tsx`)**
   - Group tabs into 3 categories:
     - **Analysis** (Overview, Claims, Coverage, Ownership, Architecture, Tech Audit)
     - **Defense Arena** (Oral Defense, PR Defense, Commit Defense, War Room, Stress Test, Arch Defense)
     - **Insights** (Analytics)
   - Ensure active tab category is prominently highlighted with horizontal scrolling or responsive pill indicators.

3. **Phase C: Integrate into Project Overview (`projects/[id]/page.tsx`)**
   - Add `<SimulationArenaGrid projectId={overview.project_id} />` to the overview page.
   - Verify layout spacing and visual hierarchy.

4. **Phase D: Tests & Production Build Verification**
   - Author `frontend/src/components/domain/__tests__/SimulationArenaGrid.test.ts`.
   - Run `npm run typecheck --prefix frontend` (0 errors).
   - Run `npm run build --prefix frontend` (clean compilation across all App Router routes).

---

## 8. Verification & Acceptance Criteria

### Automated Tests
```bash
cd frontend && npm run typecheck && npm run build
node --test src/components/domain/__tests__/SimulationArenaGrid.test.ts
```

### Acceptance Checklist
- [ ] `SimulationArenaGrid` showcases all 6 simulation modes plus Analytics with working links.
- [ ] `ProjectNavHeader` renders cleanly without viewport overflow across standard desktop screen widths.
- [ ] `/projects/[id]` displays the Simulation Arena hub prominently.
- [ ] `npm run typecheck` passes with 0 errors.
- [ ] `npm run build` succeeds cleanly across all 19 routes.
- [ ] All files strictly $\le 300$ LOC.
