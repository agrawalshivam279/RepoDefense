# 📄 Technical Specification: Next.js 15 Frontend Scaffolding & Landing Page

> **Step ID**: `1.1c`  
> **Target Module**: `frontend/`  
> **Git Feature Branch**: `feat/step-1-1c-frontend-scaffold`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-10-26  

---

## 1. Executive Summary

This specification provisions the frontend application for **RepoDefense** using Next.js 15 (App Router), React 19, TypeScript, and Tailwind CSS. It establishes the client configuration, root layout with dark-mode typography, and an interactive landing page showcasing the product identity ("Prove that you understand — and can defend — the software you built"), the 7-stage state machine loop (Evidence → Claim → Defense → Stress Test → Evaluation → Mentor → Re-test), and a live backend connectivity indicator probing `/api/health`.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - Step 1.1a (FastAPI `/api/health` endpoint and CORS origins).
  - Step 1.1b (Container configuration and environment template).
- **Blocked by**: None.
- **Tech Stack Invariant**:
  - Next.js 15 (App Router).
  - React 19 / TypeScript 5+.
  - Tailwind CSS + Lucide React.
  - Adheres strictly to [Gemini.md](file:///d:/RepoDefense/Gemini.md) without introducing alternative UI frameworks or micro-frontends.

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Client-side static rendering and fetch only; no arbitrary script evaluation.
- [x] **XSS Defense**: Safe React JSX standard rendering with no unescaped HTML injections.
- [x] **Strict Type Checking**: TypeScript strict mode enabled in `tsconfig.json`.
- [x] **File Length Limit**: Every target file strictly maintains $\le 300$ LOC.

---

## 4. 🧠 Sequential Thinking Strategy

- **Complexity Evaluation**: Standard Next.js 15 App Router scaffolding and Tailwind UI layout. Sequential Thinking MCP is **Skipped** for this step as no AST traversals or complex state transitions are required.

---

## 5. Data Contracts & Interfaces

### 5.1 Backend Health Contract (`frontend/src/types/api.ts`)

```typescript
export interface HealthStatus {
  status: string;
  app: string;
  version: string;
  timestamp: string;
}
```

---

## 6. Step-by-Step Implementation Sequence

### Phase A: Next.js 15 Project Configuration
1. **Author `frontend/package.json`**:
   - Next.js 15, React 19, Lucide React, Tailwind CSS, TypeScript.
   - Scripts: `dev`, `build`, `start`, `lint`.
2. **Author `frontend/tsconfig.json`**:
   - Path aliases (`@/*` -> `./src/*`).
3. **Author `frontend/next.config.mjs`**, `frontend/tailwind.config.ts`, `frontend/postcss.config.mjs`.

### Phase B: Design System & Root Layout
4. **Author `frontend/src/app/globals.css`**:
   - Modern dark-first color tokens and typography.
5. **Author `frontend/src/lib/utils.ts`**:
   - Utility class merging function (`cn`).
6. **Author `frontend/src/app/layout.tsx`**:
   - Metadata (`title: "RepoDefense | Architectural Stress-Testing for Codebases"`).
   - Global dark-mode wrapper and navigation header.

### Phase C: Landing Page UI
7. **Author `frontend/src/app/page.tsx`**:
   - Hero section with badge and value proposition.
   - 7-Stage Core Loop interactive feature cards.
   - Live backend health indicator probing `${NEXT_PUBLIC_API_URL:-http://localhost:8000}/api/health`.
   - Call to action buttons ("Start Defense", "Explore Architecture").

### Phase D: Automated Verification
8. **Execute Type Check & Build Validation**:
   - Run `npm run build` or `npx tsc --noEmit` in `frontend/`.

---

## 7. Verification & Acceptance Criteria

### Automated Tests & Checks
```bash
cd frontend && npm install && npx tsc --noEmit && npm run build
```

### Acceptance Checklist
- [ ] Next.js 15 application builds cleanly with 0 TypeScript errors.
- [ ] Landing page renders product title, tagline, and 7-stage architectural loop.
- [ ] Backend health indicator gracefully probes `/api/health` with fallback handling.
- [ ] All files strictly $\le 300$ LOC.
