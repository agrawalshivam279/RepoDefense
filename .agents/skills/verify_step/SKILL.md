---
name: verify_step
version: '2.0'
description: >-
  Automated Quality Gate & Verification Pipeline for RepoDefense. Sequentially chains compiler & lint checks (Stage 0),
  schema & contract validation (Stage 0.5), test_writer (Stage 1A), test_runner (Stage 1B),
  and code_reviewer (Stage 2) to provide total quality verification before code is merged.
  Enforces strict failure halts, incremental test execution, and precision fix prompts.
  Use whenever code implementation is finished, before shipping, or calling /verify_step.
---

# 🧪 Verify Step — Dynamic & Static Quality Gate Pipeline

`verify_step` is the automated quality gate for **RepoDefense**. It guarantees that newly written code **actually works dynamically** (automated unit/integration tests pass with $\ge 80\%$ coverage), **conforms to database, API, and AST schemas** (Pydantic models, SQLAlchemy async models & Tree-sitter contracts), AND **is architecturally sound statically** (reviewed for zero arbitrary code execution, path traversal defense, 300 LOC limit, and evidence grounding) before any code is committed or merged into `main`.

---

## 🔄 End-to-End Pipeline Workflow

```mermaid
flowchart TD
    A["Trigger /verify_step (Feature / Active Files)"] --> S0["⚡ Stage 0: Pre-flight Compiler & Lint Gate<br/>(ruff check, pytest --collect-only, tsc --noEmit) [Max 30s]"]
    S0 --> S0Check{"Syntax / Types Valid?"}
    S0Check -- "❌ Errors" --> S0Fail["🛑 FAST FAIL: Return Diagnostics + Instant Fix Prompt"]
    S0Check -- "✅ Clean" --> S05{"Feature Touches Schemas, Parsers or Models?"}

    S05 -- "Yes" --> S05Val["🔍 Stage 0.5: Schema & Contract Validator<br/>(Pydantic v2, Tree-sitter AST, Safe Path Checks) [Max 15s]"]
    S05Val --> S05Check{"Contracts Valid?"}
    S05Check -- "❌ Schema Drift" --> S05Fail["🛑 STOP: Return Schema Drift Details + Fix Prompt"]
    S05Check -- "✅ Valid" --> B["✍️ Stage 1A: test_writer (Spec-driven test authoring) [Max 120s]"]
    S05 -- "No" --> B

    B --> C["🏃 Stage 1B: test_runner (Execute pytest / npm test) [Max 60s]"]
    C --> D{"🧪 All Tests Pass & Coverage Met?"}

    D -- "❌ Tests Failed" --> E["🛑 HARD STOP: Output Failure Trace + Curated Auto-Fix Prompt"]
    D -- "✅ All Passed" --> F["🕵️ Stage 2: code_reviewer (Static Rules, Security, Zero Code Exec & LOC) [Max 90s]"]

    F --> G{"💡 Code Polish / Invariants Check?"}
    G -- "Issues Found" --> H["Present Detailed Snippets + Single-Turn Fix Prompt"]
    G -- "Clean / Approved" --> I["✅ 100% Quality Gate Passed -> Ready for /ship_step"]
```

---

## 🛑 MANDATORY STOP GATE: Anti-Auto-Advance Rule

> **CRITICAL RULE**: After `/verify_step` completes compiler checks, contract validation, dynamic tests, and static code review, the agent **MUST IMMEDIATELY STOP** and present the Quality Gate Report.  
> **DO NOT** commit changes to git.  
> **DO NOT** push to GitHub.  
> **DO NOT** open a PR or merge into main.  
> **DO NOT** trigger `/ship_step` automatically.  
> Wait for the developer to review and explicitly trigger `/ship_step`. The only exception is `/auto_cycle`.

---

## ⏱️ Timeout & Budget Guardrails

To prevent hangs or infinite loops during verification:

