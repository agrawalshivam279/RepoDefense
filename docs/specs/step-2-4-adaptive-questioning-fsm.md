# 📄 Technical Specification: Adaptive Questioning State Machine & Topic Confidence Engine

> **Step ID**: `Step 2.4`  
> **Target Module**: `backend/app/ai/...`  
> **Git Feature Branch**: `feat/step-2-4-adaptive-questioning-fsm`  
> **Status**: 📋 Draft / Ready for Implementation  
> **Created**: 2026-11-06  

---

## 1. Executive Summary

Step 2.4 delivers **Milestone 2.4: Adaptive Questioning State Machine** under Phase 2 (Differentiation). In the baseline defense implementation (Milestone 1.14), the interview state machine stepped sequentially through a pre-generated static list of questions without reacting to the candidate's demonstrated depth.

This milestone equips the RepoDefense interview engine with real-time adaptive questioning and continuous topic confidence tracking:
1. **Per-Topic Confidence Tracking**: Maintains an exponential moving average confidence score (0.0 to 1.0) for each evaluated architectural category (`architecture`, `scalability`, `reliability`, `security`, `tradeoffs`, `database`).
2. **Dynamic Difficulty Adjustment**:
   - **$< 50\%$ Score ($< 5/10$)**: Lowers difficulty tier (`intermediate` $\rightarrow$ `foundational`) and drills down into the same topic category to diagnose foundational comprehension.
   - **$\ge 90\%$ Score ($\ge 9/10$)**: Elevates difficulty tier (`intermediate` $\rightarrow$ `advanced`) and injects complex production scalability/tradeoff stress constraints.
   - **$50\% \le \text{Score} < 90\%$**: Retains current difficulty tier while updating topic mastery metrics.
3. **Question Adaptation Engine (`adaptive.py`)**: Modulates question phrasing, technical scope, and context anchors based on the target difficulty level while preserving evidence grounding in AST symbols.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Milestone 1.14`: Defense Session FSM State Machine & Evaluation (`fsm.py`, `evaluator.py`, `defense.py`).
  - `Milestone 1.13`: Evidence-Grounded Question Generation schemas (`question.py`).
- **Blocked by**: None.
- **Tech Stack Invariants**:
  - FastAPI (Python 3.12+) + Pydantic v2 + structlog.
  - Zero code execution; static analysis evidence grounding only.
  - Strict compliance with `Gemini.md` architecture and file length limits ($\le 300$ LOC per file).

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Pure state machine logic and deterministic mathematical calculations for confidence updating and difficulty adjustment.
- [x] **Preserved Evidence Grounding**: Adapted questions must never discard cited AST symbols or hallucinate unverified files.
- [x] **Prompt Injection Defense**: All adapted question prompts pass through standardized XML delimiter boundaries (`<question_context>`, `<candidate_answer>`).

---

## 4. 🧭 Specialized Skills Directive

| Specialized Skill | Scope of Impact & Mandate | Verification Requirement |
| :--- | :--- | :--- |
| **[`eval_persona`](file:///d:/RepoDefense/.agents/skills/eval_persona/SKILL.md)** | Audits Principal Engineer persona tone during difficulty transitions (firm, rigorous on advanced; pedagogical, structured on foundational). | Validates that difficulty labels and interviewer turn phrasing align with calibrated persona expectations. |
| **[`doctor`](file:///d:/RepoDefense/.agents/skills/doctor/SKILL.md)** | Pre-flight and post-implementation health checks across Python 3.12+ test suites and Ruff linting. | Asserts 100% test pass rate with zero lint or typing errors. |

---

## 5. 🧠 Sequential Thinking & Architecture Strategy

### 5.1 Architecture Separation & $\le 300$ LOC Guardrail
- `backend/app/ai/fsm.py` is currently at 299 lines. Adding adaptive logic directly into `fsm.py` would violate the strict $\le 300$ LOC rule.
- Therefore, we engineer a dedicated, modular engine:
  - `backend/app/schemas/defense.py`: Add `DifficultyLevel` enum, `current_difficulty`, and `topic_confidence` dictionary to `DefenseSessionState` and `DefenseQuestionProgress`.
  - `backend/app/ai/adaptive.py` (New file, $\le 200$ LOC): Implements `update_topic_confidence`, `determine_next_difficulty`, and `adapt_question_for_difficulty`.
  - `backend/app/ai/fsm.py`: Refactor `_advance_or_complete_session` to delegate to `adaptive.py`, trimming verbose lines so `fsm.py` drops to $\sim 270$ LOC.
  - `backend/tests/test_adaptive_questioning.py`: Comprehensive test suite verifying difficulty scaling, confidence updates, and state transitions ($\le 250$ LOC).

---

## 6. Data Contracts & Mathematical Specifications

### 6.1 Difficulty Enum & Session Extensions (`backend/app/schemas/defense.py`)

```python
class DifficultyLevel(str, Enum):
    """Calibrated difficulty levels for defense questions."""
    FOUNDATIONAL = "foundational"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
```

### 6.2 Topic Confidence Updating Formula

For a question evaluated with $\text{score} \in [1, 10]$ in category $C$:
$$\text{normalized\_score} = \frac{\text{score}}{10.0}$$
$$\text{confidence}_{\text{new}}(C) = \alpha \cdot \text{normalized\_score} + (1 - \alpha) \cdot \text{confidence}_{\text{prior}}(C)$$
where $\alpha = 0.6$ (weighting recent performance while preserving prior session mastery), defaulting prior confidence to $0.5$ if unobserved.

### 6.3 Difficulty Transition Rules

$$\text{NextDifficulty}(\text{curr}, \text{score}) = \begin{cases} 
\max(\text{FOUNDATIONAL}, \text{curr} - 1) & \text{if } \text{score} < 5 \\
\min(\text{ADVANCED}, \text{curr} + 1) & \text{if } \text{score} \ge 9 \\
\text{curr} & \text{otherwise}
\end{cases}$$

---

## 7. Quality Gate & Acceptance Criteria

1. **Unit & Integration Tests**: `python -m pytest backend/tests/test_adaptive_questioning.py -v` passes 100%.
2. **Existing Test Suite**: `test_defense_session.py`, `test_claim_verification.py`, `test_claim_extraction.py` continue passing with zero regressions.
3. **Ruff Linter**: `python -m ruff check backend/app backend/tests` returns 0 errors.
4. **LOC Audit**: Every file strictly complies with $\le 300$ LOC.
