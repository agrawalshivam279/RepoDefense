# Mandatory Verification Gate (/verify_step) Rule

> **Scope**: All feature implementations, refactors, and milestone deliveries across RepoDefense.  
> **Status**: NON-NEGOTIABLE CORE INVARIANT  

## The Strict Development Lifecycle
The development sequence for any feature or milestone MUST ALWAYS follow:
1. **`Plan`** (`/plan_step`) ➔ Plan, branch, and author specification. Stop and await approval.
2. **`Implement`** ➔ Write application code (strictly $\le 300$ LOC per file).
3. **`Verify`** (`/verify_step`) ➔ **MANDATORY GATE**. Execute:
   - **Stage 0**: Pre-flight compiler, lint & type checks (`ruff check`, `tsc --noEmit`, `next build`).
   - **Stage 0.5**: Specialized Domain Skill & Contract Validator (`security_auditor`, `ast_inspector`, `db_migrator`, `eval_rag`, `eval_persona`).
   - **Stage 1**: Dynamic tests execution (`pytest`, `test_writer` / `test_runner`).
   - **Stage 2**: Static architecture review (`code_reviewer`, 300 LOC limit, zero code execution, parameterized queries).
   - **Present Report**: Output the formal `# 🛡️ /verify_step Quality Gate Report` and STOP.
4. **`Ship`** (`/ship_step`) ➔ Living memory sync (`flashback.md`), git commit, push, PR, CI polling, squash merge.

## Prohibited Behaviors
- **NEVER** jump directly from Implementation to `/ship_step`.
- **NEVER** ask or prompt the user to ship before `/verify_step` has been fully executed and its formal report presented.
- If a test or command hangs or fails during verification, diagnose and resolve it, but **NEVER skip the `/verify_step` Quality Gate**.
