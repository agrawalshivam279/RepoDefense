# 📄 Technical Specification: FastAPI Project Scaffold & Health Check

> **Step ID**: `1.1a`  
> **Target Module**: `backend/app/`  
> **Git Feature Branch**: `feat/step-1-1a-fastapi-scaffold`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-10-26  

---

## 1. Executive Summary

This specification establishes the core backend foundation for **RepoDefense** as a modular FastAPI (Python 3.12+) application. It defines the project dependency configuration in `pyproject.toml`, structured settings management via Pydantic v2 `BaseSettings` in `backend/app/core/config.py`, global CORS middleware configuration for Next.js 15 client integration, and the root health check endpoint at `/api/health`. This step provides the clean foundation upon which database models, AST analyzers, and interview state machines will be built.

---

## 2. Dependencies & Prerequisites

- **Depends on**: Initial repository architecture and agent suite setup.
- **Blocked by**: None.
- **Tech Stack Invariant**:
  - Python 3.12+
  - FastAPI $\ge 0.115$
  - Pydantic v2 / Pydantic Settings
  - Uvicorn (ASGI web server)
  - Pytest & HTTPX (for test client execution)
  - Adheres strictly to [Gemini.md](file:///d:/RepoDefense/Gemini.md) without introducing microservices, unapproved third-party frameworks, or Celery.

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Pure static API scaffolding. No `eval()`, `exec()`, or process spawning for user-provided code.
- [x] **Path Traversal Defense**: Safe boundary rules established for subsequent file operations.
- [x] **CORS Restrictiveness**: Origins configurable via `CORS_ORIGINS` environment setting (defaults to `http://localhost:3000` for Next.js).
- [x] **File Length Limit**: Every target file strictly maintains $\le 300$ LOC.

---

## 4. 🧠 Sequential Thinking Strategy

- **Complexity Evaluation**: Scaffolding and health endpoint follow standard FastAPI patterns. Sequential Thinking MCP is **Skipped** for this step as no complex AST grammars, vector chunking math, or multi-turn FSM algorithms are present.

---

## 5. Data Contracts & Interfaces

### 5.1 Settings Schema (`backend/app/core/config.py`)

```python
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core application settings loaded from environment or defaults."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "RepoDefense API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )


settings = Settings()
```

### 5.2 Health Response Schema (`backend/app/schemas/health.py` or inline in `main.py`)

```python
from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check payload response model."""
    status: str = Field(default="ok", description="Service health status")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic version")
    timestamp: datetime = Field(..., description="UTC server timestamp")
```

---

## 6. Step-by-Step Implementation Sequence

### Phase A: Dependencies & Configuration
1. **Author `backend/pyproject.toml`**:
   - Define project metadata `repodefense-backend`.
   - Specify Python requirement `>=3.12`.
   - Configure dependencies: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `httpx`, `pytest`, `pytest-asyncio`.
   - Configure tool settings for `ruff` and `pytest`.
2. **Implement `backend/app/core/config.py`**:
   - Create `Settings` class with Pydantic v2 `BaseSettings`.
   - Export singleton instance `settings`.

### Phase B: FastAPI Scaffolding & Health Route
3. **Implement `backend/app/main.py`**:
   - Instantiate FastAPI application with `settings.PROJECT_NAME` and `settings.VERSION`.
   - Attach `CORSMiddleware` with allowed origins from `settings.CORS_ORIGINS`.
   - Register GET `/api/health` endpoint returning `HealthResponse`.
   - Include root route `/` returning API metadata.

### Phase C: Automated Tests & Verification
4. **Implement `backend/tests/test_health.py`**:
   - Use `httpx.AsyncClient` or FastAPI `TestClient`.
   - Test `GET /api/health` asserts status `200` and `status == "ok"`.
   - Test `GET /` asserts status `200`.

---

## 7. Verification & Acceptance Criteria

### Automated Tests
```bash
pytest backend/tests/test_health.py -v
```

### Acceptance Checklist
- [ ] `GET /api/health` returns HTTP 200 with JSON payload `{"status": "ok", "app": "RepoDefense API", "version": "0.1.0", ...}`.
- [ ] All created files $\le 300$ LOC.
- [ ] No arbitrary code execution or unvalidated parameters.
- [ ] `pytest backend/tests/test_health.py -v` passes cleanly with 0 errors.
