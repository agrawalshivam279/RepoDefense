# 📄 Technical Specification: Step 2.9a — Backend Mermaid Architecture Diagram Generation Engine & REST API

> **Step ID**: `Step 2.9a`  
> **Target Module**: `backend/app/...`  
> **Git Feature Branch**: `feat/step-2-9a-mermaid-diagram-engine`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-11-07  

---

## 1. Overview & Objective

RepoDefense provides grounded architectural assessment of candidate software. Milestone 2.9 delivers the **Architecture Diagram Engine** to automatically synthesize visual Mermaid flowcharts representing repository topology (Client Tier, API / Web Framework Tier, Background Queues / Workers, Database / Cache Persistence, and External Integrations) from extracted `Dependency` and `Evidence` records.

Step 2.9a implements:
1. **Pydantic v2 Schemas (`backend/app/schemas/diagram.py`)**: Data contracts for diagram nodes, directional relationships, subgraphs, and complete diagram responses (`DiagramType`, `DiagramResponse`).
2. **Principal Engineer Prompt Template (`backend/app/ai/prompts.py`)**: Centralized `MERMAID_DIAGRAM_SYSTEM_PROMPT` commanding the LLM to output valid Mermaid syntax (`flowchart TD`) with quoted node labels, grouped subgraphs, and zero syntax hallucinations.
3. **Deterministic Fallback Diagram Generator (`backend/app/analyzers/diagram.py`)**: Rule-based synthesis that constructs valid, multi-tier Mermaid flowchart syntax when offline or when LLM API keys are unconfigured.
4. **Diagram Orchestration Service (`backend/app/services/diagram.py`)**: Asynchronously queries project snapshot, dependencies, and evidence, calls LiteLLM with structured output/syntax validation, and falls back gracefully to the deterministic generator on any parse anomaly.
5. **Authenticated REST API (`backend/app/api/v1/diagram.py`)**: `GET /api/v1/projects/{project_id}/diagram` requiring Supabase JWT bearer token authentication and enforcing multi-tenant isolation.

---

## 2. Core Architecture Principles & Invariants

1. **Strictly Static Analysis (Zero Code Execution)**:
   Diagrams are constructed strictly from static dependency strings, directory metadata, and pre-extracted `Evidence` rows. No user code is executed or compiled.
2. **Syntax Safety & Injection Defense**:
   All node labels are strictly quoted and sanitized (e.g. `id["Label (Extra)"]`) to prevent syntax crashes caused by special characters `()[]{}"'` or HTML injection.
3. **Deterministic Fallback Invariant**:
   The system must never fail to return a valid Mermaid diagram. If the LLM generates invalid Mermaid syntax, the service intercepts the error and returns a deterministic flowchart generated from classified tiers.
4. **File Length Gate ($\le 300$ LOC)**:
   Every created or modified file must remain strictly under 300 lines of code.

---

## 3. Data Contracts (`backend/app/schemas/diagram.py`)

```python
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class DiagramType(str, Enum):
    FLOWCHART_TD = "flowchart TD"
    FLOWCHART_LR = "flowchart LR"


class DiagramNode(BaseModel):
    node_id: str = Field(..., description="Alphanumeric identifier for Mermaid node")
    label: str = Field(..., description="Display label for the node")
    node_type: str = Field(..., description="'frontend' | 'backend' | 'database' | 'queue' | 'external'")
    subgraph: str | None = Field(default=None, description="Optional enclosing subgraph/tier name")


class DiagramEdge(BaseModel):
    source_id: str
    target_id: str
    label: str | None = None
    style: str | None = None  # e.g. "solid" | "dotted"


class DiagramResponse(BaseModel):
    project_id: str
    project_name: str
    diagram_type: DiagramType
    mermaid_code: str = Field(..., description="Raw, valid Mermaid flowchart syntax")
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    is_fallback: bool = Field(default=False)
    summary: str

    model_config = ConfigDict(from_attributes=True)
```

---

## 4. Architectural Tier Mapping Taxonomy

The diagram generator organizes extracted evidence and dependencies into standard architectural subgraphs:

