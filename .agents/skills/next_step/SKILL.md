---
name: next_step
version: '2.0'
description: >-
  Mandatorily consults Gemini.md, implementation_plan.md, and flashback.md to determine the exact
  next actionable step for RepoDefense. Enforces the 5-Gate Goldilocks Task Granularity Standard with
  FastAPI / Next.js 15 full-stack calibration (40-50% context headroom), sub-slices oversized steps,
  and automatically hands over to create_specs to establish the Git branch and technical specification.
  Use whenever the user asks "what's next", "suggest next step", "next action", or calls /next_step.
---

# 🎯 Next Step — Atomic Action Planner & Specification Handoff

`next_step` is the tactical pacing and alignment mechanism for **RepoDefense**. It bridges the master roadmap in [`implementation_plan.md`](file:///d:/RepoDefense/implementation_plan.md) with the live project state in [`.agents/memory/flashback.md`](file:///d:/RepoDefense/.agents/memory/flashback.md) and the architectural invariants in [`Gemini.md`](file:///d:/RepoDefense/Gemini.md), [`architecture.md`](file:///d:/RepoDefense/architecture.md), and [`design.md`](file:///d:/RepoDefense/design.md).

It strictly enforces the **5-Gate Goldilocks Task Granularity Standard**, guaranteeing that every step fits within the model's context window with **40–50% reserved headroom** for iterative edits, debugging, test runs, and code reviews before handing over to [`create_specs`](file:///d:/RepoDefense/.agents/skills/create_specs/SKILL.md).

---

## 🏛️ Mandatory Three-Pillar Context Consultation

Before formulating ANY next step, action plan, or verdict, `next_step` **MUST MANDATORILY READ AND CROSS-REFERENCE ALL THREE CORE FILES**:

1. 📖 [`Gemini.md`](file:///d:/RepoDefense/Gemini.md) — Master strategy, architecture principles, static analysis invariant (no code execution), 300 LOC limits, and tech stack locks.
2. 🗺️ [`implementation_plan.md`](file:///d:/RepoDefense/implementation_plan.md) — Phased master checklists (Phases 1–5), build order, dependencies, acceptance criteria, and AI prompts.
3. 🕰️ [`.agents/memory/flashback.md`](file:///d:/RepoDefense/.agents/memory/flashback.md) — Canonical living memory ledger, ADRs, active phase status, and chronological changelog.

_Additionally, perform a quick scan of the workspace files to ensure the proposed task aligns with real repository state._

---

## ⚖️ The 5-Gate Goldilocks Granularity Standard

To prevent context exhaustion and ensure maximum code quality, every step MUST pass all 5 gates before handoff:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Context Window Breakdown (128k Token Standard Budget)                  │
├────────────────────────────────────────────────────────────────────────┤
│ Base Overhead (Prompts, Tools, References, System Invariants)  : ~50k  │
│ Target Step Code Generation (~150-300 LOC)                    : ~4k    │
│ Test Runner Execution & Stack Traces (pytest / Jest)          : ~4k    │
│ Iterative Debugging & Type-Fix Loops (1-2 turns)               : ~15k   │
│ Code Reviewer Evaluation & Diff Analysis                       : ~5k    │
├────────────────────────────────────────────────────────────────────────┤
│ PEAK TURN USAGE (Goldilocks Sized Step)                        : ~78k  │
│ RESERVED SAFETY HEADROOM (35–45% Buffer for Iterations)        : ~50k  │
└────────────────────────────────────────────────────────────────────────┘
```

### The 5 Gates Checklist:

1. **Target File Gate**: $\le 4$ target files total ($\le 2$ implementation files, $\le 1$ schema/model file, $\le 1$ test file).
2. **Code Volume Gate**: $\le 300$ LOC per file (strict project limit from `Gemini.md`), calibrated for FastAPI async handlers, SQLAlchemy models, Tree-sitter visitors, or React components.
3. **Single Architectural Concern**: Step addresses exactly ONE layer (e.g. DB Models + Migration OR Service/Analyzer OR API Router OR UI Component + Hook; never full-stack from DB to UI in one turn).
4. **Verifiable Unit Gate**: Exactly 1 targeted test command to prove correctness (`pytest backend/tests/...` or `npm test -- ...`).
5. **Headroom Assurance Gate**: Estimated turn consumption $\le 25,000$ tokens, ensuring $\ge 40\%$ context window headroom remains for debugging and reviewer feedback.

---

## ✂️ Automatic Sub-Slicing Rule

If a milestone in [`implementation_plan.md`](file:///d:/RepoDefense/implementation_plan.md) fails ANY of the 5 gates (e.g., an entire ingestion pipeline or the complete interview FSM):

- **Do NOT attempt to execute the entire milestone at once.**
- Automatically slice it into alphabetical sub-steps: `Milestone 1.5a: Git Shallow Cloner`, `Milestone 1.5b: Security Sanitizer & Size Limits`, `Milestone 1.5c: ARQ Job Coordination`.
- Package only the **first incomplete sub-step** and pass it to `create_specs`.
- Note the remaining sub-steps in the "Up Next in Queue" section.

---

## 🔄 Workflow & Operating Procedure

```mermaid
flowchart TD
    A["📖 Consult Gemini.md, implementation_plan.md & flashback.md"] --> B["🔍 Inspect Real Codebase & Git Status"]
    B --> C["🎯 Locate Active Phase & Next Unchecked Task"]
    C --> D{"⚖️ Passes 5-Gate Granularity?"}
    D -- "No (Too Big)" --> E["✂️ Sub-slice into Step X.Ya, X.Yb..."]
    D -- "Yes (Goldilocks)" --> F["📋 Formulate Execution Blueprint"]
    E --> F
    F --> G["🚀 Automatic Handoff to /create_specs"]
    G --> H["🌿 Branch Created + Spec Written -> Await User Approval to Execute"]
```

### Step 1: Consult Three Core Files & Codebase
- Read `Gemini.md` for architecture rules and technology locks.
- Read `implementation_plan.md` to dynamically locate the current unchecked task `[ ]`.
- Read `.agents/memory/flashback.md` for latest ADRs and activity history.
- Inspect workspace directories to check existing modules in `backend/` and `frontend/`.

### Step 2: Apply 5-Gate Sizing & Formulate Blueprint
Extract:
- `step_number`: e.g. `1.1a`, `1.2`, `1.5b`
- `feature_title`: Human-readable title in Title Case (e.g. `FastAPI Project Scaffold & Health Check`)
- `feature_slug`: Kebab-cased slug (e.g. `step-1-1a-fastapi-scaffold`)
- `target_files`: List of files within calibrated file limits ($\le 4$ files, $\le 300$ LOC/file)
- `objective`: 1-2 sentence statement of purpose
- `execution_checklist`: Specific atomic tasks
- `verification_criteria`: 1 targeted acceptance command and test

### Step 3: Automatic Handoff to `create_specs`
Immediately invoke or trigger `create_specs` with the formulated step metadata so that:
1. Working directory cleanliness is verified (`git status -s`).
2. Latest `main` is checked out and updated (`git checkout main && git pull origin main`).
3. Dedicated feature branch is created (`git checkout -b feat/<feature_slug>`).
4. Production-grade technical specification file is written to `docs/specs/<feature_slug>.md`.

---

## 📤 Standard Output Format

```markdown
### 🧭 Current Status Snapshot

- **Active Phase**: Phase X — [Phase Name]
- **Consulted References**: `Gemini.md` | `implementation_plan.md` | `flashback.md`
- **Last Completed**: [Brief mention of the most recently finished milestone/task]

---

### 🎯 Immediate Next Step: [Step ID] — [Step Title]

- **Scope**: Single Atomic Task (Goldilocks Calibrated: ~[X] LOC, [N] files)
- **Target Files**:
  - `[NEW]` [backend/app/.../file.py](file:///d:/RepoDefense/backend/app/.../file.py)
  - `[MODIFY]` [backend/app/.../file.py](file:///d:/RepoDefense/backend/app/.../file.py)
- **Objective**: [1-2 sentences clearly describing what this specific step achieves]

#### 📋 Execution Checklist for this Step

1. [ ] [Specific sub-task 1, e.g. Define Pydantic request schema and endpoint]
2. [ ] [Specific sub-task 2, e.g. Implement analyzer service adhering to <= 300 LOC limit]
3. [ ] [Specific sub-task 3, e.g. Add unit test with mocked fixtures]

#### 🧪 Verification & Acceptance Criteria

- [ ] [Single targeted test command, e.g. `pytest backend/tests/test_health.py -v`]
- [ ] [Expected outcome or API response]

---

### 🚀 Handoff to `create_specs`

_Proceeding to invoke `/create_specs` with:_

- **Step ID**: `[Step ID]`
- **Title**: `[Step Title]`
- **Slug**: `[feature-slug]`
- **Branch**: `feat/[feature-slug]`
- **Spec Path**: `docs/specs/[feature-slug].md`

_(Calling `create_specs` to verify git status, branch off main, and generate the technical spec...)_
```

---

## 🚀 Triggers

- `/next_step`
- `"What is the next step?"`
- `"Suggest next action"`
- `"What should we work on next?"`
