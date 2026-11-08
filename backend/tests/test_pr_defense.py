"""Hermetic unit and integration tests for Step 3.2a: PR Defense Session Backend.

Tests:
  Unit (TestPRQuestionGenerator): 8 tests for generator, fallback, parsing, and serialization.
  Endpoint (TestPRDefenseEndpoints): 7 tests for start, get, and answer endpoints.
Uses isolated _drive_coro runner to avoid socket-bound event loops in sandboxed environments.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.ai.fsm import defense_store
from app.ai.pr_question_generator import (
    _build_fallback_questions,
    _select_top_files,
    _serialize_diff_context,
    generate_pr_defense_questions,
)
from app.api.v1.pr_defense import (
    get_pr_defense_session,
    start_pr_defense_session,
    submit_pr_defense_answer,
)
from app.models.project import User
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseStage,
    DifficultyLevel,
    EvaluationOutput,
    SecondaryEvaluationOutput,
    SubmitAnswerRequest,
)
from app.schemas.pr_analysis import (
    DiffLineType,
    FileChangeStatus,
    ParsedDiffHunk,
    ParsedDiffLine,
    ParsedFileDiff,
    PRAnalysisResponse,
    PRMetadata,
)
from app.schemas.pr_defense import (
    DiffGroundedQuestion,
    PRDefenseSessionState,
    StartPRDefenseRequest,
)
from app.schemas.question import QuestionCategory


def _drive_coro(coro):
    """Hermetic coroutine runner that avoids socket-bound event loops in sandboxed environments."""
    stack = [coro]
    val, exc = None, None
    while stack:
        current = stack[-1]
        try:
            to_send = current.throw(exc) if exc is not None else current.send(val)
            exc, val = None, None
            if hasattr(to_send, "send"):
                stack.append(to_send)
        except StopIteration as stop:
            val = stop.value
            stack.pop()
        except Exception as e:
            exc = e
            stack.pop()
    if exc is not None:
        raise exc
    return val


def _make_line(content: str, line_type: DiffLineType = DiffLineType.ADDITION) -> ParsedDiffLine:
    return ParsedDiffLine(line_type=line_type, content=content, new_line_number=1)


def _make_hunk(header: str = "@@ -1,3 +1,5 @@", added: int = 2) -> ParsedDiffHunk:
    lines = [_make_line(f"line {i}") for i in range(added)]
    return ParsedDiffHunk(
        old_start=1, old_lines=3, new_start=1, new_lines=5,
        header=header, lines=lines, added_count=added, deleted_count=0,
    )


def _make_file(path: str = "app.py", adds: int = 5, dels: int = 1) -> ParsedFileDiff:
    return ParsedFileDiff(
        new_path=path, status=FileChangeStatus.MODIFIED,
        hunks=[_make_hunk(added=min(adds, 2))], total_additions=adds, total_deletions=dels,
    )


def _make_pr(files: list[ParsedFileDiff] | None = None) -> PRAnalysisResponse:
    files = files if files is not None else [_make_file()]
    adds = sum(f.total_additions for f in files)
    dels = sum(f.total_deletions for f in files)
    meta = PRMetadata(
        pr_number=42, title="Refactor", author="dev", base_branch="main",
        head_branch="feat/r", head_sha="a1", state="open",
        html_url="https://github.com/o/r/pull/42", created_at="2026-11-09T00:00:00Z",
    )
    return PRAnalysisResponse(
        metadata=meta, files=files, total_files_changed=len(files),
        total_additions=adds, total_deletions=dels, summary_narrative="PR #42 changes.",
    )


class TestPRQuestionGenerator:
    def test_select_top_files_sorted_capped(self):
        files = [_make_file(f"f{i}.py", adds=i * 2, dels=i) for i in range(5)]
        top = _select_top_files(files)
        assert len(top) == 3
        assert top[0].new_path == "f4.py"

    def test_serialize_diff_context_headers(self):
        pr = _make_pr([_make_file("api.py", adds=3, dels=1)])
        ctx = _serialize_diff_context(pr)
        assert "api.py" in ctx and "@@ -1,3 +1,5 @@" in ctx and "PR #42" in ctx

    def test_serialize_diff_context_strips_secrets(self):
        secret = _make_line("[REDACTED_SECRET] TOKEN=xyz")
        hunk = ParsedDiffHunk(
            old_start=1, old_lines=1, new_start=1, new_lines=2,
            header="@@ -1,1 +1,2 @@", lines=[secret, _make_line("safe code")],
            added_count=2, deleted_count=0,
        )
        pr = _make_pr([ParsedFileDiff(
            new_path="sec.py", status=FileChangeStatus.MODIFIED,
            hunks=[hunk], total_additions=2, total_deletions=0,
        )])
        ctx = _serialize_diff_context(pr)
        assert "[REDACTED_SECRET]" not in ctx and "safe code" in ctx

    def test_fallback_generates_grounded_questions(self):
        pr = _make_pr([_make_file("a.py"), _make_file("b.py")])
        qs = _build_fallback_questions(pr, num_questions=2)
        assert len(qs) == 2
        assert all(isinstance(q, DiffGroundedQuestion) and q.diff_hunk_header for q in qs)

    def test_fallback_handles_empty_files(self):
        pr = _make_pr([])
        qs = _build_fallback_questions(pr, num_questions=1)
        assert len(qs) == 1 and qs[0].diff_file_path == "(diff)"

    def test_empty_diff_raises_value_error(self):
        with pytest.raises(ValueError, match="No diff content"):
            _drive_coro(generate_pr_defense_questions(_make_pr([]), num_questions=1))

    def test_llm_error_uses_fallback(self):
        with patch("app.ai.pr_question_generator.litellm.acompletion", side_effect=RuntimeError):
            qs = _drive_coro(
                generate_pr_defense_questions(
                    _make_pr(), num_questions=1, api_key="k", max_retries=0
                )
            )
        assert len(qs) >= 1 and isinstance(qs[0], DiffGroundedQuestion)

    def test_llm_json_parsing_success(self):
        resp_data = [{
            "category": "architecture", "question_text": "Why refactor?",
            "context_hint": "In app.py", "cited_files": ["app.py"],
            "diff_file_path": "app.py", "diff_hunk_header": "@@ -1,3 +1,5 @@",
            "change_type": "modification", "cited_lines": ["+line 0"],
        }]
        choice = MagicMock(message=MagicMock(content=json.dumps(resp_data)))
        with patch(
            "app.ai.pr_question_generator.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=MagicMock(choices=[choice]),
        ):
            qs = _drive_coro(
                generate_pr_defense_questions(_make_pr(), num_questions=1, api_key="k")
            )
        assert len(qs) == 1 and qs[0].category == QuestionCategory.ARCHITECTURE


def _make_session(status=DefenseStage.QUESTION_ACTIVE) -> PRDefenseSessionState:
    q = DiffGroundedQuestion(
        category=QuestionCategory.ARCHITECTURE, question_text="Why this change?",
        context_hint="Hint", cited_files=["app.py"], diff_file_path="app.py",
        diff_hunk_header="@@ -1,3 +1,5 @@", change_type="modification",
        cited_lines=["+added"],
    )
    prog = DefenseQuestionProgress(
        question=q, status=status, difficulty=DifficultyLevel.INTERMEDIATE,
    )
    return PRDefenseSessionState(
        project_id="proj-1", status=status, current_question_index=0,
        total_questions=1, questions=[prog], diff_questions=[q],
        pr_number=42, pr_title="PR", pr_html_url="http://pr", pr_author="u",
        pr_analysis_summary="summary", created_at="2026-11-09T00:00:00Z",
        updated_at="2026-11-09T00:00:00Z",
    )


class TestPRDefenseEndpoints:
    def setup_method(self):
        self.mock_user = User(id=uuid.uuid4(), email="tester@repodefense.dev")

    def test_get_session_not_found(self):
        with pytest.raises(HTTPException) as exc_info:
            _drive_coro(get_pr_defense_session("missing-id", current_user=self.mock_user))
        assert exc_info.value.status_code == 404

    def test_submit_answer_session_completed_409(self):
        session = _make_session(status=DefenseStage.SESSION_COMPLETED)
        _drive_coro(defense_store.save(session))
        req = SubmitAnswerRequest(answer="My answer")
        with pytest.raises(HTTPException) as exc_info:
            _drive_coro(submit_pr_defense_answer(
                session.session_id, payload=req, current_user=self.mock_user
            ))
        assert exc_info.value.status_code == 409
        _drive_coro(defense_store.delete(session.session_id))

    def test_get_existing_session_200(self):
        session = _make_session()
        _drive_coro(defense_store.save(session))
        res = _drive_coro(get_pr_defense_session(session.session_id, current_user=self.mock_user))
        assert res.pr_number == 42
        assert res.status == DefenseStage.QUESTION_ACTIVE
        _drive_coro(defense_store.delete(session.session_id))

    def test_submit_vague_answer_triggers_pushback(self):
        session = _make_session()
        _drive_coro(defense_store.save(session))
        vague_out = EvaluationOutput(
            passed_initial_defense=False, depth_score=3, grounding_verified=False,
            is_vague=True, pushback_prompt="Be specific.", feedback="Vague answer.",
        )
        with patch(
            "app.api.v1.pr_defense.evaluate_candidate_defense",
            new_callable=AsyncMock,
            return_value=vague_out,
        ):
            req = SubmitAnswerRequest(answer="it just works")
            res = _drive_coro(submit_pr_defense_answer(
                session.session_id, payload=req, current_user=self.mock_user
            ))
        assert res.status == DefenseStage.PUSHBACK_ACTIVE
        _drive_coro(defense_store.delete(session.session_id))

    def test_submit_pass_triggers_stress_test(self):
        session = _make_session()
        _drive_coro(defense_store.save(session))
        pass_out = EvaluationOutput(
            passed_initial_defense=True, depth_score=8, grounding_verified=True,
            is_vague=False, feedback="Great.", stress_test_prompt="What if load spikes?",
        )
        with patch(
            "app.api.v1.pr_defense.evaluate_candidate_defense",
            new_callable=AsyncMock,
            return_value=pass_out,
        ):
            req = SubmitAnswerRequest(answer="I added caching and connection pooling.")
            res = _drive_coro(submit_pr_defense_answer(
                session.session_id, payload=req, current_user=self.mock_user
            ))
        assert res.status == DefenseStage.STRESS_TEST_ACTIVE
        _drive_coro(defense_store.delete(session.session_id))

    def test_submit_stress_answer_completes_session(self):
        session = _make_session(status=DefenseStage.STRESS_TEST_ACTIVE)
        session.questions[0].status = DefenseStage.STRESS_TEST_ACTIVE
        session.questions[0].defense_score = 8
        session.questions[0].stress_test_prompt = "What if load spikes?"
        _drive_coro(defense_store.save(session))
        sec_out = SecondaryEvaluationOutput(
            handled_successfully=True, follow_up_score=9, feedback="Excellent mitigation.",
        )
        with patch(
            "app.api.v1.pr_defense.evaluate_secondary_turn",
            new_callable=AsyncMock,
            return_value=sec_out,
        ):
            req = SubmitAnswerRequest(answer="We use Redis with circuit breaking.")
            res = _drive_coro(submit_pr_defense_answer(
                session.session_id, payload=req, current_user=self.mock_user
            ))
        assert res.status == DefenseStage.SESSION_COMPLETED
        _drive_coro(defense_store.delete(session.session_id))

    def test_start_session_project_not_found(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
        req = StartPRDefenseRequest(pr_url="https://github.com/o/r/pull/1", num_questions=2)
        with pytest.raises(HTTPException) as exc_info:
            _drive_coro(start_pr_defense_session(
                project_id=uuid.uuid4(), payload=req, current_user=self.mock_user, db=mock_db
            ))
        assert exc_info.value.status_code == 404
