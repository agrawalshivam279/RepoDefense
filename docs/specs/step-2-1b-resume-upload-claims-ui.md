# 📄 Technical Specification: Next.js 15 Resume Upload UI & Extracted Claims Dashboard

> **Step ID**: `Step 2.1b`  
> **Target Module**: `frontend/src/...`  
> **Git Feature Branch**: `feat/step-2-1b-resume-upload-claims-ui`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-11-05  

---

## 1. Executive Summary

Step 2.1b completes **Milestone 2.1 (Resume Claim Extraction)** by delivering the user-facing resume upload interface and extracted claims dashboard in Next.js 15 App Router. In Step 2.1a, the backend REST API (`POST /api/v1/claims/extract` and `POST /api/v1/claims/upload`) was implemented and verified.

This milestone provides a clean, responsive UI allowing developers to drag-and-drop PDF resumes (enforcing $\le 10$ MB client-side validation) or paste raw text. The extracted claims are presented in an interactive dashboard featuring domain categorization badges (`Architecture`, `Scalability`, `Security`, `Database`, `Performance`, `Framework`, `Infrastructure`), detected technology chips, category filter tabs, search filtering, and verifiability indicators.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Step 2.1a` (Backend Claim Extraction REST API & pypdf parser - merged to `main`).
  - Next.js 15 App Router + Tailwind CSS + Lucide Icons + Supabase Auth client.
- **Blocked by**: None.
- **Tech Stack Invariant**:
  - Next.js 15 (App Router) + TypeScript + Tailwind CSS.
  - Zero unapproved heavy external UI libraries.
  - Strict compliance with `Gemini.md` architecture and file length limits ($\le 300$ LOC per file).

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Client-side document transfer only; no client-side evaluation of untrusted files.
- [x] **Client-Side Upload Validation**: Strictly validates `.pdf` extension and `application/pdf` MIME type, plus client-side 10MB file size ceiling before issuing network requests.
- [x] **Safe Token Handling**: All API requests pass Supabase JWT bearer token via `Authorization` headers without leaking secrets in URLs.
- [x] **Resilient Error Boundaries**: Gracefully handles network failures, backend 413 Payload Too Large, and 400 Bad Request responses with user-friendly alerts.

---

## 4. 🧭 Specialized Skills Directive

| Specialized Skill | Scope of Impact & Mandate | Verification Requirement |
| :--- | :--- | :--- |
| **[`doctor`](file:///d:/RepoDefense/.agents/skills/doctor/SKILL.md)** | Pre-flight and post-implementation health checks across Next.js 15 build, TypeScript typecheck (`tsc --noEmit`), and new `/claims` route compilation. | Validates zero TypeScript errors and successful production build across all routes. |
| **[`security_auditor`](file:///d:/RepoDefense/.agents/skills/security_auditor/SKILL.md)** | Audits client-side file upload sanitization (file size capping $\le 10$ MB, PDF mime-type guard, and zero token exposure in form requests). | Asserts that non-PDF and oversized files are blocked before upload transmission. |

---

## 5. 🧠 Sequential Thinking Strategy

1. **User Flow & State Progression**:
   - `EMPTY / IDLE`: Developer views upload card with two tabs: "Upload PDF" and "Paste Text".
   - `UPLOADING / EXTRACTING`: Loading spinner with animated status ("Parsing document...", "Extracting technical claims with AI Principal Engineer...").
   - `CLAIMS DISPLAY`: Once extracted, renders top scorecard (total claims, character count, detected technologies cloud) and claims list.
   - `FILTER & SEARCH`: Developer can filter by domain categories (`Architecture`, `Scalability`, etc.) or search keywords.
2. **Component Modularity & LOC Guardrails**:
   - `frontend/src/types/claim.ts`: TypeScript interfaces mirroring backend Pydantic schemas (~40 LOC).
   - `frontend/src/lib/claimApi.ts`: REST API client calling FastAPI `/api/v1/claims` endpoints (~80 LOC).
   - `frontend/src/components/domain/ResumeUploadCard.tsx`: Dual-mode upload component with drag-and-drop and text paste (~170 LOC).
   - `frontend/src/app/claims/page.tsx`: Full claims dashboard page with scorecard, filters, search, and claim cards (~250 LOC).
   - All files strictly $\le 300$ LOC.

---

## 6. Data Contracts & Interfaces

### 6.1 TypeScript Types (`frontend/src/types/claim.ts`)

```typescript
export type ClaimCategory =
  | "architecture"
  | "scalability"
  | "performance"
  | "database"
  | "security"
  | "framework"
  | "infrastructure";

export interface TechnicalClaim {
  id: string;
  statement: string;
  category: ClaimCategory;
  technologies: string[];
  verifiable: boolean;
  source_context?: string;
}

export interface ClaimExtractionResponse {
  claims: TechnicalClaim[];
  total_claims: number;
  source_char_count: number;
  technologies_detected: string[];
}
```

---

## 7. Target File Architecture

| Action | Path | Target LOC | Responsibilities |
| :--- | :--- | :---: | :--- |
| `[NEW]` | `frontend/src/types/claim.ts` | ~40 LOC | TypeScript contracts mirroring backend claim schemas. |
| `[NEW]` | `frontend/src/lib/claimApi.ts` | ~80 LOC | Typed REST API client for `/api/v1/claims/extract` and `/api/v1/claims/upload`. |
| `[NEW]` | `frontend/src/components/domain/ResumeUploadCard.tsx` | ~170 LOC | Drag-and-drop PDF upload and raw text paste with client-side 10MB validation. |
| `[NEW]` | `frontend/src/app/claims/page.tsx` | ~250 LOC | Extracted claims dashboard with scorecards, category filter chips, search, and claim list. |
| `[MODIFY]` | `frontend/src/app/layout.tsx` | ~125 LOC | Add `/claims` link to global navbar header. |

---

## 8. Step-by-Step Implementation Sequence

1. **Phase A: Types & API Client**:
   - Create `frontend/src/types/claim.ts`.
   - Create `frontend/src/lib/claimApi.ts` with error handling and Supabase auth token integration.
2. **Phase B: Upload Component**:
   - Create `frontend/src/components/domain/ResumeUploadCard.tsx` with drag-and-drop, tab toggle, and file size checks.
3. **Phase C: Claims Dashboard Page**:
   - Create `frontend/src/app/claims/page.tsx` with metrics scorecard, category filter chips, search bar, and claim cards.
   - Update `frontend/src/app/layout.tsx` with navbar link to "Claims".
4. **Phase D: Verification Gate (`/verify_step`)**:
   - Run `npx tsc --noEmit` and `npm run build` across all 9 App Router routes.
   - Verify all files strictly conform to the $\le 300$ LOC limit.
   - Output formal `/verify_step` Quality Gate Report and await approval.

---

## 9. Verification & Acceptance Criteria

### Automated Verification Commands
```bash
# 1. Frontend TypeScript typecheck
cd frontend && npx tsc --noEmit

# 2. Frontend Next.js production build
cd frontend && npm run build

# 3. Backend lint check
python -m ruff check backend/app backend/tests
```

### Acceptance Checklist
- [ ] All files strictly $\le 300$ LOC.
- [ ] Drag-and-drop PDF upload and raw text paste work smoothly.
- [ ] Client-side validation blocks non-PDF and oversized (>10MB) files with clear error toast/alert.
- [ ] Extracted claims display category badges, technology pills, and verifiability status.
- [ ] Category filter and search filter update claim list in real time.
- [ ] Next.js 15 production build compiles all 9 routes cleanly with 0 errors.
