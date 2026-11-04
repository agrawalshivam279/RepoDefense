import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import enqueue_clone_job
from app.core.security import get_current_user
from app.models.analysis import AnalyzedFile, Dependency, Evidence
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.evidence import EvidenceResponse
from app.schemas.project import (
    DependencyOverviewItem,
    LanguageMetric,
    ProjectCreate,
    ProjectOverviewResponse,
    ProjectResponse,
    RepositoryOverviewMetrics,
)
from app.schemas.summary import ProjectSummary

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a GitHub repository project",
)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Creates a new Project record for the authenticated user and enqueues cloning."""
    stmt = select(Project).where(
        Project.user_id == current_user.id,
        Project.github_url == payload.github_url,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project with this GitHub URL already exists for current user",
        )

    project = Project(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=payload.get_normalized_name(),
        github_url=payload.github_url,
        default_branch=payload.default_branch,
        status="pending",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    await enqueue_clone_job(project.id)

    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse], summary="List all user projects")
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectResponse]:
    """Retrieves all projects belonging to the current user."""
    stmt = (
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get project by ID")
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Retrieves a single project owned by the current user."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a project")
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Deletes a project owned by the current user."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    await db.delete(project)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{project_id}/evidence",
    response_model=list[EvidenceResponse],
    summary="List architectural evidence",
)
async def list_project_evidence(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EvidenceResponse]:
    """Retrieves all architectural evidence records for the specified project."""
    stmt_proj = select(Project).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )
    project = (await db.execute(stmt_proj)).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    stmt_ev = (
        select(Evidence)
        .where(Evidence.project_id == project_id)
        .order_by(Evidence.start_line, Evidence.id)
    )
    evidence_rows = (await db.execute(stmt_ev)).scalars().all()
    return [EvidenceResponse.model_validate(e) for e in evidence_rows]


@router.get(
    "/{project_id}/overview",
    response_model=ProjectOverviewResponse,
    summary="Get repository overview",
)
async def get_project_overview(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectOverviewResponse:
    """Retrieves full repository analysis overview for a project owned by the current user."""
    stmt_proj = select(Project).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )
    project = (await db.execute(stmt_proj)).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # 1. Fetch latest repository snapshot
    stmt_snap = (
        select(RepositorySnapshot)
        .where(RepositorySnapshot.project_id == project_id)
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(1)
    )
    snapshot = (await db.execute(stmt_snap)).scalar_one_or_none()

    # 2. Fetch cataloged dependencies
    stmt_deps = (
        select(Dependency)
        .where(Dependency.project_id == project_id)
        .order_by(Dependency.is_dev, Dependency.name)
    )
    dep_rows = (await db.execute(stmt_deps)).scalars().all()
    dep_items = [
        DependencyOverviewItem(
            name=d.name,
            version=d.version,
            source_file=d.source_file,
            is_dev=d.is_dev,
        )
        for d in dep_rows
    ]

    # 3. Fetch evidence count
    stmt_ev_count = select(func.count(Evidence.id)).where(Evidence.project_id == project_id)
    evidence_count = (await db.execute(stmt_ev_count)).scalar() or 0

    # 4. Aggregate file & language metrics from the snapshot
    language_metrics: list[LanguageMetric] = []
    total_files = 0
    total_lines = 0

    if snapshot:
        stmt_files = (
            select(
                AnalyzedFile.language,
                func.count(AnalyzedFile.id).label("file_count"),
                func.coalesce(func.sum(AnalyzedFile.total_lines), 0).label("total_lines"),
            )
            .where(AnalyzedFile.snapshot_id == snapshot.id)
            .group_by(AnalyzedFile.language)
            .order_by(func.coalesce(func.sum(AnalyzedFile.total_lines), 0).desc())
        )
        file_rows = (await db.execute(stmt_files)).all()
        for r in file_rows:
            language_metrics.append(
                LanguageMetric(
                    language=r.language,
                    file_count=r.file_count,
                    total_lines=r.total_lines,
                )
            )
            total_files += r.file_count
            total_lines += r.total_lines

    # 5. Deserialize AI project summary if present
    parsed_summary: Optional[ProjectSummary] = None
    commit_hash: Optional[str] = None
    if snapshot:
        commit_hash = snapshot.commit_hash
        if snapshot.summary:
            try:
                parsed_summary = ProjectSummary.model_validate_json(snapshot.summary)
            except Exception:
                parsed_summary = None

    metrics = RepositoryOverviewMetrics(
        total_files=total_files,
        total_lines=total_lines,
        languages=language_metrics,
        dependency_count=len(dep_items),
        evidence_count=evidence_count,
    )

    return ProjectOverviewResponse(
        project_id=project.id,
        name=project.name,
        github_url=project.github_url,
        default_branch=project.default_branch,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        commit_hash=commit_hash,
        summary=parsed_summary,
        metrics=metrics,
        dependencies=dep_items,
    )
