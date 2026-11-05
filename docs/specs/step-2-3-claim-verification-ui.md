# 📄 Technical Specification: Claim Verification UI & Evidence Graph View

> **Step ID**: `Step 2.3`  
> **Target Module**: `frontend/src/...`  
> **Git Feature Branch**: `feat/step-2-3-claim-verification-ui`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-11-06  

---

## 1. Executive Summary

Step 2.3 completes **Milestone 2.3 (Claim Verification UI - Evidence Graph View)** under Phase 2 (Differentiation). In Step 2.2a, the backend verification engine was deployed, providing `POST /api/v1/projects/{project_id}/claims/verify` with pgvector semantic retrieval (`all-MiniLM-L6-v2`), architectural evidence lookups, and LiteLLM Principal Engineer grounding.

This milestone delivers the Next.js 15 App Router frontend interface to visualize, explore, and audit candidate resume claims mapped against repository code truth. The interface provides:
1. **Status Color-Coding**: Prominent visual indicators for `SUPPORTED` (emerald/green), `CONTRADICTED` (rose/red), and `UNVERIFIABLE` (amber/yellow).
2. **Confidence Metric**: Normalized confidence score percentage meter for each claim assessment.
3. **Evidence Citations Graph / Drawer**: Expandable code snippet viewer showing exact relative file paths, 1-indexed line spans, semantic similarity ratings, and architectural evidence tags (frameworks, databases, auth guards, endpoints, queues).
4. **Suggested Defense Questions**: Displays the targeted interview questions synthesized by the Principal Engineer for candidate interview preparation.
5. **Interactive Verification Pipeline**: Allows users to load candidate claims (from sample presets or parsed resumes) and trigger real-time verification against the active repository snapshot.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Step 2.2a`: Backend Claim-Evidence Verification Engine & REST API (`POST /api/v1/projects/{project_id}/claims/verify`).
  - `Step 2.1b`: Next.js 15 Resume Upload UI & Extracted Claims Dashboard.
  - Next.js 15 App Router, TypeScript, Tailwind CSS, Lucide Icons, Supabase Auth.
- **Blocked by**: None.
- **Tech Stack Invariants**:
  - Strictly Next.js 15 (App Router) + TypeScript + Tailwind CSS.
  - Zero code execution; untrusted file and code snippets rendered strictly through React safe escaping.
  - Strict compliance with `Gemini.md` architecture and file length limits ($\le 300$ LOC per file).

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: All retrieved code snippets and candidate claim statements are handled as pure static strings; no client-side `eval`, `dangerouslySetInnerHTML`, or arbitrary script execution.
- [x] **Safe Token Handling**: All API requests pass the Supabase JWT bearer token via `Authorization: Bearer <token>` headers without exposing tokens in query parameters or browser history.
- [x] **Strict Multi-Tenant Alignment**: Verifies that requests are scoped to the user's authenticated `projectId`.
- [x] **Evidence Grounding Transparency**: Displays exact file paths, line ranges, and similarity rankings so users can independently verify why a claim was marked supported, contradicted, or unverifiable.

---

## 4. 🧭 Specialized Skills Directive

| Specialized Skill | Scope of Impact & Mandate | Verification Requirement |
| :--- | :--- | :--- |
| **[`doctor`](file:///d:/RepoDefense/.agents/skills/doctor/SKILL.md)** | Pre-flight and post-implementation health checks across Next.js 15 App Router build and TypeScript typecheck (`tsc --noEmit`). | Validates zero TypeScript errors and successful production build across all routes including `/projects/[id]/claims`. |
| **[`eval_rag`](file:///d:/RepoDefense/.agents/skills/eval_rag/SKILL.md)** | Audits frontend rendering of semantic similarity scores, file line boundaries (`start_line`..`end_line`), and architectural evidence tags. | Asserts that code citations display exact line ranges and similarity percentages accurately without truncating file paths. |
| **[`eval_persona`](file:///d:/RepoDefense/.agents/skills/eval_persona/SKILL.md)** | Verifies presentation of Principal Engineer suggested defense questions and reasoning notes. | Ensures suggested interview questions are prominent and actionable with direct launch CTAs to defense interviews. |

---

## 5. 🧠 Sequential Thinking Strategy

1. **User Flow & State Progression**:
   - `EMPTY / LOAD CLAIMS`: The user visits `/projects/[id]/claims`. If no verification results exist, offers presets ("Load Sample Resume Claims", "Upload Resume PDF", or paste claims).
   - `VERIFYING`: When the user clicks "Run Claim Verification", shows an animated progress bar and spinner ("Grounding claims against AST symbols & vector embeddings...").
   - `VERIFICATION DASHBOARD`: Displays:
     - KPI Scorecards: Total Claims, Supported, Contradicted, Unverifiable, and Grounded Accuracy %.
     - Filter & Search: Filter by status (`all`, `supported`, `contradicted`, `unverifiable`) or search claim text/technologies.
     - Claims List: Individual `ClaimVerificationCard` components with collapsible evidence citations.
   - `EVIDENCE INSPECTOR`: Expanding a claim reveals:
     - Principal Engineer Reasoning & Confidence percentage meter.
     - Code Citations: File path, line numbers, similarity badge, formatted code snippet.
     - Architecture Citations: Badges indicating detected frameworks, databases, auth guards, endpoints.
     - Suggested Interview Questions: Questions candidate should be ready to defend, with "Defend in Interview" CTA.
2. **Component Modularity & LOC Guardrails**:
   - `frontend/src/types/claim.ts`: Extend with verification interfaces (`VerificationStatus`, `EvidenceCitation`, `ClaimVerificationResult`, `BatchClaimVerificationResponse`) (~60 LOC total).
   - `frontend/src/lib/claimApi.ts`: Add `verifyProjectClaims` method calling backend verification endpoint (~115 LOC total).
   - `frontend/src/components/domain/ClaimVerificationCard.tsx`: Modular card component handling status coloring, confidence meter, expandable citations, and suggested questions (~230 LOC).
   - `frontend/src/app/projects/[id]/claims/page.tsx`: Full project claim verification dashboard with summary metrics, filter pills, search, verification runner, and empty state (~270 LOC).
   - `frontend/src/app/projects/[id]/page.tsx`: Add "Verify Claims" navigation button (~285 LOC).
   - All files strictly $\le 300$ LOC.

---

## 6. Data Contracts & Interfaces

### 6.1 TypeScript Interfaces (`frontend/src/types/claim.ts`)

```typescript
export type VerificationStatus = "supported" | "contradicted" | "unverifiable";

