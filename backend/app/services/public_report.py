"""Service for cryptographic share tokens, public report sanitization, and SVG badges."""

import asyncio
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fsm import defense_store
from app.models.project import Project, RepositorySnapshot
from app.schemas.defense import DefenseSessionState, DefenseStage
from app.schemas.public_report import (
    CreateShareTokenRequest,
    PublicCategoryScore,
    PublicDefenseReportResponse,
    PublicShareTokenResponse,
)
from app.services.enhanced_report import generate_enhanced_defense_report

logger = structlog.get_logger(__name__)


@dataclass
class PublicShareRecord:
    """Internal registry record linking a public share token to a defense session."""

    share_token: str
    session_id: str
    project_id: str
    user_id: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None


class PublicReportStore:
    """Thread-safe in-memory registry for public defense report share tokens."""

    def __init__(self) -> None:
        self._tokens: Dict[str, PublicShareRecord] = {}
        self._session_tokens: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def save(self, record: PublicShareRecord) -> PublicShareRecord:
        async with self._lock:
            self._tokens[record.share_token] = record
            self._session_tokens[record.session_id] = record.share_token
            return record

    async def get_by_token(self, token: str) -> Optional[PublicShareRecord]:
        async with self._lock:
            return self._tokens.get(token)

    async def get_by_session(self, session_id: str) -> Optional[PublicShareRecord]:
        async with self._lock:
            token = self._session_tokens.get(session_id)
            return self._tokens.get(token) if token else None

    async def delete_by_session(self, session_id: str) -> bool:
        async with self._lock:
            token = self._session_tokens.pop(session_id, None)
            if token:
                self._tokens.pop(token, None)
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._tokens.clear()
            self._session_tokens.clear()


public_share_store = PublicReportStore()


def determine_certification_tier(score: float, verdict: str) -> str:
    """Classifies candidate defense into standard certification tiers."""
    v_lower = verdict.lower()
    if score >= 7.5 or "certified" in v_lower or "principal" in v_lower:
        return "Certified Principal"
    if score >= 5.0 or "solid" in v_lower or "passed" in v_lower:
        return "Solid Architect"
    return "Remediation Required"


def build_share_response(
    record: PublicShareRecord,
    base_web_url: str = "http://localhost:3000",
    base_api_url: str = "http://localhost:8000",
) -> PublicShareTokenResponse:
    """Builds the share response with web verification URLs and embed snippets."""
    clean_web = base_web_url.rstrip("/")
    clean_api = base_api_url.rstrip("/")
    share_url = f"{clean_web}/verify/{record.share_token}"
    badge_url = f"{clean_api}/api/v1/public/badges/{record.share_token}.svg"

    md = f"[![RepoDefense Certified]({badge_url})]({share_url})"
    html = f'<a href="{share_url}"><img src="{badge_url}" alt="RepoDefense Certified" /></a>'

    return PublicShareTokenResponse(
        session_id=record.session_id,
        project_id=record.project_id,
        share_token=record.share_token,
        share_url=share_url,
        badge_url=badge_url,
        markdown_badge=md,
        html_badge=html,
        is_active=record.is_active,
        created_at=record.created_at.isoformat(),
        expires_at=record.expires_at.isoformat() if record.expires_at else None,
    )


