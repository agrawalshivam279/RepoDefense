# Technical Specification: Step 3.6a — Backend Architecture Defense Mode (Diagram-Grounded Interrogation & REST API)

- **Feature Slug**: `step-3-6a-arch-defense-backend`
- **Branch**: `feat/step-3-6a-arch-defense-backend`
- **Target Phase**: Phase 3 — The State Machine (Milestone 3.6: Architecture Defense Mode, Sub-slice 3.6a)
- **Date**: 2026-11-12
- **Status**: Implemented & Verified

---

## 1. Objective & Scope

### Objective
Implement the backend **Architecture Defense Mode** engine (`Step 3.6a`), enabling RepoDefense to interrogate high-level system design decisions grounded directly in a repository's detected architectural patterns, identified architectural risks (Milestone 2.8), and generated Mermaid architecture diagrams (Milestone 2.9).

### Sub-Slicing Rationale (5-Gate Goldilocks Standard)
Milestone 3.6 spans full-stack backend interrogation logic and an interactive diagram-plus-chat Next.js 15 UI. Sub-slicing into **Step 3.6a (Backend Engine & REST API)** and **Step 3.6b (Next.js 15 Architecture Defense UI)** keeps this step scoped to a single architectural boundary (`4` backend production files + `1` dedicated test suite, each strictly `<= 300 LOC`, single targeted pytest verification command, `>= 40%` context headroom).

### Scope (In-Scope for Step 3.6a)
1. **Pydantic Data Contracts (`backend/app/schemas/arch_defense.py`)**: Schemas for architectural focus areas (`PATTERN_CHOICE`, `COMPONENT_BOUNDARY`, `DATA_FLOW_COUPLING`, `ARCHITECTURAL_RISK`), diagram targets (`DiagramTarget`), interrogation topics (`ArchDefenseTopic`), session state machine stages (`TOPIC_ACTIVE`, `TRADEOFF_CHALLENGE`, `COMPLETED`), structured evaluator output (`ArchDefenseEvaluationOutput`), and safe `_LLMOverrideBase` request DTOs.
2. **AI Interrogation & Evaluation Engine (`backend/app/ai/arch_defense_generator.py`)**:
   - Topic synthesis strictly grounded in `ArchitectureReportResponse` (patterns + risks) and `DiagramResponse` (`nodes`, `edges`, `mermaid_code`), with a deterministic offline fallback generator.
   - Multi-turn Principal Architect evaluation function with a deterministic keyword/concept fallback rubric when LLM credentials are omitted or unreachable.
3. **FastAPI REST Router (`backend/app/api/v1/arch_defense.py`) & Mount (`backend/app/main.py`)**:
   - Endpoints under `/api/v1/arch-defense` to synthesize diagram-grounded defense topics, launch active defense sessions, inspect session state, and submit candidate defenses across the FSM stages.
4. **Hermetic Test Suite (`backend/tests/test_arch_defense.py`)**:
   - Full unit & async HTTP endpoint tests covering deterministic topic synthesis, LLM structured synthesis/fallback, multi-stage FSM transitions (`TOPIC_ACTIVE -> TRADEOFF_CHALLENGE -> COMPLETED`), SSRF/credential leakage blocks, ownership IDOR enforcement (`404`), and topic cache fingerprinting/invalidation.

### Out of Scope (Deferred to Step 3.6b)
- Next.js 15 TypeScript clients, interactive Mermaid diagram click/highlight defense viewer, and multi-turn architecture defense chat components (`Step 3.6b`).

---

## 2. Architecture & Design Alignment

- **GEMINI.md Adherence**:
  - **Modular Monolith & Reuse**: Directly calls `detect_repository_architecture(project, db)` (`app/services/architecture.py`) and `generate_project_architecture_diagram(project, db, ...)` (`app/services/diagram.py`) instead of duplicating SQL queries, AST tokenizers, or Mermaid generators.
  - **Evidence Over Hallucination**: Every `ArchDefenseTopic` explicitly references real `DiagramNode.node_id`s, `DiagramEdge` relationships, `DetectedPattern.pattern_name`, or `ArchitecturalRisk` findings from static analysis.
  - **Rigid Deterministic State Machine**: Enforces deterministic transitions (`TOPIC_ACTIVE -> TRADEOFF_CHALLENGE -> COMPLETED`) in FastAPI controller logic, delegating only narrow topic synthesis and response grading to LiteLLM structured outputs.
  - **Canonical Stack**: FastAPI (Python 3.12+), SQLAlchemy 2.0 Async, Pydantic v2, LiteLLM (`litellm.acompletion`) with FreeLLMAPI default & deterministic offline fallback, `structlog`.