export interface CodeCitation {
  file_path: string;
  start_line: number;
  end_line: number;
  similarity_score: number;
  code_snippet: string;
}

export interface ArchitectureCitation {
  evidence_type: string;
  name: string;
  source_file: string;
}

export interface ClaimVerificationResult {
  claim_id: string;
  claim_statement: string;
  claim_category: ClaimCategory;
  status: VerificationStatus;
  confidence_score: number;
  reasoning: string;
  code_citations: CodeCitation[];
  evidence_citations: ArchitectureCitation[];
  suggested_interview_questions: string[];
}

export interface BatchClaimVerificationResponse {
  project_id: string;
  verified_at: string;
  results: ClaimVerificationResult[];
  total_claims: number;
  supported_count: number;
  contradicted_count: number;
  unverifiable_count: number;
}
```

### 6.2 API Client (`frontend/src/lib/claimApi.ts`)

```typescript
export async function verifyProjectClaims(
  projectId: string,
  claims: TechnicalClaim[],
  token?: string
): Promise<BatchClaimVerificationResponse>
```

---

## 7. Quality Gate & Acceptance Criteria

1. **TypeScript Typecheck**: `npm --prefix frontend run typecheck` passes with 0 errors.
2. **Next.js Production Build**: `npm --prefix frontend run build` succeeds cleanly across all routes including `/projects/[id]/claims`.
3. **LOC Audit**: Every file strictly complies with $\le 300$ LOC.
4. **Interactive Capabilities**:
   - Status color-coding (`SUPPORTED` in emerald, `CONTRADICTED` in rose, `UNVERIFIABLE` in amber).
   - Expandable code citations with line numbers, similarity %, and formatted snippets.
   - Architectural evidence tags and suggested defense questions.
   - Seamless navigation between Project Overview, Claims Verification, and Defense Interview.
