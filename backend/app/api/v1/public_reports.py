"""API router for managing public shareable defense reports and dynamic SVG resume badges."""

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fsm import defense_store
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.public_report import (
    CreateShareTokenRequest,
    PublicDefenseReportResponse,
    PublicShareTokenResponse,
)
from app.services.public_report import (
    build_share_response,
    create_or_update_share_token,
    generate_defense_svg_badge,
    public_share_store,
    resolve_public_report,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Public Defense Reports"])


async def _verify_project_ownership(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Project:
    """Verifies project existence and tenant ownership."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == user_id,
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized.",
        )
    return project


@router.post(
    "/projects/{project_id}/defense/{session_id}/share",
    response_model=PublicShareTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update public share credentials for a completed defense session",
)
async def create_public_share(
    project_id: uuid.UUID,
    session_id: str,
    payload: Optional[CreateShareTokenRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PublicShareTokenResponse:
    """Generates an unguessable cryptographic token for public report access."""
    project = await _verify_project_ownership(project_id, current_user.id, db)
    session = await defense_store.get(session_id)
    if not session or session.project_id != str(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Defense session '{session_id}' not found for this project.",
        )

    req = payload or CreateShareTokenRequest()
    try:
        return await create_or_update_share_token(
            session=session,
            project=project,
            payload=req,
            base_web_url="http://localhost:3000",
            base_api_url="http://localhost:8000",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/projects/{project_id}/defense/{session_id}/share",
    response_model=PublicShareTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current public share credentials and embed snippets",
)
async def get_public_share_info(
    project_id: uuid.UUID,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PublicShareTokenResponse:
    """Fetches share token details if public sharing is active."""
    await _verify_project_ownership(project_id, current_user.id, db)
    record = await public_share_store.get_by_session(session_id)
    if not record or record.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public share link not configured for this defense session.",
        )
    return build_share_response(record)


@router.delete(
    "/projects/{project_id}/defense/{session_id}/share",
    status_code=status.HTTP_200_OK,
    summary="Revoke public sharing for a defense session",
)
async def revoke_public_share(
    project_id: uuid.UUID,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revokes public access token for a defense session."""
    await _verify_project_ownership(project_id, current_user.id, db)
    revoked = await public_share_store.delete_by_session(session_id)
    return {"revoked": revoked, "session_id": session_id}


@router.get(
    "/public/reports/{share_token}",
    response_model=PublicDefenseReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve verified public defense report without authentication",
)
async def get_public_defense_report_endpoint(
    share_token: str,
    db: AsyncSession = Depends(get_db),
) -> PublicDefenseReportResponse:
    """Publicly accessible verification endpoint for recruiters and engineering hiring managers."""
    try:
        report, _ = await resolve_public_report(share_token, db)
        return report
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc.args[0]),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(exc),
        ) from exc


@router.get(
    "/public/badges/{share_token}.svg",
    status_code=status.HTTP_200_OK,
    summary="Dynamic SVG verification badge for GitHub READMEs and resumes",
)
async def get_public_badge_endpoint(
    share_token: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Renders dynamic, cache-controlled SVG badge for embeds."""
    try:
        report, _ = await resolve_public_report(share_token, db)
        svg_content = generate_defense_svg_badge(report.certification_tier, report.overall_score)
    except Exception:
        # Fallback neutral badge when token is invalid or report is unavailable
        svg_content = generate_defense_svg_badge("Unverified", 0.0)

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=300, s-maxage=3600",
            "Content-Type": "image/svg+xml; charset=utf-8",
        },
    )
