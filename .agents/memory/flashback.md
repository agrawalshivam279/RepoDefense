# 🕰️ FLASHBACK — Project Memory & Decision Ledger

> **Product**: RepoDefense  
> **Tagline**: "Prove that you understand — and can defend — the software you built."  
> **Core Loop**: Evidence → Claim → Defense → Stress Test → Evaluation → Mentor → Re-test  
> **Status**: 🟢 Initialized — Specifications & Foundations Complete (Ready for Phase 1 Scaffolding)  
> **Last Synchronized**: 2026-10-06  

---

## 1. Executive Status Snapshot

RepoDefense is a structured, AI-driven technical interview simulation platform that analyzes a user's GitHub repository, grounds all interaction in actual code evidence, and conducts a multi-stage architectural defense against a Principal Engineer AI persona.

| Module | Stack | Status |
| :--- | :--- | :--- |
| **Frontend Core** | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui | 🟢 Milestone 1.1 Complete |
| **Backend API** | FastAPI (Python 3.12+) + Pydantic v2 + structlog | 🟢 Milestone 1.1 Complete |
| **Database & Vectors** | PostgreSQL 17 + pgvector (Supabase) + SQLAlchemy asyncpg | 🟢 Milestone 1.2 Complete |
| **Authentication** | Supabase Auth (GitHub OAuth + Email/Password) | 🟢 Milestone 1.3 Complete |
| **Background Queue** | ARQ (asyncio + Upstash Redis) | 🟢 Milestone 1.5 Complete |
| **Static Code Ingestion** | Shallow Git Clone + Security Filter (No Code Exec) | 🟢 Milestone 1.5 Complete |
| **AST Analysis** | Tree-sitter (Python, TS/JS, Go, Java) | ⚪ Phase 2 Planned (Milestone 1.7) |
| **Embeddings & RAG** | `all-MiniLM-L6-v2` via sentence-transformers (Local) | ⚪ Phase 2 Planned (Milestone 1.8) |
| **AI LLM Routing** | LiteLLM (OpenAI-compatible, FreeLLMAPI primary) | ⚪ Phase 3 Planned (Milestone 1.9) |
| **Defense State Machine** | Deterministic Python FSM (`backend/app/ai/fsm.py`) | ⚪ Phase 3 Planned (Milestone 1.10) |
| **IDE Code Viewer** | Monaco / Prism code viewer with AST evidence highlights | ⚪ Phase 4 Planned |
| **Evaluation & Export** | Rubric generator + PDF transcript export | ⚪ Phase 5 Planned |

---

## 2. Architecture Decision Records (ADRs)

### ADR-001: Modular Monolith over Microservices
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Microservices introduce network latency, complex debugging, distributed tracing requirements, and deployment overhead that RepoDefense does not need at its current stage.
- **Decision**: Build a single FastAPI backend containing all logic (parsing, API, background job coordination, AI routing) organized into clean domain boundaries (`api/`, `services/`, `analyzers/`, `ai/`, `workers/`, `security/`, `models/`, `schemas/`, `core/`), paired with a Next.js 15 App Router frontend.
- **Consequences**: Fast developer velocity, zero network serialization penalty between internal modules, unified deployment artifact.

### ADR-002: PostgreSQL 17 + pgvector as Single Relational & Vector DB
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Relational data (Users, Sessions, Interviews, Repositories, Claims) must be strongly coupled to vector data (Code Chunks, File Embeddings). Using separate databases (like Pinecone) introduces sync issues and extra infrastructure.
- **Decision**: Use PostgreSQL 17 with the `pgvector` extension hosted on Supabase (free tier).
- **Consequences**: Standard SQL `JOIN`s between code chunks, AST symbols, and interview sessions. ACID compliance, simplified migrations with Alembic, zero additional vector DB costs.

### ADR-003: Static Analysis Only (Strictly No Arbitrary Code Execution)
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Ingesting untrusted user repositories poses massive remote code execution (RCE) and security risks if repositories are compiled or executed.
- **Decision**: Rely 100% on static analysis (Tree-sitter AST parsing, regex, file walking, and embeddings). Never run `eval()`, never compile, and never run `docker run <user-code>`.
- **Consequences**: Complete elimination of sandbox breakout vulnerabilities, lightweight compute requirements, and fully deterministic facts extraction.

