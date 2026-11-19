# Technical Specification: Step 5.1b Next.js 15 Public Defense Verification Portal & Badge Dialog

## 1. Objective & Scope
Provide a recruiter- and peer-facing public verification portal and an embeddable badge modal for RepoDefense candidates. Candidates can generate unguessable share links, copy dynamic SVG badges in Markdown or HTML for their GitHub READMEs or resumes, and visitors can independently verify candidates' architectural defense credentials without an account.

## 2. Target Files & Artifacts
1. `frontend/src/types/publicReport.ts`: TypeScript contracts for public verification, category scores, and share tokens.
2. `frontend/src/lib/publicReportApi.ts`: REST client for unauthenticated public reports and authenticated share token lifecycle.
3. `frontend/src/components/domain/ShareBadgeModal.tsx`: Interactive modal dialog for configuring sharing, previewing SVG badges, and copying markdown/HTML snippets.
4. `frontend/src/app/verify/[token]/page.tsx`: Unauthenticated public verification page with score gauge, verified commit, and tamper-proof credential seal.
5. `frontend/src/app/report/[id]/page.tsx`: Integration of "Share & Badges" button and modal trigger.

## 3. Invariants & Security
- **File Length**: All files strictly <= 300 lines of code.
- **Zero Arbitrary Code Execution**: Pure display and static API interaction.
- **Public Accessibility**: `/verify/[token]` requires no authentication or cookies.
- **Graceful Error States**: Handle expired (410) and revoked/invalid (404) links with informative recovery messaging.