- **Specialized Domain Skills Consulted**:
  - `eval_persona`: Principal Architect tone calibration, strict adherence to `<architecture_context>` / `<diagram_mermaid>` evidence, balanced rubric (`depth_score`, `pattern_rationale_solid`, `tradeoffs_articulated`, `boundary_coherence_score`), explicit prompt/context size caps.
  - `security_auditor`: Zero code execution invariant, SSRF allowlist on `base_url`, API key isolation when caller overrides `base_url`, delimiter sandboxing against prompt injection, and strict session/project ownership authorization.

---

## 3. Security, Grounding & Invariants Impact

1. **Zero Arbitrary Code Execution**: Relies 100% on pre-computed static analysis (`ArchitectureReportResponse` + `DiagramResponse`) and text analysis. Never uses `eval()`, `exec()`, subprocesses, or container runs.
2. **SSRF & Secret Exfiltration Prevention**:
   - Request schemas inherit `_LLMOverrideBase`, validating `base_url` strictly through `app.core.config.validate_llm_base_url` (HTTPS-only allowlist via `ALLOWED_LLM_BASE_HOSTS`, blocks credentials, private/loopback IPs, and arbitrary hosts).
   - **Credential Isolation Rule**: In `ai/arch_defense_generator.py`, when `base_url` is caller-supplied without `api_key`, `effective_key = api_key` (`None` if omitted). **NEVER** forward `settings.FREELLMAPI_API_KEY` to a caller-supplied `base_url`.
3. **Authorization & IDOR Prevention**:
   - Project-scoped endpoints resolve projects via `_get_owned_project(project_id, current_user.id, db)`, raising HTTP `404` if not owned.
   - Session storage (`_arch_session_store`) records `(user_id, ArchDefenseSessionState)` pairs so `GET /sessions/{session_id}` and `POST /sessions/{session_id}/respond` strictly verify `record.user_id == current_user.id` and return HTTP `404` on mismatch or missing ID.
4. **Prompt Injection Sandboxing**:
   - Dynamic repository labels, Mermaid code, diagram node/edge labels, and `candidate_answer` strings are enclosed inside explicit boundary delimiters (`<architecture_context>...</architecture_context>`, `<candidate_defense>...</candidate_defense>`) and truncated cleanly (`MAX_DIAGRAM_CHARS`, `MAX_NODES_IN_PROMPT`) before invoking LiteLLM. System instructions explicitly warn the evaluator to treat text inside `<candidate_defense>` strictly as untrusted candidate input.
5. **Bounded Cache & Override Bypass Integrity**:
   - Topic catalogs are cached in a bounded per-project store (`MAX_CACHED_PROJECTS = 100`, `MAX_CACHED_TOPICS_PER_PROJECT = 50`, bounded `_arch_session_store` capped at `MAX_ACTIVE_SESSIONS = 500` with oldest eviction).
   - Cache key/validation tracks an architecture fingerprint (`(total_files_analyzed, primary_pattern_type, len(nodes), len(edges), risk_count)`) so updated repo snapshots automatically invalidate stale catalogs.
   - Requests providing `model`, `api_key`, or `base_url` overrides bypass cache read/write to prevent tenant-wide or global fallback pollution. Filtered requests (`focus_area` specified) return filtered views without overwriting an existing unfiltered catalog, while retaining active selectable topic IDs in a bounded per-project lookup map so `sessions/start` resolves any topic freshly returned to the client.
6. **File Size & Quality Cap**: Every touched/created Python file remains strictly `<= 300 LOC`, lines `<= 100` chars (`ruff`).

---

## 4. Sequential Thinking Strategy

Because Step 3.6a combines two upstream static-analysis outputs (`ArchitectureReportResponse` + `DiagramResponse`) with multi-stage Principal Architect FSM transitions and security isolation boundaries, `sequential-thinking` MCP analysis was completed to lock:
- How `DiagramNode`, `DiagramEdge`, `DetectedPattern`, and `ArchitecturalRisk` map cleanly onto the four `ArchFocusAreaType` interrogation axes (`PATTERN_CHOICE`, `COMPONENT_BOUNDARY`, `DATA_FLOW_COUPLING`, `ARCHITECTURAL_RISK`) without inventing nonexistent files or nodes.
- How `TOPIC_ACTIVE -> TRADEOFF_CHALLENGE -> COMPLETED` transitions operate deterministically both with LiteLLM structured JSON outputs and under offline fallback evaluation.
- How `(user_id, session)` binding, LLM credential isolation, and snapshot fingerprinting integrate cleanly within 4 compact backend modules.

