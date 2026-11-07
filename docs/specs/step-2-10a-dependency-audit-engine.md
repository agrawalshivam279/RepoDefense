# 📄 Technical Specification: Step 2.10a — Backend Dependency & Technology Audit Engine & REST API

> **Step ID**: `Step 2.10a`  
> **Target Module**: `backend/app/...`  
> **Git Feature Branch**: `feat/step-2-10a-dependency-audit-engine`  
> **Status**: 📋 In Progress / Implementation  
> **Created**: 2026-11-07  

---

## 1. Executive Summary

RepoDefense authenticates candidate technical knowledge by challenging them on real architectural decisions and technical debt. Milestone 2.10 builds the **Dependency / Technology Audit Engine** to scan repository `Dependency` records, detect outdated or deprecated packages, flag security risks and unmaintained libraries, compute an architectural health score, and suggest modern replacements.

Step 2.10a implements the backend evaluation engine:
1. **Pydantic v2 Schemas (`backend/app/schemas/tech_audit.py`)**: Data contracts for audit categories, severity tiers, audited dependency items, and complete audit responses (`TechAuditReportResponse`).
2. **Deterministic Audit Engine (`backend/app/analyzers/tech_audit.py`)**: Rule-based static vulnerability and obsolescence heuristics evaluating Python and Node.js/TS packages without external API calls or dynamic code execution.
3. **Audit Service Orchestrator (`backend/app/services/tech_audit.py`)**: Async service querying project dependencies, applying version checks, and calculating aggregate repository tech health scores ($0-100\%$).
4. **Authenticated REST Endpoint (`backend/app/api/v1/tech_audit.py`)**: `GET /api/v1/projects/{project_id}/tech-audit` enforcing Supabase JWT bearer authentication and multi-tenant isolation.
5. **Hermetic Test Suite (`backend/tests/test_tech_audit.py`)**: 100% test coverage for version parsing, vulnerability heuristics, health score metrics, and router security.

---

## 2. Core Architecture Principles & Invariants

1. **Zero Code Execution**: Dependency versions and package names are parsed purely as text tokens. No package managers (`pip`, `npm`) or package code are executed.
2. **Deterministic Knowledge Heuristics**: Evaluates against an embedded catalog of well-known deprecated, outdated, or vulnerable packages (e.g. `request`, `moment`, `urllib3<2.0.7`, `react<18.0`, `django<4.2`, `express<4.19`).
3. **Bounded Health Score ($0-100\%$)**: Penalizes critical ($-25$), high ($-15$), medium ($-8$), and low ($-3$) severity findings, clamped at zero.
4. **File Length Limit ($\le 300$ LOC)**: Every file remains strictly under 300 lines of code.

---

## 3. Data Contracts (`backend/app/schemas/tech_audit.py`)

```python
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class AuditSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AuditCategory(str, Enum):
    DEPRECATED = "deprecated"
    SECURITY_RISK = "security_risk"
    OUTDATED = "outdated"
    UNMAINTAINED = "unmaintained"


class AuditedDependencyItem(BaseModel):
    name: str
    version: str | None = None
    is_dev: bool = False
    severity: AuditSeverity
    category: AuditCategory
    issue_description: str
    suggested_alternative: str
    reference_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TechAuditReportResponse(BaseModel):
    project_id: str
    project_name: str
    total_dependencies_audited: int
    flagged_dependencies_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    tech_health_score: int = Field(..., ge=0, le=100)
    audited_items: list[AuditedDependencyItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
```

---

## 4. Specialized Skills Directive

| Skill | Directive & Verification Requirement |
| :--- | :--- |
| **`security_auditor`** | Asserts zero dynamic code execution during version string evaluation and safe regex parsing. |
| **`code_reviewer`** | Enforces strictly $\le 300$ LOC per file, parameterized SQL queries, and async database session safety. |
| **`eval_persona`** | Asserts that flagged dependencies provide clear alternative recommendations that the Principal Engineer persona can challenge during defense interviews. |

---

## 5. Implementation Sequence & Target Files

1. `backend/app/schemas/tech_audit.py`: ~60 LOC
2. `backend/app/schemas/__init__.py`: Export tech audit schemas (~10 LOC diff)
3. `backend/app/analyzers/tech_audit.py`: Heuristic rules catalog & semver parser (~210 LOC)
4. `backend/app/analyzers/__init__.py`: Export analyzer functions (~10 LOC diff)
5. `backend/app/services/tech_audit.py`: Database query & score orchestrator (~90 LOC)
6. `backend/app/services/__init__.py`: Export service (~5 LOC diff)
7. `backend/app/api/v1/tech_audit.py`: Authenticated REST router (~55 LOC)
8. `backend/app/main.py`: Mount tech audit router (~3 LOC diff)
9. `backend/tests/test_tech_audit.py`: Hermetic tests (~220 LOC)
