"""Unit and integration tests for Step 3.3a: Commit Defense Session Backend."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.ai.fsm import defense_store
from app.analyzers.commit_fetcher import fetch_github_commit_data, parse_github_commit_url_or_sha
from app.api.v1.commit_defense import (
    analyze_commit_diff,
    get_commit_defense_session,
    start_commit_defense_session,
    submit_commit_defense_answer,
)
from app.models.project import User
from app.schemas.commit_defense import (
    CommitDefenseSessionState,
    CommitGroundedQuestion,
    CommitMetadata,
    StartCommitDefenseRequest,
)
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseStage,
    DefenseTurn,
    DifficultyLevel,
    EvaluationOutput,
    SecondaryEvaluationOutput,
    SubmitAnswerRequest,
    TurnRole,
)
from app.schemas.pr_defense import DiffGroundedQuestion
from app.schemas.question import QuestionCategory


def _drive_coro(coro):
    stack, val, exc = [coro], None, None
    while stack:
        current = stack[-1]
        try:
            to_send = current.throw(exc) if exc is not None else current.send(val)
            exc, val = None, None
            if hasattr(to_send, "send"):
                stack.append(to_send)
        except StopIteration as stop:
            val, _ = stop.value, stack.pop()
        except Exception as e:
            exc, _ = e, stack.pop()
    if exc is not None:
        raise exc
    return val


SAMPLE_DIFF = """diff --git a/src/app.py b/src/app.py
index e69de29..496d8b7 100644
--- a/src/app.py
+++ b/src/app.py
@@ -10,3 +10,5 @@ def handler():
+    # Load balancing route
+    return {"status": "ok"}
"""


class TestCommitFetcher:
    """Unit tests for commit URL parsing and GitHub commit data fetching."""

    def test_parse_commit_url_valid(self):
        long_sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        url = f"https://github.com/owner/my-repo/commit/{long_sha}"
        owner, repo, sha = parse_github_commit_url_or_sha(url)
        assert (owner, repo, sha) == ("owner", "my-repo", long_sha)

    def test_parse_commit_sha_with_project(self):
        proj_url = "https://github.com/testowner/testrepo.git"
        owner, repo, sha = parse_github_commit_url_or_sha("abcdef1", proj_url)
        assert owner == "testowner" and repo == "testrepo" and sha == "abcdef1"

    def test_parse_commit_invalid(self):
        with pytest.raises(HTTPException) as exc:
            parse_github_commit_url_or_sha("not-a-valid-sha")
        assert exc.value.status_code == 400

    def test_fetch_commit_data_success(self):
        mock_client = AsyncMock()
        mock_meta_res = MagicMock(status_code=200)
        mock_meta_res.json.return_value = {
            "sha": "a1b2c3d4",
            "commit": {
                "author": {"name": "Alice", "email": "a@t.com", "date": "2026-11-09T00:00:00Z"},
                "message": "feat: route",
            },
            "html_url": "https://github.com/o/r/commit/a1b2c3d4",
            "stats": {"additions": 3, "deletions": 1},
            "files": [{"filename": "src/app.py"}],
        }
        mock_diff_res = MagicMock(status_code=200, text=SAMPLE_DIFF)
        mock_client.get = AsyncMock(side_effect=[mock_meta_res, mock_diff_res])

        meta, diff = _drive_coro(
            fetch_github_commit_data("o", "r", "a1b2c3d4", client=mock_client)
        )
        assert meta.author_name == "Alice" and meta.total_additions == 3 and "diff --git" in diff

    def test_fetch_commit_data_404(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))
        with pytest.raises(HTTPException) as exc:
            _drive_coro(fetch_github_commit_data("o", "r", "missing", client=mock_client))
        assert exc.value.status_code == 404

    def test_fetch_commit_data_rate_limit(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=MagicMock(status_code=429))
        with pytest.raises(HTTPException) as exc:
            _drive_coro(fetch_github_commit_data("o", "r", "any", client=mock_client))
        assert exc.value.status_code == 429


class TestCommitDefenseEndpoints:
    """Endpoint tests for commit-scoped defense sessions and answer submission."""

    def _mock_project(self, proj_id: uuid.UUID, user_id: uuid.UUID):
        return MagicMock(id=proj_id, user_id=user_id, github_url="https://github.com/owner/repo")

    def _mock_db(self, proj=None):
        return AsyncMock(
            execute=AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=proj)))
        )

    def _make_test_session(
        self, sess_id: str, status: DefenseStage = DefenseStage.QUESTION_ACTIVE, score: int = None
    ):
        q = CommitGroundedQuestion(
            id="q-1", category=QuestionCategory.ARCHITECTURE, question_text="Why this design?",
            context_hint="hint", cited_evidence_ids=[], cited_files=["src/app.py"],
            diff_file_path="src/app.py", diff_hunk_header="@@ -10,3 +10,5 @@",
            change_type="addition", cited_lines=["+ ok"], commit_hash="c1",
        )
        prog = DefenseQuestionProgress(question=q, status=status, defense_score=score)
        turn = DefenseTurn(role=TurnRole.INTERVIEWER, content="Turn", stage=status)
        return CommitDefenseSessionState(
            session_id=sess_id, project_id=str(uuid.uuid4()), status=status,
            current_question_index=0, current_difficulty=DifficultyLevel.INTERMEDIATE,
            total_questions=1, questions=[prog], turns=[turn],
            created_at="2026-11-09T00:00:00Z", updated_at="2026-11-09T00:00:00Z",
            commit_hash="c1", commit_message="msg", commit_author="dev",
            commit_html_url="url", commit_analysis_summary="summary", diff_questions=[q],
        )

    def test_start_commit_defense_session(self):
        proj_id, user_id = uuid.uuid4(), uuid.uuid4()
        user, proj = User(id=user_id, email="dev@test.com"), self._mock_project(proj_id, user_id)
        mock_db = self._mock_db(proj)

        mock_meta = CommitMetadata(
            commit_hash="a1b2c3d4e5f6", author_name="Dev", committed_at="2026-11-09T00:00:00Z",
            message="Add endpoint", html_url="https://github.com/owner/repo/commit/a1b2c3d4e5f6",
            total_additions=2, total_deletions=0, total_files=1,
        )
        fake_q = DiffGroundedQuestion(
            id="q-1", category=QuestionCategory.ARCHITECTURE, question_text="Why this change?",
            context_hint="hint", cited_evidence_ids=[], cited_files=["src/app.py"],
            diff_file_path="src/app.py", diff_hunk_header="@@ -10,3 +10,5 @@",
            change_type="addition", cited_lines=["+ ok"],
        )
        fetch_patch = patch(
            "app.api.v1.commit_defense.fetch_github_commit_data", new_callable=AsyncMock
        )
        gen_patch = patch(
            "app.analyzers.commit_fetcher.generate_pr_defense_questions", new_callable=AsyncMock
        )
        with fetch_patch as mock_fetch, gen_patch as mock_gen:
            mock_fetch.return_value = (mock_meta, SAMPLE_DIFF)
            mock_gen.return_value = [fake_q]
            payload = StartCommitDefenseRequest(commit_url_or_hash="a1b2c3d4e5f6", num_questions=2)
            session = _drive_coro(
                start_commit_defense_session(proj_id, payload, current_user=user, db=mock_db)
            )

        assert session.status == DefenseStage.QUESTION_ACTIVE
        assert session.commit_hash == "a1b2c3d4e5f6"
        assert len(session.diff_questions) == 1
        assert "COMMIT DEFENSE" in session.turns[0].content

    def test_start_commit_defense_project_not_found(self):
        mock_db = self._mock_db(None)
        user = User(id=uuid.uuid4(), email="dev@test.com")
        with pytest.raises(HTTPException) as exc:
            payload = StartCommitDefenseRequest(commit_url_or_hash="a1b2c3d4e5f6")
            _drive_coro(
                start_commit_defense_session(uuid.uuid4(), payload, current_user=user, db=mock_db)
            )
        assert exc.value.status_code == 404

    def test_get_commit_defense_session(self):
        user = User(id=uuid.uuid4(), email="dev@test.com")
        sess_id = f"commit-test-{uuid.uuid4()}"
        sess = self._make_test_session(sess_id)
        _drive_coro(defense_store.save(sess))
        res = _drive_coro(get_commit_defense_session(sess_id, current_user=user))
        assert res.session_id == sess_id

    def test_get_commit_defense_session_not_found(self):
        user = User(id=uuid.uuid4(), email="dev@test.com")
        with pytest.raises(HTTPException) as exc:
            _drive_coro(get_commit_defense_session("missing-session", current_user=user))
        assert exc.value.status_code == 404

    def test_submit_commit_answer_passed_stress(self):
        user = User(id=uuid.uuid4(), email="dev@test.com")
        sess_id = f"commit-ans-{uuid.uuid4()}"
        _drive_coro(defense_store.save(self._make_test_session(sess_id)))

        eval_out = EvaluationOutput(
            depth_score=8, feedback="Solid.", passed_initial_defense=True,
            grounding_verified=True, stress_test_prompt="What happens if pool drops?",
        )
        eval_patch = patch(
            "app.api.v1.commit_defense.evaluate_candidate_defense", new_callable=AsyncMock
        )
        with eval_patch as mock_eval:
            mock_eval.return_value = eval_out
            payload = SubmitAnswerRequest(answer="I chose this pattern because of async I/O.")
            res = _drive_coro(submit_commit_defense_answer(sess_id, payload, current_user=user))

        assert res.status == DefenseStage.STRESS_TEST_ACTIVE
        assert any("Production Stress-Test" in t.content for t in res.turns)

    def test_submit_commit_answer_vague_pushback(self):
        user = User(id=uuid.uuid4(), email="dev@test.com")
        sess_id = f"commit-pb-{uuid.uuid4()}"
        _drive_coro(defense_store.save(self._make_test_session(sess_id)))

        eval_out = EvaluationOutput(
            depth_score=3, feedback="Too brief.", passed_initial_defense=False,
            grounding_verified=True, is_vague=True, pushback_prompt="Explain concrete mechanism?",
        )
        eval_patch = patch(
            "app.api.v1.commit_defense.evaluate_candidate_defense", new_callable=AsyncMock
        )
        with eval_patch as mock_eval:
            mock_eval.return_value = eval_out
            payload = SubmitAnswerRequest(answer="It just works better.")
            res = _drive_coro(submit_commit_defense_answer(sess_id, payload, current_user=user))

        assert res.status == DefenseStage.PUSHBACK_ACTIVE
        assert any("Pushback" in t.content for t in res.turns)

    def test_submit_commit_answer_stress_turn_advances(self):
        user = User(id=uuid.uuid4(), email="dev@test.com")
        sess_id = f"commit-sec-{uuid.uuid4()}"
        _drive_coro(
            defense_store.save(
                self._make_test_session(sess_id, status=DefenseStage.STRESS_TEST_ACTIVE, score=7)
            )
        )

        sec_out = SecondaryEvaluationOutput(
            handled_successfully=True, follow_up_score=9, feedback="Handled stress well."
        )
        sec_patch = patch(
            "app.api.v1.commit_defense.evaluate_secondary_turn", new_callable=AsyncMock
        )
        with sec_patch as mock_sec:
            mock_sec.return_value = sec_out
            payload = SubmitAnswerRequest(answer="I would add Redis caching with TTL.")
            res = _drive_coro(submit_commit_defense_answer(sess_id, payload, current_user=user))

        assert res.status == DefenseStage.SESSION_COMPLETED

    def test_analyze_commit_diff(self):
        proj_id, user_id = uuid.uuid4(), uuid.uuid4()
        user, proj = User(id=user_id, email="dev@test.com"), self._mock_project(proj_id, user_id)
        mock_db = self._mock_db(proj)

        mock_meta = CommitMetadata(
            commit_hash="c123456", author_name="Dev", committed_at="2026-11-09T00:00:00Z",
            message="Refactor", html_url="https://github.com/owner/repo/commit/c123456",
            total_additions=2, total_deletions=0, total_files=1,
        )
        fetch_patch = patch(
            "app.api.v1.commit_defense.fetch_github_commit_data", new_callable=AsyncMock
        )
        with fetch_patch as mock_fetch:
            mock_fetch.return_value = (mock_meta, SAMPLE_DIFF)
            payload = StartCommitDefenseRequest(commit_url_or_hash="c123456")
            res = _drive_coro(analyze_commit_diff(proj_id, payload, current_user=user, db=mock_db))

        assert res.total_files_changed == 1
        assert res.total_additions == 2
        assert "c123456" in res.summary_narrative