---

## 5. Data Contracts & Interfaces

### 5.1 Enums (`backend/app/schemas/arch_defense.py`)
```python
class ArchFocusAreaType(str, Enum):
    PATTERN_CHOICE = "PATTERN_CHOICE"
    COMPONENT_BOUNDARY = "COMPONENT_BOUNDARY"
    DATA_FLOW_COUPLING = "DATA_FLOW_COUPLING"
    ARCHITECTURAL_RISK = "ARCHITECTURAL_RISK"


class ArchDefenseStage(str, Enum):
    TOPIC_ACTIVE = "TOPIC_ACTIVE"
    TRADEOFF_CHALLENGE = "TRADEOFF_CHALLENGE"
    COMPLETED = "COMPLETED"
```

### 5.2 Core Models & Request/Response DTOs
- **`DiagramTarget`**: `node_id: str`, `label: str`, `node_type: str = "service"`, `subgraph: Optional[str] = None`, `connected_edges: List[str] = Field(default_factory=list)`
- **`ArchDefenseTopic`**: `id: str` (UUID), `title: str`, `focus_area: ArchFocusAreaType`, `pattern_name: str`, `severity_or_confidence: str = "HIGH"`, `target_nodes: List[DiagramTarget]`, `design_claim: str`, `interrogation_prompt: str`, `expected_tradeoffs: List[str]`, `risk_references: List[str]`
- **`ArchDefenseTurn`**: `id: str` (UUID), `role: str` (`interviewer` | `candidate` | `system`), `content: str`, `stage: ArchDefenseStage`, `timestamp: str` (UTC ISO-8601), `metadata: Dict[str, Any]`
- **`ArchDefenseEvaluationOutput`**: `depth_score: int (1..10)`, `pattern_rationale_solid: bool`, `tradeoffs_articulated: bool`, `boundary_coherence_score: int (1..10)`, `feedback: str`, `follow_up_challenge: Optional[str] = None`, `is_terminal: bool = False`
- **`ArchDefenseSessionState`**: `session_id`, `project_id`, `topic: ArchDefenseTopic`, `mermaid_code: str`, `diagram_summary: str`, `primary_pattern_name: str`, `stage: ArchDefenseStage`, `current_turn_index: int`, `turns: List[ArchDefenseTurn]`, `overall_score: Optional[float]`, `pattern_rationale_solid: Optional[bool]`, `boundary_coherence_score: Optional[int]`, `feedback: Optional[str]`, `created_at`, `updated_at`
- **`_LLMOverrideBase`**: `model: Optional[str] = None`, `api_key: Optional[str] = None`, `base_url: Optional[str] = None` with `@field_validator("base_url")` -> `validate_llm_base_url(value)` (inherited without redeclaring duplicate fields!).
- **`GenerateArchTopicsRequest(_LLMOverrideBase)`**: `focus_area: Optional[ArchFocusAreaType] = None`, `max_topics: int = Field(default=4, ge=1, le=10)`
- **`ArchTopicListResponse`**: `project_id`, `project_name`, `primary_pattern: DetectedPattern`, `diagram_type: DiagramType`, `mermaid_code: str`, `nodes: List[DiagramNode]`, `edges: List[DiagramEdge]`, `is_diagram_fallback: bool`, `total_topics: int`, `topics: List[ArchDefenseTopic]`
- **`StartArchDefenseRequest(_LLMOverrideBase)`**: `topic_id: str = Field(..., min_length=1)`
- **`SubmitArchAnswerRequest(_LLMOverrideBase)`**: `answer: str = Field(..., min_length=1, max_length=8000)`

### 5.3 AI Engine Interface (`backend/app/ai/arch_defense_generator.py`)
```python
async def generate_arch_defense_topics(
    report: ArchitectureReportResponse,
    diagram: DiagramResponse,
    focus_area: Optional[ArchFocusAreaType] = None,
    max_topics: int = 4,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: float = 12.0,
) -> List[ArchDefenseTopic]: ...

async def evaluate_arch_defense(
    topic: ArchDefenseTopic,
    candidate_answer: str,
    stage: ArchDefenseStage,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: float = 12.0,
) -> ArchDefenseEvaluationOutput: ...
```