### ADR-004: Deterministic Interview State Machine over Autonomous Multi-Agent Loops
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Autonomous multi-agent loops (e.g., AutoGPT, CrewAI) suffer from context drift, non-deterministic loops, hallucinations, and erratic user experiences during timed interviews.
- **Decision**: Enforce interview progression via a rigid, deterministic Python Finite State Machine (`app/ai/fsm.py`). LLM calls are invoked only as pure functions for specific state tasks (`generate_question`, `evaluate_defense`, `stress_test`, `mentor_feedback`).
- **Consequences**: Guaranteed interview flow through the canonical loop (Evidence → Claim → Defense → Stress Test → Evaluation → Mentor → Re-test).

### ADR-005: Local all-MiniLM-L6-v2 Embeddings via sentence-transformers
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Repositories contain hundreds or thousands of code chunks. Generating embeddings via cloud APIs (OpenAI / Cohere) quickly exhausts free-tier credits and adds ingestion latency.
- **Decision**: Run `all-MiniLM-L6-v2` locally via `sentence-transformers` on backend workers.
- **Consequences**: Free, fast, zero API rate limits during repository chunk vectorization. Produces 384-dimensional embeddings stored directly in `pgvector`.

### ADR-006: LiteLLM Abstraction with FreeLLMAPI Primary Provider
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Need vendor independence so models can be swapped (FreeLLMAPI, Groq, OpenAI, Anthropic) without altering application logic or prompt orchestration.
- **Decision**: Standardize all model calls through `litellm` in `backend/app/ai/`. Default to FreeLLMAPI with OpenAI-compatible fallback routing.
- **Consequences**: Zero vendor lock-in; instantaneous provider switching via environment variables.

### ADR-007: ARQ (Asyncio + Redis) for Background Jobs
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Long-running repository ingestion, file walking, AST parsing, and embedding generation must not block FastAPI HTTP request threads.
- **Decision**: Use ARQ backed by Upstash Redis.
- **Consequences**: Native Python `asyncio` compatibility, lightweight configuration compared to Celery, reliable job queuing with timeout handling.

### ADR-008: Tree-sitter for Multi-Language Deterministic AST Parsing
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Need precise extraction of classes, functions, imports, decorators, and line ranges across Python, TypeScript/JavaScript, Go, and Java without compiling code.
- **Decision**: Integrate `tree-sitter` language grammars into `backend/app/analyzers/`.
- **Consequences**: Fast, robust syntax tree navigation, deterministic symbol indexing, and structurally grounded code chunk boundaries.

### ADR-009: Supabase for Auth & Managed Postgres
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Rapid launch requires turnkey GitHub OAuth, email authentication, and managed PostgreSQL with pgvector on generous free tier.
- **Decision**: Use Supabase for Auth, PostgreSQL 17 database, and initial storage needs.
- **Consequences**: Zero AWS infra maintenance, fast client-side and backend JWT validation.

### ADR-010: Mandatory Evidence Grounding & Untrusted Input Sanitization
- **Date**: 2026-10-06
- **Status**: Accepted
- **Context**: Untrusted repositories may attempt prompt injections, zip bombs, or path traversal attacks. LLMs may hallucinate questions about non-existent code.
- **Decision**: Enforce strict input sanitization (500MB max, 10k files max, binary exclusion, path traversal checks, secret redaction). In prompts, wrap untrusted code in strict boundary delimiters and mandate: *"Every question and evaluation must map to an AST symbol or verified code chunk"*.
- **Consequences**: Bulletproof prompt isolation and hallucination-free interviews.

---

## 3. Implementation Phase Tracker

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | Ingestion & Core MVP (Scaffolding, Auth, Git Clone, Security Filter) | 🟡 In Progress |
| **Phase 2** | Analysis & Vectorization (Tree-sitter AST, Chunking, Local Embeddings, pgvector, ARQ) | ⚪ Planned |
| **Phase 3** | The State Machine (LiteLLM, Evidence Grounding, Principal Engineer FSM, Prompts) | ⚪ Planned |
| **Phase 4** | Interactive Frontend (Next.js 15, SSE / WebSocket chat, Monaco/Prism Code Viewer) | ⚪ Planned |
| **Phase 5** | Evaluation & Export (Rubric Scoring, Transcript Generation, PDF & Badge Export) | ⚪ Planned |

---

## 4. Chronological Activity & Change Log

