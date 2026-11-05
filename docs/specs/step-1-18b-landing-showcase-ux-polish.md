# 📄 Technical Specification: Landing Page Showcase & End-to-End UX Polish

> **Step ID**: `Step 1.18b`  
> **Target Module**: `frontend/src/...`  
> **Git Feature Branch**: `feat/step-1-18b-landing-showcase-ux-polish`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-11-05  

---

## 1. Executive Summary

Step 1.18b completes **Phase 1 (Core MVP)** by delivering a production-grade, highly engaging landing page showcase and end-to-end UX polish for RepoDefense. While previous milestones built the complete underlying technical defense stack—from shallow cloning, Tree-sitter AST symbol indexing, and pgvector embeddings to the interactive FSM interview engine, evidence inspector drawer, defense reports, and project overview dashboards—the initial landing page remains a basic prototype scaffold.

This milestone replaces the placeholder home screen with an interactive showcase of the 7-stage core loop (`Evidence → Claim → Defense → Stress Test → Evaluation → Mentor → Re-test`), featuring a simulated Principal Engineer defense exchange, architectural differentiators against generic LeetCode/AI chat tools, global navigation continuity across all 8 Next.js 15 App Router views, and a resilient production health indicator.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Step 1.14b` (Interactive Defense Session UI & Turn Exchange)
  - `Step 1.15` (Evidence Display Panel & Grounding Inspector)
  - `Step 1.16b` (Comprehensive Defense Report Page)
  - `Step 1.17b` (Project Overview Page & Tech Stack Visualizer)
  - `Step 1.18a` (GitHub Actions CI/CD Pipeline & Readiness Suite)
- **Blocked by**: None (All prior Phase 1 backend, frontend, and CI/CD milestones merged to main).
- **Tech Stack Invariant**:
  - Next.js 15 (App Router) + TypeScript + Tailwind CSS + Lucide Icons + shadcn/ui patterns.
  - Strictly no arbitrary external CDNs or heavy unapproved dependencies.
  - Strict compliance with `Gemini.md` architecture and file length limits ($\le 300$ LOC per file).

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Static analysis and simulation only; no user code execution on client or server.
- [x] **Safe External Navigation**: All outbound GitHub or documentation anchors enforce `rel="noreferrer"` and `target="_blank"`.
- [x] **Safe Client State**: Clean Supabase auth session subscriptions without token leakage in URL query parameters.
- [x] **Evidence-Grounded Persona Consistency**: The interactive showcase dialogue strictly reflects AST grounding, Principal Engineer tone calibration, and real architectural trade-offs.

---

## 4. 🧭 Specialized Skills Directive

This milestone activates and coordinates with the following specialized skills:

| Specialized Skill | Scope of Impact & Mandate | Verification Requirement |
| :--- | :--- | :--- |
| **[`doctor`](file:///d:/RepoDefense/.agents/skills/doctor/SKILL.md)** | Pre-flight and post-implementation health checks across Next.js 15 frontend build, TypeScript compile (`tsc --noEmit`), and backend health check compatibility. | Validates zero TypeScript errors and successful production export across all 8 Next.js 15 App Router routes. |
| **[`security_auditor`](file:///d:/RepoDefense/.agents/skills/security_auditor/SKILL.md)** | Audits client-side external links, untrusted string rendering, and Supabase auth token storage safety. | Verifies no `dangerouslySetInnerHTML`, safe external link rel tags, and zero secret leakage in client state. |
| **[`eval_persona`](file:///d:/RepoDefense/.agents/skills/eval_persona/SKILL.md)** | Audits showcase interview dialogue to ensure authentic Principal Engineer persona tone, XML isolation compliance, and grounded stress test scenarios. | Validates dialogue realism matching FSM state transitions and scoring rubric tiers. |

---

## 5. 🧠 Sequential Thinking Strategy

1. **Information Architecture & User Journey**:
   - *First-Time Visitor*: Lands on `/` → reads value proposition ("Prove that you understand...") → explores interactive defense scenario showcase → reads "Why RepoDefense vs LeetCode" → clicks "Start Defense" → `/signup` or `/dashboard`.
   - *Returning Authenticated Developer*: Lands on `/` → sees live session email and "Go to Dashboard" CTA → launches project defense in 1 click.
2. **Interactive Showcase State Modeling**:
   - Rather than static text, `DefenseShowcaseCard.tsx` should support step-through tabs or stage progression:
     - Stage 1: *Evidence Anchor* (`backend/app/ai/fsm.py:120-165` - State Machine)
     - Stage 2: *Interviewer Inquiry* ("Why a deterministic state machine instead of an autonomous multi-agent loop?")
     - Stage 3: *Candidate Defense* ("State machines eliminate context drift and non-deterministic UX...")
     - Stage 4: *Stress Test Constraint* ("What happens when Redis connection drops during state transition?")
     - Stage 5: *Principal Engineer Evaluation* (Score 9.4/10 — Certified Principal Defense)
3. **Component Modularity & LOC Guardrails**:
   - To strictly respect the 300 LOC limit, decompose the page into:
     - `page.tsx`: Layout composition, hero, core loop, feature grid, and CTAs (~220 LOC).
     - `DefenseShowcaseCard.tsx`: Interactive demo dialogue simulation with tabbed stage navigation (~220 LOC).
     - `SystemHealthBadge.tsx`: Resilient backend health probing with status pill and tooltip (~90 LOC).
     - `layout.tsx`: Global navigation header, mobile menu, and footer (~120 LOC).

---

## 6. Data Contracts & Interfaces

### 6.1 Showcase Dialogue Turn Contract

```typescript
export interface ShowcaseStep {
  id: "evidence" | "claim" | "defense" | "stress_test" | "evaluation";
  stepNumber: string;
  badgeLabel: string;
  badgeColor: string;
  speaker: "interviewer" | "candidate" | "system";
  headline: string;
  codeSnippet?: {
    file: string;
    lines: string;
    language: string;
    code: string;
  };
  content: string;
  annotation?: string;
}
```

### 6.2 System Health State Contract

```typescript
export interface SystemHealthState {
  status: "ok" | "probing" | "offline";
  app: string;
  version: string;
  timestamp?: string;
}
```

---

## 7. Target File Architecture

| Action | Path | Target LOC | Responsibilities |
| :--- | :--- | :--- | :--- |
| `[NEW]` | `frontend/src/components/domain/DefenseShowcaseCard.tsx` | ~220 LOC | Interactive tabbed showcase component demonstrating live defense dialogue, code evidence anchor, stress test, and rubric score. |
| `[NEW]` | `frontend/src/components/domain/SystemHealthBadge.tsx` | ~90 LOC | Modular production health pill probing `/api/health` with animated ping, version display, and graceful fallback. |
| `[MODIFY]` | `frontend/src/app/page.tsx` | ~230 LOC | Comprehensive landing page with hero, showcase integration, 7-stage core loop, differentiator table, tech stack badges, and CTAs. |
| `[MODIFY]` | `frontend/src/app/layout.tsx` | ~120 LOC | Global navigation header with active anchors, `SystemHealthBadge`, GitHub link, mobile responsiveness, and footer. |

---

## 8. Step-by-Step Implementation Sequence

### Phase A: Modular Components (`DefenseShowcaseCard` & `SystemHealthBadge`)
1. Create `frontend/src/components/domain/DefenseShowcaseCard.tsx`:
   - Define realistic RepoDefense architectural interview scenario grounded in `backend/app/ai/fsm.py`.
   - Implement interactive step selector (Evidence → Claim → Defense → Stress Test → Evaluation).
   - Render code snippet container with file badge and line ranges.
   - Render dialogue bubble with Principal Engineer avatar and evaluation badge.
2. Create `frontend/src/components/domain/SystemHealthBadge.tsx`:
   - Probe `/api/health` using `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`.
   - Handle loading, online, and offline states cleanly with colored indicators.

### Phase B: Global Navigation & Layout Polish (`layout.tsx`)
1. Update `frontend/src/app/layout.tsx`:
   - Add navigation links: "Showcase", "Core Loop", "Differentiators", "GitHub".
   - Embed `SystemHealthBadge` in the header nav.
   - Add polished footer with tech stack credits (FastAPI, Next.js 15, PostgreSQL 17 + pgvector, Tree-sitter), repository link, and Phase 1 MVP status badge.

### Phase C: Comprehensive Landing Page Composition (`page.tsx`)
1. Overhaul `frontend/src/app/page.tsx`:
   - Hero section with taglines from `Gemini.md`: *"Prove that you understand — and can defend — the software you built."*
   - Dynamic CTA based on auth state (Redirect to `/dashboard` if logged in, `/signup` if guest).
   - Embed `DefenseShowcaseCard` in `#showcase` section.
   - Render 7-stage core loop grid with distinct Lucide icons and stage gradients.
   - Add "Why RepoDefense" comparison matrix (RepoDefense vs LeetCode vs Generic AI Chatbots).
   - Tech stack grid with canonical technologies.
   - Bottom CTA section driving project creation.

