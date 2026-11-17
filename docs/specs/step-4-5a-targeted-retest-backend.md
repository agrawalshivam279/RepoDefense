# Step 4.5a Technical Specification: Backend Targeted Re-Testing Service & REST API

## 1. Overview & Problem Statement
In RepoDefense Phase 4 (Learning Loop), Milestone 4.5 introduces **Targeted Re-Testing**. After a candidate encounters architectural blind spots during defense sessions (tracked as `CandidateWeakness` records) and reviews mentor remediation guides (Milestone 4.2) or completes mini challenges (Milestone 4.3), they need a structured way to prove they have mastered the remediated concept through targeted re-testing.

Step 4.5a implements the backend targeted re-testing engine:
1. **Targeted Question Generator (`backend/app/ai/retest_generator.py`)**: Uses LiteLLM (with robust deterministic offline fallbacks) to synthesize challenging, repository-grounded re-test questions specifically targeting the candidate's active architectural weaknesses.
2. **Re-Test Evaluation Engine**: Evaluates the candidate's re-test defense against the targeted architectural constraint, grades conceptual depth and remediation effectiveness, and provides structured feedback.
3. **Automated Weakness Resolution & Skill Reinforcement (`backend/app/services/retest_service.py`)**: If the candidate passes the re-test, automatically marks the corresponding `CandidateWeakness` as resolved via `weakness_tracker.resolve_weakness` and boosts associated `UserSkill` proficiency.
4. **FastAPI REST Router (`backend/app/api/v1/retest.py`)**: Exposes multi-tenant endpoints for starting re-test sessions, fetching active candidate weaknesses, and submitting re-test evaluations.

## 2. Security & Architectural Invariants
- **Zero Arbitrary Code Execution**: No user code is executed or compiled. Static analysis and prompt grounding only.
- **Strict Multi-Tenant IDOR Isolation**: All queries filter by `user_id == current_user.id`. A candidate cannot re-test or resolve weaknesses belonging to another user.
- **Prompt Injection Defense**: Weakness topics, candidate previous responses, and code snippets are encapsulated within strict XML boundary tags (`<weakness_context>`, `<original_question>`, `<mentor_feedback>`, `<candidate_retest_answer>`).
- **File Length Limit**: Every authored Python file must strictly adhere to the `<= 300 LOC` constraint (`Gemini.md`).

## 3. Schemas & Data Contracts (`backend/app/schemas/retest.py`)
- `TargetedRetestSessionCreate`: `project_id: Optional[UUID]`, `weakness_ids: Optional[List[UUID]]`, `category: Optional[str]`, `max_questions: int = Field(default=3, ge=1, le=10)`
- `RetestQuestion`: `question_id: str`, `weakness_id: UUID`, `category: str`, `topic: str`, `severity: str`, `question_text: str`, `architectural_constraint: str`, `evaluation_rubric: str`
- `TargetedRetestSessionResponse`: `session_id: str`, `user_id: UUID`, `project_id: Optional[UUID]`, `questions: List[RetestQuestion]`, `created_at: datetime`
- `SubmitRetestAnswerRequest`: `session_id: str`, `question_id: str`, `weakness_id: UUID`, `candidate_response: str = Field(min_length=10, max_length=5000)`
- `RetestEvaluationResponse`: `question_id: str`, `weakness_id: UUID`, `passed: bool`, `score: float`, `feedback: str`, `key_improvements: List[str]`, `remaining_gaps: List[str]`, `weakness_resolved: bool`, `updated_proficiency: Optional[float]`

## 4. API Endpoints
- `POST /api/v1/retest/session`: Initiates a targeted re-test session for the authenticated user, selecting unresolved weaknesses.
- `GET /api/v1/retest/weaknesses`: Returns active, unresolved weaknesses for the user eligible for targeted re-testing.
- `POST /api/v1/retest/evaluate`: Grades the candidate's re-test answer, returns structured evaluation, and auto-resolves the weakness if passed.

## 5. Verification Plan
- Hermetic unit & API contract tests in `backend/tests/test_retest.py`.
- Tests for:
  1. Session generation with selected weakness IDs.
  2. Fallback question generation when LLM is offline.
  3. Answer grading with pass outcome (weakness marked resolved, skill proficiency boosted).
  4. Answer grading with fail outcome (weakness remains unresolved).
  5. Multi-tenant IDOR defense (cannot access or evaluate other users' weaknesses).
  6. Empty weakness pool handling.
