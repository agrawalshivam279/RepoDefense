# Technical Specification: Step 5.1a — Backend Public Shareable Defense Reports, Cryptographic Verification Tokens & Dynamic SVG Resume Badge REST API

## 1. Overview & Objective
RepoDefense authenticates candidate engineering depth through rigorous, code-grounded architectural defense simulations. However, evaluation reports and transcripts are currently restricted to authenticated project owners (`get_current_user`). To fulfill the core product promise of providing "verifiable proof on a resume" (`Gemini.md` Phase 5 & ADRs), Step 5.1a delivers the backend public verification subsystem:
1. **Cryptographic Share Token Generation**: Secure, high-entropy tokens allowing candidates to share public read-only defense reports.
2. **Public-Safe Defense Report Sanitization**: An extraction engine compiling verified reports while stripping sensitive user identifiers, internal file-system paths, and secrets.
3. **Dynamic SVG Resume Badge Generation**: Shields.io-compliant, vector-sharp SVG badges displaying candidate defense verdicts (e.g. "RepoDefense: Certified Principal • 8.8/10") embeddable on GitHub READMEs, personal portfolios, and resumes.
4. **Public REST Endpoints**: Authenticated token management for candidates and unauthenticated verification endpoints for recruiters, engineering hiring managers, and badge consumers.

---

## 2. Invariant & Security Compliance
- **Zero Arbitrary Code Execution**: No user code execution; operates strictly on static AST defense evaluation data and session state.
- **Path Traversal & Data Leak Protection**: Public report responses sanitize absolute filesystem paths and project tenancy IDs.
- **IDOR Protection**: Share token creation, revocation, and inspection require authenticated project ownership.
- **Unguessable Tokens**: Generated using Python standard library `secrets.token_urlsafe(32)` providing 256 bits of cryptographic entropy.
- **Cache-Control & Headers**: SVG badges returned with `Content-Type: image/svg+xml`, `Cache-Control: public, max-age=300, s-maxage=3600`, preventing denial-of-service load while ensuring fresh status.
- **LOC Limit**: All files strictly $\le 300$ LOC.

---

## 3. Data Contracts & Pydantic Schemas (`backend/app/schemas/public_report.py`)
- `PublicShareConfig`: Request payload to configure public sharing (active flag, optional expiration in days).
- `PublicShareTokenResponse`: Share URL, badge URL, Markdown snippet, HTML snippet, active state, and expiration timestamps.
- `PublicCategoryScore`: Public-safe category breakdown (score, status, summary, questions count).
- `PublicDefenseReportResponse`: Publicly accessible verified report including project name, sanitized repo URL, commit SHA, overall score, verdict, certification tier, category scores, key strengths, architectural pattern, tech health score, and verification timestamp.

---

## 4. Service Architecture (`backend/app/services/public_report.py`)
- `PublicShareRecord`: Internal dataclass holding token metadata, session reference, project reference, owner reference, creation time, and expiration.
- `PublicReportStore`: Thread-safe, bounded in-memory store for public share records with lookup by `share_token` and `(project_id, session_id)`.
- `create_or_update_share_token(...)`: Generates cryptographic token or updates existing share record with IDOR verification.
- `revoke_share_token(...)`: Revokes public access for a given session.
- `get_public_report_by_token(...)`: Resolves share token, checks expiration, loads session from `defense_store`, extracts public-safe fields, and builds `PublicDefenseReportResponse`.
- `generate_defense_svg_badge(...)`: Generates valid, accessible SVG badge with dynamic pill widths, text metrics, and certification color grading:
  - Score $\ge 7.5$: Emerald `#059669` / `#10b981` ("Certified Principal")
  - Score $\ge 5.0$: Sky `#0284c7` / `#38bdf8` ("Solid Architect")
  - Score $< 5.0$: Amber `#d97706` / `#f59e0b` ("Remediation Required")

---

## 5. API Endpoints (`backend/app/api/v1/public_reports.py`)
1. `POST /api/v1/projects/{project_id}/defense/{session_id}/share`:
   - Authenticated (`get_current_user`). Generates or toggles public sharing.
2. `GET /api/v1/projects/{project_id}/defense/{session_id}/share`:
   - Authenticated (`get_current_user`). Retrieves active share token and embed codes.
3. `DELETE /api/v1/projects/{project_id}/defense/{session_id}/share`:
   - Authenticated (`get_current_user`). Revokes public access.
4. `GET /api/v1/public/reports/{share_token}`:
   - Unauthenticated / Public. Returns sanitized `PublicDefenseReportResponse`.
5. `GET /api/v1/public/badges/{share_token}.svg`:
   - Unauthenticated / Public. Returns dynamic `image/svg+xml`.

---

## 6. Verification Criteria
- `pytest backend/tests/test_public_reports.py -v` passes 100%.
- Full test coverage for share token creation, revocation, expired token handling, public report sanitization, SVG badge generation, and unauthenticated public retrieval.
- `ruff check backend/app` passes with 0 errors.