### [2026-10-26] — Step 1.5b: ARQ Background Worker & Git Shallow Clone Pipeline
- **Scope / Module**: Asynchronous Ingestion & Background Worker (`backend/app/core/redis.py`, `backend/app/workers/cloner.py`, `backend/app/workers/main.py`, `backend/app/api/v1/projects.py`, `backend/tests/test_cloner_worker.py`)
- **Details**: Implemented ARQ Redis background job infrastructure and shallow git cloning pipeline. Built connection pool manager `backend/app/core/redis.py` with offline fallback logging. Implemented `backend/app/workers/cloner.py` with strict git branch sanitization (`sanitize_git_branch`) against argument injection, shallow git clone (`--depth=1 --single-branch`) and HEAD commit extraction (`git rev-parse HEAD`) via `asyncio.create_subprocess_exec` in isolated temporary directories. Integrated `sanitize_workspace` to enforce 500 MB / 10,000 files quota, record `RepositorySnapshot` upon completion, and manage state machine transitions (`pending` -> `cloning` -> `cloned` / `failed`). Wired background job enqueuing to `POST /api/v1/projects` and configured application lifespan shutdown hooks. Verified 100% via 10 hermetic unit/integration tests and 33/33 full backend test suite passing. Concludes Milestone 1.5 (Repository Cloning & Security Filter).
- **Key Files**: `backend/app/core/redis.py`, `backend/app/workers/cloner.py`, `backend/app/workers/main.py`, `backend/app/api/v1/projects.py`, `backend/app/main.py`, `backend/pyproject.toml`, `backend/tests/test_cloner_worker.py`, `docs/specs/step-1-5b-arq-cloner-worker.md`

### [2026-10-26] — Step 1.5a: Untrusted Code Sanitizer, Path Traversal Defense & Secret Scanner
- **Scope / Module**: Ingestion Security & Static Code Filter (`backend/app/security/traversal.py`, `backend/app/security/secrets.py`, `backend/app/security/sanitizer.py`, `backend/tests/test_sanitizer.py`)
- **Details**: Built production-grade untrusted repository sanitization and security inspection pipeline under strict zero arbitrary code execution invariants. Implemented `validate_safe_path` using canonical `Path.resolve()` and `Path.is_relative_to()` protecting against directory traversal attacks (`../`) and external symlink escapes. Created `scan_for_secrets` and `redact_secrets` detecting AWS access keys, GitHub personal access tokens, and private keys. Developed `sanitize_workspace` enforcing 500 MB max repo size, 10,000 max file count, and 10 MB single-file limits while excluding noisy/build directories (`.git`, `node_modules`, `venv`, `__pycache__`) and binary content (`is_binary_content`). Verified 100% via 5 hermetic unit tests in `test_sanitizer.py` and 23/23 backend test suite passing.
- **Key Files**: `backend/app/security/traversal.py`, `backend/app/security/secrets.py`, `backend/app/security/sanitizer.py`, `backend/app/security/__init__.py`, `backend/tests/test_sanitizer.py`, `docs/specs/step-1-5a-security-sanitizer-scanner.md`

### [2026-10-26] — Step 1.4b: Next.js 15 Project Dashboard & Add Repository Form
- **Scope / Module**: Frontend Dashboard & Repository Ingestion (`frontend/src/types/project.ts`, `frontend/src/components/domain/ProjectCard.tsx`, `frontend/src/components/domain/AddProjectModal.tsx`, `frontend/src/app/dashboard/page.tsx`, `frontend/src/components/domain/AuthStatus.tsx`)
- **Details**: Implemented full repository project management on the frontend in Next.js 15 App Router. Created `ProjectCard` component with real-time status badges, branch labels, and deletion callbacks. Designed `AddProjectModal` dialog with live GitHub URL format validation, repository slug preview, and API integration with the FastAPI backend using the Supabase JWT Bearer token. Implemented protected `/dashboard` route with authentication session verification, responsive project grid, and empty state fallback. Full Next.js production build (`next build`) and typecheck verified. Concludes Milestone 1.4 (Project Creation & GitHub URL Input).
- **Key Files**: `frontend/src/types/project.ts`, `frontend/src/components/domain/ProjectCard.tsx`, `frontend/src/components/domain/AddProjectModal.tsx`, `frontend/src/app/dashboard/page.tsx`, `frontend/src/components/domain/AuthStatus.tsx`, `docs/specs/step-1-4b-nextjs-project-dashboard.md`

