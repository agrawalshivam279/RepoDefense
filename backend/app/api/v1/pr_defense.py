"""FastAPI REST router for PR-scoped defense sessions.

Endpoints:
  POST /api/v1/pr-defense/projects/{project_id}/start  — start PR defense session
  GET  /api/v1/pr-defense/sessions/{session_id}        — get session state
  POST /api/v1/pr-defense/sessions/{session_id}/answer — submit candidate answer
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.evaluator import evaluate_candidate_defense, evaluate_secondary_turn
from app.ai.fsm import DefenseSessionStore, _advance_or_complete_session, defense_store
from app.ai.pr_question_generator import generate_pr_defense_questions
from app.analyzers.diff_parser import DiffParsingError, parse_unified_diff
from app.api.v1.pull_requests import fetch_github_pr_data, parse_github_pr_url
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseStage,
    DefenseTurn,
    DifficultyLevel,
    SubmitAnswerRequest,
    TurnRole,
)
from app.schemas.pr_analysis import PRAnalysisResponse
from app.schemas.pr_defense import PRDefenseSessionState, StartPRDefenseRequest

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["PR Defense"])


def _format_diff_question_turn(idx: int, total: int, text: str, hunk: str, path: str) -> str:
    return (
        f"Question {idx + 1}/{total} [PR DEFENSE]:\n\n{text}\n\n"
        f"Context: Changes in `{path}` at hunk `{hunk}`"
    )


async def _build_pr_session(
    project_id: str, pr_url: str, num_questions: int, store: DefenseSessionStore,
) -> PRDefenseSessionState:
    owner, repo, pr_number = parse_github_pr_url(pr_url)
    try:
        pr_meta, diff_text = await fetch_github_pr_data(owner, repo, pr_number)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch PR data from GitHub: {exc}",
        ) from exc

    try:
        parsed_files = parse_unified_diff(diff_text)
    except DiffParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse PR diff: {exc}",
        ) from exc

    if not parsed_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PR #{pr_number} has no code changes to defend.",
        )

    adds = sum(f.total_additions for f in parsed_files)
    dels = sum(f.total_deletions for f in parsed_files)
    narrative = f"PR #{pr_meta.pr_number} ('{pr_meta.title}') (+{adds}, -{dels})."
    pr_analysis = PRAnalysisResponse(
        metadata=pr_meta, files=parsed_files, total_files_changed=len(parsed_files),
        total_additions=adds, total_deletions=dels, summary_narrative=narrative,
    )

    diff_questions = await generate_pr_defense_questions(pr_analysis, num_questions)
    q_progress = [
        DefenseQuestionProgress(
            question=q,
            status=DefenseStage.QUESTION_ACTIVE if i == 0 else DefenseStage.INITIALIZING,
            difficulty=DifficultyLevel.INTERMEDIATE,
        )
        for i, q in enumerate(diff_questions)
    ]
    first_q, now_iso = diff_questions[0], datetime.now(timezone.utc).isoformat()

    session = PRDefenseSessionState(
        project_id=project_id, status=DefenseStage.QUESTION_ACTIVE,
        current_question_index=0, current_difficulty=DifficultyLevel.INTERMEDIATE,
        total_questions=len(diff_questions), questions=q_progress,
        created_at=now_iso, updated_at=now_iso,
        pr_number=pr_meta.pr_number, pr_title=pr_meta.title,
        pr_html_url=pr_meta.html_url, pr_author=pr_meta.author,
        pr_analysis_summary=narrative, diff_questions=diff_questions,
        turns=[
            DefenseTurn(
                role=TurnRole.INTERVIEWER,
                content=_format_diff_question_turn(
                    0, len(diff_questions), first_q.question_text,
                    first_q.diff_hunk_header, first_q.diff_file_path,
                ),
                stage=DefenseStage.QUESTION_ACTIVE,
                metadata={"question_id": first_q.id, "diff_file_path": first_q.diff_file_path},
            )
        ],
    )
    await store.save(session)
    logger.info("pr_defense_session_created", session_id=session.session_id, pr_number=pr_number)
    return session


@router.post(
    "/projects/{project_id}/start",
    response_model=PRDefenseSessionState,
    status_code=status.HTTP_201_CREATED,
    summary="Start a PR-scoped defense session",
)
async def start_pr_defense_session(
    project_id: uuid.UUID,
    payload: StartPRDefenseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PRDefenseSessionState:
    stmt = select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return await _build_pr_session(
        project_id=str(project_id),
        pr_url=payload.pr_url,
        num_questions=payload.num_questions,
        store=defense_store,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=PRDefenseSessionState,
    summary="Get current PR defense session state",
)
async def get_pr_defense_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> PRDefenseSessionState:
    session = await defense_store.get(session_id)
    if not session or not isinstance(session, PRDefenseSessionState):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PR defense session '{session_id}' not found.",
        )
    return session


async def _handle_secondary(
    session: PRDefenseSessionState,
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


def _apply_pr_branch(
    session: PRDefenseSessionState,
    prog: DefenseQuestionProgress,
    eval_out,
) -> None:
    diff_q = session.diff_questions[session.current_question_index]
    if eval_out.passed_initial_defense:
        prog.status = session.status = DefenseStage.STRESS_TEST_ACTIVE
        prompt = eval_out.stress_test_prompt or (
            f"Under a 10x traffic spike on `{diff_q.diff_file_path}`, how does your change scale?"
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
            role=TurnRole.INTERVIEWER, content=content, stage=session.status,
            metadata={"depth_score": eval_out.depth_score},
        )
    )


@router.post(
    "/sessions/{session_id}/answer",
    response_model=PRDefenseSessionState,
    summary="Submit a candidate answer in a PR defense session",
)
async def submit_pr_defense_answer(
    session_id: str,
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
) -> PRDefenseSessionState:
    raw_session = await defense_store.get(session_id)
    if not raw_session or not isinstance(raw_session, PRDefenseSessionState):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PR defense session '{session_id}' not found.",
        )
    session: PRDefenseSessionState = raw_session
    if session.status == DefenseStage.SESSION_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This PR defense session has already been completed.",
        )

    prog = session.questions[session.current_question_index]
    diff_q = session.diff_questions[session.current_question_index]
    ans = payload.answer
    session.turns.append(DefenseTurn(role=TurnRole.CANDIDATE, content=ans, stage=session.status))

    if session.status == DefenseStage.QUESTION_ACTIVE:
        eval_out = await evaluate_candidate_defense(diff_q, ans)
        prog.initial_defense = ans
        prog.defense_score, prog.feedback = eval_out.depth_score, eval_out.feedback

        if eval_out.is_vague and prog.pushback_count < 1:
            prog.pushback_count += 1
            pb = eval_out.pushback_prompt or (
                f"Looking at `{diff_q.diff_file_path}`, what concrete mechanism drove this change?"
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
            _apply_pr_branch(session, prog, eval_out)

    elif session.status == DefenseStage.PUSHBACK_ACTIVE:
        prog.pushback_response = ans
        eval_out = await evaluate_candidate_defense(diff_q, ans)
        prog.defense_score, prog.feedback = eval_out.depth_score, eval_out.feedback
        _apply_pr_branch(session, prog, eval_out)

    elif session.status == DefenseStage.STRESS_TEST_ACTIVE:
        prompt_ctx = prog.stress_test_prompt or diff_q.question_text
        await _handle_secondary(session, prog, ans, prompt_ctx, is_stress=True)

    elif session.status == DefenseStage.MENTOR_ACTIVE:
        prompt_ctx = prog.retest_question or diff_q.question_text
        await _handle_secondary(session, prog, ans, prompt_ctx, is_stress=False)

    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit an answer in session state '{session.status}'.",
        )

    session.updated_at = datetime.now(timezone.utc).isoformat()
    await defense_store.save(session)
    return session
