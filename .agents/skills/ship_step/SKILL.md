---
name: ship_step
version: '2.0'
description: >-
  Automated Memory Sync, Git PR & Transition Pipeline for RepoDefense. Seamlessly chains flashback (milestone logging
  and plan checkbox updates) with update-github (conventional commit <100 chars, push, PR creation,
  CI/status check verification polling, squash merge to main, local branch cleanup, remote branch retention),
  followed by next_step to preview the upcoming atomic task. Use whenever code is verified and ready to ship, or calling /ship_step.
---

# 🚀 Ship Step — Memory Sync, Git PR & Transition Pipeline

`ship_step` is the automated release and synchronization engine for **RepoDefense**. It takes verified, high-quality code, logs the achievement in the project's living memory ledger ([`.agents/memory/flashback.md`](file:///d:/RepoDefense/.agents/memory/flashback.md)), checks off the roadmap milestone in [`implementation_plan.md`](file:///d:/RepoDefense/implementation_plan.md), executes the complete Git & GitHub PR squash-merge lifecycle with CI status check polling, and pre-fetches the next atomic task.

---

## 🔄 End-to-End Pipeline Workflow

```mermaid
flowchart TD
    A["Trigger /ship_step"] --> B["🕰️ flashback (Log Milestone & Check Plan [x])"]
    B --> C["🔍 Inspect Git Changes & Generate Conventional Commit (<100 chars)"]
    C --> D["🌿 git push -u origin feat/<slug>"]
    D --> E["🐙 Create GitHub Pull Request via MCP / gh CLI"]
    E --> F["⏳ Poll Actions CI Check Runs via timer (Backend & Frontend)"]
    F --> G{"Actions CI Passed?"}
    G -- "❌ CI Failing / Timeout" --> H["🛑 HARD STOP: Report CI failure & await developer fix"]
    G -- "✅ CI Passed" --> G2{"High-Risk Files Touched?"}
    G2 -- "Yes (Wait CodeRabbit ~8-12m)" --> G3{"Critical/Major Issues?"}
    G3 -- "Yes" --> H2["🛑 HARD STOP: Report Critical/Major findings & AI fix prompts"]
    G3 -- "No (Only Nitpicks/Clean)" --> I["🔀 Squash Merge PR to main"]
    G2 -- "No (Low-Risk Fast-Path)" --> I
    I --> J{"⚠️ Merge Conflict?"}

    J -- "Yes" --> K["🛑 HARD STOP: Report exact conflict & await human guidance"]
    J -- "No" --> L["🌿 Switch to main && git pull origin main"]
    L --> M["🗑️ Delete local branch (Retain origin/feat/<slug> on GitHub)"]
    M --> N["🎯 Query next_step for upcoming atomic task"]
    N --> O["⚡ Output Final Shipping Summary + Next Step Preview"]
```

---

## 🛑 MANDATORY STOP GATE: Anti-Auto-Advance Rule

> **CRITICAL RULE**: After `/ship_step` completes squash-merge, local cleanup, and memory sync, the agent **MUST IMMEDIATELY STOP** and preview the next task in queue.  
> **DO NOT** execute `/plan_step` for the next task.  
> **DO NOT** create a new feature branch.  
> **DO NOT** start coding the next task.  
> Wait for the developer to explicitly trigger `/plan_step` or instruct the next action. The only exception is `/auto_cycle`.

---

## 🔒 Automated Execution Stages

### Stage 1: Living Memory & Plan Synchronization (`flashback`)

