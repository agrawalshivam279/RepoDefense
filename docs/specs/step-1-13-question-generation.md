# 📄 Technical Specification: Step 1.13 — Evidence-Grounded Question Generation Engine

> **Step ID**: `1.13`  
> **Target Module**: `backend/app/schemas/question.py`, `backend/app/ai/prompts.py`, `backend/app/ai/llm.py`, `backend/app/api/v1/questions.py`  
> **Git Feature Branch**: `feat/step-1-13-question-generation`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-11-03

---

## 1. Executive Summary

Per **Gemini.md** (Sections 2, 4, 5, 6) and **implementation_plan.md** (Milestone 1.13):
RepoDefense shifts technical hiring from generic algorithmic quizzes to authentic, repository-specific architectural defenses. Grounding every interaction in actual codebase evidence is the fundamental invariant of the platform.

Once a repository has been scanned, AST symbols extracted, dependencies resolved, architectural evidence classified, and vector embeddings generated (Milestones 1.5–1.12), the **Question Generation Engine** synthesizes these concrete facts into challenging, principal-engineer-level interview questions.

Instead of asking *"How would you design a caching layer in abstract?"*, RepoDefense asks:
> *"In `backend/app/workers/cloner.py`, your worker queries PostgreSQL on every git commit without an in-memory cache layer. If 1,000 repositories are enqueued simultaneously, how does your connection pool handle exhaustion, and how would you redesign the concurrency model?"*

Milestone 1.13 implements:
1. Pydantic schemas for categorized, evidence-cited questions.
2. Centralized system and user prompt templates in `backend/app/ai/prompts.py` enforcing the rigorous Principal Engineer persona with XML boundary isolation against prompt injection.
3. LiteLLM generator function in `backend/app/ai/llm.py` with retries, timeout handling, markdown stripping, and deterministic fallback generation.
4. FastAPI REST API endpoint `POST /api/v1/projects/{project_id}/questions` to generate and retrieve evidence-grounded questions for any evaluated project.
5. Hermetic unit and integration tests verifying question synthesis, evidence citation, and provider resilience.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - Milestone 1.10 (LiteLLM Client Wrapper & FreeLLMAPI Routing)
  - Milestone 1.11 (Architectural Evidence Items in `Evidence` model)
  - Milestone 1.12 (Vector Embeddings in `pgvector` & Code Chunks)
- **Blocked by**: None.
- **Tech Stack Invariant**:
  - LiteLLM with local FreeLLMAPI gateway (`http://127.0.0.1:31415/v1`) or configured cloud providers.
  - Pydantic v2 schemas for structured extraction.
  - Zero arbitrary code execution — only code snippets and metadata are passed to LLM prompts.

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Repository code chunks and AST symbols are statically analyzed text; never executed or dynamically evaluated.
- [x] **Evidence Grounding Invariant**: Every generated question must explicitly cite at least one `Evidence` record ID, file path, and relevant line range/symbol. Free-form hallucinated questions lacking evidence citations are rejected.
- [x] **Prompt Injection Defense**: Repository evidence titles, file contents, and symbol signatures are wrapped in XML tags (`<evidence_catalog>`, `<evidence_item>`) and sanitized against delimiter breakouts.
- [x] **Deterministic Fallback**: If FreeLLMAPI is offline or times out, the engine deterministically generates categorized architectural questions directly from the project's top `Evidence` items, ensuring the interview pipeline never blocks.
- [x] **Parameterized SQL**: Database reads for `Project` and `Evidence` use SQLAlchemy 2.0 async sessions with parameterized ORM statements.

---

## 4. 🧠 Sequential Thinking Strategy

1. **Question Categorization Distribution**:
   - Technical interviews assess multiple dimensions of engineering maturity.
   - Questions should be categorized across 5 distinct domains:
     - `architecture`: High-level system topology, module coupling, and framework decisions.
     - `scalability`: Concurrency, caching, database indexing, and traffic bottlenecks.
     - `reliability`: Error handling, transaction boundaries, timeouts, and failure recovery.
     - `security`: Authentication, authorization, untrusted input sanitization, and secret protection.
     - `tradeoffs`: Alternative libraries, design patterns considered, and legacy constraints.
