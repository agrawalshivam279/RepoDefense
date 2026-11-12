# Technical Specification — Step 3.6b: Next.js 15 Architecture Defense Mode UI & Interactive Diagram-Linked Defense Flow

- **Status:** Planned (Awaiting Implementation Approval)
- **Phase:** Phase 3 — Interactive Frontend & Defense Engine (Milestone 3.6)
- **Feature Branch:** `feat/step-3-6b-arch-defense-ui`
- **Target Scope:** Goldilocks Calibrated (`4` new files + `1` nav link update, strictly `<= 300 LOC/file`)
- **Backend Dependency:** Step 3.6a (`/api/v1/arch-defense` — merged in PR #64)

---

## 1. Objective & Architectural Fit

Build the **Next.js 15 (App Router) + TypeScript + Tailwind CSS** user interface for **Architecture Defense Mode** at `/projects/[id]/arch-defense`, connecting seamlessly to the FastAPI backend endpoints delivered in **Step 3.6a**:

- `POST /api/v1/arch-defense/projects/{project_id}/topics`
- `POST /api/v1/arch-defense/projects/{project_id}/sessions/start`
- `GET /api/v1/arch-defense/sessions/{session_id}`
- `POST /api/v1/arch-defense/sessions/{session_id}/respond`

Candidates inspect their project's detected architecture pattern and Mermaid topology diagram alongside targeted design topics (`PATTERN_CHOICE`, `COMPONENT_BOUNDARY`, `DATA_FLOW_COUPLING`, `ARCHITECTURAL_RISK`), select a topic to initiate an oral-style defense (`TOPIC_ACTIVE` → `TRADEOFF_CHALLENGE` → `COMPLETED`), and submit explanations while viewing referenced diagram nodes, connected edges, and the interactive rendered Mermaid graph side by side.

---

## 2. Target Files & Module Responsibilities

| File | Action | Est. LOC | Responsibility |
| :--- | :--- | :---: | :--- |
| `frontend/src/types/archDefense.ts` | `[NEW]` | ~105 | Exact TypeScript interfaces mirroring `backend/app/schemas/arch_defense.py`. |
| `frontend/src/lib/archDefenseApi.ts` | `[NEW]` | ~235 | Runtime-validated REST client with `AbortSignal` support and status-aware error parsing (`400`/`404`/`429`/`503`). |
| `frontend/src/components/domain/ArchDefenseSession.tsx` | `[NEW]` | ~275 | Side-by-side split workspace pairing interactive [`MermaidViewer`](file:///d:/RepoDefense/frontend/src/components/domain/MermaidViewer.tsx) + highlighted `target_nodes` badges with live multi-turn defense transcript, `1..8000` char answer composer, and final rubric scorecard. |
| `frontend/src/app/projects/[id]/arch-defense/page.tsx` | `[NEW]` | ~280 | App Router page integrating `ProjectNavHeader`, pattern summary banner, `ArchFocusAreaType` filter tabs, diagram preview, grounded topic cards, and session transition orchestration. |
| `frontend/src/components/domain/ProjectNavHeader.tsx` | `[MODIFY]` | +3 | Register `"arch-defense"` tab (`Arch Defense` → `/arch-defense`) in `ProjectNavTab` and `TABS`. |

*(All files MUST remain strictly `<= 300 LOC` and zero-error under `tsc --noEmit`, `next lint`, and `next build`.)*

---

## 3. Data Contracts (`frontend/src/types/archDefense.ts`)

Mirror `backend/app/schemas/arch_defense.py` verbatim, reusing existing contracts from [`architecture.ts`](file:///d:/RepoDefense/frontend/src/types/architecture.ts) and [`diagram.ts`](file:///d:/RepoDefense/frontend/src/types/diagram.ts):

- `ArchFocusAreaType`: `"PATTERN_CHOICE" | "COMPONENT_BOUNDARY" | "DATA_FLOW_COUPLING" | "ARCHITECTURAL_RISK"`
- `ArchDefenseStage`: `"TOPIC_ACTIVE" | "TRADEOFF_CHALLENGE" | "COMPLETED"`
- `DiagramTarget`: `{ node_id: string; label: string; node_type: string; subgraph?: string | null; connected_edges: string[] }`
- `ArchDefenseTopic`: `{ id, title, focus_area, pattern_name, severity_or_confidence, target_nodes: DiagramTarget[], design_claim, interrogation_prompt, expected_tradeoffs: string[], risk_references: string[] }`
- `ArchDefenseTurn`: `{ id, role: "interviewer" | "candidate" | "system" | string, content, stage: ArchDefenseStage, timestamp, metadata: Record<string, unknown> }`
- `ArchDefenseSessionState`: `{ session_id, project_id, topic, mermaid_code, diagram_summary, primary_pattern_name, stage, current_turn_index, turns, overall_score?: number | null, pattern_rationale_solid?: boolean | null, boundary_coherence_score?: number | null, feedback?: string | null, created_at, updated_at }`
- `ArchTopicListResponse`: `{ project_id, project_name, primary_pattern: DetectedPattern, diagram_type: DiagramType, mermaid_code, nodes: DiagramNode[], edges: DiagramEdge[], is_diagram_fallback, total_topics, topics: ArchDefenseTopic[] }`
- Request DTOs:
  - `GenerateArchTopicsRequest`: `{ focus_area?: ArchFocusAreaType; max_topics?: number; model?: string; api_key?: string; base_url?: string }`
  - `StartArchDefenseRequest`: `{ topic_id: string }` (note Step 3.6a rejects LLM overrides on `/sessions/start`)
  - `SubmitArchAnswerRequest`: `{ answer: string; model?: string; api_key?: string; base_url?: string }`

---

## 4. API Client & Runtime Guards (`frontend/src/lib/archDefenseApi.ts`)

1. Use `API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`.
2. Export:
   - `fetchArchDefenseTopics(projectId, token, options?, signal?)` → `POST /api/v1/arch-defense/projects/${encodeURIComponent(projectId)}/topics`
   - `startArchDefenseSession(projectId, topicId, token)` → `POST /api/v1/arch-defense/projects/${encodeURIComponent(projectId)}/sessions/start`
   - `getArchDefenseSession(sessionId, token, signal?)` → `GET /api/v1/arch-defense/sessions/${encodeURIComponent(sessionId)}`
   - `submitArchDefenseTurn(sessionId, payload, token)` → `POST /api/v1/arch-defense/sessions/${encodeURIComponent(sessionId)}/respond`
3. Strict runtime validation (`isDiagramTarget`, `isArchTopic`, `isArchTurn`, `isArchSessionState`, `isArchTopicListResponse`) throwing descriptive errors on malformed backend payloads.
4. Preserve status-aware messages (`400` already completed/invalid override, `404` missing project/topic/session, `409` concurrent transition conflict, `429` per-user active session limit, `503` capacity limit).

---

## 5. Interactive UI & Concurrency/Race Safety

### `frontend/src/app/projects/[id]/arch-defense/page.tsx`
- Auth gate via `supabase.auth.getSession()`, redirecting unauthenticated sessions to `/login`.
- Load project overview (`getProjectOverview`) alongside architecture defense topics (`fetchArchDefenseTopics`).
- **Diagram Overview Collapsible / Split Card:** Reuses [`MermaidViewer`](file:///d:/RepoDefense/frontend/src/components/domain/MermaidViewer.tsx) (`DiagramResponse` built from `ArchTopicListResponse`) plus `primary_pattern` badge (`pattern_name`, `confidence_score`, `tier`).
- **Focus Filter Bar:** Interactive tabs for `All Axes`, `Pattern Choice`, `Component Boundary`, `Data Flow Coupling`, and `Architectural Risk` triggering `AbortController`-guarded topic refreshes (`latestRequestRef` prevents stale filter overwrite).
- **Topic Cards:** Display `focus_area` badge, `severity_or_confidence` indicator, referenced `target_nodes` pills with edge counts, `design_claim`, and "Start Design Defense" CTA (`startingSession` lock prevents duplicate session starts).

### `frontend/src/components/domain/ArchDefenseSession.tsx`
- **Split-Pane Workspace (`lg:grid-cols-12`):**
  - **Left Pane (`lg:col-span-5`):** Sticky context card showing the active diagram via [`MermaidViewer`](file:///d:/RepoDefense/frontend/src/components/domain/MermaidViewer.tsx) + interrogated `target_nodes` cards (label, `node_type`, `subgraph`, and `connected_edges`) + collapsible `expected_tradeoffs` & `risk_references` hints (locked or toggled cleanly so candidates stay focused).
  - **Right Pane (`lg:col-span-7`):** Stage progress pill (`TOPIC_ACTIVE` / `TRADEOFF_CHALLENGE` / `COMPLETED`), scrollable chronological `turns` transcript (`interviewer` / `candidate` / `system` styling matching existing defense session panes), final scorecard (`overall_score / 10`, `boundary_coherence_score / 10`, `pattern_rationale_solid` badge, closing `feedback`), and `1..8000` character composer with live countCodePoints counter and double-submit `submitRequestIdRef` / `activeSessionIdRef` unmount safety.
- Clear answer box ONLY after confirmed non-stale `submitArchDefenseTurn` resolution so network/429/409 errors never wipe typed candidate defenses.

---

## 6. Specialized Skills Directive & Security Checklist

- **Active Matrix Assignment:** Pure Next.js 15 UI + typed REST client (`None` of backend `ast_inspector`/`db_migrator`/`eval_rag`/`eval_persona` triggers apply directly).
- **Security Invariants Enforced in `/verify_step`:**
  1. **Zero XSS / Untrusted Repo Safety:** All Mermaid code renders exclusively through [`MermaidViewer`](file:///d:/RepoDefense/frontend/src/components/domain/MermaidViewer.tsx) (`mermaid.initialize({ securityLevel: "strict" })`); all LLM `design_claim`, `feedback`, `turns`, and `diagram_summary` render as React text nodes — **never** `dangerouslySetInnerHTML`.
  2. **Zero Code Execution:** Pure static API data display; no dynamic `eval`/`Function` execution.
  3. **Credential Hygiene:** Bearer JWT retrieved ephemerally per request from Supabase session; no API keys hardcoded or stored in `localStorage`.
  4. **Line Count Cap:** Every new or edited file strictly `<= 300 LOC`.

---

## 7. Verification Criteria

Single verification gate matching GitHub Actions CI (`Frontend Typecheck & Production Build (Next.js 15)`):

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- Zero TypeScript errors (`tsc --noEmit`).
- Zero ESLint errors (`next lint`).
- Clean production bundle (`next build`) including `/projects/[id]/arch-defense`.