### Phase D: Verification & Quality Assurance
1. Run `npx tsc --noEmit` across `frontend/`.
2. Run `npm run build` in `frontend/` to verify production compilation across all 8 routes.
3. Verify file line counts ($\le 300$ LOC limit).
4. Run `pytest backend/tests/test_health.py` to confirm backend health probe compatibility.

---

## 9. Verification & Acceptance Criteria

### Automated Verification Commands
```bash
# 1. Frontend TypeScript typecheck
cd frontend && npx tsc --noEmit

# 2. Frontend Next.js production build
cd frontend && npm run build

# 3. Frontend lint check
cd frontend && npm run lint

# 4. Backend health test check
pytest backend/tests/test_health.py -v
```

### Acceptance Checklist
- [ ] `page.tsx`, `DefenseShowcaseCard.tsx`, `SystemHealthBadge.tsx`, and `layout.tsx` are all $\le 300$ lines.
- [ ] Interactive showcase allows stepping through Evidence, Claim, Defense, Stress Test, and Evaluation.
- [ ] System health badge accurately displays backend status or graceful fallback.
- [ ] Navigation anchors (`#showcase`, `#core-loop`, `#differentiators`) work smoothly.
- [ ] Next.js 15 production build (`npm run build`) completes with 0 errors across all 8 App Router routes.
- [ ] Zero arbitrary code execution or ungrounded claims.
