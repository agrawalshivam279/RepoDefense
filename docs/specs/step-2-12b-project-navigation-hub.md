# 📄 Technical Specification: Frontend Project Navigation Hub, Breadcrumbs & Phase 2 UI Polish

> **Step ID**: `Step 2.12b`  
> **Target Module**: `frontend/src/components/domain/ProjectNavHeader.tsx` & `frontend/src/app/projects/[id]/...`  
> **Git Feature Branch**: `feat/step-2-12b-project-navigation-hub`  
> **Status**: 📋 Ready for Implementation  
> **Created**: 2026-11-08  

---

## 1. Executive Summary

Step 2.12b introduces a centralized, cohesive project navigation experience for RepoDefense across all Phase 2 analytical tools. Currently, each project sub-page (`/projects/[id]`, `/claims`, `/coverage`, `/ownership`, `/architecture`, `/tech-audit`) implements ad-hoc, disjointed header bars and incomplete navigation links, leading to UI inconsistency and risk of breaching the strict 300 LOC file limit. This milestone creates a modular `ProjectNavHeader.tsx` component that provides standardized hierarchical breadcrumbs, repository metadata displays, unified 6-tab navigation (Overview, Claims, Coverage, Ownership, Architecture, Tech Audit) with active state indicators, refresh state management, and the primary "Start Defense" call-to-action. In this step, we author the navigation component and integrate it into the Project Overview, Claims Grounding Inspector, and Architecture Audit pages.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Step 1.17b`: Project Overview UI (`frontend/src/app/projects/[id]/page.tsx`)
  - `Step 2.3`: Claim Verification UI (`frontend/src/app/projects/[id]/claims/page.tsx`)
  - `Step 2.9b`: Architecture & Mermaid Visualizer (`frontend/src/app/projects/[id]/architecture/page.tsx`)
  - `Step 2.12a`: Backend composite database indexes optimizing Phase 2 workloads
- **Tech Stack Invariant**:
  - Next.js 15 App Router
  - TypeScript
  - Tailwind CSS + Lucide React
  - Zero external state library additions (standard React props & state)
  - Strict $\le 300$ LOC per file limit

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Pure frontend client component and presentation logic; no arbitrary code evaluation.
- [x] **Client-Side Sanitization**: Relative URL generation with strictly typed project IDs and verified routing targets.
- [x] **Accessible Breadcrumbs & Navigation**: Standard HTML `<nav>` semantic tags and `aria-label="Breadcrumb"` for accessibility.
- [x] **File Length Gate**: All modified files and the new component strictly $\le 300$ LOC.

---

## 4. 🧠 Sequential Thinking Strategy

- **Complexity**: Low-to-Moderate UI coordination. Sequential Thinking MCP is skipped as data flow is straightforward React props and Next.js `Link` routing.
- **Edge Cases & Error Fallbacks**:
  - Missing project name gracefully falls back to `"Project"`.
  - Missing `githubUrl` omits the external repository link without throwing undefined errors.
  - Optional `onRefresh` prop displays the refresh button only when a fetch callback is supplied.
  - Active tab styling uses high-contrast text and border highlight to clearly orient the user within the deep Phase 2 suite.

---

## 5. Data Contracts & Interfaces

### 5.1 ProjectNavHeader Props (`frontend/src/components/domain/ProjectNavHeader.tsx`)

```typescript
export type ProjectNavTab =
  | "overview"
  | "claims"
  | "coverage"
  | "ownership"
  | "architecture"
  | "tech-audit";

export interface ProjectNavHeaderProps {
  projectId: string;
  projectName?: string;
  githubUrl?: string;
  defaultBranch?: string;
  commitHash?: string;
  activeTab: ProjectNavTab;
  statusBadge?: string;
  subtitle?: string;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  rightSlot?: React.ReactNode;
}
```

---

## 6. Step-by-Step Implementation Sequence

1. **Phase A: Modular Navigation Component**
   - Author `frontend/src/components/domain/ProjectNavHeader.tsx` (~150 LOC) with:
     - Breadcrumb trail (`Dashboard > Projects > {projectName} > {Tab Label}`).
     - Top metadata bar (Back button, Project title, Status badge, GitHub link, Branch/Commit info, Subtitle).
     - Global action buttons (Custom `rightSlot`, optional `RefreshCw` button, and "Start Defense" CTA).
     - Unified navigation tabs row with 6 styled tabs (Overview, Claims, Coverage, Ownership, Architecture, Tech Audit).

2. **Phase B: Integrate into Overview Page**
   - Refactor `frontend/src/app/projects/[id]/page.tsx` to replace the inline header with `<ProjectNavHeader activeTab="overview" ... />`.
   - Verify LOC reduction and clean data propagation.

3. **Phase C: Integrate into Claims Page**
   - Refactor `frontend/src/app/projects/[id]/claims/page.tsx` to replace the inline header with `<ProjectNavHeader activeTab="claims" ... />`.
   - Verify LOC reduction and consistent layout.

4. **Phase D: Integrate into Architecture Page**
   - Refactor `frontend/src/app/projects/[id]/architecture/page.tsx` to replace the inline header with `<ProjectNavHeader activeTab="architecture" ... />`.
   - Verify LOC reduction and consistent layout.

---

## 7. Verification & Acceptance Criteria

### Automated Verification
```bash
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```

### Acceptance Checklist
- [ ] `ProjectNavHeader.tsx` renders all 6 Phase 2 tabs with correct icons, colors, and active highlight.
- [ ] Breadcrumbs correctly link back to `/dashboard` and `/projects/${projectId}`.
- [ ] "Start Defense" button properly navigates to `/interview/${projectId}`.
- [ ] All 4 touched files are strictly $\le 300$ LOC.
- [ ] `npx tsc --noEmit` reports 0 type errors.
- [ ] `npm run lint` passes with 0 lint errors.
- [ ] `npm run build` generates production bundles across all routes cleanly.

---

## 8. 🩺 Specialized Domain Skills Directive

- **Applicable Skill**: `None (pure UI / Next.js 15 navigation glue)`
- **Invariants Enforced**:
  - File length gate: strictly $\le 300$ LOC.
  - Zero external dependencies introduced.
  - Responsive layout for tablet and mobile viewport widths.
