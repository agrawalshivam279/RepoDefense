# 📄 Technical Specification: Step 1.10 — LiteLLM Wrapper & AI Project Summary Generator

> **Step ID**: `1.10`  
> **Target Module**: `backend/app/ai/`, `backend/app/schemas/`, `backend/app/core/`, `backend/app/workers/`  
> **Git Feature Branch**: `feat/step-1-10-llm-project-summary`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-11-03

---

## 1. Executive Summary

Per **Gemini.md** (Sections 3, 4, 6, 8, 9) and **implementation_plan.md** (Milestone 1.10):
RepoDefense grounds technical interview defense in code evidence. Once a repository is cloned, sanitized, and statically inspected (files scanned, AST symbols extracted, manifest dependencies resolved, git commit history parsed, architectural evidence classified, and vector embeddings generated), the system synthesizes these disparate facts into a coherent, high-level **AI Project Summary**.

This summary provides:
1. High-level architectural narrative: What the application is, its core design paradigm (e.g., modular monolith, event-driven, microservices), and detected frameworks.
2. Load-bearing component map: Critical services, data stores, background queues, and authentication boundaries.
3. Candidate defense topics: Identified architectural stress points and trade-offs to seed future interview questions in the State Machine (Milestone 1.13 & 1.14).

Milestone 1.10 implements the foundational LiteLLM abstraction layer using `FreeLLMAPI` (OpenAI-compatible) as the primary provider, structured Pydantic response models, a prompt template engine in `app/ai/prompts.py`, resilient async execution with retries and timeouts, and integration into the ARQ clone background worker pipeline (`app/workers/cloner.py`).

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - Milestone 1.6 (File Scanning & Language Distribution)
  - Milestone 1.7 (Tree-sitter AST Symbol Extraction)
  - Milestone 1.8 (Dependency & Infrastructure Manifest Parsers)
  - Milestone 1.9 (Git History & Contributor Analytics)
  - Milestone 1.11 (Architectural Evidence Records)
- **Blocked by**: None. FreeLLMAPI key is configured in local environment.
- **Tech Stack Invariant**:
  - LiteLLM (`litellm>=1.40.0`) for OpenAI-compatible LLM routing.
  - Strict Pydantic v2 schemas for structured output extraction.
  - Zero arbitrary code execution — prompt inputs are strictly sanitized code metadata strings, never evaluated or executed.

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Only metadata (file counts, language breakdown, top dependencies, architectural evidence tags, contributor stats) and bounded code symbol signatures are passed to the prompt.
- [x] **Prompt Injection Defense & Boundary Isolation**: Repository metadata (commit messages, symbol names) are escaped and enclosed in strict XML delimiter tags (`<repository_metadata>`, `<dependencies>`, `<evidence>`) to neutralize prompt injection from untrusted repo content.
- [x] **Graceful Degradation & Timeout Circuit Breaker**: The LLM call is wrapped in a hard timeout (`30.0s`) and bounded retries. If the LLM provider is unavailable, rate-limited, or returns malformed output, the system falls back to a deterministic structured summary without crashing the ARQ clone worker.
- [x] **Parameterized SQL**: All database operations use SQLAlchemy 2.0 async sessions without raw SQL string concatenation.

---

## 4. 🧠 Sequential Thinking Strategy

1. **Structured Output Reliability across Providers**:
   - FreeLLMAPI / OpenAI-compatible proxies may or may not support native `response_format={"type": "json_object"}` or function calling depending on the underlying model routing.
   - *Design Choice*: Request JSON directly in the system prompt instructions with an exact schema representation, and use Pydantic `model_validate_json()` with markdown JSON codeblock stripping (````json ... ````) for universal provider compatibility.
2. **Context Window Token Budgeting**:
   - Repositories can have thousands of files and dependencies. Passing entire symbol lists or commit trees would blow the token budget and cause latency spikes.
   - *Design Choice*: Deterministically aggregate top languages, top 25 runtime dependencies, top 20 evidence tags, and top 3 contributors into a compact metadata summary (~500–800 tokens), leaving plenty of context room.
3. **Storage Format**:
   - `RepositorySnapshot.summary` in PostgreSQL is a `Text` column. Storing the Pydantic-validated JSON string allows rich querying, frontend rendering, and backward compatibility.

---

## 5. Data Contracts & Interfaces

### 5.1 Pydantic Schemas (`backend/app/schemas/summary.py`)

