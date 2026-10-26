# 📋 Technical Specification — Step 1.9: Git Commit & Contributor History Analyzer

> **Module**: Codebase Ingestion & Git Metadata Analysis  
> **Status**: Ready for Implementation  
> **Target Files**:
> - `backend/app/analyzers/git.py` (New — Git log extractor, contributor statistics aggregator, Pydantic schemas)
> - `backend/app/analyzers/__init__.py` (Update — Re-export git history schemas and functions)
> - `backend/app/workers/cloner.py` (Update — Update shallow clone depth to 100 and wire git extraction)
> - `backend/tests/test_git_history.py` (New — Hermetic unit and integration tests)

---

## 1. Context & Architectural Motivation

Per **Gemini.md** (Section 5 & 6) and **architecture.md** (Section 3 & 9):
RepoDefense grounds technical interview questions in code evidence and architectural ownership.
A critical ownership signal is understanding *who* wrote which parts of a codebase. If a candidate claims to have architected a system, but git history reveals that 95% of the codebase was authored by another developer, the AI Principal Engineer persona uses this factual grounding to pose deeper questions probing actual comprehension.

Milestone 1.9 implements deterministic git log analysis and contributor extraction. The analyzer extracts recent commits, authorship timelines, files touched per commit, and computes contributor activity metrics without executing arbitrary repository code.

---

## 2. Invariants & Security Rules

1. **Zero Code Execution**:
   - The git analyzer strictly runs read-only git queries (`git log --no-color`).
   - It never executes git hooks, scripts, or checkout filters.
   - Subprocesses are spawned using `asyncio.create_subprocess_exec` with explicit argument arrays, preventing shell injection.
2. **Untrusted Workspace Safety**:
   - The analyzer verifies `repo_dir.is_dir()` and `(repo_dir / ".git").exists()`.
   - If git execution fails or the workspace lacks valid git history, the analyzer returns an empty `GitHistorySummary` rather than crashing the background worker.
   - Subprocess execution is bounded by an explicit timeout (`timeout=30.0`).
3. **Deterministic Delimited Parsing**:
   - Uses unit separator character (`%x1f` / `\x1f`) for `git log --pretty=format:` fields to completely avoid delimiter collisions with commas, colons, or quotes in commit messages.
4. **Goldilocks 5-Gate Granularity**:
   - Max 4 target files.
   - All files $\le 300$ LOC.
   - Single architectural concern: git commit history and contributor extraction.
   - Reserved $\ge 40\%$ context window headroom.

---

## 3. Data Contracts & Pydantic Schemas

### `GitCommitMetadata`
```python
class GitCommitMetadata(BaseModel):
    commit_hash: str = Field(..., description="40-character hex commit SHA")
    author_name: str = Field(..., description="Commit author display name")
    author_email: str = Field(..., description="Commit author email address")
    committed_at: datetime = Field(..., description="ISO 8601 commit timestamp with timezone")
    message: str = Field(..., description="Commit subject line")
    files_changed: list[str] = Field(default_factory=list, description="Repository-relative file paths touched in commit")
```

### `ContributorStats`
```python
class ContributorStats(BaseModel):
    name: str = Field(..., description="Contributor name (latest observed)")
    email: str = Field(..., description="Normalized lowercase email address")
    commit_count: int = Field(..., description="Number of commits authored in sample")
    percentage: float = Field(..., description="Percentage of total sampled commits (0.0 to 100.0)")
    files_touched_count: int = Field(..., description="Count of distinct files modified by contributor")
    first_commit_at: Optional[datetime] = Field(None, description="Timestamp of earliest commit in sample")
    last_commit_at: Optional[datetime] = Field(None, description="Timestamp of most recent commit in sample")
```

### `GitHistorySummary`
```python
class GitHistorySummary(BaseModel):
    total_commits: int = Field(0, description="Total number of commits parsed (up to max_commits)")
    commits: list[GitCommitMetadata] = Field(default_factory=list, description="Chronological list of parsed commits (most recent first)")
    contributors: list[ContributorStats] = Field(default_factory=list, description="Contributors sorted by commit count descending")
    primary_author: Optional[str] = Field(None, description="Name of the top contributor by commit count")
```

---

## 4. Implementation Logic

### 4.1. Git Log Extractor (`backend/app/analyzers/git.py`)
- **Signature**: `async def extract_git_history(repo_dir: Path, max_commits: int = 100, timeout: float = 30.0) -> GitHistorySummary`
- **Subprocess Command**:
  ```python
  cmd = [
      "git",
      "-C",
      str(repo_dir),
      "log",
      f"-n{max_commits}",
      "--no-color",
      "--pretty=format:%H%x1f%an%x1f%ae%x1f%aI%x1f%s",
      "--name-only",
  ]
  ```
