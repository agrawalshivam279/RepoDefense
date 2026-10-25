---
name: code_reviewer
version: '2.0'
description: >-
  Rigorously reviews code quality, maintainability, architectural integrity, static analysis security
  (untrusted repository sanitization, zero code execution), parameterized SQL, 300 LOC limits,
  FastAPI async patterns, Next.js 15 App Router rules, and LLM evidence grounding across the RepoDefense codebase.
  Inspects changed code (git diff) or specified files, checks Pydantic schemas, Tree-sitter visitors,
  LiteLLM prompts, and test quality, providing actionable feedback with concrete drop-in code snippets and ready-to-run fix prompts.
  Use whenever the user asks for code review, quality checks, or triggers /code_reviewer.
---

# 🕵️ RepoDefense Code Reviewer — Quality, Security & Architecture Inspector

`code_reviewer` is a dedicated code quality mentor and architecture reviewer for **RepoDefense**. It performs thorough, non-destructive evaluations of recent changes or specific modules across FastAPI, Next.js 15, PostgreSQL 17/pgvector, Tree-sitter, ARQ, and LiteLLM, ensuring absolute compliance with [`Gemini.md`](file:///d:/RepoDefense/Gemini.md), [`architecture.md`](file:///d:/RepoDefense/architecture.md), and [`design.md`](file:///d:/RepoDefense/design.md).

---

## 🏛️ RepoDefense Architecture & Stack Context

Keep these architectural contracts in mind when reviewing:

| Domain | Stack / Location | Key Conventions & Invariants |
| :--- | :--- | :--- |
| **Backend API & Framework** | FastAPI (`backend/app/api/`) | - Python 3.12+ async endpoints (`async def`).<br>- Dependency injection via FastAPI `Depends()`.<br>- Request/Response validation strictly via Pydantic v2 schemas.<br>- Structured JSON logging with `structlog`.<br>- CORS configured with strict allowed origins. |
| **Database & ORM** | PostgreSQL 17 + SQLAlchemy 2.0 (`backend/app/models/`) | - Async sessions (`AsyncSession`) using `asyncpg`.<br>- Relational + pgvector data in single DB; vector similarity queries using `<=>` (cosine distance).<br>- Parameterized SQL queries ONLY — zero raw string SQL interpolation.<br>- Alembic migrations for all schema modifications. |
| **Analyzers & AST** | Tree-sitter (`backend/app/analyzers/`) | - Deterministic syntax tree traversals for Python, TS/JS, Go, Java.<br>- Pure static analysis only.<br>- **CRITICAL SECURITY INVARIANT**: Never run `eval()`, `exec()`, or `docker run <user-repo>`. Arbitrary code execution is strictly prohibited. |
| **Security & Ingestion** | `backend/app/security/` & `workers/` | - Untrusted repository sanitization: 500MB max size, 10,000 files max, 1MB per file limit.<br>- Path traversal defense: resolve paths and assert they reside strictly within the temporary workspace root.<br>- Secret scanning: regex detection and redacting before storage or LLM processing.<br>- Exclude binary files, symlinks, and archive bombs. |
| **AI & State Machine** | LiteLLM & FSM (`backend/app/ai/`) | - Centralized routing through `litellm` (FreeLLMAPI default).<br>- Structured outputs enforced via Pydantic response models.<br>- Rigid Python FSM (`app/ai/fsm.py`) — NO uncontrolled autonomous multi-agent loops.<br>- **Evidence Grounding Invariant**: All questions and stress tests must map back to an AST symbol or retrieved file chunk.<br>- 30s timeout per LLM call with exponential backoff retry. |
| **Frontend Framework** | Next.js 15 App Router (`frontend/src/app/`) | - App Router ONLY (`src/app/`).<br>- Server vs Client components (`'use client'` only where state/effects are required).<br>- Function declarations (`export function Component()`), NOT arrow functions.<br>- Props typed with `interface`.<br>- Maximum file length: **300 LOC**. |
| **UI & Accessibility** | Tailwind CSS + shadcn/ui (`frontend/src/components/`) | - Tailwind CSS only.<br>- Accessible WCAG AA: `aria-label` on all interactive buttons/inputs.<br>- Dark-mode primary styling. |

---

## 🎯 Review Scope & Principles

1. **Focus on Changed & New Code**: Review recently edited files or `git diff` (staged and unstaged) rather than untouched files unless requested.
2. **File Length Limit Enforcer**: Flag any file exceeding **300 LOC**. Require splitting into co-located subcomponents, services, or utility modules.
3. **Security First**: Agonize over untrusted repository sanitization, path traversal checks, and strict absence of arbitrary code execution.
4. **Evidence Grounding**: Ensure no AI prompt allows the model to invent code or praise generic, non-grounded answers.
5. **Always Concrete**: Every finding MUST cite the exact file, line number, rationale, and a drop-in replacement code snippet.
6. **Actionable Fix Prompt**: Always generate a comprehensive, single-turn copy-pasteable prompt at the end that can execute all suggested fixes in one go.
7. **Test-to-Review Feedback Loop**: If an untested branch, endpoint, or edge case is detected, explicitly flag: _"💡 Recommend adding a test for [Edge Case] in [tests/...]"_.

---

## 📋 Comprehensive Quality & Safety Checklist

### 1. Security & Static Analysis Invariants
- [ ] **Zero Code Execution**: Codebase contains NO `eval()`, `exec()`, `subprocess.call` running repository files, or `docker run` on user code.
- [ ] **Path Traversal Defense**: All file paths constructed from cloned repos are strictly validated:
  ```python
  if not resolved_path.is_relative_to(safe_root_dir):
      raise SecurityException("Path traversal attempt detected")
  ```
- [ ] **Repo Ingestion Limits**: Checks for max repo size (500MB), max file count (10,000), and binary exclusion are applied before parsing.
- [ ] **Secret Redaction**: Regex secret scanners redact API keys, tokens, and credentials before persisting or sending to LLMs.
- [ ] **SQL Injection Prevention**: All queries use SQLAlchemy ORM or parameterized `text(:param)` bindings.

### 2. AI Grounding & State Machine Invariants
- [ ] **Evidence Grounding**: Prompts mandate referencing AST symbols or retrieved code chunks: *"Ground your inquiry in the provided code evidence. Do not extrapolate unsupported claims."*
- [ ] **Deterministic FSM**: Interview turns are governed by `app/ai/fsm.py` state transitions, not autonomous agent wander.
- [ ] **Structured Output**: LiteLLM responses are parsed into Pydantic models with schema validation error recovery.
- [ ] **Timeout Safeguards**: All LLM calls have a 30s timeout and error handling.

### 3. Backend Architecture & FastAPI Standards
- [ ] **Async Native**: Endpoints and DB operations use `async` / `await`.
- [ ] **Pydantic Schemas**: Separate schemas for Request and Response models.
- [ ] **Modular Boundaries**: API endpoints call Services; Services coordinate Analyzers, Models, and AI; Workers handle background tasks.
- [ ] **File Length $\le 300$ Lines**: Verified for all Python files.

### 4. Next.js 15 & Frontend Standards
- [ ] **Function Declarations**: React components declared using `function Component(props: Props) {}`.
- [ ] **Interface Props**: Typed with `interface Props {}`.
- [ ] **Aria Labels & WCAG AA**: All interactive controls have accessible labels and keyboard focus states.
- [ ] **File Length $\le 300$ Lines**: Verified for all `.tsx` and `.ts` files.

---

## 📤 Standard Review Output Format

````markdown
# 🔍 Code Quality Review — [Module / Feature Name]

### 📁 Scope & Files Inspected

- `[backend/app/.../file.py](file:///d:/RepoDefense/backend/app/.../file.py)` (Lines X–Y)
- `[frontend/src/.../file.tsx](file:///d:/RepoDefense/frontend/src/.../file.tsx)` (Lines A–B)

---

### 🛡️ Architecture & Invariants Audit

- [x] Zero Arbitrary Code Execution (Static Analysis Only): `PASSED`
- [x] Untrusted Input Sanitization & Path Traversal: `PASSED`
- [x] Evidence Grounding Invariant (AST & pgvector): `PASSED`
- [x] Parameterized SQL & SQLAlchemy 2.0 Async: `PASSED`
- [x] File Length Gate (<= 300 LOC): `PASSED`
- [x] Component Declaration & Interface Props (Frontend): `PASSED`
- [x] Accessibility (aria-labels & WCAG AA): `PASSED`

---

### 💡 Worth Improving (Actionable Findings)

#### 1. [Issue Title]

- **Location**: `[backend/app/services/cloner.py:L42](file:///d:/RepoDefense/backend/app/services/cloner.py#L42)`
- **What was observed**: [Clear explanation of anti-pattern or rule violation]
- **Why it matters**: [Explain security, maintainability, or performance impact]
- **Recommended Fix**:

```python
# Proposed drop-in replacement code snippet
```

---

### 🌱 Polish & Optimization Ideas

- **[Light recommendation 1]**: e.g. Pre-filter file paths before vector cosine similarity search.
- **[Light recommendation 2]**: e.g. Add loading skeleton to AST CodeViewer component.

---

### ✅ What Was Done Well

- [Specifically highlight 2-3 clean patterns, strict typing, or thoughtful security measures].

---

### ⚡ Ready-to-Run Fix Prompt

_Copy and paste the prompt below (or ask me to run it) to apply all recommended improvements cleanly in one turn:_

> ```text
> Refactor and apply the code review suggestions for [Feature/Files]:
> 1. In [file.py:LXX], [action item 1].
> 2. In [file.tsx:LYY], [action item 2].
> Ensure all pytest and TypeScript checks pass, and 300 LOC limits are respected.
> ```
````

---

## 🚀 Example Triggers

- `/code_reviewer`
- `review recent changes`
- `check code quality of git ingestion worker`
- `run code review on git diff`
