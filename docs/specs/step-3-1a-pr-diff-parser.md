# 📄 Technical Specification: Step 3.1a — GitHub PR Fetcher, Diff Parser & REST API

> **Step ID**: `Step 3.1a`  
> **Target Module**: `backend/app/schemas/pr_analysis.py`, `backend/app/analyzers/diff_parser.py`, `backend/app/api/v1/pull_requests.py`  
> **Git Feature Branch**: `feat/step-3-1a-pr-diff-parser`  
> **Status**: 📋 Ready for Implementation  
> **Created**: 2026-11-08  

---

## 1. Executive Summary

Milestone 3.1 initiates **Phase 3 (Advanced Defense)** by shifting the defense interrogation scope from entire repositories down to specific GitHub Pull Requests. Candidates often claim significant repository work when their actual contribution was a specific PR or slice of commits. Step 3.1a builds the backend ingestion and parsing engine for pull requests:
1. Validates and parses GitHub PR URLs (`https://github.com/{owner}/{repo}/pull/{number}`).
2. Fetches PR metadata and unified diff patches from the GitHub REST API (`https://api.github.com/repos/{owner}/{repo}/pulls/{number}`) using `application/vnd.github.v3.diff`.
3. Implements a deterministic unified diff parser in `backend/app/analyzers/diff_parser.py` that decomposes diffs into structured file changes, hunks, 1-indexed line spans, additions, deletions, and modified symbol contexts.
4. Enforces strict input validation and security sanitization (max 10MB diff, max 50,000 lines, secret redaction, and path traversal protection).
5. Exposes authenticated REST endpoints `POST /api/v1/projects/{project_id}/pr/analyze` and `POST /api/v1/pr/parse-diff`.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Step 1.4a`: Projects API & GitHub URL validation (`backend/app/api/v1/projects.py`)
  - `Step 1.5a`: Security sanitizer, secret scanner & traversal protection (`backend/app/security/`)
  - `Step 2.12b`: Centralized project navigation hub and Phase 2 closure
- **Tech Stack Invariant**:
  - FastAPI (Python 3.12+)
  - Pydantic v2 schemas
  - `httpx` async client for GitHub API communication
  - Zero external code execution
  - Strict $\le 300$ LOC limit per file

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: PR diffs are treated strictly as untrusted text streams; no git hook execution or dynamic compilation.
- [x] **Path Traversal Containment**: All file paths in diff headers (`diff --git a/... b/...`) are checked against directory traversal (`../`, absolute paths, null bytes).
- [x] **Secret Redaction**: Diffs are run through `redact_secrets` before structured persistence to prevent API key leaks from candidate commits.
- [x] **Quota & ReDoS Defense**: Diffs exceeding 10MB or 50,000 lines are rejected with `413 Payload Too Large`. Regex patterns are linear ($O(n)$) without catastrophic backtracking.
- [x] **Multi-Tenant Isolation**: PR analysis for an existing project requires verify that `project.user_id == current_user.id`.

---

## 4. 🧠 Sequential Thinking Strategy

- **Diff Parsing Complexity**:
  - Git diff formats vary: standard unified diff, rename-only without hunks, file creation (`new file mode 100644`), file deletion (`deleted file mode 100644`), binary files (`Binary files a/... and b/... differ`).
  - Hunk header parsing: `@@ -old_start,old_count +new_start,new_count @@ [optional heading]`.
  - Line number tracking: Maintain accurate 1-indexed `old_line_number` and `new_line_number` for each changed line to allow Phase 3 AI questions to point candidates to exact diff line numbers.
- **Edge Cases**:
  - Empty diff (PR with 0 commits or whitespace-only ignored changes).
  - Malformed patch or truncated diff stream.
  - Rate limiting from GitHub REST API (`403 Forbidden` / `429 Too Many Requests` handled with descriptive error response).

---

## 5. Data Contracts & Interfaces (`backend/app/schemas/pr_analysis.py`)

```python
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FileChangeStatus(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    BINARY = "binary"

class DiffLineType(str, Enum):
    ADDITION = "addition"       # '+'
    DELETION = "deletion"       # '-'
    CONTEXT = "context"         # ' '

class ParsedDiffLine(BaseModel):
    line_type: DiffLineType
    content: str
    old_line_number: Optional[int] = None
    new_line_number: Optional[int] = None

class ParsedDiffHunk(BaseModel):
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    header: str
    lines: List[ParsedDiffLine]
    added_count: int
    deleted_count: int

class ParsedFileDiff(BaseModel):
    old_path: Optional[str] = None
    new_path: str
    status: FileChangeStatus
    hunks: List[ParsedDiffHunk]
    total_additions: int
    total_deletions: int
    is_binary: bool = False

class PRAnalysisRequest(BaseModel):
    pr_url: str = Field(..., description="GitHub Pull Request URL")

class PRMetadata(BaseModel):
    pr_number: int
    title: str
    body: Optional[str] = None
    author: str
    base_branch: str
    head_branch: str
    head_sha: str
    state: str
    html_url: str
    created_at: str

class PRAnalysisResponse(BaseModel):
    metadata: PRMetadata
    files: List[ParsedFileDiff]
    total_files_changed: int
    total_additions: int
    total_deletions: int
    summary_narrative: str
```

---

## 6. Step-by-Step Implementation Sequence

1. **Phase A: Pydantic Data Contracts**
   - Create `backend/app/schemas/pr_analysis.py` with `FileChangeStatus`, `DiffLineType`, `ParsedDiffLine`, `ParsedDiffHunk`, `ParsedFileDiff`, and request/response models.
   - Re-export in `backend/app/schemas/__init__.py`.

2. **Phase B: Deterministic Diff Parser Engine**
   - Create `backend/app/analyzers/diff_parser.py` (~180 LOC) with:
     - `parse_unified_diff(diff_text: str) -> List[ParsedFileDiff]`
     - Regex parser for `diff --git a/{old} b/{new}`
     - Hunk header parser `@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@`
     - Per-line 1-indexed coordinate tracking and line sanitization.
     - Redact secrets across all parsed lines using `redact_secrets`.

3. **Phase C: GitHub PR Client & REST API Endpoint**
   - Create `backend/app/api/v1/pull_requests.py` (~160 LOC):
     - `fetch_github_pr_diff(pr_url: str) -> tuple[PRMetadata, str]` using `httpx.AsyncClient` with custom headers (`Accept: application/vnd.github.v3.diff`).
     - Endpoint `POST /api/v1/projects/{project_id}/pr/analyze` (authenticated via Supabase JWT, verifying project ownership).
     - Endpoint `POST /api/v1/pr/parse-diff` (utility endpoint parsing raw diff payload for tests and manual submissions).
   - Mount router in `backend/app/main.py`.

4. **Phase D: Comprehensive Test Suite**
   - Author `backend/tests/test_pr_diff_parser.py` (~220 LOC):
     - Tests for single and multi-file diff parsing.
     - Tests for addition-only, deletion-only, and mixed hunks.
     - Tests for renamed and binary file diffs.
     - Tests for path traversal sanitization and secret redaction.
     - Tests for GitHub PR URL parsing and mock API responses.

---

## 7. Verification & Acceptance Criteria

### Automated Tests
```bash
python -m pytest backend/tests/test_pr_diff_parser.py -v
python -m ruff check backend/app backend/tests
```

### Acceptance Checklist
- [ ] Correctly parses standard unified diff headers, hunks, and line numbers.
- [ ] Enforces path traversal and secret redaction on diff streams.
- [ ] Returns structured `PRAnalysisResponse` with accurate additions, deletions, and metadata.
- [ ] All 4 touched files are strictly $\le 300$ LOC.
- [ ] `ruff check` passes with 0 warnings/errors.
- [ ] 100% unit test pass rate with $\ge 80\%$ line coverage.

---

## 8. 🩺 Specialized Domain Skills Directive

- **Active Skill**: **`security_auditor`**
- **Invariants Enforced**:
  - Zero code execution: diffs parsed via string state machine only.
  - Path traversal defense: validates that `old_path` and `new_path` do not contain `..` or leading slashes.
  - Secret scanner: diff contents pass through `redact_secrets`.
  - Quota limit: rejects raw diffs $> 10$ MB.
