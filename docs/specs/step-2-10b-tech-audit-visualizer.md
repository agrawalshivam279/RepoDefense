# Technical Specification: Step 2.10b — Next.js 15 Technology Health Audit Visualizer & Deprecation Inspector

## 1. Overview
Step 2.10b builds the frontend user interface for the RepoDefense Technology & Dependency Audit engine. It renders an architectural tech health scorecard, severity counters, and an interactive list of flagged dependencies with categorized issues and concrete remediation guidance.

## 2. Requirements & Acceptance Criteria
- **TypeScript Data Models (`frontend/src/types/techAudit.ts`)**:
  - `AuditSeverity`: `"critical" | "high" | "medium" | "low"`
  - `AuditCategory`: `"deprecated" | "security_risk" | "outdated" | "unmaintained"`
  - `AuditedDependencyItem`: name, version, is_dev, severity, category, issue_description, suggested_alternative, reference_url.
  - `TechAuditReportResponse`: project_id, project_name, total_dependencies_audited, flagged_dependencies_count, critical_count, high_count, medium_count, low_count, tech_health_score, audited_items.
- **Typed API Client (`frontend/src/lib/techAuditApi.ts`)**:
  - `getProjectTechAudit(projectId: string, token?: string): Promise<TechAuditReportResponse>` calling `GET /api/v1/projects/{projectId}/tech-audit`.
- **Scorecard Component (`frontend/src/components/domain/TechAuditScorecard.tsx`)**:
  - Displays 0-100% health score with color graduation (Emerald for 85-100%, Amber for 70-84%, Orange for 50-69%, Rose for <50%).
  - Severity metric badges: Critical, High, Medium, Low counters.
  - Total scanned vs flagged dependencies breakdown.
- **Audited Dependency List Component (`frontend/src/components/domain/AuditedDependencyList.tsx`)**:
  - Filter by severity (all, critical, high, medium, low) and category (all, deprecated, security_risk, outdated, unmaintained).
  - Search filter input for package names.
  - Cards rendering package name, version, dev badge, severity pill, category tag, issue description, and suggested alternative migration advice.
  - Zero-issue empty state banner ("Clean bill of health").
- **App Router Tab Page (`frontend/src/app/projects/[id]/tech-audit/page.tsx`)**:
  - Client component with Supabase JWT authentication.
  - Navigation links to other project subpages (Claims, Coverage, Ownership, Architecture).
  - Loading skeleton and error retry UI.
- **Project Navigation Updates**:
  - Add "Tech Audit" navigation button to `/projects/[id]` and `/projects/[id]/architecture`.
- **Constraints**:
  - Next.js 15 App Router strict adherence.
  - Every created and modified file strictly $\le 300$ LOC.
  - Zero compile errors (`tsc --noEmit` and `next build`).
