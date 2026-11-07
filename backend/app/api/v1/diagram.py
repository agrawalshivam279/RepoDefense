import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.diagram import DiagramResponse
from app.services.diagram import generate_project_architecture_diagram

router = APIRouter(tags=["Diagram"])


@router.get(
    "/projects/{project_id}/diagram",
    response_model=DiagramResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Mermaid architecture flowchart for repository",
    description=(
        "Synthesizes a multi-tier Mermaid flowchart diagram from repository "
        "dependencies, file topologies, and architectural evidence records. "
        "Employs LiteLLM with automatic deterministic fallback guarantees."
    ),
)
async def get_project_diagram(
    project_id: Annotated[
        uuid.UUID,
        Path(description="Unique UUID of the project"),
    ],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagramResponse:
    """Retrieve the automated architecture diagram for a repository."""
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
            detail="Not authorized to access this project's architecture diagram",
        )

    return await generate_project_architecture_diagram(project, db)