| Subgraph / Tier | Detection Signals | Example Nodes |
| :--- | :--- | :--- |
| **`Client / Frontend Tier`** | `next`, `react`, `vue`, `angular`, `svelte`, `frontend/` directory | `web["Next.js 15 Client"]`, `mobile["Mobile App"]` |
| **`API / Service Tier`** | `fastapi`, `express`, `django`, `flask`, `nest`, `backend/` directory | `api["FastAPI REST Router"]`, `svc["Core Domain Service"]` |
| **`Asynchronous Queue Tier`** | `arq`, `celery`, `redis`, `rabbitmq`, `bullmq`, `workers/` directory | `queue["Redis / ARQ Worker Pool"]` |
| **`Persistence Tier`** | `sqlalchemy`, `pgvector`, `postgres`, `prisma`, `mongodb`, `redis` | `db["PostgreSQL 17 + pgvector"]`, `cache["Redis Cache"]` |
| **`External / Auth Tier`** | `supabase`, `firebase`, `auth0`, `github`, `stripe`, `aws` | `auth["Supabase Auth / OAuth"]`, `ext["GitHub REST API"]` |

---

## 5. Specialized Skills Directive

| Specialized Skill | Scope of Impact & Mandate | Verification Requirement |
| :--- | :--- | :--- |
| **[`eval_persona`](file:///d:/RepoDefense/.agents/skills/eval_persona/SKILL.md)** | Audits `MERMAID_DIAGRAM_SYSTEM_PROMPT` in `prompts.py` for XML boundary isolation, Mermaid syntax constraints (valid identifiers, quoted labels, allowed `flowchart` syntax), and zero hallucination of non-existent libraries. | Asserts prompt calibration and Pydantic structured output conformance. |
| **[`security_auditor`](file:///d:/RepoDefense/.agents/skills/security_auditor/SKILL.md)** | Audits deterministic fallback and prompt input formatting for unsanitized user repository paths or dependency strings. | Verifies quote escaping and zero dynamic code execution (`eval/exec`). |
| **[`code_reviewer`](file:///d:/RepoDefense/.agents/skills/code_reviewer/SKILL.md)** | Audits file length limits ($\le 300$ LOC), async database session handling, and clean error fallbacks. | Confirms no file exceeds 300 LOC and tests provide 100% pass rate. |

---

## 6. Implementation Sequence & Target Files

1. **`backend/app/schemas/diagram.py`** (~70 LOC):
   - Define `DiagramType`, `DiagramNode`, `DiagramEdge`, and `DiagramResponse`.
2. **`backend/app/ai/prompts.py`** (~35 LOC addition):
   - Add `MERMAID_DIAGRAM_SYSTEM_PROMPT` with strict Mermaid flowchart rules.
3. **`backend/app/analyzers/diagram.py`** (~180 LOC):
   - Deterministic rule-based Mermaid diagram builder mapping `Dependency` and `Evidence` records into multi-tier `flowchart TD` code.
   - Robust label escaping and ID sanitization (`re.sub(r'[^a-zA-Z0-9_]', '_', name)`).
4. **`backend/app/services/diagram.py`** (~130 LOC):
   - `generate_project_architecture_diagram(project, db_session) -> DiagramResponse`
   - LiteLLM integration with timeout, syntax validator, and deterministic fallback on exception or syntax errors.
5. **`backend/app/api/v1/diagram.py`** (~60 LOC):
   - Authenticated endpoint `GET /api/v1/projects/{project_id}/diagram`.
   - Mounted in `backend/app/main.py`.
6. **`backend/tests/test_diagram.py`** (~180 LOC):
   - Hermetic tests for node sanitization, tier classification, deterministic fallback generation, and API router.

---

## 7. Verification Strategy & Acceptance Criteria

1. **Static Analysis & Lint**:
   - `ruff check backend/app backend/tests` must pass with 0 errors.
2. **Dynamic Tests**:
   - `pytest backend/tests/test_diagram.py` must pass 100% of tests.
3. **Mermaid Syntax Conformance**:
   - Generated syntax starts with `flowchart TD` or `flowchart LR`.
   - Node IDs contain only alphanumeric/underscore characters.
   - Labels are enclosed in quotes `id["Label"]`.
   - Subgraphs have matching `end` tokens.
