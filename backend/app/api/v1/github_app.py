"""API endpoints for GitHub App integration, webhooks, and private repository ingestion."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import enqueue_clone_job
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.github_app import (
    GitHubAppRepoItem,
    GitHubAppRepoListResponse,
    GitHubAppStatusResponse,
    GitHubWebhookResponse,
    PrivateRepoProjectCreate,
)
from app.schemas.project import ProjectResponse
from app.services.github_app import (
    get_github_app_status,
    list_installation_repositories,
    verify_webhook_signature,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/github-app", tags=["GitHub App"])


@router.get(
    "/status",
    response_model=GitHubAppStatusResponse,
    summary="Get GitHub App deployment status and installation URL",
)
async def get_status() -> GitHubAppStatusResponse:
    """Returns whether the GitHub App is configured and its installation link."""
    status_dict = get_github_app_status()
    return GitHubAppStatusResponse(**status_dict)


@router.post(
    "/webhook",
    response_model=GitHubWebhookResponse,
    summary="GitHub App Webhook event receiver",
)
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str = Header("ping", alias="X-GitHub-Event"),
) -> GitHubWebhookResponse:
    """Verifies HMAC SHA-256 signature and processes GitHub App events."""
    payload_bytes = await request.body()

    if not verify_webhook_signature(payload_bytes, x_hub_signature_256):
        logger.warning(
            "github_webhook_signature_invalid",
            github_event=x_github_event,
            has_sig=bool(x_hub_signature_256),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing GitHub webhook signature",
        )

    action: str | None = None
    try:
        if payload_bytes:
            data: Dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))
            action = data.get("action")
    except Exception:
        pass

    logger.info(
        "github_webhook_received",
        github_event=x_github_event,
        action=action,
    )

    return GitHubWebhookResponse(
        status="ok",
        event=x_github_event,
        action=action,
        message="Webhook processed successfully",
    )


@router.get(
    "/installations/{installation_id}/repositories",
    response_model=GitHubAppRepoListResponse,
    summary="List accessible repositories for a GitHub App installation",
)
async def get_installation_repositories(
    installation_id: int,
    current_user: User = Depends(get_current_user),
) -> GitHubAppRepoListResponse:
    """Fetches repositories accessible under the specified GitHub App installation."""
    try:
        total, raw_repos = await list_installation_repositories(installation_id)
    except Exception as exc:
        logger.error(
            "list_installation_repositories_failed",
            installation_id=installation_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch repositories from GitHub App: {str(exc)}",
        )

    repo_items = [
        GitHubAppRepoItem(
            id=r["id"],
            name=r["name"],
            full_name=r["full_name"],
            private=r.get("private", False),
            default_branch=r.get("default_branch", "main"),
            description=r.get("description"),
            clone_url=r.get("clone_url", f"https://github.com/{r['full_name']}.git"),
            html_url=r.get("html_url", f"https://github.com/{r['full_name']}"),
            updated_at=r.get("updated_at"),
        )
        for r in raw_repos
    ]

    return GitHubAppRepoListResponse(
        installation_id=installation_id,
        total_count=total,
        repositories=repo_items,
    )


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Project from a private GitHub App repository",
)
async def create_private_project(
    payload: PrivateRepoProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Registers a private repository accessed via GitHub App and kicks off background analysis."""
    repo_name = payload.full_name.split("/")[-1].strip()
    canonical_url = f"https://github.com/{payload.full_name.strip()}"

    stmt = select(Project).where(
        Project.user_id == current_user.id,
        Project.github_url == canonical_url,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project with this GitHub repository already exists for current user",
        )

    now = datetime.now(timezone.utc)
    project = Project(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=repo_name,
        github_url=canonical_url,
        default_branch=payload.default_branch.strip() or "main",
        status="pending",
        installation_id=payload.installation_id,
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    await enqueue_clone_job(project.id)

    return ProjectResponse.model_validate(project)
