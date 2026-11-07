import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.architecture import ArchitectureReportResponse
from app.services.architecture import detect_repository_architecture

router = APIRouter(tags=["Architecture"])


@router.get(
    "/projects/{project_id}/architecture",
    response_model=ArchitectureReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect and classify repository architecture pattern and risks",
    description=(
        "Performs deterministic static analysis on repository directory topology, "
        "dependency manifests, and architectural evidence to classify high-level design "
        "patterns (Modular Monolith, MVC, Clean Architecture, Event-Driven, etc.) "
        "and identify structural design smells."
    ),
)
async def get_project_architecture(
    project_id: Annotated[
        uuid.UUID,
        Path(description="Unique UUID of the project"),
    ],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchitectureReportResponse:
    """Retrieve the automated architectural pattern audit for a repository."""
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project's architecture audit",
        )

    return await detect_repository_architecture(project, db)
