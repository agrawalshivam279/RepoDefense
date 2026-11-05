# 📄 Technical Specification: Backend Claim-Evidence Verification Engine, LiteLLM Grounding & REST API

> **Step ID**: `Step 2.2a`  
> **Target Module**: `backend/app/...`  
> **Git Feature Branch**: `feat/step-2-2a-claim-verification-engine`  
> **Status**: 📋 In Progress / Implementation Approved  
> **Created**: 2026-11-05  

---

## 1. Executive Summary

Step 2.2a implements the core differentiating verification engine of **RepoDefense**: mapping candidate resume technical claims directly against real codebase truth extracted during Phase 1. 

Candidates frequently make unverified assertions on resumes (e.g., *"Engineered high-throughput event processing with Apache Kafka"*, *"Implemented Redis distributed caching with LRU eviction"*). Step 2.2a establishes the deterministic and semantic retrieval pipeline:
1. Embeds the candidate claim statement with the local `all-MiniLM-L6-v2` embedding generator (producing a 384-dimensional query vector).
2. Performs cosine similarity retrieval (`<=>`) on `code_embeddings` joined with `analyzed_files` and `repository_snapshots` in PostgreSQL 17 / pgvector.
3. Cross-references extracted architectural `Evidence` (frameworks, database, auth, endpoints, infra) and `Dependency` records.
4. Synthesizes this ground truth into `<claim>` and `<codebase_evidence>` XML boundaries and queries LiteLLM using a specialized Principal Engineer prompt (`CLAIM_VERIFICATION_SYSTEM_PROMPT`).
5. Generates structured verification results classifying each claim as `SUPPORTED`, `CONTRADICTED`, or `UNVERIFIABLE`, complete with confidence scoring, evidence citations, rationale, and targeted follow-up defense interview questions.
6. Provides an offline deterministic heuristic fallback when LiteLLM is unavailable.
7. Exposes `POST /api/v1/projects/{project_id}/claims/verify` with multi-tenant isolation and user ownership verification.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Step 2.1a` (`app/schemas/claim.py`, `app/ai/claim_extractor.py`, `app/api/v1/claims.py`).
  - `Step 1.12b` (`app/analyzers/embeddings.py`, `retrieve_relevant_chunks`, `all-MiniLM-L6-v2` sentence-transformers).
  - `Step 1.11` (`app/models/analysis.py` - `Evidence`, `CodeEmbedding`, `Dependency`, `AnalyzedFile`).
  - `app/ai/llm.py` (LiteLLM client wrapper with structured JSON extraction and retries).
- **Blocked by**: None.
- **Tech Stack Invariant**:
  - Python 3.12+ / FastAPI / SQLAlchemy 2.0 Async / pgvector / LiteLLM / Pydantic v2.
  - Local embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`), zero external embedding API cost.
  - Strict compliance with `Gemini.md` architecture and file length limits ($\le 300$ LOC per file).

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Static analysis only. Code chunks and claims are strictly analyzed as text data; never compiled, run, or evaluated.
- [x] **Prompt Injection Defense**: Untrusted claims and code chunks are sanitized and wrapped in strict `<claim>` and `<codebase_evidence>` XML delimiters with explicit instructions to ignore injected system instructions.
- [x] **Parameterized SQL**: All database queries use SQLAlchemy 2.0 ORM statements with parameterized values (`select(...)`), completely preventing SQL injection.
- [x] **Multi-Tenant Ownership Isolation**: API enforces `current_user` verification against `Project.user_id`, preventing unauthorized cross-tenant verification requests.
- [x] **Input Quota Limits**: Max 25 claims per request, claim statement max length 2,000 characters, top_k bounded between 1 and 15 chunks.

---

## 4. 🧭 Specialized Skills Directive