| Stage | Operation | Max Wall-Clock Time | Failure Action |
| :--- | :--- | :--- | :--- |
| **Stage 0** | Compiler & Lint Check | **30s** | Kill process, output type/lint errors |
| **Stage 0.5** | Schema & Contract Validation | **15s** | Halt on schema drift or security flaw |
| **Stage 1A** | `test_writer` Authoring | **120s** | Check syntax, verify test file exists |
| **Stage 1B** | `test_runner` Execution | **60s** per test file | Terminate hung test, diagnose async lock |
| **Stage 2** | `code_reviewer` Review | **90s** | Generate actionable fix prompt |

---

## 🔒 Automated Execution Stages

### Stage 0: Pre-flight Compiler & Lint Gate

Before invoking testing subagents, execute a fast static compilation sweep:

1. **Backend Python Lint & Syntax Check**:
   ```bash
   ruff check backend/app
   pytest backend/tests/ --collect-only
   ```
2. **Frontend TypeScript & Next.js Lint**:
   ```bash
   cd frontend && npx tsc --noEmit && npm run lint
   ```
3. **Fast-Fail Gate**:
   - If syntax, import, lint, or type errors are discovered, **HALT IMMEDIATELY**.
   - Output the exact compiler errors and provide an instant fix prompt without wasting token cycles on dynamic tests.

---

### Stage 0.5: Schema & Contract Validator

_(Triggered conditionally when the feature touches schemas, analyzers, models, or security)_