- **Parsing Algorithm**:
  - Split stdout by newline.
  - When a line contains `\x1f`, split into 5 tokens: `hash`, `author_name`, `author_email`, `committed_at` (parse via `datetime.fromisoformat`), `message`.
  - Non-empty lines following a commit header before the next header represent file paths changed in that commit.
  - Filter out empty lines.
- **Contributor Aggregation**:
  - Key by `author_email.strip().lower()`.
  - Track author commit counts, unique modified file paths, earliest `committed_at`, latest `committed_at`, and most recent `author_name`.
  - Compute percentages: `round((count / total_commits) * 100.0, 1)`.
  - Sort contributors descending by `commit_count`.
  - Set `primary_author = contributors[0].name` if contributors exist.

### 4.2. Clone Depth Update & Pipeline Wiring (`backend/app/workers/cloner.py`)
- Update `run_git_shallow_clone`:
  ```python
  async def run_git_shallow_clone(
      github_url: str,
      branch: str,
      target_dir: Path,
      depth: int = 100,
      timeout: float = 120.0,
  ) -> str:
      ...
      clone_cmd = [
          "git",
          "clone",
          f"--depth={depth}",
          "--single-branch",
          "--branch",
          safe_branch,
          github_url,
          str(target_dir),
      ]
  ```
- In `clone_and_sanitize_repository`:
  - After dependency extraction:
    ```python
    git_history = await extract_git_history(temp_dir, max_commits=100)
    ```
  - Format top contributors in summary string:
    ```python
    contributors_str = ", ".join(
        f"{c.name} ({c.percentage}%, {c.commit_count} commits)"
        for c in git_history.contributors[:3]
    )
    summary_text = (
        f"Cloned commit {commit_hash[:7]} with {len(files_meta)} files "
        f"({total_lines} lines, {size_mb:.2f} MB, {total_symbols} symbols, "
        f"{total_deps} dependencies). Languages: {top_langs_str}. "
        f"Contributors ({git_history.total_commits} commits): {contributors_str or 'None'}."
    )
    ```
  - Include git stats in the job return payload:
    `"total_commits": git_history.total_commits`,
    `"contributor_count": len(git_history.contributors)`,
    `"top_contributor": git_history.primary_author`

---

## 5. Testing & Verification Plan

### Test Suite (`backend/tests/test_git_history.py`)
1. **`test_extract_git_history_multi_commit`**:
   - Creates a temporary git repo using `git init`, configures local user, creates multiple commits across two different authors modifying distinct files.
   - Verifies:
     - `total_commits == expected`
     - Commit hashes, author names, emails, dates, messages, and files changed match exact expectations.
     - Contributor statistics correctly calculate counts, percentages (summing to ~100%), and touched files.
     - `primary_author` matches the author with the majority of commits.
2. **`test_extract_git_history_single_commit`**:
   - Verifies 100.0% attribution for a single-commit repo.
3. **`test_extract_git_history_empty_repo`**:
   - Verifies that an empty initialized repo (0 commits) returns `total_commits=0`, empty lists, and `primary_author=None` without throwing.
4. **`test_extract_git_history_non_git_directory`**:
   - Points extractor to a non-git directory; asserts graceful fallback without exceptions.
5. **`test_extract_git_history_max_commits_limit`**:
   - Generates 15 commits, requests `max_commits=5`, verifies exactly 5 most recent commits are returned.
6. **`test_cloner_worker_git_history_integration`**:
   - Tests `clone_and_sanitize_repository` execution on a local mock repo, asserting `snapshot.summary` contains contributor metrics and return dict contains `total_commits`.

---

## 6. Acceptance Criteria

- [ ] `extract_git_history` extracts commit hash, author name, email, ISO date, message, and files touched.
- [ ] `ContributorStats` groups by author email, computes commit count, percentage, unique files touched, and date range.
- [ ] Non-git directories and empty repos are handled gracefully with zero unhandled exceptions.
- [ ] `run_git_shallow_clone` uses `--depth=100` ensuring up to 100 commits are available for analysis.
- [ ] `cloner.py` incorporates contributor stats into `RepositorySnapshot.summary` and worker return values.
- [ ] All new tests in `test_git_history.py` pass hermetically.
- [ ] Full backend test suite passes 100% without regression ($\ge 74$ tests).