| Specialized Skill | Scope of Impact & Mandate | Verification Requirement |
| :--- | :--- | :--- |
| **[`eval_rag`](file:///d:/RepoDefense/.agents/skills/eval_rag/SKILL.md)** | Audits RAG retrieval accuracy and citation traceability. Asserts that claim embedding queries match relevant code chunks via pgvector cosine distance (`<=>`), and that citations include `file_path`, line numbers, and similarity scores. | Validates that `retrieve_relevant_chunks` executes efficiently, uses normalized 384-dim vectors, and handles empty chunk tables gracefully. |
| **[`eval_persona`](file:///d:/RepoDefense/.agents/skills/eval_persona/SKILL.md)** | Audits `CLAIM_VERIFICATION_SYSTEM_PROMPT` to enforce rigorous Principal Engineer tone. Ensures classification objectively categorizes claims as `SUPPORTED`, `CONTRADICTED`, or `UNVERIFIABLE`. | Asserts zero hallucinated citations, strict adherence to Pydantic v2 schema, and incisive suggested defense questions. |
| **[`security_auditor`](file:///d:/RepoDefense/.agents/skills/security_auditor/SKILL.md)** | Audits XML boundary isolation on untrusted user claims and code chunks to prevent prompt injection, ReDoS, and unauthorized project data leakage. | Verifies `_sanitize_meta_str` tag stripping, tenant isolation on `project_id`, and payload size validation. |

---

## 5. 🧠 Sequential Thinking Strategy

1. **Evidence Multi-Source Triangulation**:
   - A claim like *"Implemented JWT authentication middleware with refresh tokens"* can be grounded across three distinct data sources:
     - **Semantic Code Chunks (`CodeEmbedding`)**: pgvector cosine search finds middleware methods, token handlers, and verification logic.
     - **Architectural Evidence (`Evidence`)**: Rules engine detected "auth" type evidence (e.g. `middleware.ts`, `auth.py`).
     - **Dependencies (`Dependency`)**: Presence of `jsonwebtoken`, `pyjwt`, `python-jose`.
   - Combining these 3 sources gives the Principal Engineer persona bulletproof factual grounding.
2. **Three-State Verdict Rubric**:
   - `SUPPORTED`: Direct codebase evidence (semantic chunks + dependencies) confirms candidate built or used this technology/pattern. Confidence: 0.70 - 1.00.
   - `CONTRADICTED`: Codebase exhibits direct contrary evidence (e.g., claims Redis caching for session store, but code explicitly uses in-memory global dict or un-cached raw DB queries; claims GraphQL, but only REST endpoints exist). Confidence: 0.65 - 1.00.
   - `UNVERIFIABLE`: Neither positive code proof nor direct contradiction exists (e.g., claims cloud DevOps metrics like "reduced AWS bill by 30%", or files not present in cloned repository snapshot). Confidence: 0.50 - 0.90.
3. **Resilience & Deterministic Heuristic Fallback**:
   - If LiteLLM or FreeLLMAPI is offline, times out, or throws an error:
     - Check semantic chunks: if top chunk similarity $\ge 0.65$ and claimed technologies exist in chunks/dependencies $\rightarrow$ `SUPPORTED`.
     - Check dependencies: if claimed technologies are explicitly contradictory $\rightarrow$ `CONTRADICTED`.
     - Otherwise $\rightarrow$ `UNVERIFIABLE`.
     - Never fail the HTTP request with a 500 when offline; return valid deterministic structured evaluations.
4. **Modularity & LOC Guardrails**:
   - `backend/app/schemas/claim_verification.py`: ~95 LOC.
   - `backend/app/ai/prompts.py`: +35 LOC (total ~260 LOC, strictly $\le 300$).
   - `backend/app/ai/claim_verifier.py`: ~220 LOC.
   - `backend/app/api/v1/claims.py`: +55 LOC (total ~170 LOC, strictly $\le 300$).
   - `backend/tests/test_claim_verification.py`: ~230 LOC.

---

## 6. Data Contracts & Interfaces

### 6.1 Pydantic Schemas (`backend/app/schemas/claim_verification.py`)

```python
from enum import StrEnum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.claim import TechnicalClaim

class VerificationStatus(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNVERIFIABLE = "unverifiable"

class EvidenceCitation(BaseModel):
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    symbol_name: Optional[str] = None
    snippet: str
    relevance_score: float
    source_type: str = "code_chunk"

class ClaimVerificationResult(BaseModel):
    claim_id: str
    statement: str
    status: VerificationStatus
    confidence_score: float
    reasoning: str
    citations: List[EvidenceCitation] = Field(default_factory=list)
    suggested_defense_questions: List[str] = Field(default_factory=list)

class ClaimVerificationRequest(BaseModel):
    claims: List[TechnicalClaim] = Field(..., min_length=1, max_length=25)
    top_k_chunks: int = Field(default=5, ge=1, le=15)
    min_similarity_threshold: float = Field(default=0.40, ge=0.0, le=1.0)

class BatchClaimVerificationResponse(BaseModel):
    project_id: uuid.UUID
    total_claims: int
    verified_claims: List[ClaimVerificationResult]
    summary_counts: dict[str, int]
```

---

## 7. Quality Gates & Acceptance Criteria

- [ ] **Stage 0: Lint & Types**: `ruff check` passes with 0 errors, `mypy` / python imports resolve cleanly.
- [ ] **Stage 0.5: Specialized Domain Skill Contract Verification**:
  - `eval_rag`: pgvector cosine search and embedding generation run hermetically.
  - `eval_persona`: `CLAIM_VERIFICATION_SYSTEM_PROMPT` enforces strict schema and Principal Engineer tone.
  - `security_auditor`: Zero code execution, parameterized SQL, XML delimiter sanitization, tenant isolation.
- [ ] **Stage 1: Hermetic Test Suite**: `pytest` passes with 100% assertions covering single and batch verification, supported, contradicted, unverifiable states, offline fallbacks, and API route security.
- [ ] **Stage 2: Static Code Review & LOC Audit**: All modified and created files strictly $\le 300$ LOC.
