# 📄 Technical Specification: Backend Resume Parsing, Claim Extraction Engine & REST API

> **Step ID**: `Step 2.1a`  
> **Target Module**: `backend/app/...`  
> **Git Feature Branch**: `feat/step-2-1a-resume-claim-extraction-backend`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-11-05  

---

## 1. Executive Summary

Step 2.1a initiates **Phase 2: Differentiation** by building the backend claim extraction engine for RepoDefense. In technical hiring, candidates make implicit and explicit claims on their resumes (e.g., *"Architected distributed caching with Redis handling 10k ops/sec"*, *"Implemented JWT RBAC middleware"*). 

This milestone delivers the data schemas, PDF/raw text parser, LiteLLM-powered architectural claim extraction prompt, resilient fallback generator, and REST API endpoint (`POST /api/v1/claims/extract`). This provides the foundation for Milestone 2.2, which maps these extracted claims directly against codebase AST symbols and pgvector embeddings.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Phase 1 Core MVP` (Complete & merged to `main`).
  - `app/ai/llm.py` (LiteLLM client wrapper with retry, fallback, and timeout support).
  - `app/core/config.py` (Settings and environment configuration).
- **Blocked by**: None.
- **Tech Stack Invariant**:
  - Python 3.12+ / FastAPI / Pydantic v2 / LiteLLM.
  - `pypdf` for pure-Python, zero-execution PDF text extraction.
  - Strict compliance with `Gemini.md` architecture and file length limits ($\le 300$ LOC per file).

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: PDF extraction uses pure static text stream parsing; strictly no external binaries, compilation, or shell executions.
- [x] **Untrusted File Quotas**: PDF uploads enforced at $\le 10$ MB max file size and text length capped at 50,000 characters to prevent memory exhaustion / ReDoS.
- [x] **Prompt Injection Defense**: Untrusted resume content wrapped in strict `<resume_text>` XML boundaries with explicit system prompt instructions to ignore embedded instructions.
- [x] **Multi-Tenant Isolation**: API accepts authenticated JWT or session headers, keeping claim extraction scoped per request.

---

## 4. 🧭 Specialized Skills Directive

| Specialized Skill | Scope of Impact & Mandate | Verification Requirement |
| :--- | :--- | :--- |
| **[`security_auditor`](file:///d:/RepoDefense/.agents/skills/security_auditor/SKILL.md)** | Audits PDF upload sanitization, memory limits, and XML boundary prompt isolation against resume-based prompt injection. | Verifies strict 10MB quota, safe PDF stream closing, and boundary delimiters. |
| **[`eval_persona`](file:///d:/RepoDefense/.agents/skills/eval_persona/SKILL.md)** | Audits `CLAIM_EXTRACTION_SYSTEM_PROMPT` calibration to ensure claims focus strictly on verifiable architectural, performance, and concurrency decisions. | Asserts that extracted claims classify category, claimed technologies, and verifiability flags cleanly into Pydantic v2 schemas. |

---

## 5. 🧠 Sequential Thinking Strategy

1. **Claim Granularity & Categorization**:
   - Resumes contain soft skills ("team player") and technical claims ("built custom connection pool").
   - The extraction prompt must filter out non-technical fluff and only extract statements that make concrete architectural, algorithmic, or infrastructure assertions.
   - Categories: `architecture`, `scalability`, `performance`, `database`, `security`, `framework`, `infrastructure`.
2. **Dual Ingestion Paths (Raw Text & PDF)**:
   - Provide a clean endpoint supporting either JSON `{ "text": "..." }` or multipart form file upload (`file: UploadFile`).
   - Use `pypdf.PdfReader` with `io.BytesIO` to extract page text without touching the disk.
3. **Resilience & Deterministic Fallbacks**:
   - If LiteLLM or FreeLLMAPI is unreachable or rate-limited, provide a deterministic regex/heuristic fallback extracting bullet points with action verbs (e.g. `Architected`, `Designed`, `Implemented`, `Scaled`).
4. **File Structure & LOC Guardrails**:
   - `backend/app/schemas/claim.py`: ~80 LOC.
   - `backend/app/ai/claim_extractor.py`: ~160 LOC.
   - `backend/app/api/v1/claims.py`: ~130 LOC.
   - `backend/tests/test_claim_extraction.py`: ~180 LOC.
   - All files strictly $\le 300$ LOC.

---

## 6. Data Contracts & Interfaces

### 6.1 Pydantic Schemas (`backend/app/schemas/claim.py`)

```python
from enum import StrEnum
from pydantic import BaseModel, Field


class ClaimCategory(StrEnum):
    ARCHITECTURE = "architecture"
    SCALABILITY = "scalability"
    PERFORMANCE = "performance"
    DATABASE = "database"
    SECURITY = "security"
    FRAMEWORK = "framework"
    INFRASTRUCTURE = "infrastructure"


class TechnicalClaim(BaseModel):
    id: str = Field(description="Unique claim UUID")
    statement: str = Field(description="Concrete technical claim made by candidate")
    category: ClaimCategory = Field(description="Architectural or domain category")
    technologies: list[str] = Field(default_factory=list, description="Claimed tools/frameworks")
    verifiable: bool = Field(default=True, description="Whether claim can be verified in code")
    source_context: str = Field(default="", description="Original resume sentence/bullet")


class ClaimExtractionRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50000, description="Resume text content")


class ClaimExtractionResponse(BaseModel):
    claims: list[TechnicalClaim]
    total_claims: int
    source_char_count: int
    technologies_detected: list[str]
```

---

## 7. Target File Architecture

| Action | Path | Target LOC | Responsibilities |
| :--- | :--- | :---: | :--- |
| `[NEW]` | `backend/app/schemas/claim.py` | ~80 LOC | Pydantic v2 schemas for technical claims, categories, and extraction response. |
| `[NEW]` | `backend/app/ai/claim_extractor.py` | ~160 LOC | PDF text parser (`pypdf`), prompt template, LiteLLM synthesis & deterministic fallbacks. |
| `[NEW]` | `backend/app/api/v1/claims.py` | ~130 LOC | FastAPI router exposing `POST /api/v1/claims/extract` (JSON & PDF upload). |
| `[MODIFY]` | `backend/app/main.py` | ~80 LOC | Mount claims router under `/api/v1/claims`. |
| `[MODIFY]` | `backend/pyproject.toml` | ~68 LOC | Add `pypdf>=5.0.0` to dependencies. |
| `[NEW]` | `backend/tests/test_claim_extraction.py` | ~180 LOC | Hermetic unit & integration tests covering text & PDF extraction and fallbacks. |

---

## 8. Verification & Acceptance Criteria

### Automated Verification Commands
```bash
# 1. Backend static lint check
python -m ruff check backend/app backend/tests

# 2. Targeted claim extraction tests
python -m pytest backend/tests/test_claim_extraction.py -v

# 3. File length audit
(Get-Content backend/app/schemas/claim.py).Length
(Get-Content backend/app/ai/claim_extractor.py).Length
(Get-Content backend/app/api/v1/claims.py).Length
```

### Acceptance Checklist
- [ ] All files strictly $\le 300$ LOC.
- [ ] Pure static PDF text parsing via `pypdf` without disk leakage.
- [ ] Untrusted resume content safely isolated in `<resume_text>` XML boundaries.
- [ ] Technical claims categorized across architecture, database, security, and scalability.
- [ ] Deterministic fallback extracts action-oriented claims when LLM is unavailable.
- [ ] All unit and integration tests pass cleanly.
