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
| **Frontend Core** | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui | 🟡 Phase 1 Planned (Milestone 1.1) |
| **Backend API** | FastAPI (Python 3.12+) + Pydantic v2 + structlog | 🟡 Phase 1 Planned (Milestone 1.1) |
| **Database & Vectors** | PostgreSQL 17 + pgvector (Supabase) + SQLAlchemy asyncpg | 🟡 Phase 1 Planned (Milestone 1.2) |
| **Authentication** | Supabase Auth (GitHub OAuth + Email/Password) | 🟡 Phase 1 Planned (Milestone 1.3) |
| **Background Queue** | ARQ (asyncio + Upstash Redis) | 🟡 Phase 1 Planned (Milestone 1.5) |
| **Static Code Ingestion** | Shallow Git Clone + Security Filter (No Code Exec) | 🟡 Phase 1 Planned (Milestone 1.5) |
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
