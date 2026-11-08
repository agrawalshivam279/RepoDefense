# Technical Specification: Step 3.1b — Next.js 15 PR Ingestion & Diff Viewer UI

> **Milestone:** 3.1 — PR Fetch & Analysis  
> **Step:** 3.1b  
> **Feature Branch:** `feat/step-3-1b-pr-diff-viewer-ui`  
> **Status:** Draft / Ready for Approval  
> **Target Release:** Phase 3 (Advanced Defense)

---

## 1. Executive Summary

Step 3.1a delivered the backend GitHub PR fetcher, unified diff parser engine, and REST API endpoints (`/api/v1/pr/parse-diff`, `/api/v1/pr/projects/{project_id}/analyze`). Step 3.1b delivers the complete user-facing interactive frontend interface in Next.js 15 App Router (`/projects/[id]/pr-defense`), allowing developers to ingest GitHub Pull Requests by URL or raw patch text, inspect structured file diffs with syntax-highlighted additions/deletions, review PR executive change metrics, and prepare for PR-grounded architectural defense interviews.

---

## 2. Architectural Alignment & Tech Stack

This milestone strictly aligns with the canonical tech stack and core architecture principles in `Gemini.md`:
* **Frontend:** Next.js 15 (App Router) + TypeScript strict mode + Tailwind CSS + Lucide icons.
* **Authentication:** Supabase Auth JWT Bearer token passed in the `Authorization` header to the FastAPI backend.
* **Security & Invariants:**
  * **Zero Arbitrary Code Execution:** Diff streams are parsed and displayed as pure text/CSS. No `eval`, script execution, or dangerouslySetInnerHTML is used.
  * **Secret Redaction Visibility:** Redacted secrets (`[REDACTED_SECRET]`) are highlighted with security indicator badges.
  * **Strict LOC Limit:** All created and modified files strictly $\le 300$ lines of code.

---

## 3. Data Contracts & TypeScript Interfaces

### `frontend/src/types/prAnalysis.ts`
```typescript
export type FileChangeStatus = "added" | "modified" | "deleted" | "renamed" | "binary";
export type DiffLineType = "addition" | "deletion" | "context";

export interface ParsedDiffLine {
  line_type: DiffLineType;
  content: string;
  old_line_number: number | null;
  new_line_number: number | null;
}

export interface ParsedDiffHunk {
  old_start: number;
  old_lines: number;
  new_start: number;
  new_lines: number;
  header: string;
  lines: ParsedDiffLine[];
  added_count: number;
  deleted_count: number;
}

export interface ParsedFileDiff {
  old_path: string | null;
  new_path: string;
  status: FileChangeStatus;
  hunks: ParsedDiffHunk[];
  total_additions: number;
  total_deletions: number;
  is_binary: boolean;
}

export interface PRMetadata {
  pr_number: number;
  title: string;
  author: string;
  base_branch: string;
  head_branch: string;
  head_sha: string;
  html_url: string;
  created_at: string;
}

export interface PRAnalysisResponse {
  metadata: PRMetadata;
  files: ParsedFileDiff[];
  total_files_changed: number;
  total_additions: number;
  total_deletions: number;
  summary_narrative: string;
}
```

---

## 4. API Client Specification

### `frontend/src/lib/prAnalysisApi.ts`
* `analyzeProjectPR(projectId: string, prUrl: string): Promise<PRAnalysisResponse>`:
  * Calls `POST ${API_BASE}/api/v1/pr/projects/${projectId}/analyze`
  * Body: `{ pr_url: prUrl }`
  * Injects Supabase JWT Bearer token from browser session.
  * Handles 400 (invalid URL), 404 (project/PR not found), 422 (unparseable diff), 502 (GitHub API rate limit/outage).
* `parseRawDiff(diffText: string): Promise<ParsedFileDiff[]>`:
  * Calls `POST ${API_BASE}/api/v1/pr/parse-diff`
  * Body: `{ diff_text: diffText }`
  * Unauthenticated utility endpoint for direct patch testing.

---

## 5. UI Component Hierarchy & Features

```
/projects/[id]/pr-defense/page.tsx
├── ProjectNavHeader (Active Tab: "pr-defense")
├── PR Ingestion Card (Tabs: "GitHub PR URL" vs "Paste Raw Patch")
├── Executive Metrics Scorecard (Files, +Adds, -Dels, Base -> Head Branch, Author)
├── AI Summary Narrative Callout
├── PRDiffViewer
│   ├── Filter Bar (Search by path, filter by status: All, Added, Modified, Deleted)
│   └── Collapsible File Cards
│       ├── File Header (Path, status badge, +adds/-dels count, expand/collapse)
│       └── Unified Hunk Viewer (1-indexed old/new line numbers, colored rows)
└── "Launch PR Defense Interview" CTA (Prepares for Milestone 3.2)
```

### Key UI Features:
1. **Collapsible File Accordions:** Users can collapse large files or focus on specific modules.
2. **Accessible Line Numbers:** Old and new 1-indexed line numbers rendered side-by-side with monospaced code blocks.
3. **Contrast-Compliant Styling:**
   * Additions: `bg-emerald-950/40 text-emerald-200 border-l-2 border-emerald-500`
   * Deletions: `bg-rose-950/40 text-rose-200 border-l-2 border-rose-500`
   * Context: `text-zinc-300 hover:bg-zinc-900/50`
   * Redacted Secrets: Badge indicator `[REDACTED_SECRET]` rendered in warning amber.

---

## 6. Navigation Hub Integration

Update `frontend/src/components/domain/ProjectNavHeader.tsx`:
* Add `"pr-defense"` to `ProjectNavTab`.
* Add tab item `{ id: "pr-defense", label: "PR Defense", hrefSuffix: "/pr-defense", Icon: GitPullRequest, accentColor: "text-rose-400" }`.

---

## 7. Verification & Acceptance Criteria

1. **TypeScript Typecheck:** `npx tsc --noEmit` exits with 0 errors.
2. **Next.js Production Build:** `npm run build` compiles all 14 routes cleanly.
3. **Backend Regression:** All 10 unit/endpoint tests in `test_pr_diff_parser.py` continue passing in $< 3$ seconds.
4. **LOC Compliance:**
   * `frontend/src/types/prAnalysis.ts`: $< 60$ LOC
   * `frontend/src/lib/prAnalysisApi.ts`: $< 90$ LOC
   * `frontend/src/components/domain/PRDiffViewer.tsx`: $< 250$ LOC
   * `frontend/src/app/projects/[id]/pr-defense/page.tsx`: $< 270$ LOC
   * `frontend/src/components/domain/ProjectNavHeader.tsx`: $< 210$ LOC
