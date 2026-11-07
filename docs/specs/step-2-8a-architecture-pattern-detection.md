# Technical Specification: Step 2.8a — Backend Architecture Pattern Detection Engine & REST API

## 1. Overview & Objective
RepoDefense authenticates candidate engineering claims against ground-truth codebase structure. Milestone 2.8 builds the **Architecture Audit & Detection Engine** to classify high-level design patterns (Modular Monolith, MVC, Clean/Hexagonal Architecture, Event-Driven, Microservices, Layered Architecture, Serverless/BaaS) through deterministic static inspection of directory topologies, dependency clusters, and architectural evidence records.

Step 2.8a implements the backend pattern classification algorithms, Pydantic v2 schemas, scoring heuristics, architectural risk detection, and authenticated REST endpoint `GET /api/v1/projects/{project_id}/architecture`.

---

## 2. Core Architecture Principles & Invariants
1. **Strictly Static Analysis (Zero Code Execution)**:
   All pattern classifications evaluate static directory trees, dependency strings, and pre-extracted `Evidence` rows. No user code is executed, compiled, or dynamically evaluated.
2. **Deterministic Mathematical Grounding**:
   Patterns are assigned confidence scores ($0.0 - 1.0$) based on explicit indicator weights (e.g., matching directories $+0.35$, key dependencies $+0.25$, supporting evidence $+0.20$), avoiding black-box LLM hallucinations for structural facts.
3. **Multi-Tenant Isolation**:
   Every request must authenticate via Supabase JWT Bearer token and assert that `Project.user_id == current_user.id`.
4. **Strict File Length & Modularity ($\le 300$ LOC)**:
   Every created or modified file must remain strictly under 300 lines of code.

---

## 3. Architecture Patterns & Detection Taxonomy

| Pattern Type | Key Directory Signals | Key Dependency Signals | Supporting Evidence |
| :--- | :--- | :--- | :--- |
| `modular_monolith` | `frontend/` + `backend/`, `packages/`, `apps/`, `domains/`, `modules/` | Shared root configs (`docker-compose`, monorepo tools), full-stack dependencies | Framework + Database + Queue |
| `mvc` | `controllers/`, `views/`, `models/`, `templates/` | `django`, `rails`, `express`, `nest`, `spring`, `laravel` | Framework (`django`, `express`), Database |
| `clean_architecture` | `domain/`, `core/`, `ports/`, `adapters/`, `use_cases/`, `entities/` | Decoupled domain models, dependency injection libraries | Interface abstractions, Auth guards |
| `event_driven` | `workers/`, `consumers/`, `events/`, `queues/`, `subscribers/` | `arq`, `celery`, `redis`, `aiokafka`, `rabbitmq`, `pika`, `bullmq` | Queue evidence (`arq`, `celery`), Background jobs |
| `layered_architecture` | `api/`, `services/`, `repositories/`, `dao/`, `models/` | Standard web frameworks (`fastapi`, `express`, `flask`) | API endpoints, DB repositories |
| `microservices` | Multiple top-level services with separate `Dockerfile`/manifests | Multi-service compose, gRPC/proto, service mesh configs | Infrastructure + Multiple Services |
| `serverless_jamstack` | `app/api/`, `pages/api/`, `functions/`, `netlify/`, `amplify/` | `@supabase/supabase-js`, `firebase`, `@aws-sdk`, Vercel/Netlify | Serverless APIs, BaaS integration |
| `unstructured` | Flat root directory, no clear modular boundaries | Ad-hoc scripts | Minimal structured evidence |

---

## 4. Data Contracts (`backend/app/schemas/architecture.py`)

```python
from enum import Enum
from pydantic import BaseModel, Field

class ArchitecturePatternType(str, Enum):
    MODULAR_MONOLITH = "modular_monolith"
    MVC = "mvc"
    CLEAN_ARCHITECTURE = "clean_architecture"
    LAYERED_ARCHITECTURE = "layered_architecture"
    EVENT_DRIVEN = "event_driven"
    MICROSERVICES = "microservices"
    SERVERLESS_JAMSTACK = "serverless_jamstack"
    UNSTRUCTURED = "unstructured"

class PatternConfidenceTier(str, Enum):
    HIGH = "high"          # >= 0.75
    MODERATE = "moderate"  # 0.45 - 0.74
    LOW = "low"            # < 0.45

class PatternIndicator(BaseModel):
    indicator_type: str  # "directory" | "dependency" | "evidence"
    description: str
    weight: float
    matched_items: list[str]

class DetectedPattern(BaseModel):
    pattern_type: ArchitecturePatternType
    pattern_name: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    tier: PatternConfidenceTier
    summary: str
    indicators: list[PatternIndicator] = Field(default_factory=list)

class ArchitecturalRisk(BaseModel):
    risk_id: str
    severity: str  # "critical" | "high" | "medium" | "low"
    title: str
    description: str
    recommendation: str

class ArchitectureReportResponse(BaseModel):
    project_id: str
    project_name: str
    primary_pattern: DetectedPattern
    secondary_patterns: list[DetectedPattern]
    all_patterns: list[DetectedPattern]
    architectural_risks: list[ArchitecturalRisk]
    directory_summary: dict[str, int]
    total_files_analyzed: int
```

---

## 5. Architectural Risk Detection Engine

The service evaluates common architectural blind spots:
1. **`FAT_ROUTER_MISSING_SERVICE`**: Substantial API endpoint logic exists without a dedicated `services/` or `use_cases/` abstraction.
2. **`MISSING_LAYER_SEPARATION`**: Flat directory hierarchy with over 20 source files in root directories.
3. **`UNISOLATED_BACKGROUND_TASKS`**: Database or API endpoints perform compute-heavy work without a detected message queue (`workers/`, `celery`, `arq`).
4. **`DECOUPLED_MONOLITH_LEAK`**: Monorepo with inter-module imports crossing clean architectural boundaries.

---

## 6. Implementation Plan & Target Files

1. **`backend/app/schemas/architecture.py`** (~100 LOC):
   - Pydantic models for patterns, indicators, risks, and report response.
2. **`backend/app/services/architecture.py`** (~220 LOC):
   - `detect_repository_architecture(project_id, db_session) -> ArchitectureReportResponse`
   - Path normalization, directory frequency aggregation, dependency signature matching, weighted scoring heuristics, and risk identification.
3. **`backend/app/api/v1/architecture.py`** (~70 LOC):
   - Authenticated router `GET /api/v1/projects/{project_id}/architecture` with multi-tenant check.
   - Mounted in `backend/app/main.py`.
4. **`backend/tests/test_architecture.py`** (~210 LOC):
   - Unit tests for directory token extraction, pattern scoring heuristics, risk detection, empty repositories, and endpoint responses.

---

## 7. Specialized Domain Skill Directives

- **`security_auditor`**:
  - Assert zero code execution on user file names or dependency strings.
  - Enforce path normalization and sanitize directory tokens against directory traversal characters (`..`).
- **`code_reviewer`**:
  - Enforce strictly $\le 300$ LOC limit per file.
  - Parameterized database queries and async session management.
- **Verification Commands**:
  - Lint: `ruff check backend/app backend/tests`
  - Tests: `python -m pytest backend/tests/test_architecture.py -v`
