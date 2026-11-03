# 📄 Technical Specification: Milestone 1.15 — Evidence Display Panel & Grounding Inspector

> **Milestone ID**: `1.15`  
> **Target Module**: `backend/app/api/v1/projects.py`, `frontend/src/types/evidence.ts`, `frontend/src/lib/defenseApi.ts`, `frontend/src/components/domain/EvidencePanel.tsx`, `frontend/src/app/interview/[id]/page.tsx`  
> **Git Feature Branch**: `feat/milestone-1-15-evidence-display`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-11-04  

---

## 1. Executive Summary

Per **Gemini.md** (Sections 2, 4, 5, 9) and **implementation_plan.md** (Milestone 1.15):
The primary differentiator of RepoDefense is strict grounding: every question posed by the Principal Engineer AI is mathematically anchored in actual codebase artifacts. To make this tangible and uncheatable for candidates, **Milestone 1.15** introduces the **Evidence Display Panel**.

When defending their architecture:
1. Candidates can toggle an interactive side drawer/panel displaying all load-bearing architectural evidence extracted from the repository snapshot.
2. The panel dynamically highlights the specific evidence items cited by the **active question** (`cited_evidence_ids`), displaying file paths, exact line intervals (`lines 15-40`), and categorized evidence badges (`Framework`, `Database`, `Auth`, `Endpoint`, `Queue`, `Infrastructure`).
3. Candidates can filter evidence by category or view only question-cited anchors, ensuring complete transparency into *why* a question is being asked.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - Milestone 1.11 (Architectural Evidence Extractor & `Evidence` database model)
  - Milestone 1.13 (Evidence-Grounded Question Generation Engine)
  - Milestone 1.14 (Interactive Defense Session FSM & Next.js 15 UI)
- **Blocked by**: None.
- **Tech Stack Invariant**:
  - FastAPI backend with async SQLAlchemy 2.0 and Pydantic v2.
  - Next.js 15 App Router + Tailwind CSS + Lucide React.
  - Strictly $\le 300$ LOC per file across all new and modified modules.

---

## 3. 🛡️ Invariants & Security Impact

- [x] **Zero Code Execution**: Evidence display is strictly static metadata and line boundaries; no files are compiled or executed.
- [x] **Multi-Tenant Isolation**: The `GET /api/v1/projects/{project_id}/evidence` endpoint enforces tenancy verification (`Project.user_id == current_user.id`).
- [x] **Safe Path Representation**: File paths are repository-relative normalized strings; client avoids arbitrary filesystem resolution.
- [x] **300 LOC Invariant**: Component logic is cleanly decoupled: API endpoint in `projects.py` ($\le 160$ LOC), types in `evidence.ts` ($\le 60$ LOC), drawer component in `EvidencePanel.tsx` ($\le 200$ LOC).

---

## 3.5. 🩺 Specialized Domain Skill Directives

Per `.agents/skills/plan_step/SKILL.md` (v2.1):
The following specialized skills are assigned to Milestone 1.15 and will be audited during `/verify_step`:
1. **`security_auditor`**:
   - Audit tenant ownership on `GET /api/v1/projects/{project_id}/evidence` to prevent unauthorized cross-tenant evidence leakage.
   - Assert repository file paths exposed to the frontend are relative strings without directory traversal (`../`) escapes.
2. **`eval_persona`**:
   - Verify that evidence items rendered in the frontend match the exact AST symbols and line boundaries cited by the Principal Engineer during question generation and stress testing.

---

## 4. Architecture & Data Flow

```mermaid
flowchart LR
    subgraph Backend
        DB[(PostgreSQL 17)] --> |Evidence records| API["GET /api/v1/projects/{id}/evidence"]
    end

    subgraph Frontend
        API --> |EvidenceResponse[]| Client["defenseApi.getProjectEvidence()"]
        Client --> Page["/interview/[id]/page.tsx"]
        Page --> |activeEvidenceIds & evidenceList| Panel["EvidencePanel (Drawer/Side Panel)"]
        Panel --> Badges["Category Badges (Framework, Auth, DB...)"]
        Panel --> Anchors["File Path & Lines (e.g. app/core/db.py#L15-L40)"]
    end
```

---

## 5. Data Contracts & Interfaces

### Backend Schema (`backend/app/schemas/evidence.py` - existing)
```python
class EvidenceResponse(EvidenceBase):
    id: uuid.UUID
    project_id: uuid.UUID
    evidence_type: EvidenceType
    title: str
    description: str
    file_path: str
    start_line: int
    end_line: int
```

### Frontend Interface (`frontend/src/types/evidence.ts`)
```typescript
export type EvidenceType =
  | "framework"
  | "database"
  | "auth"
  | "api_endpoint"
  | "queue"
  | "infrastructure"
  | "architecture";

export interface EvidenceItem {
  id: string;
  project_id: string;
  evidence_type: EvidenceType;
  title: string;
  description: string;
  file_path: string;
  start_line: number;
  end_line: number;
}
```

---

## 6. Implementation Sequence

1. **Backend Endpoint (`backend/app/api/v1/projects.py`)**:
   - Add `GET /api/v1/projects/{project_id}/evidence` returning `list[EvidenceResponse]`.
   - Verify tenant ownership (`Project.user_id == current_user.id`).
   - Support optional `ids` query parameter for multi-id lookup.
   - Author hermetic endpoint tests in `backend/tests/test_evidence_endpoint.py`.

2. **Frontend Types & API Client (`frontend/src/types/evidence.ts` & `frontend/src/lib/defenseApi.ts`)**:
   - Define `EvidenceItem` and `EvidenceType`.
   - Add `getProjectEvidence(projectId: string, token: string): Promise<EvidenceItem[]>`.

3. **Evidence Panel Component (`frontend/src/components/domain/EvidencePanel.tsx`)**:
   - Collapsible drawer / slide-over panel.
   - Category filtering pills (`All`, `Cited in Question`, `Database`, `Auth`, etc.).
   - Visual badges with distinct color accents (emerald for framework, blue for DB, purple for auth, amber for queue).
   - Line range and file reference indicators (`#L15-L40`).
   - "Cited by Active Question" highlight border.

4. **Integration into Interview Page (`frontend/src/app/interview/[id]/page.tsx`)**:
   - Fetch project evidence on mount alongside defense session.
   - Header button: `View Evidence ({cited_count} cited / {total} total)`.
   - Active question card has one-click "Inspect Cited Evidence" pill.

---

## 7. Quality Gates & Acceptance Criteria

- [ ] `GET /api/v1/projects/{project_id}/evidence` passes unit and integration tests (200, 401 unauth, 404 not found).
- [ ] `npx tsc --noEmit` and `npm run build` succeed with 0 errors.
- [ ] `python -m ruff check app tests` passes with 0 warnings/errors.
- [ ] All modified and new files strictly $\le 300$ LOC.