### [2026-10-26] — Step 1.4a: FastAPI Projects API & GitHub URL Validation
- **Scope / Module**: Backend Project API & Repository Ingestion Validation (`backend/app/schemas/project.py`, `backend/app/api/v1/projects.py`, `backend/app/main.py`, `backend/tests/test_projects.py`)
- **Details**: Implemented parameterized GitHub repository URL validation with regex pattern matching, automatic `.git` trimming, and repository slug name normalization (`ProjectCreate`). Created CRUD endpoints for `POST /api/v1/projects` (with 409 Conflict duplicate checks), `GET /api/v1/projects` (with multi-tenant isolation), `GET /api/v1/projects/{id}`, and `DELETE /api/v1/projects/{id}` with cascading cleanup. Verified 100% across 18 backend tests and Next.js 15 production build.
- **Key Files**: `backend/app/schemas/project.py`, `backend/app/api/v1/projects.py`, `backend/app/main.py`, `backend/app/core/security.py`, `backend/tests/test_projects.py`, `docs/specs/step-1-4a-fastapi-projects-api.md`

### [2026-10-26] — Step 1.3b: Next.js 15 Supabase Auth Client, Auth Pages & Session State
- **Scope / Module**: Frontend Authentication & UI (`frontend/src/lib/supabase.ts`, `frontend/src/app/(auth)/login/page.tsx`, `frontend/src/app/(auth)/signup/page.tsx`, `frontend/src/components/domain/AuthStatus.tsx`, `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`)
- **Details**: Installed `@supabase/supabase-js` and configured an SSG-safe browser client in `frontend/src/lib/supabase.ts`. Implemented accessible, dark-themed sign-in and sign-up interfaces supporting Email/Password and GitHub OAuth with client-side validation and confirmation states. Created real-time reactive `AuthStatus` component embedded in global navigation header with Sign Out capability. Full Next.js production build (`next build`) and typecheck verified. Concludes Milestone 1.3 (Authentication).
- **Key Files**: `frontend/package.json`, `frontend/src/lib/supabase.ts`, `frontend/src/app/(auth)/login/page.tsx`, `frontend/src/app/(auth)/signup/page.tsx`, `frontend/src/components/domain/AuthStatus.tsx`, `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`, `docs/specs/step-1-3b-nextjs-supabase-auth-pages.md`

### [2026-10-26] — Step 1.3a: FastAPI Supabase JWT Auth Dependency & Protected Current User Route
- **Scope / Module**: Authentication & API Security (`backend/app/core/config.py`, `backend/app/schemas/auth.py`, `backend/app/core/security.py`, `backend/app/api/v1/auth.py`, `backend/tests/test_auth.py`)
- **Details**: Implemented stateless cryptographic verification of Supabase-issued JWT Bearer tokens with audience verification (`aud="authenticated"`) and algorithm checking (`HS256`). Created `get_current_user` FastAPI dependency resolving user identities from local PostgreSQL 17 or auto-provisioning new user records upon initial authentication. Exposed protected `GET /api/v1/auth/me` endpoint. Verified 100% via hermetic test suite covering unauthenticated rejection (401), invalid/expired token handling, and database synchronization.
- **Key Files**: `backend/app/core/config.py`, `backend/app/schemas/auth.py`, `backend/app/core/security.py`, `backend/app/api/v1/auth.py`, `backend/app/main.py`, `backend/tests/test_auth.py`, `docs/specs/step-1-3a-fastapi-supabase-jwt-auth.md`

### [2026-10-26] — Step 1.2b: Code Analysis & pgvector Vector Models + Alembic Migrations
- **Scope / Module**: Database & Vector Architecture (`backend/app/models/analysis.py`, `backend/app/models/project.py`, `backend/alembic/`, `backend/tests/test_analysis_models.py`)
- **Details**: Created SQLAlchemy 2.0 async models for repository code inspection: `AnalyzedFile`, `CodeSymbol`, `Dependency`, `Evidence`, and `CodeEmbedding` with `Vector(384)` and HNSW cosine distance index `idx_code_embeddings_hnsw` (`m=16, ef_construction=64`). Initialized Alembic async migration suite with auto-escaping for URL special characters (`%%`), generated initial migration `16d48d0545e1_create_initial_schema.py`, and applied to Supabase PostgreSQL 17. Validated 100% via pgvector cosine distance queries and full 9/9 test suite. Completes Milestone 1.2 (Database Models & Migrations).
- **Key Files**: `backend/app/models/analysis.py`, `backend/app/models/project.py`, `backend/app/models/__init__.py`, `backend/alembic/versions/16d48d0545e1_create_initial_schema.py`, `backend/tests/test_analysis_models.py`, `docs/specs/step-1-2b-code-analysis-pgvector-models.md`

