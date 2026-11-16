# 📋 Technical Specification: Step 4.2a — Backend Mentor Engine, Schemas, Teaching Content Synthesizer & REST API

> **Step ID**: `step-4-2a`  
> **Milestone**: 4.2 (Mentor Mode — Teaching Content)  
> **Phase**: Phase 4 — Learning Loop & Weakness Tracking  
> **Status**: Ready for Implementation  
> **Git Feature Branch**: `feat/step-4-2a-mentor-teaching-content`  

---

## 1. Executive Summary & Objective

In **Milestone 4.1**, we established persistent candidate technical skills and weakness tracking (`user_skills` and `candidate_weaknesses` tables, `WeaknessTrackerService`, and the `/api/v1/skills` API).

In **Step 4.2a**, we initiate **Milestone 4.2 (Mentor Mode — Teaching Content)**. When a candidate encounters an architectural blind spot or fails a defense challenge (or accesses a recorded weakness), Mentor Mode shifts the tone from adversarial interrogation to **constructive, Socratic principal engineering mentorship**:
1. **Explain the Root Cause / Architectural Risk**: Articulate why the candidate's approach or omission introduces production hazards (e.g. connection pool exhaustion, race conditions, missing idempotency keys, unhandled network partitions, or cascading timeouts).
2. **Teach Core Design Principles**: Ground the explanation in production design patterns (e.g., Leaky Bucket rate limiting, Optimistic Concurrency Control, Transactional Outbox, Cache-Aside with TTL jitter).
3. **Synthesize Drop-in Code Remediation**: Generate concrete Before-and-After code blocks illustrating the anti-pattern vs. the hardened implementation, with realistic file paths and annotations.
4. **Deliver Socratic Follow-Up**: Provide targeted key takeaways and an architectural challenge question preparing the candidate for re-testing.

---

## 2. Specialized Domain Skills Directive

| Skill | Required Verification Checks |
| :--- | :--- |
| **`eval_persona`** | Ensure the mentor prompt strictly embodies the "Constructive Principal Engineer & Socratic Mentor" persona. It must avoid generic boilerplate, cite exact architectural mechanics, wrap untrusted candidate inputs in XML boundary delimiters (`<weakness_context>`, `<candidate_response>`, `<code_context>`), and output structured JSON matching the Pydantic schema. |
| **`security_auditor`** | Enforce multi-tenant authorization: when fetching a `CandidateWeakness` by `weakness_id`, verify `weakness.user_id == current_user.id` (return HTTP 404 for unauthorized IDs to prevent IDOR). Ensure zero arbitrary code execution: all before/after code snippets are purely educational static strings and never compiled or executed. |

---

## 3. Target Files & LOC Budgets

All touched and newly authored files must strictly comply with the **$\le 300$ LOC** project invariant:

| Target File | Role | Expected LOC | Budget Limit |
| :--- | :--- | :--- | :--- |
| `backend/app/schemas/mentor.py` | Pydantic v2 Contracts for Mentor Requests & Responses | ~140 LOC | $\le 300$ LOC |
| `backend/app/ai/mentor_generator.py` | LiteLLM Prompt Orchestrator & Deterministic Fallbacks | ~240 LOC | $\le 300$ LOC |
| `backend/app/api/v1/mentor.py` | FastAPI REST Router for Mentor Mode Endpoints | ~180 LOC | $\le 300$ LOC |
| `backend/app/main.py` | Mount `mentor_router` under `/api/v1/mentor` | ~105 LOC | $\le 300$ LOC |
| `backend/app/schemas/__init__.py` | Export new mentor schema symbols | ~50 LOC | $\le 300$ LOC |
| `backend/tests/test_mentor.py` | Hermetic Unit and Endpoint Contract Tests | ~260 LOC | $\le 300$ LOC |

---

## 4. Architectural Design & API Contracts

### 4.1 Schemas (`backend/app/schemas/mentor.py`)

- `CodeRemediationSnippet`:
  - `title: str`
  - `language: str = "python"`
  - `file_context: Optional[str] = None`
  - `before_code: str` (The flawed or vulnerable pattern)
  - `after_code: str` (The hardened, production-grade remediation)
  - `explanation: str` (Why this transformation resolves the risk)
