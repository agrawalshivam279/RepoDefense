"""FastAPI REST router for Git Commit-scoped defense sessions.

Endpoints:
  POST /api/v1/commit-defense/projects/{project_id}/start   — start commit defense session
  GET  /api/v1/commit-defense/sessions/{session_id}         — get session state
  POST /api/v1/commit-defense/sessions/{session_id}/answer  — submit candidate answer
  POST /api/v1/commit-defense/projects/{project_id}/analyze — analyze commit diff
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.evaluator import evaluate_candidate_defense, evaluate_secondary_turn
from app.ai.fsm import _advance_or_complete_session, defense_store
from app.analyzers.commit_fetcher import (
    build_commit_session,
    fetch_github_commit_data,
    parse_github_commit_url_or_sha,
)
from app.analyzers.diff_parser import DiffParsingError, parse_unified_diff
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.commit_defense import (
    CommitAnalysisResponse,
    CommitDefenseSessionState,
    StartCommitDefenseRequest,
)
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseStage,
    DefenseTurn,
    SubmitAnswerRequest,
    TurnRole,
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Commit Defense"])


@router.post(
    "/projects/{project_id}/start",
    response_model=CommitDefenseSessionState,
    status_code=status.HTTP_201_CREATED,
    summary="Start a commit-scoped defense session",
)
async def start_commit_defense_session(
    project_id: uuid.UUID,
    payload: StartCommitDefenseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommitDefenseSessionState:
    stmt = select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project '{project_id}' not found.")
    owner, repo, sha = parse_github_commit_url_or_sha(
        payload.commit_url_or_hash, project.github_url
    )
    meta, diff_text = await fetch_github_commit_data(owner, repo, sha)
    return await build_commit_session(
        str(project_id), meta, diff_text, payload.num_questions, defense_store
    )


@router.get(
    "/sessions/{session_id}",
    response_model=CommitDefenseSessionState,
    summary="Get current commit defense session state",
)
async def get_commit_defense_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> CommitDefenseSessionState:
    session = await defense_store.get(session_id)
    if not session or not isinstance(session, CommitDefenseSessionState):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Commit defense session '{session_id}' not found."
        )
    return session


async def _handle_commit_secondary(
    session: CommitDefenseSessionState,
    prog: DefenseQuestionProgress,
    answer: str,
    prompt_ctx: str,
    is_stress: bool,
) -> None:
    sec = await evaluate_secondary_turn(prompt_ctx, answer)
    init_score = prog.defense_score or (5 if is_stress else 3)
    w_init, w_sec = (0.6, 0.4) if is_stress else (0.4, 0.6)
    prog.final_score = int(round(w_init * init_score + w_sec * sec.follow_up_score))
    label = "Evaluation" if is_stress else "Mentor Evaluation"
    if is_stress:
        prog.stress_test_response = answer
    else:
        prog.retest_response = answer
    prog.status = DefenseStage.QUESTION_COMPLETED
    session.turns.append(
        DefenseTurn(
            role=TurnRole.INTERVIEWER,
            content=f"{label}: {sec.feedback}",
            stage=DefenseStage.QUESTION_COMPLETED,
            metadata={"final_score": prog.final_score},
        )
    )
    _advance_or_complete_session(session)


def _apply_commit_branch(
    session: CommitDefenseSessionState,
    prog: DefenseQuestionProgress,
    eval_out,
) -> None:
    diff_q = session.diff_questions[session.current_question_index]
    if eval_out.passed_initial_defense:
        prog.status = session.status = DefenseStage.STRESS_TEST_ACTIVE
        prompt = (
            eval_out.stress_test_prompt
            or f"Under heavy load on `{diff_q.diff_file_path}`, how does your commit scale?"
        )
        prog.stress_test_prompt = prompt
        content = f"{eval_out.feedback}\n\nProduction Stress-Test:\n{prompt}"
    else:
        ref = f"`{diff_q.diff_file_path}` at `{diff_q.diff_hunk_header}`"
        prog.status = session.status = DefenseStage.MENTOR_ACTIVE
        hint = eval_out.mentor_hint or f"Re-examine changes in {ref}. Consider edge cases."
        retest = eval_out.retest_question or f"Given changes in {ref}, what fallback would you add?"
        prog.mentor_hint, prog.retest_question = hint, retest
        content = f"{eval_out.feedback}\n\nMentor Hint: {hint}\n\nFollow-up: {retest}"
    session.turns.append(
        DefenseTurn(
            role=TurnRole.INTERVIEWER,
            content=content,
            stage=session.status,
            metadata={"depth_score": eval_out.depth_score},
        )
    )


@router.post(
    "/sessions/{session_id}/answer",
    response_model=CommitDefenseSessionState,
    summary="Submit candidate defense answer in a commit defense session",
)
async def submit_commit_defense_answer(
    session_id: str,
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
) -> CommitDefenseSessionState:
    raw_session = await defense_store.get(session_id)
    if not raw_session or not isinstance(raw_session, CommitDefenseSessionState):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Commit defense session '{session_id}' not found."
        )
    session: CommitDefenseSessionState = raw_session
    if session.status == DefenseStage.SESSION_COMPLETED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This commit defense session has already been completed."
        )

    prog = session.questions[session.current_question_index]
    diff_q = session.diff_questions[session.current_question_index]
    ans = payload.answer
    session.turns.append(DefenseTurn(role=TurnRole.CANDIDATE, content=ans, stage=session.status))

    if session.status == DefenseStage.QUESTION_ACTIVE:
        eval_out = await evaluate_candidate_defense(diff_q, ans)
        prog.initial_defense, prog.defense_score, prog.feedback = (
            ans,
            eval_out.depth_score,
            eval_out.feedback,
        )
        if eval_out.is_vague and prog.pushback_count < 1:
            prog.pushback_count += 1
            pb = (
                eval_out.pushback_prompt
                or f"Looking at `{diff_q.diff_file_path}`, what concrete mechanism drove this?"
            )
            prog.pushback_prompt = pb
            prog.status = session.status = DefenseStage.PUSHBACK_ACTIVE
            session.turns.append(
                DefenseTurn(
                    role=TurnRole.INTERVIEWER,
                    content=f"{eval_out.feedback}\n\nPrincipal Engineer Pushback:\n{pb}",
                    stage=DefenseStage.PUSHBACK_ACTIVE,
                    metadata={"depth_score": eval_out.depth_score, "is_vague": True},
                )
            )
        else:
            _apply_commit_branch(session, prog, eval_out)

    elif session.status == DefenseStage.PUSHBACK_ACTIVE:
        prog.pushback_response = ans
        eval_out = await evaluate_candidate_defense(diff_q, ans)
        prog.defense_score, prog.feedback = eval_out.depth_score, eval_out.feedback
        _apply_commit_branch(session, prog, eval_out)

    elif session.status in (DefenseStage.STRESS_TEST_ACTIVE, DefenseStage.MENTOR_ACTIVE):
        is_stress = session.status == DefenseStage.STRESS_TEST_ACTIVE
        prompt_ctx = (
            prog.stress_test_prompt if is_stress else prog.retest_question
        ) or diff_q.question_text
        await _handle_commit_secondary(session, prog, ans, prompt_ctx, is_stress=is_stress)

    else:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot submit an answer in session state '{session.status}'.",
        )

    session.updated_at = datetime.now(timezone.utc).isoformat()
    await defense_store.save(session)
    return session


@router.post(
    "/projects/{project_id}/analyze",
    response_model=CommitAnalysisResponse,
    summary="Analyze commit diff without starting a defense session",
)
async def analyze_commit_diff(
    project_id: uuid.UUID,
    payload: StartCommitDefenseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommitAnalysisResponse:
    stmt = select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project '{project_id}' not found.")

    owner, repo, sha = parse_github_commit_url_or_sha(
        payload.commit_url_or_hash, project.github_url
    )
    meta, diff_text = await fetch_github_commit_data(owner, repo, sha)
    try:
        parsed_files = parse_unified_diff(diff_text)
    except DiffParsingError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Failed to parse commit diff: {exc}"
        ) from exc

    adds, dels = (
        sum(f.total_additions for f in parsed_files),
        sum(f.total_deletions for f in parsed_files),
    )
    short_sha = meta.commit_hash[:7]
    count = len(parsed_files)
    narrative = f"Commit {short_sha} ('{meta.message}') touched {count} file(s) (+{adds}/-{dels})."
    return CommitAnalysisResponse(
        metadata=meta,
        files=parsed_files,
        total_files_changed=len(parsed_files),
        total_additions=adds,
        total_deletions=dels,
        summary_narrative=narrative,
    )