### [2026-10-26] — Step 1.2a: SQLAlchemy 2.0 Async Engine & Core Tenancy Models
- **Scope / Module**: Database & Core Models (`backend/app/core/database.py`, `backend/app/models/base.py`, `backend/app/models/project.py`, `backend/tests/test_database.py`)
- **Details**: Configured asynchronous database connection engine and session factory (`AsyncSessionLocal`) with connection pool tuning for Supabase PostgreSQL 17. Defined DeclarativeBase and `TimestampMixin`. Implemented core tenancy domain models: `User` (Supabase Auth reference), `Project` (GitHub repository records), and `RepositorySnapshot` with UUID primary keys and cascading referential integrity. Verified 100% via live database integration tests against Supabase PostgreSQL 17.11.
- **Key Files**: `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/models/base.py`, `backend/app/models/project.py`, `backend/tests/test_database.py`, `docs/specs/step-1-2a-sqlalchemy-core-models.md`

### [2026-10-26] — Step 1.1c: Next.js 15 Frontend Scaffolding & Landing Page
- **Scope / Module**: Frontend UI (`frontend/src/app`, `frontend/src/lib`, `frontend/tailwind.config.ts`)
- **Details**: Scaffolded Next.js 15 (v15.5.28) App Router application with React 19, TypeScript strict mode, and Tailwind CSS. Implemented root layout, global dark-first design theme, 7-Stage Core Loop architecture showcase, and live backend connectivity status badge probing `/api/health`. Full Next.js production build (`next build`) and TypeScript check (`tsc --noEmit`) verified 100%. Concludes Milestone 1.1 (Project Scaffolding).
- **Key Files**: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/globals.css`, `docs/specs/step-1-1c-frontend-scaffold.md`

### [2026-10-26] — Step 1.1b: Local Infrastructure & Docker Compose Setup
- **Scope / Module**: Infrastructure & Containerization (`docker-compose.yml`, `.env.example`, `backend/Dockerfile`, `backend/tests/test_infra.py`)
- **Details**: Configured reproducible local developer infrastructure using Docker Compose with PostgreSQL 17 (`pgvector/pgvector:pg17`) and Redis 7 (`redis:7-alpine`) backed by health checks and named volumes. Defined `.env.example` mapping local and cloud settings. Created multi-stage non-root `backend/Dockerfile` (`appuser` UID 10001). Implemented automated infrastructure tests in `backend/tests/test_infra.py`.
- **Key Files**: `docker-compose.yml`, `.env.example`, `backend/Dockerfile`, `backend/tests/test_infra.py`, `docs/specs/step-1-1b-local-infra-docker.md`

### [2026-10-26] — Step 1.1a: FastAPI Project Scaffold & Health Check
- **Scope / Module**: Backend API (`backend/app/core`, `backend/app/schemas`, `backend/app/main.py`)
- **Details**: Provisioned foundational FastAPI (Python 3.12+) application scaffolding with `pyproject.toml`, Pydantic v2 `BaseSettings` (`backend/app/core/config.py`), CORS middleware, and `/api/health` probe endpoint (`HealthResponse`). Verified 100% via unit tests in `backend/tests/test_health.py` and zero lint errors with `ruff`.
- **Key Files**: `backend/pyproject.toml`, `backend/app/core/config.py`, `backend/app/schemas/health.py`, `backend/app/main.py`, `backend/tests/test_health.py`, `docs/specs/step-1-1a-fastapi-scaffold.md`

### [2026-10-06] — Project Inception & Engineering Tooling Suite Deployed
- **Details**: Established the RepoDefense architectural foundations, product requirement definitions (PRD.md), technical design specifications (design.md), system architecture (architecture.md), implementation plan (implementation_plan.md), and master reference guide (Gemini.md). Configured the full `.agents` autonomous workflow and quality suite (`auto_cycle`, `code_reviewer`, `create_specs`, `doctor`, `eval_persona`, `flashback`, `next_step`, `plan_step`, `ship_step`, `test_runner`, `test_writer`, `update-github`, `verify_step`), alongside the 4 specialized domain engines (`ast_inspector`, `security_auditor`, `eval_rag`, `db_migrator`) cross-connected into `verify_step`, `doctor`, and `create_specs`. Added dual-job GitHub Actions CI workflow (`ci.yml`). Project is primed for Milestone 1.1 scaffolding.
- **Key Files**: `PRD.md`, `design.md`, `architecture.md`, `implementation_plan.md`, `Gemini.md`, `.agents/memory/flashback.md`, `.github/workflows/ci.yml`, `.agents/skills/*/SKILL.md`
