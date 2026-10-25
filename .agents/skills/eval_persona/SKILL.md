---
name: eval_persona
version: '1.0'
description: >-
  AI Principal Engineer Persona & Interview Grounding Evaluator for RepoDefense.
  Audits prompt templates in backend/app/ai/prompts.py and state transitions in backend/app/ai/fsm.py,
  checks structured output schema conformance against Pydantic models (QuestionPayload, EvaluationResult, StressTestScenario),
  audits character tone calibration (Rigorous Principal Engineer vs Constructive Mentor mode),
  and verifies strict codebase evidence grounding (AST symbols, file chunks) and token budget limits.
  Use whenever authoring/refining interview prompts or calling /eval_persona.
---

# 🎭 Eval Persona — AI Principal Engineer Persona & Grounding Evaluator

`eval_persona` is the prompt engineering auditor and persona fidelity evaluator for **RepoDefense**. It guarantees that system prompts and FSM orchestrators in `backend/app/ai/prompts.py` and `backend/app/ai/fsm.py` produce strictly grounded, technically rigorous architectural defense questions, stress-test constraints, and constructive mentorship without hallucination, generic LeetCode drifting, or superficial approvals.

---

## 🎯 The 5 Core Evaluation Vectors

```mermaid
flowchart TD
    A["Trigger /eval_persona"] --> B["1. AST & Codebase Evidence Grounding (Symbols, Line Ranges, Chunks)"]
    B --> C["2. Principal Engineer Persona Calibration (Rigorous, Technical Pushback)"]
    C --> D["3. Mentor Mode Calibration (Pedagogical Guidance & Re-test Prep)"]
    D --> E["4. Pydantic Structured Output Conformance (JSON Schemas & Fallbacks)"]
    E --> F["5. Token Budget, Context Assembly & Latency Constraints"]
    F --> G["📊 Persona Fidelity Report & Calibration Prompts"]
```

---

## 📋 Evaluation Guidelines & Invariants

### 1. Evidence Grounding & Anti-Hallucination Invariant
- **Rule**: Every generated question and stress-test MUST be anchored in factual code evidence:
  - Valid `file_path`, AST `symbol_name` (class, function, decorator, import), and `line_range`.
  - The model must NEVER invent files or endpoints not present in the ingested repo.
  - If retrieved context is insufficient, the system prompt must instruct the LLM:
    > *"Ground all questions exclusively in the provided code evidence. If evidence is lacking, state that the architecture cannot be inferred from the retrieved chunks."*
- **Rejection of Generic Questions**:
  - ❌ *"Can you explain the difference between a process and a thread?"* (Generic textbook)
  - ❌ *"Reverse a linked list in O(n) time."* (Generic LeetCode)
  - ✅ *"In `backend/app/services/auth.py:L45`, your `verify_token` function queries the database on every request. What happens to your connection pool if traffic surges to 10k req/sec?"* (RepoDefense grounded)

### 2. Principal Engineer Persona Calibration
- **Role**: Staff / Principal Software Engineer conducting a high-stakes architecture defense.
- **Voice**: Authoritative, intellectually demanding, deeply curious about trade-offs, respectful.
- **Pushback Logic**:
  - Automatically identifies shallow, hand-waving, or evasive answers.
  - Demands justification for architectural choices: *"Why did you choose Redis over Memcached for this specific cache schema?"*
  - Introduces production stress tests: concurrency bottlenecks, network partitions, cold-start latency, cache stampedes.

### 3. Mentor Mode Calibration
- **Role**: Senior engineering mentor supporting candidate growth after a failed defense step.
- **Tone**: Constructive, pedagogical, encouraging — NEVER condescending or dismissive.
- **Guidance Invariant**:
  - Explains the underlying systems concept using the candidate's *own code* as the case study.
  - Does NOT simply provide the complete answer; provides conceptual clues and guides the candidate into the **Re-test Phase**.

### 4. Pydantic Schema & Contract Conformance
- Every prompt intended for structured output must validate against backend schemas:
  - `QuestionPayload`: Question text, targeted file, AST symbol, evaluation criteria.
  - `EvaluationResult`: Score (0-100), depth rating (shallow, adequate, deep), pushback required flag, rationale.
  - `StressTestScenario`: Hypothetical constraint, affected component, expected mitigation.
  - `MentorshipNote`: Concept explained, recommended architecture fix, re-test prompt.
- Handlers must cleanly strip markdown code fences (`\`\`\`json`) and parse partial JSON strings safely.

### 5. Token Budget & Latency Budget
- Maximum context assembly tokens: $\le 4,000$ tokens (including retrieved code chunks).
- Maximum completion output tokens: $\le 1,000$ tokens.
- Hard timeout constraint: $30$ seconds with LiteLLM retry and exponential backoff.

---

## 🛠️ Audit Protocol & Workflow

1. **Ingest Target Prompt**: Read template from `backend/app/ai/prompts.py`.
2. **Static Invariant Scan**:
   - Check for evidence grounding instructions.
   - Verify prompt uses parameterized template variables (`code_chunk`, `symbol_name`, `user_defense`).
   - Verify no hardcoded API keys.
3. **Mock Generation & Schema Test**:
   - Feed sample AST symbol and code chunk fixtures into the prompt.
   - Validate LiteLLM response parses cleanly into the target Pydantic schema.
4. **Tone & Stress Audit**: Ensure the output challenges the candidate with realistic systems trade-offs without toxic negativity.
5. **Output Fidelity Scorecard**: Output report with pass/fail grades and calibration recommendations.

---

## 📤 Standard Fidelity Report Output

```markdown
# 🎭 Persona Fidelity Report — [Prompt / Template Name]

### 📊 Evaluation Scorecard

| Evaluation Vector | Status | Notes |
| :--- | :--- | :--- |
| **Evidence Grounding** | 🟢 PASS | Anchored strictly in AST symbols and line ranges |
| **Principal Engineer Tone** | 🟢 PASS | Sharp trade-off pushback; no generic LeetCode queries |
| **Mentor Mode Tone** | 🟢 PASS | Constructive feedback using candidate's code context |
| **Pydantic Schema Match** | 🟢 PASS | Output conforms to `QuestionPayload` / `EvaluationResult` |
| **Token Budget & Latency** | 🟢 PASS | Est. 1,200 tokens context, well within 30s timeout |

---

### 💡 Tone & Calibration Insights

- **Question Depth**: Effectively targets connection pooling in `middleware.ts`.
- **Stress-Test Relevance**: Injected 10k req/s traffic spike constraint directly tests DB limits.

---

### 🚦 Verdict: READY FOR PRODUCTION
```

---

## 🚀 Triggers

- `/eval_persona`
- `/eval_prompt`
- `"Evaluate principal engineer interview persona"`
- `"Audit prompt grounding and tone"`
