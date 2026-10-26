# Technical Specification: Step 1.5b — ARQ Background Worker & Git Shallow Clone Pipeline

> **Milestone**: 1.5 Repository Cloning & Security Filter  
> **Feature Branch**: `feat/step-1-5b-arq-cloner-worker`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.5b is to build the asynchronous repository ingestion pipeline using ARQ and Redis. When a user submits a valid GitHub repository URL via `POST /api/v1/projects`, the backend must not block the HTTP request while cloning and inspecting code. Instead:

1. The project record is created with initial status `pending`.
2. A background task `clone_and_sanitize_repository` is enqueued into the ARQ Redis queue.
3. The ARQ worker picks up the job:
   - Updates `Project.status = "cloning"`.
   - Safely performs a shallow git clone (`git clone --depth=1 --single-branch`) into an isolated temporary directory.
   - Deterministically extracts the current commit hash (`git rev-parse HEAD`).
   - Runs `sanitize_workspace(temp_dir)` from `backend/app/security/sanitizer.py` to enforce the 500 MB / 10,000 files quota and filter noise/binaries.
   - On success: Creates a `RepositorySnapshot` record and transitions `Project.status = "cloned"`.
   - On failure (timeout, git error, or quota exceeded): Records the error and transitions `Project.status = "failed"`.
   - Always cleans up the temporary workspace directory.

---

## 2. Invariants & Security Guardrails

1. **Zero Code Execution**: Strictly execute standard `git clone` and `git rev-parse HEAD` CLI arguments via `asyncio.create_subprocess_exec` (never `shell=True`). Never execute scripts, hooks, or package installers from the cloned repo.
2. **Flag Injection Prevention**: Sanitize the branch name before passing it to git CLI to prevent argument injection attacks (e.g. branch names starting with `--upload-pack` or dashes).
3. **Hermetic Temporary Workspace**: Each clone occurs in a dedicated `tempfile.TemporaryDirectory()`. The directory is cleaned up in a `finally` block regardless of outcome.
4. **Resilient Queueing & Offline Graceful Degradation**: If Redis is temporarily unreachable during `POST /projects`, log a warning and return the created project rather than failing the HTTP request with a 500 internal server error.
5. **Strict 5-Gate Goldilocks Compliance**:
   - $\le 4$ target source files modified/created.
   - $\le 300$ LOC per file.
   - Single architectural concern: Asynchronous cloning, sanitization, and snapshot creation.
   - Complete hermetic test verification.

---

## 3. Target Files & Component Specifications

### 1. `backend/app/core/redis.py` (New File, $\le 70$ LOC)
- `def get_redis_settings() -> RedisSettings`:
  - Parses `settings.REDIS_URL` into an ARQ `RedisSettings` instance.
- `async def get_arq_redis_pool() -> ArqRedis | None`:
  - Creates or returns a cached `ArqRedis` connection pool using `create_pool(get_redis_settings())`.
  - Catches connection errors gracefully, returning `None` if Redis is offline.
- `async def enqueue_clone_job(project_id: uuid.UUID) -> str | None`:
  - Enqueues `"clone_and_sanitize_repository"` with argument `str(project_id)`.
  - Returns the ARQ job ID if successfully queued, or `None` if Redis is unavailable.

### 2. `backend/app/workers/cloner.py` (New File, $\le 160$ LOC)
- `def sanitize_git_branch(branch: str) -> str`:
  - Validates branch name: must match `^[a-zA-Z0-9_\.\/-]+$` and must NOT start with `-`.
  - Raises `ValueError` on malicious or invalid branch inputs.
- `async def run_git_shallow_clone(github_url: str, branch: str, target_dir: Path, timeout: float = 120.0) -> str`:
  - Executes: `["git", "clone", "--depth=1", "--single-branch", "--branch", branch, github_url, str(target_dir)]`.
  - Executes: `["git", "-C", str(target_dir), "rev-parse", "HEAD"]` to retrieve the 40-character commit hash.
  - Raises `RuntimeError` or `asyncio.TimeoutError` on failure.
- `async def clone_and_sanitize_repository(ctx: dict, project_id: str) -> dict`:
  - Entrypoint for the ARQ worker.
  - Opens an `AsyncSessionLocal()` session.
  - Queries `Project` where `id == UUID(project_id)`.
  - Transitions `project.status = "cloning"`.
  - Inside a `tempfile.TemporaryDirectory()` context:
    - Runs `run_git_shallow_clone`.
    - Runs `sanitize_workspace(temp_dir)`.
    - Creates or updates `RepositorySnapshot(project_id=project.id, commit_hash=commit_hash, summary=...)`.
    - Transitions `project.status = "cloned"`.
  - Error handling:
    - Catches `SanitizationQuotaExceededError`, `RuntimeError`, `ValueError`, `asyncio.TimeoutError`, or generic exceptions.
    - Transitions `project.status = "failed"`.
    - Commits session and logs structured error.
  - Returns result dictionary with `status`, `commit_hash`, and `file_count`.

### 3. `backend/app/workers/main.py` (New File, $\le 45$ LOC)
- `class WorkerSettings`:
  - `functions = [clone_and_sanitize_repository]`
  - `redis_settings = get_redis_settings()`
  - `on_startup = startup`
  - `on_shutdown = shutdown`
  - `max_jobs = 10`
  - `job_timeout = 300`

### 4. `backend/app/api/v1/projects.py` (Edit Existing File, $\le 140$ LOC)
- Update `create_project`:
  - After `await db.commit()` and `await db.refresh(project)`:
  - Invokes `await enqueue_clone_job(project.id)`.

### 5. `backend/pyproject.toml` (Edit Existing File)
- Add `arq>=0.26.0` and `redis>=5.0.0` to project dependencies.

---

## 4. Verification Plan

### Automated Test Suite: `backend/tests/test_cloner_worker.py`
1. **Branch Sanitization Test**:
   - Asserts valid branches (`main`, `feature/xyz`, `v1.0.0`) are accepted.
   - Asserts dangerous branches (`--upload-pack=evil`, `-f`, `invalid branch with spaces`) raise `ValueError`.
2. **Git Clone & Snapshot Success Integration Test**:
   - Simulates a repository clone (mocked `run_git_shallow_clone` or local git init fixture).
   - Verifies project state transitions from `pending` -> `cloning` -> `cloned`.
   - Verifies `RepositorySnapshot` is created with the exact commit hash and attached to the project.
3. **Sanitization Failure Test**:
   - Simulates a quota violation (e.g. file size or count exceeded).
   - Verifies project status is updated to `failed`.
4. **Git Command Failure Test**:
   - Simulates a git subprocess non-zero exit code (e.g. non-existent repository or network timeout).
   - Verifies project status is updated to `failed` cleanly without uncaught exceptions.
5. **ARQ Redis Pool & Enqueueing Test**:
   - Verifies `enqueue_clone_job` returns `None` gracefully without throwing an uncaught exception when Redis is not running or unreachable.

### Acceptance Criteria
- Full backend pytest suite passing (`pytest backend/tests`).
- Ruff linter passing with zero warnings or formatting errors.
- Frontend production build (`npm run build`) remains clean and unbroken.
- Zero arbitrary code execution maintained.
