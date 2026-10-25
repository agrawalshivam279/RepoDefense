# 📄 Technical Specification: Local Infrastructure & Docker Compose Setup

> **Step ID**: `1.1b`  
> **Target Module**: Root & `backend/`  
> **Git Feature Branch**: `feat/step-1-1b-local-infra-docker`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-10-26  

---

## 1. Executive Summary

This specification defines the local developer environment and containerization strategy for **RepoDefense**. It provisions a Docker Compose stack containing PostgreSQL 17 equipped with the `pgvector` extension (using the official `pgvector/pgvector:pg17` image) and a lightweight Redis 7 container for ARQ background job queuing. It establishes an authoritative `.env.example` configuration reference covering local and cloud targets (Supabase, Upstash, FreeLLMAPI) and defines an optimized `backend/Dockerfile` with non-root execution for deployment parity on Render.

---

## 2. Dependencies & Prerequisites

- **Depends on**: Step 1.1a (FastAPI project scaffold, `pyproject.toml`, settings).
- **Blocked by**: None.
- **Tech Stack Invariant**:
  - PostgreSQL 17 + pgvector (using `pgvector/pgvector:pg17` for exact parity with Supabase Postgres 17 pgvector).
  - Redis 7 (`redis:7-alpine` for local caching and ARQ message broker).
  - Docker & Docker Compose v2.
  - Python 3.12-slim base image for backend container.
  - Adheres strictly to [Gemini.md](file:///d:/RepoDefense/Gemini.md) without introducing microservices or unapproved databases.

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Docker Compose strictly runs isolated database and cache services; no execution of untrusted user repository code.
- [x] **Non-Root Container Security**: `backend/Dockerfile` creates and runs as an unprivileged user `appuser` (UID 10001).
- [x] **Secret Isolation**: Secrets in `docker-compose.yml` and `.env.example` are developer placeholders; `.gitignore` strictly blocks accidental staging of live `.env` files.
- [x] **File Length Limit**: Every target file strictly maintains $\le 300$ LOC.

---

## 4. 🧠 Sequential Thinking Strategy

- **Complexity Evaluation**: Standard container orchestration and environment variable specification. Sequential Thinking MCP is **Skipped** for this step as no complex AST algorithms or state machines are involved.

---

## 5. Data Contracts & Interfaces

### 5.1 Environment Variable Schema (`.env.example`)

```bash
# Application Configuration
PROJECT_NAME="RepoDefense API"
VERSION="0.1.0"
ENVIRONMENT="development"
API_V1_STR="/api"
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# PostgreSQL 17 + pgvector
POSTGRES_USER=repouser
POSTGRES_PASSWORD=repopassword
POSTGRES_DB=repodefense
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://repouser:repopassword@localhost:5432/repodefense

# Redis (Local / Upstash)
REDIS_URL=redis://localhost:6379/0

# Supabase Auth & Cloud Database (Production)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# LLM Routing (LiteLLM via FreeLLMAPI)
FREELLMAPI_BASE_URL=https://api.freellmapi.com/v1
FREELLMAPI_API_KEY=your-api-key
```

### 5.2 Docker Compose Service Contracts (`docker-compose.yml`)

- **Service: `postgres`**:
  - Image: `pgvector/pgvector:pg17`
  - Ports: `5432:5432`
  - Healthcheck: `pg_isready -U repouser -d repodefense`
  - Volume: `postgres_data:/var/lib/postgresql/data`
- **Service: `redis`**:
  - Image: `redis:7-alpine`
  - Ports: `6379:6379`
  - Healthcheck: `redis-cli ping`
  - Volume: `redis_data:/data`
- **Service: `backend`** (optional local profile):
  - Build: `./backend`
  - Ports: `8000:8000`
  - Depends on: `postgres` (healthy), `redis` (healthy)

---

## 6. Step-by-Step Implementation Sequence

### Phase A: Environment Template & Dockerfile
1. **Author `.env.example`**:
   - Provide well-documented defaults for local Docker development and cloud keys (Supabase, Upstash, FreeLLMAPI).
2. **Author `backend/Dockerfile`**:
   - Multi-stage or slim build using `python:3.12-slim`.
   - Install dependencies from `pyproject.toml`.
   - Create unprivileged system user `appuser`.
   - Expose port `8000`.
   - Define CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### Phase B: Docker Compose Orchestration
3. **Author `docker-compose.yml`**:
   - Configure `postgres` service with `pgvector/pgvector:pg17`.
   - Configure `redis` service with `redis:7-alpine`.
   - Add robust container health checks.
   - Configure persistent named volumes (`postgres_data`, `redis_data`).

### Phase C: Automated Tests & Verification
4. **Implement `backend/tests/test_infra.py`**:
   - Validate `.env.example` contains all expected keys referenced in `backend/app/core/config.py`.
   - Validate `docker-compose.yml` structure, required services (`postgres`, `redis`), images, and health checks.
   - Validate `backend/Dockerfile` specifies non-root user and correct entrypoint.

---

## 7. Verification & Acceptance Criteria

### Automated Tests
```bash
python -m pytest backend/tests/test_infra.py -v
```

### Acceptance Checklist
- [ ] `.env.example` documents all required environment variables for local and cloud environments.
- [ ] `docker-compose.yml` uses `pgvector/pgvector:pg17` and `redis:7-alpine` with health checks.
- [ ] `backend/Dockerfile` uses Python 3.12, creates non-root user, and runs uvicorn.
- [ ] All files $\le 300$ LOC.
- [ ] `python -m pytest backend/tests/test_infra.py -v` passes cleanly.