1. Appends a chronological entry in [`.agents/memory/flashback.md`](file:///d:/RepoDefense/.agents/memory/flashback.md) under **Section 4: Chronological Activity Log**:
   - Scope / Module impacted (`Backend API` | `Tree-sitter Analyzers` | `AI FSM` | `Frontend UI` | `Security` | `Database`).
   - Summary of changes, new models, routers, parsers, and tests added.
   - List of key files created/modified.
2. Updates checkboxes `[x]` in [`implementation_plan.md`](file:///d:/RepoDefense/implementation_plan.md) for completed tasks.
3. If an architectural decision was established during the feature, records an ADR in `.agents/memory/flashback.md`.

---

### Stage 2: Git Commit, Push & GitHub PR Lifecycle (`update-github`)

1. **Identify Branch**: Confirms current feature branch name (`CURRENT_BRANCH`).
2. **Conventional Commit Message Generation**:
   - Prefix: `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`, `style:`
   - Format: Lowercase, no trailing period.
   - **Length Constraint**: **Strictly under 100 characters**.
3. **Stage & Commit**:
   ```bash
   git add .
   git commit -m "<conventional-message>"
   ```
4. **Push Upstream**:
   ```bash
   git push -u origin CURRENT_BRANCH
   ```
5. **Create Pull Request**:
   - Creates Pull Request into `main` via GitHub MCP / `gh pr create`.
   - Embeds verification metrics in the PR description (pytest count, type check, lint status, security checks).
6. **Risk-Tiered CI & CodeRabbit Gate Protocol**:
   - **Classify PR Risk from Changed Files**:
     - **High-Risk PR** (touches `backend/alembic/**`, `backend/app/models/**`, `backend/app/api/**`, `backend/app/core/**`, `backend/app/security/**`, `backend/app/ai/**`, `backend/app/workers/**`, `.github/workflows/**`, or `.coderabbit.yaml`): **MUST keep the PR open** until the `CodeRabbit` check-run completes (merging early cancels CodeRabbit because `abort_on_close: true`).
     - **Low-Risk / UI Fast-Path PR** (touches only `frontend/**`, `docs/**`, `.agents/**`, tests, or root markdown): merge as soon as GitHub Actions CI passes (still inspect CodeRabbit comments if it already finished before Actions completed).
   - **Poll Check Runs (`schedule` timers, never shell `sleep`)**:
     - GitHub Actions and CodeRabbit report to GitHub's Check Runs API (`/repos/<owner>/<repo>/commits/<head_sha>/check-runs`), not just legacy `get_pull_request_status`. Wait 45–60s after PR creation, then poll check-runs.
     - Verify required GitHub Actions workflows (`Backend Lint & Tests (Python 3.12)`, `Frontend Typecheck & Production Build (Next.js 15)`) reach `completed` + `success`. **Hard Stop** immediately if any Actions check fails (`failure`, `cancelled`, `timed_out`).
     - On **High-Risk PRs**, continue polling via 60–90s `schedule` timers until the `CodeRabbit` check-run finishes (up to ~12 minutes total from PR open). If still pending after 12 minutes, ask the developer whether to keep waiting or merge now.
   - **Automated CodeRabbit Comment Severity Filter**:
     - Once `CodeRabbit` completes (if finished before merge), fetch `coderabbitai[bot]` inline review comments (`/pulls/<number>/comments`) and review summaries (`/pulls/<number>/reviews`).
     - **STOP & Report Before Merging** on any actionable inline comment marked **`Critical`**, **`Major`**, **`Potential issue`**, or inline **`Minor`** tagged `Security`, `Functional Correctness`, `Stability & Availability`, or `Data Integrity`. Present each with file, line range, severity, summary, and CodeRabbit's `Prompt for AI Agents`.
     - **Auto-Ignore & Proceed**: Ignore collapsible `Nitpick comments` / `Additional comments`, wording/style tweaks, and `warning`-mode title/description notices. Note the ignored nitpick count cleanly in the ship summary.
7. **Squash Merge**:
   - Execute **Squash Merge** into `main` via GitHub MCP `merge_pull_request` (`merge_method: "squash"`) or `gh pr merge --squash`.
8. **Local Cleanup & Remote Retention**:
   - Switches to `main`: `git checkout main && git pull origin main`.
   - _Git Recovery_: If `git pull` encounters conflict with uncommitted local work: `git stash` $\rightarrow$ `git pull origin main` $\rightarrow$ `git stash pop` $\rightarrow$ resolve.
   - Deletes local branch: `git branch -D CURRENT_BRANCH`.
   - **Rule**: **Preserves `origin/CURRENT_BRANCH` on GitHub** for revision history and audit trails.

---

### Stage 3: Next Atomic Task Query (`next_step`)

1. Immediately queries [`next_step`](file:///d:/RepoDefense/.agents/skills/next_step/SKILL.md) to inspect the updated plan and memory ledger.
2. Prepares the next atomic, Goldilocks-sized task in queue.

---

## 📤 Standard Output Format

```markdown
# 🚢 /ship_step Complete — [Feature Title]

### 📦 GitHub PR & Merge Summary

- **Commit**: `<type>: <description>` _(Under 100 characters)_
- **Pull Request**: `PR #<NUMBER> — <PR Title>`
- **Risk Tier**: `High-Risk (Waited CodeRabbit)` | `Low-Risk (Fast-Path)`
- **CI Status**: `✅ Passed (Backend & Frontend workflows green)`
- **CodeRabbit Gate**: `✅ 0 Critical/Major findings (ignored N nitpicks)` | `⏭️ Skipped/Cancelled via Fast-Path`
- **Merge Strategy**: `Squash & Merge` ➔ `main` (Up to date)
- **Branch Status**:
  - `✓` Remote branch preserved on GitHub: `origin/feat/<feature-slug>`
  - `✓` Local feature branch cleaned up: `feat/<feature-slug>`

---

### 🕰️ Memory Ledger Synchronized

- **Flashback Log**: [`.agents/memory/flashback.md`](file:///d:/RepoDefense/.agents/memory/flashback.md) updated.
- **Roadmap Checklist**: [`implementation_plan.md`](file:///d:/RepoDefense/implementation_plan.md) marked `[x]` for completed step.

---

### ⏭️ Up Next in Queue

_The next atomic task in the RepoDefense roadmap is:_

> **[Step ID] — [Next Step Title]**  
> _Objective: [1-sentence description of what comes next]_

---

### ⚡ Ready to Continue?

Would you like me to trigger `/plan_step` for **[Next Step ID: Next Step Title]**?
```

---

## 🚀 Triggers

- `/ship_step`
- `"Ship current feature and merge to main"`
- `"Merge PR and update memory"`
- `"Complete step and update github"`