```python
from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectSummary(BaseModel):
    """Structured architectural overview of a repository synthesized by AI."""

    title: str = Field(..., description="Concise descriptive title of the system")
    tagline: str = Field(..., description="One-line elevator pitch explaining what the repository does")
    primary_language: str = Field(..., description="Dominant language of the codebase")
    detected_frameworks: List[str] = Field(
        default_factory=list, description="Primary web frameworks and libraries identified"
    )
    architectural_style: str = Field(
        ..., description="Architectural paradigm (e.g. Modular Monolith, Microservices, SPA + API, CLI Tool)"
    )
    key_components: List[str] = Field(
        default_factory=list, description="Key functional components or modules identified"
    )
    potential_defense_topics: List[str] = Field(
        default_factory=list, description="Architectural trade-offs or stress points for defense sessions"
    )
    narrative: str = Field(
        ..., description="2-3 paragraph deep-dive architectural narrative grounded in code evidence"
    )


class ProjectSummaryInput(BaseModel):
    """Consolidated repository metadata fed into the summary generation prompt."""

    project_name: str
    commit_hash: str
    total_files: int
    total_lines: int
    top_languages: List[str]
    dependencies: List[str]
    evidence_tags: List[str]
    top_contributors: List[str]
```

### 5.2 Settings Extension (`backend/app/core/config.py`)

```python
FREELLMAPI_BASE_URL: str = Field(
    default="https://api.freellmapi.com/v1",
    description="FreeLLMAPI or OpenAI-compatible base URL",
)
FREELLMAPI_API_KEY: str = Field(
    default="",
    description="API key for FreeLLMAPI / OpenAI-compatible endpoint",
)
LLM_MODEL: str = Field(
    default="openai/gpt-4o-mini",
    description="LiteLLM model identifier",
)
LLM_TIMEOUT_SECONDS: float = Field(
    default=30.0,
    description="Timeout in seconds for LLM generation requests",
)
LLM_MAX_RETRIES: int = Field(
    default=2,
    description="Maximum retry attempts on transient LLM failures",
)
```

### 5.3 LiteLLM Client & Generator (`backend/app/ai/llm.py`)

```python
async def generate_project_summary(
    meta: ProjectSummaryInput,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ProjectSummary:
    """Invokes LiteLLM to generate a grounded, structured ProjectSummary with retries and fallback."""
```

### 5.4 Centralized Prompt Templates (`backend/app/ai/prompts.py`)

- `PROJECT_SUMMARY_SYSTEM_PROMPT`: Directs the AI to act as a Principal Software Engineer analyzing a codebase, enforcing strict JSON conforming to `ProjectSummary` schema, grounded in the provided metadata.
- `format_project_summary_user_prompt(meta: ProjectSummaryInput) -> str`: Renders XML-isolated metadata inputs.

---

## 6. Step-by-Step Implementation Sequence

1. **Step 1: Declare Dependencies & Update Config**
   - Add `litellm>=1.40.0` to `backend/pyproject.toml`.
   - Update `backend/app/core/config.py` with `FREELLMAPI_BASE_URL`, `FREELLMAPI_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`.

2. **Step 2: Define Pydantic Summary Schemas**
   - Create `backend/app/schemas/summary.py` defining `ProjectSummary` and `ProjectSummaryInput`.
   - Re-export in `backend/app/schemas/__init__.py`.

3. **Step 3: Centralized Prompt Templates**
   - Create `backend/app/ai/prompts.py` with system and user prompts adhering to the Principal Engineer persona and grounding invariants.

4. **Step 4: LiteLLM Async Wrapper & Client**
   - Create `backend/app/ai/llm.py` implementing `generate_project_summary` with exponential backoff, timeout handling, markdown JSON cleaning, and deterministic fallback generation.
   - Create `backend/app/ai/__init__.py` exposing the client.

5. **Step 5: Worker Pipeline Integration**
   - Update `backend/app/workers/cloner.py` to extract `ProjectSummaryInput` from scanned files, dependencies, evidence, and git history, invoke `generate_project_summary`, and save the result as formatted JSON to `RepositorySnapshot.summary`.

6. **Step 6: Unit & Integration Tests**
   - Author hermetic tests in `backend/tests/test_llm_summary.py` testing:
     - Prompt formatting & XML boundary escaping.
     - Pydantic validation and markdown JSON extraction.
     - LiteLLM completion mocking (success & transient failure retry).
     - Fallback summary generation when LLM is unavailable.
     - Snapshot summary persistence in worker workflow.

---

## 7. Verification & Acceptance Criteria

### Automated Tests
```bash
python -m pytest backend/tests/test_llm_summary.py -v
```

### Acceptance Checklist
- [ ] All new files adhere to the strict $\le 300$ LOC limit.
- [ ] LiteLLM client passes all mock tests with 100% reliability.
- [ ] Fallback summary operates without errors when API key is empty or remote service is unreachable.
- [ ] Snapshot summary stores valid JSON adhering to `ProjectSummary`.
- [ ] Working tree remains clean and linted with `ruff`.