### 5.4 REST API Endpoints (`backend/app/api/v1/arch_defense.py`, mounted at `/api/v1/arch-defense`)
| Method | Route | Request DTO | Response DTO | Status | Auth |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/projects/{project_id}/topics` | `Optional[GenerateArchTopicsRequest]` | `ArchTopicListResponse` | `200` | Owner (`404` otherwise) |
| `POST` | `/projects/{project_id}/sessions/start` | `StartArchDefenseRequest` | `ArchDefenseSessionState` | `201` | Owner (`404` on missing project/topic) |
| `GET` | `/sessions/{session_id}` | — | `ArchDefenseSessionState` | `200` | Session owner (`404` otherwise) |
| `POST` | `/sessions/{session_id}/respond` | `SubmitArchAnswerRequest` | `ArchDefenseSessionState` | `200` | Session owner (`404`/`400` if completed) |

---

## 6. Step-by-Step Implementation Sequence

1. **Create `backend/app/schemas/arch_defense.py` (`<= 240 LOC`)**:
   - Define enums, diagram target/topic/turn/evaluation/session Pydantic models, `_LLMOverrideBase`, and request/response schemas importing `DiagramNode`, `DiagramEdge`, `DiagramType` from `app.schemas.diagram` and `DetectedPattern` from `app.schemas.architecture`.
2. **Create `backend/app/ai/arch_defense_generator.py` (`<= 280 LOC`)**:
   - Implement credential resolver helper (`_resolve_llm_credentials(model, api_key, base_url)`) enforcing no key fallback onto caller-supplied `base_url`.
   - Implement sandboxed system/user prompt builders wrapping diagram nodes, edges, Mermaid code, detected patterns, and architectural risks cleanly within token limits.
   - Implement `generate_arch_defense_topics` with structured JSON parsing via `clean_json_response` + `DiagramNode` lookup validation (filtering hallucinated node IDs against actual diagram nodes) and deterministic offline generator fallback (`_build_deterministic_topics`).
   - Implement `evaluate_arch_defense` with Principal Architect evaluation rubric + deterministic heuristic fallback scoring diagram component mentions, coupling/tradeoff concepts, and architectural rationale (`_build_deterministic_evaluation`).
3. **Create `backend/app/api/v1/arch_defense.py` (`<= 270 LOC`) & Mount in `backend/app/main.py`**:
   - Define bounded topic catalog store (`_arch_topic_catalog`), active diagram context snapshot store per project, and `(owner_user_id, ArchDefenseSessionState)` session store (`_arch_session_store`).
   - Implement `_get_owned_project` and `_get_owned_session` helpers.
   - Implement the 4 REST endpoints composing `detect_repository_architecture` + `generate_project_architecture_diagram` + `generate_arch_defense_topics` + `evaluate_arch_defense`.
   - Register `arch_defense_router` in `backend/app/main.py` with `prefix=f"{settings.API_V1_STR}/v1/arch-defense"`.
4. **Author `backend/tests/test_arch_defense.py` (`<= 290 LOC`)**:
   - Cover schema validation (`validate_llm_base_url` blocking SSRF localhost/IP/HTTP), credential isolation when `base_url` is overridden without `api_key`, deterministic fallback topic generation & diagram grounding across all `ArchFocusAreaType` values, LLM mocked JSON topic synthesis, full multi-turn FSM progression (`TOPIC_ACTIVE -> TRADEOFF_CHALLENGE -> COMPLETED`), completed session `400` guard, cross-user IDOR `404` checks on `GET /sessions/{id}` and `POST /sessions/{id}/respond`, and cache fingerprint invalidation & override bypass.

---

## 7. Verification & Acceptance Criteria

- **Primary Targeted Test Command**:
  `pytest tests/test_arch_defense.py -v` (executed inside `backend/` after user approval of `/verify_step`).
- **Lint & Line Limit Checks**:
  - `ruff check app/schemas/arch_defense.py app/ai/arch_defense_generator.py app/api/v1/arch_defense.py app/main.py tests/test_arch_defense.py`
  - Verify all new/modified files remain `<= 300 LOC`.
- **Functional & Security Acceptance Criteria**:
  - Topics strictly reference genuine diagram node IDs/labels, edges, detected patterns, or architectural risks from the project's Milestones 2.8/2.9 data.
  - Both LLM mode (mocked `litellm.acompletion`) and offline deterministic mode produce valid `ArchTopicListResponse` and advance `ArchDefenseSessionState` cleanly through `TOPIC_ACTIVE -> TRADEOFF_CHALLENGE -> COMPLETED`.
  - Unowned projects/sessions return HTTP `404`; invalid/disallowed `base_url` values fail schema validation (`422`); custom `base_url` without `api_key` never transmits `settings.FREELLMAPI_API_KEY`.
