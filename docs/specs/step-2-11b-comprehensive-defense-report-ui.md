# Technical Specification: Step 2.11b — Next.js 15 Comprehensive Defense Report Page with Architecture Embed, Verified Claims & Print-to-PDF Styling

## 1. Overview
Step 2.11b finishes Phase 2 Milestone 2.11 by building the comprehensive, printable Next.js 15 App Router defense evaluation report page (`/report/[id]`). It enriches the oral defense debrief with embedded Mermaid architecture topology diagrams, detected architectural patterns, dependency technology health audits, and `@media print` CSS styling for 1-click browser PDF export.

## 2. Target Files & Goldilocks Task Sizing
- `frontend/src/types/report.ts` (~35 lines added, $\le 300$ LOC total)
- `frontend/src/lib/defenseApi.ts` (~30 lines added, $\le 300$ LOC total)
- `frontend/src/components/domain/ReportArchitectureSection.tsx` (new, ~150 lines, $\le 300$ LOC)
- `frontend/src/app/report/[id]/page.tsx` (updated, ~260 lines, $\le 300$ LOC)

## 3. Requirements & Acceptance Criteria

### 3.1 Data Contracts (`frontend/src/types/report.ts`)
- Define `EnhancedDefenseReportResponse` extending `DefenseReportResponse`:
  - `architecture_primary_pattern?: string | null`
  - `architecture_confidence_tier?: string | null`
  - `diagram_mermaid_code?: string | null`
  - `tech_health_score?: number | null`
  - `tech_flagged_count?: number | null`
  - `tech_total_dependencies?: number | null`
  - `claims_verified_count?: number | null`
  - `claims_total_count?: number | null`

### 3.2 API Client (`frontend/src/lib/defenseApi.ts`)
- Add `getEnhancedDefenseReport(sessionId: string, token: string): Promise<EnhancedDefenseReportResponse>`:
  - Communicates with `GET /api/v1/defense/sessions/{sessionId}/enhanced-report`.
  - Fallbacks gracefully to base report if enhanced endpoint is unavailable or returns 404.

### 3.3 Domain Architecture & Tech Embed Component (`ReportArchitectureSection.tsx`)
- Renders:
  - System topology card with primary architecture pattern pill and confidence tier.
  - Client-side dynamic Mermaid diagram render with SVG export/viewing.
  - Technology health summary card displaying $0-100\%$ score, total audited dependencies, and flagged obsolescence count.

### 3.4 Comprehensive Report Page (`/report/[id]/page.tsx`)
- Executive Header with "Print / Export PDF" button triggering `window.print()`.
- Executive Verdict & Defense Score banner with qualification grade.
- Category scores breakdown (`CategoryScorecard`).
- Key strengths, critical blind spots, and actionable recommendations.
- Architecture and Technology Health audit sections embedded seamlessly into the flow.
- Print-to-PDF styles (`@media print`):
  - Hides navigation bars, back buttons, and refresh controls (`no-print`).
  - Forces background color rendering (`print-color-adjust: exact`).
  - Sets clean margins and prevents page-break splits inside score cards.

## 4. Specialized Domain Skill Directives
- **Doctor / Build Sanity**: Must pass `node frontend/node_modules/typescript/bin/tsc -p frontend/tsconfig.json --noEmit` and `npm run build` in `frontend/` across all 13 routes.
- **Security & Integrity**: Purely static client-side presentation, no unsafe `eval()` or unescaped HTML injection.

## 5. Verification Commands
```bash
node frontend/node_modules/typescript/bin/tsc -p frontend/tsconfig.json --noEmit
npm --prefix frontend run build
python -m pytest backend/tests/test_enhanced_report.py -v
```