async def create_or_update_share_token(
    session: DefenseSessionState,
    project: Project,
    payload: CreateShareTokenRequest,
    base_web_url: str = "http://localhost:3000",
    base_api_url: str = "http://localhost:8000",
) -> PublicShareTokenResponse:
    """Generates or updates a public share token for a completed defense session."""
    if session.status != DefenseStage.SESSION_COMPLETED:
        raise ValueError("Defense session must be completed before creating a public share link.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=payload.expires_in_days) if payload.expires_in_days else None

    existing = await public_share_store.get_by_session(session.session_id)
    token = existing.share_token if existing else f"rd_{secrets.token_urlsafe(24)}"

    record = PublicShareRecord(
        share_token=token,
        session_id=session.session_id,
        project_id=str(project.id),
        user_id=str(project.user_id),
        is_active=payload.is_active,
        created_at=existing.created_at if existing else now,
        expires_at=expires_at,
    )
    await public_share_store.save(record)
    return build_share_response(record, base_web_url, base_api_url)


async def resolve_public_report(
    share_token: str,
    db: AsyncSession,
) -> tuple[PublicDefenseReportResponse, PublicShareRecord]:
    """Resolves a share token and compiles a public-safe verified defense report."""
    record = await public_share_store.get_by_token(share_token)
    if not record or not record.is_active:
        raise KeyError("Public defense report not found or sharing has been revoked.")

    if record.expires_at and datetime.now(timezone.utc) > record.expires_at:
        raise ValueError("Public share link has expired.")

    session = await defense_store.get(record.session_id)
    if not session:
        raise KeyError("Associated defense session is no longer available.")

    enhanced = await generate_enhanced_defense_report(session, db)
    project_stmt = select(Project).where(Project.id == uuid.UUID(record.project_id))
    project = (await db.execute(project_stmt)).scalar_one_or_none()

    snap_stmt = (
        select(RepositorySnapshot)
        .where(RepositorySnapshot.project_id == uuid.UUID(record.project_id))
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(1)
    )
    snapshot = (await db.execute(snap_stmt)).scalar_one_or_none()
    commit_sha = snapshot.commit_hash[:7] if snapshot else "verified"

    tier = determine_certification_tier(enhanced.overall_score, enhanced.verdict)
    cat_scores = [
        PublicCategoryScore(
            category=cs.category,
            score=cs.score,
            questions_count=cs.questions_count,
            status=cs.status,
            summary=cs.summary,
        )
        for cs in enhanced.category_scores
    ]

    report = PublicDefenseReportResponse(
        verification_id=record.share_token,
        project_name=project.name if project else "Verified Project",
        github_url=project.github_url if project else "https://github.com",
        commit_hash=commit_sha,
        overall_score=round(enhanced.overall_score, 1),
        verdict=enhanced.verdict,
        certification_tier=tier,
        summary=enhanced.summary,
        category_scores=cat_scores,
        key_strengths=enhanced.key_strengths,
        critical_blind_spots=enhanced.critical_blind_spots,
        architecture_primary_pattern=enhanced.architecture_primary_pattern,
        tech_health_score=enhanced.tech_health_score,
        total_questions=enhanced.total_questions,
        completed_at=enhanced.completed_at,
        verified_at=datetime.now(timezone.utc).isoformat(),
        issuer="RepoDefense Verifier",
    )
    return report, record


def generate_defense_svg_badge(tier: str, score: float) -> str:
    """Renders a pixel-crisp, Shields.io-compliant dynamic SVG verification badge."""
    label = "RepoDefense"
    right_text = f"{tier} • {score:.1f}/10"

    # Color palette
    if tier == "Certified Principal":
        bg_right = "#059669"  # Emerald 600
    elif tier == "Solid Architect":
        bg_right = "#0284c7"  # Sky 600
    else:
        bg_right = "#d97706"  # Amber 600

    left_width = 90
    right_width = max(110, len(right_text) * 7 + 20)
    total_width = left_width + right_width
    left_x = left_width / 2.0
    right_x = left_width + (right_width / 2.0)

    font_family = "Verdana,Geneva,DejaVu Sans,sans-serif"
    lw7, rw7 = f"{left_width * 7:.0f}", f"{right_width * 7:.0f}"
    lx10, rx10 = f"{left_x * 10:.0f}", f"{right_x * 10:.0f}"

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" '
        f'role="img" aria-label="{label}: {right_text}">\n'
        f"  <title>{label}: {right_text}</title>\n"
        '  <linearGradient id="s" x2="0" y2="100%">\n'
        '    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>\n'
        '    <stop offset="1" stop-opacity=".1"/>\n'
        "  </linearGradient>\n"
        '  <clipPath id="r">\n'
        f'    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>\n'
        "  </clipPath>\n"
        '  <g clip-path="url(#r)">\n'
        f'    <rect width="{left_width}" height="20" fill="#18181b"/>\n'
        f'    <rect x="{left_width}" width="{right_width}" height="20" fill="{bg_right}"/>\n'
        f'    <rect width="{total_width}" height="20" fill="url(#s)"/>\n'
        "  </g>\n"
        f'  <g fill="#fff" text-anchor="middle" font-family="{font_family}" '
        'text-rendering="geometricPrecision" font-size="110">\n'
        f'    <text aria-hidden="true" x="{lx10}" y="150" fill="#010101" fill-opacity=".3" '
        f'transform="scale(.1)" textLength="{lw7}">{label}</text>\n'
        f'    <text x="{lx10}" y="140" transform="scale(.1)" fill="#fff" '
        f'textLength="{lw7}">{label}</text>\n'
        f'    <text aria-hidden="true" x="{rx10}" y="150" fill="#010101" fill-opacity=".3" '
        f'transform="scale(.1)" textLength="{rw7}">{right_text}</text>\n'
        f'    <text x="{rx10}" y="140" transform="scale(.1)" fill="#fff" '
        f'textLength="{rw7}">{right_text}</text>\n'
        "  </g>\n"
        "</svg>"
    )
    return svg
