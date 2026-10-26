# Technical Specification: Step 1.5a — Untrusted Code Sanitizer, Path Traversal Defense & Secret Scanner

> **Milestone**: 1.5 Repository Cloning & Security Filter  
> **Feature Branch**: `feat/step-1-5a-security-sanitizer-scanner`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.5a is to build the deterministic static security engine in `backend/app/security/`. Ingested GitHub repositories are untrusted user input that may contain path traversal attacks, zip bombs, oversized binaries, or sensitive credentials. 

Before any code is analyzed by Tree-sitter or embedded into `pgvector`, this engine ensures:
1. **Path Traversal Prevention**: Guarantees that every accessed file is strictly confined within the isolated temporary repository workspace directory using `Path.is_relative_to()`.
2. **Resource Exhaustion Defense (Zip Bomb / Denial-of-Service)**: Enforces hard limits: maximum total repository size of 500 MB, maximum total file count of 10,000 files, and maximum single-file size of 10 MB.
3. **Binary & Noise Exclusion**: Aggressively skips compiled binaries (ELF, PE, Mach-O), archives, media files, and build/package directories (`node_modules`, `.git`, `venv`, `__pycache__`).
4. **Secret Detection & Redaction**: Detects high-entropy credentials, AWS access keys, GitHub tokens, and private keys via pre-compiled regex, safely redacting them with `[REDACTED_SECRET]` before storage or prompt injection.

---

## 2. Invariants & Security Guardrails

1. **Zero Code Execution**: Static analysis and byte inspection only. Never execute, compile, import, or eval untrusted code.
2. **Hermetic Path Isolation**: Any file path containing `..` or symbolic links resolving outside the sandbox boundary raises `PathTraversalError`.
3. **Deterministic Exclusion**: Binary files detected via file signatures (e.g., null bytes `\x00` in the header or binary extensions) are excluded from analysis.
4. **Fail-Closed Hard Limits**: If a repository exceeds 500 MB or 10,000 files, processing immediately terminates with `SecurityLimitExceededError`.
5. **Max 300 LOC Constraint**: Every file strictly adheres to the 300 LOC limit.

---

## 3. Target Files & Component Specifications

### 1. `backend/app/security/traversal.py` (New File, $\le 60$ LOC)
- `class PathTraversalError(SecurityException)`
- `def validate_safe_path(base_dir: Path, target_path: Path) -> Path`:
  - Resolves both paths: `resolved_base = base_dir.resolve()` and `resolved_target = target_path.resolve()`.
  - Asserts `resolved_target.is_relative_to(resolved_base)`.
  - Rejects broken or outbound symlinks.
  - Returns `resolved_target`.

### 2. `backend/app/security/secrets.py` (New File, $\le 100$ LOC)
- Pre-compiled regex patterns:
  - AWS Access Key ID: `\bAKIA[0-9A-Z]{16}\b`
  - GitHub Token: `\b(?:ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b`
  - Private Key Headers: `-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----`
  - Generic Credentials / API Keys: `(?i)(?:api_key|apikey|secret|token|password)\s*[:=]\s*['"]([a-zA-Z0-9_\-.~+]{16,})['"]`
- `class SecretMatch(BaseModel)`
- `def scan_for_secrets(text: str) -> list[SecretMatch]`
- `def redact_secrets(text: str) -> str`: Drop-in redaction replacing detected tokens with `[REDACTED_SECRET]`.

### 3. `backend/app/security/sanitizer.py` (New File, $\le 180$ LOC)
- Constants:
  - `MAX_REPO_SIZE_BYTES = 500 * 1024 * 1024` (500 MB)
  - `MAX_FILE_COUNT = 10_000`
  - `MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024` (10 MB)
  - `IGNORED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "dist", "build", ".idea", ".vscode"}`
  - `BINARY_EXTENSIONS = {".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".zip", ".tar", ".gz", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".pyc", ".wasm"}`
  - `ALLOWED_EXTENSIONS`: Whitelist of standard code, config, and documentation extensions.
- `def is_binary_content(file_path: Path) -> bool`: Checks binary extension and probes first 1024 bytes for null bytes (`b"\x00"`).
- `class SanitizationSummary(BaseModel)`
- `def sanitize_workspace(workspace_dir: Path) -> SanitizationSummary`:
  - Iterates directory tree securely with `validate_safe_path`.
  - Filters out ignored directories, binaries, and oversized files.
  - Enforces overall size and count limits (raises `SecurityLimitExceededError`).
  - Returns `SanitizationSummary` containing list of sanitized relative paths, file counts, and byte metrics.

### 4. `backend/tests/test_sanitizer.py` (New File, $\le 200$ LOC)
- Hermetic test cases:
  1. `test_path_traversal_detection`: Escaping sandbox via `../` or outbound symlinks triggers `PathTraversalError`.
  2. `test_secret_redaction`: AWS keys, GitHub tokens, and API key pairs are redacted to `[REDACTED_SECRET]`.
  3. `test_binary_exclusion`: Files with null bytes or binary extensions are skipped.
  4. `test_ignored_directories_skipped`: `node_modules/`, `.git/`, and `venv/` contents are omitted.
  5. `test_size_and_count_limits`: Repositories exceeding 500 MB or 10,000 files raise `SecurityLimitExceededError`.
  6. `test_valid_repository_sanitization`: Accurate summary generated for multi-file workspace.

---

## 4. Acceptance Criteria

1. Path traversal attempts are blocked deterministically.
2. Binary files and noisy directories are excluded from downstream indexing.
3. Sensitive tokens and private keys are redacted prior to vectorization or LLM prompting.
4. Repositories exceeding resource quotas are halted before compute is consumed.
5. All new and existing 18 backend tests pass (100%).
6. All files conform to $\le 300$ LOC limit and 0 `ruff` errors.