- `MentorExplanationRequest`:
  - `weakness_id: Optional[UUID] = None` (If supplied, loads context from `candidate_weaknesses`)
  - `category: Optional[SkillCategory] = None`
  - `topic: Optional[str] = None`
  - `question_prompt: Optional[str] = None`
  - `candidate_response: Optional[str] = None`
  - `feedback: Optional[str] = None`
  - `code_context: Optional[str] = None`
  - `language: Optional[str] = "python"`
  - Optional LLM overrides: `model: Optional[str]`, `llm_base_url: Optional[str]`, `llm_api_key: Optional[str]`
- `MentorExplanationResponse`:
  - `explanation_id: UUID`
  - `category: str`
  - `topic: str`
  - `architectural_risk: str`
  - `core_concept: str`
  - `mentor_advice: str`
  - `code_examples: List[CodeRemediationSnippet]`
  - `key_takeaways: List[str]`
  - `socratic_followup: str`
  - `generated_at: datetime`

### 4.2 Mentor AI Generator (`backend/app/ai/mentor_generator.py`)

- **Persona**: Constructive Principal Software Architect & Socratic Mentor.
- **XML Context Delimiters**:
  `<weakness_context category="..." topic="...">`
  `<candidate_response>...</candidate_response>`
  `<code_context>...</code_context>`
- **Deterministic Offline Fallbacks**:
  - Provides tailored educational blueprints for canonical topics:
    - Concurrency & Race Conditions (Optimistic Concurrency / distributed locking)
    - Database Connection Exhaustion (Connection pool sizing & session lifecycle)
    - Cache Stampede / Invalidation (Cache-Aside with probabilistic early expiration)
    - Scalability & Rate Limiting (Token Bucket / Sliding Window)
    - Reliability & Circuit Breaker (Timeout, retry with exponential backoff & jitter)
    - Architecture & Decoupling (Event-driven transactional outbox)
  - Produces complete, syntactically valid before/after code blocks and Socratic follow-ups.

### 4.3 REST API Router (`backend/app/api/v1/mentor.py`)

- `POST /api/v1/mentor/explain`:
  - Authenticated via Supabase JWT Bearer Token (`current_user`).
  - If `weakness_id` is supplied: queries DB for `CandidateWeakness`, checks `weakness.user_id == current_user.id`, raises 404 if missing/unauthorized.
  - Generates mentor explanation via `generate_mentor_explanation(...)`.
- `GET /api/v1/mentor/explanations/{weakness_id}`:
  - Authenticated via Supabase JWT Bearer Token (`current_user`).
  - Fetches the weakness, validates user ownership, synthesizes the mentor explanation.

---

## 5. Security & Invariant Invariants

1. **Zero Code Execution**: Code examples are static illustrative string blocks; under no circumstance are they executed, compiled, or evaluated.
2. **Multi-Tenant Isolation**: Weaknesses are strictly checked against `current_user.id`. No cross-user disclosure or IDOR.
3. **SSRF Guard**: LLM `base_url` overrides are validated against `ALLOWED_LLM_BASE_HOSTS` or HTTPS scheme via `validate_llm_base_url`.
4. **File Length**: Strict $\le 300$ LOC limit per file.

---

## 6. Test Strategy & Acceptance Criteria

1. **Unit Tests**:
   - `test_mentor_generator_deterministic_fallback`: Test fallback generates valid before/after code snippets and structured response.
   - `test_mentor_generator_with_mock_litellm`: Mock LiteLLM call and verify structured schema parsing.
2. **API Endpoint Tests**:
   - `test_post_explain_with_inline_payload`: Generates explanation successfully.
   - `test_post_explain_with_weakness_id`: Loads from DB and synthesizes explanation.
   - `test_get_explain_weakness_idor_prevention`: Ensures user B cannot access user A's weakness (returns HTTP 404).
   - `test_explain_invalid_payload`: Returns HTTP 422 if neither weakness_id nor minimal topic/category provided.
3. **Quality Gates**:
   - `ruff check backend/app backend/tests` passes with 0 errors.
   - `pytest backend/tests/test_mentor.py` passes 100%.
   - Every file strictly $\le 300$ LOC.
