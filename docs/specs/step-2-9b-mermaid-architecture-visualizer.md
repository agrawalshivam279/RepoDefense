# 📄 Technical Specification: Step 2.9b — Next.js 15 Mermaid Architecture Visualizer & Interactive Diagram Viewer

> **Step ID**: `Step 2.9b`  
> **Target Module**: `frontend/src/...`  
> **Git Feature Branch**: `feat/step-2-9b-mermaid-architecture-visualizer`  
> **Status**: 📋 In Progress / Code Synthesis  
> **Created**: 2026-11-07  

---

## 1. Executive Summary

Step 2.9b completes **Milestone 2.9 (Architecture Diagram Generation)** under Phase 2 (Differentiation). In Step 2.9a, the backend diagram generation engine, tier classifier, and authenticated endpoint (`GET /api/v1/projects/{project_id}/diagram`) were built and verified.

This milestone delivers the interactive client-side Next.js 15 App Router visualizer:
1. **TypeScript Data Contracts (`frontend/src/types/diagram.ts`)**: Mirroring backend Pydantic models (`DiagramType`, `DiagramNode`, `DiagramEdge`, `DiagramResponse`).
2. **API Client (`frontend/src/lib/diagramApi.ts`)**: Authenticated endpoint caller for `GET /api/v1/projects/{id}/diagram` with Supabase JWT bearer token.
3. **Interactive Mermaid Component (`MermaidViewer.tsx`)**:
   - Safe client-side SVG rendering using `mermaid.render()` with `securityLevel: 'strict'`.
   - Dark mode styling calibrated for RepoDefense design palette.
   - Zoom controls (+ / - / Reset).
   - Fullscreen expansion modal for exploring complex multi-tier architectures.
   - Copy Raw Mermaid Code CTA.
   - Synthesis origin indicator ("AI Principal Engineer Synthesis" vs "Deterministic Multi-Tier Fallback").
4. **Architecture Page Integration (`/projects/[id]/architecture/page.tsx`)**: Seamlessly embedded alongside the existing Architecture Report Card and Pattern Indicators.

---

## 2. Dependencies & Invariants

- **Depends on**:
  - `Step 2.9a`: Backend Diagram API (`GET /api/v1/projects/{project_id}/diagram`).
  - `mermaid`: ^11.x client library for SVG flowchart rendering.
- **Invariants**:
  - **Zero Code Execution**: Diagram rendering executed in strict sandbox (`securityLevel: 'strict'`).
  - **300 LOC Gate**: All created or modified files strictly $\le 300$ lines.
  - **SSR Safety**: Mermaid rendering isolated to client-side lifecycle (`useEffect` / dynamic client execution).

---

## 3. Specialized Skills Directive

| Skill | Directive & Verification Requirement |
| :--- | :--- |
| **`security_auditor`** | Enforces `securityLevel: 'strict'` in Mermaid configuration to prevent arbitrary DOM or script execution from diagram labels. |
| **`code_reviewer`** | Enforces strictly $\le 300$ LOC per file, proper React 19 hook cleanup, and dark theme consistency with Tailwind CSS. |
| **`doctor`** | Pre-flight and post-implementation Next.js build verification (`npm run build`). |

---

## 4. Target Files & LOC Budget

1. `frontend/src/types/diagram.ts`: ~40 LOC
2. `frontend/src/lib/diagramApi.ts`: ~45 LOC
3. `frontend/src/components/domain/MermaidViewer.tsx`: ~180 LOC
4. `frontend/src/app/projects/[id]/architecture/page.tsx`: ~280 LOC
