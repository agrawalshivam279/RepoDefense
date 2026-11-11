---
name: update-github
version: '2.0'
description: >-
  Commit changes, push to feature branch, create PR via GitHub MCP, verify CI status checks,
  squash merge to main, and clean up the local branch while keeping the remote branch on GitHub for RepoDefense.
  Use whenever the user says "update github", "push to github", "ship feature", or calls /update-github.
---

# 🚀 Update GitHub — Commit, Push, PR & Merge Workflow

This workflow automates the end-to-end Git lifecycle for the **RepoDefense** project: verifying `.gitignore` cleanliness, creating conventional commits under 100 characters, pushing the branch, creating a Pull Request, polling CI status checks, squash merging into `main`, deleting the local branch, **preserving the remote branch on GitHub**, synchronizing living memory and roadmap checklists, and previewing the next step.

---

## Workflow Steps

### Step 1 — Verify & Identify Current Branch

```bash
git branch --show-current
git status -s
```

- Store the output as `CURRENT_BRANCH`.
- If on `main` and uncommitted changes exist:
  - Generate a descriptive branch name based on the changes (e.g. `feat/step-1-1-scaffold`).
  - Create and switch to it: `git checkout -b <new-branch-name>`
  - Set `CURRENT_BRANCH = <new-branch-name>`
- **Safety check**: Scan `git status -s` for accidentally untracked `.env`, `__pycache__/`, `*.pyc`, `node_modules/`, `.next/`, or `.pytest_cache/`. Cross-check `.gitignore` before proceeding.

---

### Step 2 — Generate Conventional Commit Message

Inspect changes and project context:

```bash
git diff --staged
git diff
git status -s
```