2. **Context Selection & Token Management**:
   - A repository may contain dozens of `Evidence` items. Passing all evidence simultaneously can exceed prompt token budgets and dilute focus.
   - *Strategy*: Deterministically select the top 6-10 load-bearing evidence items (prioritizing framework, database, auth, queue, and endpoints), passing concise code references to the prompt.
3. **Structured JSON Validation**:
   - Enforce an exact schema containing a list of `GroundedQuestion` objects, each with `id`, `category`, `question_text`, `context_hint`, and `cited_evidence_ids`.

---

## 5. Data Contracts & Interfaces

### 5.1 Pydantic Schemas (`backend/app/schemas/question.py`)

```python
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class QuestionCategory(str, Enum):
    ARCHITECTURE = "architecture"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    SECURITY = "security"
    TRADEOFFS = "tradeoffs"


class GroundedQuestion(BaseModel):
    """An evidence-grounded interview question generated for a specific codebase."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique question identifier")
    category: QuestionCategory = Field(..., description="Architectural domain of the question")
    question_text: str = Field(..., description="The direct question posed to the candidate")
    context_hint: str = Field(..., description="Factual repository context anchoring the question")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="IDs of cited Evidence records")
    cited_files: List[str] = Field(default_factory=list, description="Repository file paths referenced")

    model_config = ConfigDict(extra="ignore")


class QuestionGenerationInput(BaseModel):
    """Consolidated input passed to LiteLLM for question generation."""

    project_name: str
    summary_narrative: Optional[str] = None
    architectural_style: Optional[str] = None
    evidence_items: List[dict] = Field(default_factory=list)
    requested_count: int = Field(default=3, ge=1, le=10)


class QuestionGenerationResponse(BaseModel):
    """API response model for generated questions."""

    project_id: uuid.UUID
    project_name: str
    questions: List[GroundedQuestion]
    total_generated: int
    grounded_evidence_count: int
```

### 5.2 LiteLLM Generator (`backend/app/ai/llm.py`)

```python
async def generate_grounded_questions(
    input_data: QuestionGenerationInput,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> List[GroundedQuestion]:
    """Invokes LiteLLM with Principal Engineer persona to synthesize grounded questions."""
```

### 5.3 FastAPI Router (`backend/app/api/v1/questions.py`)

- `POST /api/v1/projects/{project_id}/questions`: Queries `Project` and `Evidence` records from DB, formats `QuestionGenerationInput`, synthesizes questions via `generate_grounded_questions`, and returns `QuestionGenerationResponse`.

---

## 6. Step-by-Step Implementation Sequence

1. **Step 1: Define Question Schemas**
   - Create `backend/app/schemas/question.py` with `QuestionCategory`, `GroundedQuestion`, `QuestionGenerationInput`, `QuestionGenerationResponse`.
   - Re-export in `backend/app/schemas/__init__.py`.

2. **Step 2: Add Question Generation Prompts**
   - Update `backend/app/ai/prompts.py` with `QUESTION_GENERATION_SYSTEM_PROMPT` and `format_question_generation_user_prompt`.

3. **Step 3: Implement Generator Function in `app/ai/llm.py`**
   - Add `build_deterministic_fallback_questions(input_data) -> List[GroundedQuestion]`.
   - Add `generate_grounded_questions(input_data, ...) -> List[GroundedQuestion]`.
   - Re-export in `backend/app/ai/__init__.py`.

4. **Step 4: Create FastAPI Questions API Router**
   - Create `backend/app/api/v1/questions.py` exposing `POST /api/v1/projects/{project_id}/questions`.
   - Register router in `backend/app/main.py`.

5. **Step 5: Author Hermetic Tests**
   - Create `backend/tests/test_question_generation.py` testing schemas, prompts, mock completions, fallback generation, and API router.
   - Run tests and verify 100% pass!
   - Run `ruff` check and verify zero lint errors!

---

## 7. Verification & Acceptance Criteria

### Automated Tests
```bash
python -m pytest backend/tests/test_question_generation.py -v
```

### Acceptance Checklist
- [ ] All new and modified files strictly $\le 300$ LOC.
- [ ] Generated questions always cite real file paths and evidence IDs.
- [ ] Fallback questions work seamlessly when API key is empty or remote service is unreachable.
- [ ] Working tree clean, zero lint errors with `ruff`.
- [ ] API endpoint `POST /api/v1/projects/{id}/questions` returns valid HTTP 200 with structured response.