1. **Target Files**: `backend/app/schemas/`, `backend/app/models/`, `backend/app/analyzers/`, `backend/app/security/`.
2. **Contract Invariants Verified**:
   - **Zero Code Execution & Sanitization**: Validated by [`security_auditor`](file:///d:/RepoDefense/.agents/skills/security_auditor/SKILL.md) (zero eval/exec, path traversal containment via `is_relative_to`, secret redaction).
   - **AST Parsing Precision**: Validated by [`ast_inspector`](file:///d:/RepoDefense/.agents/skills/ast_inspector/SKILL.md) (Tree-sitter symbol boundaries preserved without mid-statement splits).
   - **Database & Vector Schemas**: Validated by [`db_migrator`](file:///d:/RepoDefense/.agents/skills/db_migrator/SKILL.md) and [`eval_rag`](file:///d:/RepoDefense/.agents/skills/eval_rag/SKILL.md) (Vector(384) columns, HNSW index with vector_cosine_ops, Alembic migrations).
   - **Evidence Grounding**: LLM prompt schemas require valid AST symbol and line range arguments.
   - **Pydantic v2 Schema Conformance**: Request and response schemas cleanly validate.
   - **File Length $\le 300$ Lines**: Verified using line counts.
3. If contract drift or security vulnerabilities are detected, **HALT IMMEDIATELY** and report the discrepancy before authoring tests.

---

### Stage 1: Dynamic Behavioral Verification (`test_writer` ➔ `test_runner`)

#### Stage 1A — Test Authoring ([`test_writer`](file:///d:/RepoDefense/.agents/skills/test_writer/SKILL.md)):
1. Reads target feature specification (`docs/specs/...`) and [`Gemini.md`](file:///d:/RepoDefense/Gemini.md) contracts.
2. Employs standardized module fixtures from the **RepoDefense Mock Catalog** (AsyncSession mock, Tree-sitter mock, LiteLLM mock, SentenceTransformer mock).
3. Writes tests targeting:
   - Line coverage: $\ge 80\%$
   - Branch coverage: $\ge 70\%$
4. Saves tests to `backend/tests/` or `frontend/src/**/__tests__/`.

#### Stage 1B — Test Execution (`test_runner`):
1. Runs strictly **AFTER** `test_writer` completes and validates test syntax.
2. Executes targeted test command: `pytest <path-to-test> -v` or `npm test -- <path>`.
3. Parses assertion results and coverage.
4. **Hard Failure Gate**:
   - If any test fails or coverage is unmet, **HALT IMMEDIATELY**.
   - Do NOT run `code_reviewer` on broken code.
   - Output exact file & line number, expected vs actual behavior, failure classification, and an executable auto-fix prompt.

---

### Stage 2: Static Architecture, Security & Code Quality Review ([`code_reviewer`](file:///d:/RepoDefense/.agents/skills/code_reviewer/SKILL.md))

_(Triggered only after all tests pass 100%)_

1. Inspects `git diff` against **RepoDefense Invariants**:
   - **Static Analysis Invariant**: Strictly zero arbitrary code execution (verified by [`security_auditor`](file:///d:/RepoDefense/.agents/skills/security_auditor/SKILL.md)).
   - **Untrusted Input Security**: Aggressive path traversal prevention and secret detection.
   - **File Length Gate**: $\le 300$ LOC per file.
   - **Async DB Sessions**: SQLAlchemy asyncpg transactions handled cleanly.
   - **Evidence Grounding**: Prompt templates enforce strict AST mapping (calibrated by [`eval_persona`](file:///d:/RepoDefense/.agents/skills/eval_persona/SKILL.md)).
2. Formats all suggestions with concrete line numbers, drop-in replacement snippets, and a single-turn copy-pasteable fix prompt.

---

## 📤 Standard Output Format

````markdown
# 🛡️ /verify_step Quality Gate Report — [Feature Name]

### ⚡ Stage 0 — Pre-flight Compilation & Lint

- **Commands**: `ruff check backend/app`, `pytest --collect-only`
- **Status**: `✅ 0 type errors, 0 lint errors`

---

### 🔍 Stage 0.5 — Schema & Contract Validation

- **Status**: `✅ Pydantic schemas validated, zero code execution verified, <= 300 LOC verified`

---

### 🧪 Stage 1 — Dynamic Test Execution

- **Stage 1A (Authoring)**: `test_writer` generated `[backend/tests/test_feature.py](file:///d:/RepoDefense/backend/tests/test_feature.py)`
- **Stage 1B (Execution)**: `pytest backend/tests/test_feature.py -v`
- **Status**: `✅ 5 passed, 0 failed`
- **Coverage**: `Line: 89%, Branch: 81%`

---

### 🚨 Test Failure Diagnosis _(Only if tests fail)_

- **Failed Assertion**: `test_path_traversal_rejection`
- **Classification**: `SECURITY_FILTER_BYPASS`
- **Location**: `[backend/app/services/cloner.py:42](file:///d:/RepoDefense/backend/app/services/cloner.py#L42)`
- **Expected**: `SecurityException` raised for paths escaping sandbox.
- **Root Cause**: Missing boundary check.
- **⚡ Curated Auto-Fix Prompt**:

> ```text
> Update cloner.py to assert path.is_relative_to(safe_root).
> ```

---

### 🕵️ Stage 2 — Static Architecture & Security Review

_(Only displayed if tests pass)_

#### 🛡️ Architecture & Invariants Audit
- [x] Zero code execution (Static analysis only): `PASSED`
- [x] Path traversal & secret redaction verified: `PASSED`
- [x] File length <= 300 lines: `PASSED`
- [x] Evidence grounding intact: `PASSED`
- [x] Parameterized SQL queries: `PASSED`

#### 💡 Worth Improving

- **[Finding Title]**: `[backend/app/services/parser.py:55](file:///d:/RepoDefense/backend/app/services/parser.py#L55)`
- **Observation**: Missing type annotation on helper return value.
- **Recommended Fix**:

```python
# Proposed snippet
```

---

### 🚦 Final Quality Gate Verdict

- [ ] ❌ **BLOCKED**: Compilation, contracts, or tests failed. Run the curated fix prompt above.
- [ ] 🟡 **PASSED WITH POLISH**: Tests pass, but review suggestions are recommended.
- [ ] 🟢 **100% READY TO SHIP**: All tests passed, contracts verified, security checks passed, and code is clean. Ready for `/ship_step`.
````

---

## 🚀 Triggers

- `/verify_step`
- `/verify_step [feature-name]`
- `"Verify implementation and run tests"`
- `"Run full quality gate on recent changes"`
