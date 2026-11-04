# Technical Specification: Step 1.18a — GitHub Actions CI/CD Pipeline & Production Readiness Suite

> **Milestone:** 1.18 (MVP Polish & Deploy)  
> **Sub-Task:** Step 1.18a  
> **Branch:** `feat/step-1-18a-ci-pipeline-readiness`  
> **Target Files:**  
> - `.github/workflows/ci.yml` (CI workflow pipeline)  
> - `backend/pyproject.toml` (Pytest configuration & pythonpath tuning)  
> - `frontend/package.json` (Scripts and linting config)  
> - `.env.example` (Production & development environment variable template)  

---

## 1. Overview & Architectural Context

RepoDefense is reaching the conclusion of **Phase 1: Ingestion & Core MVP**. To guarantee production stability, every pull request and push to `main` must pass rigorous automated quality gates without human intervention. 

Currently, `.github/workflows/ci.yml` contains legacy placeholders:
- It runs `ruff check backend/app`, missing `backend/tests`.
- It attempts to run `npm test` which is not defined in `frontend/package.json`.
- It omits `npm run build` for the Next.js 15 frontend, which is critical to verify App Router page generation and webpack compilation.
- In `backend/pyproject.toml`, test paths and pythonpath need clean alignment so tests execute identically whether invoked from repo root or the `backend/` directory.

Step 1.18a delivers a production-grade CI/CD pipeline, hardened pytest configurations, and unified environment documentation.

---

## 2. Requirements & Changes

### 2.1 Backend CI Job Refinement (`.github/workflows/ci.yml`)
- **Python Version:** Python 3.12.
- **Service Containers:**
  - `postgres`: `pgvector/pgvector:pg17` on port 5432 (mapped to 5433 to avoid runner conflict).
  - `redis`: `redis:7-alpine` on port 6379.
- **Dependency Installation:**
  - `pip install --upgrade pip`
  - `pip install -e "./backend[dev]"` (installs all project and dev dependencies hermetically).
- **Static Analysis & Linting:**
  - `python -m ruff check backend/app backend/tests`
- **Database Migrations:**
  - `cd backend && python -m alembic upgrade head` with local postgres service credentials.
- **Automated Tests:**
  - `python -m pytest backend/tests/ -v --cov=backend/app` with hermetic test suite execution.

### 2.2 Frontend CI Job Refinement (`.github/workflows/ci.yml`)
- **Node.js Version:** Node.js 20.x (LTS).
- **Dependency Caching & Installation:**
  - `npm ci` with `cache: 'npm'` in `actions/setup-node`.
- **TypeScript Gate:**
  - `npm run typecheck` (`tsc --noEmit`) with zero type errors.
- **Production Build Gate:**
  - `npm run build` in `frontend/` with mock/build-safe environment variables (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`).
  - Asserts that all App Router routes (`/`, `/dashboard`, `/interview/[id]`, `/projects/[id]`, `/report/[id]`, `/login`, `/signup`) prerender/compile cleanly.

### 2.3 Backend Configuration Hardening (`backend/pyproject.toml`)
- Configure `[tool.pytest.ini_options]` with `testpaths = ["tests", "backend/tests"]` and `pythonpath = [".", "backend"]`.
- Ensure test discovery is deterministic across all environments.

### 2.4 Environment Template Hardening (`.env.example`)
- Audit and document all required variables for local dev, testing, and production (Supabase Auth/DB, Upstash Redis, LiteLLM/FreeLLMAPI, FastAPI backend settings, Next.js client variables).
- Enforce strict dummy/placeholder values with zero leaked development secrets.

---

## 3. Specialized Domain Skill Directives

### 🩺 `doctor` Skill Directive
- Audit environment dependencies (Python 3.12+, Node 20+, Tree-sitter, PostgreSQL 17 + pgvector).
- Verify workflow syntax and consistency before shipping.

### 🛡️ `security_auditor` Skill Directive
- Assert that `.env.example` contains zero real secrets, API keys, or database passwords.
- Assert that `.github/workflows/ci.yml` uses dummy service credentials for containerized testing.

---

## 4. 5-Gate Goldilocks Granularity Standard
- **Target Files:** 4 files (`ci.yml`, `pyproject.toml`, `package.json`, `.env.example`).
- **Code Volume:** All files $\le 300$ LOC.
- **Architectural Scope:** Single concern — CI/CD automation & production environment readiness.
- **Target Verification Command:** `ruff check`, `tsc --noEmit`, `npm run build`, `pytest --collect-only`.
- **Context Headroom:** $\sim 50\%$ reserved for execution.

---

## 5. Verification & Acceptance Criteria
1. `python -m ruff check backend/app backend/tests` passes with 0 errors.
2. `cd frontend && npm run typecheck` passes with 0 errors.
3. `cd frontend && npm run build` compiles all 8 routes cleanly.
4. `.github/workflows/ci.yml` parses with valid YAML syntax and clean multi-job separation.
5. All target files strictly conform to the $\le 300$ LOC limit.