Consult [`.agents/memory/flashback.md`](file:///d:/RepoDefense/.agents/memory/flashback.md), [`implementation_plan.md`](file:///d:/RepoDefense/implementation_plan.md), or [`Gemini.md`](file:///d:/RepoDefense/Gemini.md).

#### Commit Message Rules:
- **Type Prefix**:
  - `feat:` new feature or capability
  - `fix:` bug fix or error resolution
  - `chore:` config, dependencies, tooling, or setup
  - `docs:` documentation, specifications, or markdown notes
  - `refactor:` code refactoring without behavior change
  - `test:` adding or updating tests
  - `style:` whitespace, formatting, or UI styling adjustments
- **Format**: Lowercase prefix and message description.
- **No Period**: Do not add a trailing period.
- **Length Constraint**: **Strictly under 100 characters**.
- **User-Centric**: Describe what the change accomplishes.

**Examples**:
- `feat: implement tree-sitter python ast symbol extractor` (53 chars)
- `fix: prevent path traversal during shallow repo cloning` (55 chars)
- `chore: configure postgres 17 pgvector alembic migration` (55 chars)

---

### Step 3 — Stage and Commit

Stage all project modifications:

```bash
git add .
git commit -m "<generated-message>"
```

> [!CAUTION]
> Confirm `.gitignore` covers `.env`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, and `.next/` before staging.

Report:
```text
✓ Committed — <generated-message>
```

---

### Step 4 — Push to Remote Feature Branch

Push current branch to GitHub remote:

```bash
git push -u origin CURRENT_BRANCH
```

#### Git Push Recovery:
- If push fails due to upstream divergence: run `git pull --rebase origin CURRENT_BRANCH` and retry.
- If push fails due to missing upstream: run `git push --set-upstream origin CURRENT_BRANCH`.

Report:
```text
✓ Pushed — CURRENT_BRANCH
```

---

### Step 5 — Create Pull Request

Use GitHub MCP (or GitHub CLI `gh pr create`) to create a PR from `CURRENT_BRANCH` into `main`.

- **PR Title**: Concise Conventional Commits title matching `.coderabbit.yaml` (e.g., `feat: implement tree-sitter python ast symbol extractor`).
- **PR Description Template**:

```markdown
## What this PR does

<1-2 paragraph summary of the feature, backend services, or UI components added>

## Key Changes

- <Bullet list of modified modules, models, parsers, and tests>

## Verification

- **Automated Tests**: X/Y passed (pytest / Jest)
- **Type & Lint Check**: ✅ Clean (`ruff`, `tsc --noEmit`)
- **Security Invariants**: ✅ Zero arbitrary code execution, path traversal validated
- **Evidence Grounding**: ✅ AST symbols and vector schemas verified
```

Report:
```text
✓ PR created — <PR URL or PR Number>
```

---

### Step 6 — Verify Actions CI, Run Risk-Tiered CodeRabbit Gate & Merge

Before merging, inspect PR risk from the changed files and verify CI + CodeRabbit:

1. **Classify PR Risk Tier** (inspect committed diff against `main`):
   - **High-Risk PR** if any changed file is in `backend/alembic/**`, `backend/app/models/**`, `backend/app/api/**`, `backend/app/core/**`, `backend/app/security/**`, `backend/app/ai/**`, `backend/app/workers/**`, `.github/workflows/**`, or `.coderabbit.yaml` (or if the developer explicitly asked to wait for CodeRabbit).
   - **Low-Risk / UI Fast-Path PR** otherwise (e.g., `frontend/**`, `docs/**`, `.agents/**`, unit tests, or markdown updates).
2. **Wait & Poll GitHub Check Runs (`schedule` timers — never shell `sleep`)**:
   - Wait 45–60 seconds after creating the PR, then query the **GitHub Check Runs API** (`/repos/<owner>/<repo>/commits/<head_sha>/check-runs` via REST fetch or `gh pr checks`) as well as `get_pull_request_status` (because GitHub Actions and CodeRabbit report to check-runs, whereas `get_pull_request_status` only checks legacy commit statuses).
   - Poll every 45–60s until GitHub Actions (`Backend Lint & Tests (Python 3.12)`, `Frontend Typecheck & Production Build (Next.js 15)`) finish. If any GitHub Actions check fails (`failure`, `cancelled`, `timed_out`), **HALT IMMEDIATELY** and notify the developer.
3. **CodeRabbit Gate (Keep PR Open Until Finished on High-Risk PRs)**:
   - Because `.coderabbit.yaml` sets `abort_on_close: true`, merging a PR immediately cancels any still-running `CodeRabbit` check (`Review failed: The pull request is closed`).
   - On **High-Risk PRs**: keep the PR open and poll with 60–90s `schedule` timers until the `CodeRabbit` check-run reaches `completed` (up to ~12 minutes from PR creation; if still pending at 12 minutes, stop and ask the developer whether to keep waiting or merge now).
   - On **Low-Risk Fast-Path PRs**: do not wait for CodeRabbit once GitHub Actions CI passes; still check its comments if CodeRabbit already finished before Actions completed.
4. **Filter CodeRabbit Comments by Severity** (whenever `CodeRabbit` completed):
   - Fetch inline review comments (`get_pull_request_comments` / `/pulls/<number>/comments`) and review bodies (`/pulls/<number>/reviews`) authored by `coderabbitai[bot]`.
   - **Action Required (HALT Merge)**: Any unresolved inline comment marked **`Critical`**, **`Major`**, **`Potential issue`**, or inline **`Minor`** categorized under `Security`, `Functional Correctness`, `Stability & Availability`, or `Data Integrity`. Report the file, lines, summary, and CodeRabbit `Prompt for AI Agents` to the developer and await confirmation to fix before merging.
   - **Auto-Ignore (Non-Blocking)**: Ignore collapsible `Nitpick comments` / `Additional comments`, formatting/style suggestions, and `warning` pre-merge checks (`title`/`description`).
5. **Squash Merge**:
   - Once CI passes and the CodeRabbit gate is clear (or bypassed via Low-Risk Fast-Path), execute **Squash Merge** into `main` via GitHub MCP `merge_pull_request` (`merge_method: "squash"`) or `gh pr merge --squash`.

Report:
```text
✓ CI checks passed (Backend & Frontend)
✓ CodeRabbit gate — <0 Critical/Major (ignored N nitpicks) | Fast-Path skipped>
✓ PR merged to main (Squash Merge)
```

---

### Step 7 — Remote Branch Retention

> **Important Rule**: Do **NOT** delete the remote branch on GitHub. Preserve it for revision history and audit trails.

Report:
```text
✓ Remote branch retained on GitHub — origin/CURRENT_BRANCH
```

---

### Step 8 — Switch to Main & Pull Latest

Switch back to the local `main` branch and pull the merged changes:

```bash
git checkout main
git pull origin main
```

#### Git Pull Recovery:
- If `git pull` encounters a conflict with uncommitted local work: `git stash` $\rightarrow$ `git pull origin main` $\rightarrow$ `git stash pop` $\rightarrow$ resolve.

Report:
```text
✓ Switched to main — up to date
```

---

### Step 9 — Delete Local Feature Branch Only

Delete the local feature branch to keep the local workspace clean:

```bash
git branch -D CURRENT_BRANCH
```

Report:
```text
✓ Local branch deleted — CURRENT_BRANCH
```

---

### Step 10 — Flashback Memory Sync & Roadmap Checkbox

Perform a two-part memory synchronization:

1. **Ledger Update**: Update [`.agents/memory/flashback.md`](file:///d:/RepoDefense/.agents/memory/flashback.md) under the Chronological Activity Log with an entry noting the merged PR, commit message, and PR number.
2. **Roadmap Checkbox Tick**: Open root [`implementation_plan.md`](file:///d:/RepoDefense/implementation_plan.md) and mark the corresponding step's checkbox from `[ ]` to `[x]`.

---

### Step 11 — Preview Next Step

Invoke [`next_step`](file:///d:/RepoDefense/.agents/skills/next_step/SKILL.md) to read `implementation_plan.md` and surface the next unchecked atomic task so the forward path is clear immediately after the PR merges.

---

## Final Output Format

```text
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
/update-github complete
✓ Committed — <message>
✓ Pushed — <branch>
✓ CI checks passed
✓ CodeRabbit gate (<status>)
✓ PR created and merged (#<PR_NUMBER>)
✓ Remote branch preserved on GitHub (origin/<branch>)
✓ Switched to main (up to date)
✓ Local branch deleted (<branch>)
✓ Flashback ledger synchronized
✓ implementation_plan.md step marked [x]
✓ Next step preview: <next-step-summary>
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
```

---

## Safety & Exception Rules

1. **Never commit directly to `main`**: Always branch off before committing.
2. **Always squash merge**: Keeps `main` commit history clean and linear.
3. **Never delete remote branches**: Only remove the local branch.
4. **Push Upstream Handling**: If push fails due to missing upstream, use `git push --set-upstream origin CURRENT_BRANCH`.
5. **CI & High-Risk CodeRabbit Gate**: Never squash-merge if GitHub Actions CI fails. On High-Risk PRs (migrations, auth/security, backend API/core, AI FSM, workers, CI/CodeRabbit configs), wait for `CodeRabbit` to finish before merging and halt if it posts `Critical` / `Major` / `Potential issue` findings (ignoring collapsible `Nitpick` / `Additional comments`).
6. **Gitignore Safety**: Always validate `.gitignore` coverage before `git add .` to prevent accidental commits of secrets, virtualenvs, or caches.
7. **Pull Conflict Recovery**: If `git pull origin main` fails after squash merge, stash $\rightarrow$ pull $\rightarrow$ pop $\rightarrow$ resolve.
