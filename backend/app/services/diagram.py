"""Service for synthesizing and orchestrating architecture Mermaid diagrams."""

import asyncio
import json
import os
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.llm import clean_json_response  # noqa: E402
from app.ai.prompts import (  # noqa: E402
    MERMAID_DIAGRAM_SYSTEM_PROMPT,
    format_mermaid_diagram_user_prompt,
)
from app.analyzers.architecture import normalize_directory_tokens  # noqa: E402
from app.analyzers.diagram import (  # noqa: E402
    build_deterministic_mermaid_diagram,
    validate_mermaid_syntax,
)
from app.core.config import settings  # noqa: E402
from app.models.analysis import AnalyzedFile, Dependency, Evidence  # noqa: E402
from app.models.project import Project, RepositorySnapshot  # noqa: E402
from app.schemas.diagram import (  # noqa: E402
    DiagramResponse,
    DiagramType,
)

logger = structlog.get_logger(__name__)


async def generate_project_architecture_diagram(
    project: Project,
    db: AsyncSession,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float = 8.0,
) -> DiagramResponse:
    """Generates a Mermaid architecture diagram for a project via LiteLLM with fallback."""
    project_id = project.id
    project_name = project.name

    # 1. Retrieve latest snapshot
    stmt_snap = (
        select(RepositorySnapshot)
        .where(RepositorySnapshot.project_id == project_id)
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(1)
    )
    res_snap = await db.execute(stmt_snap)
    snapshot = res_snap.scalar_one_or_none()

    file_paths: list[str] = []
    if snapshot:
        stmt_files = select(AnalyzedFile.path).where(
            AnalyzedFile.snapshot_id == snapshot.id
        )
        res_files = await db.execute(stmt_files)
        file_paths = [r[0] for r in res_files.all()]

    # 2. Extract dependencies
    stmt_deps = select(Dependency.name).where(Dependency.project_id == project_id)
    res_deps = await db.execute(stmt_deps)
    dependencies = [r[0] for r in res_deps.all()]

    # 3. Extract evidence
    stmt_ev = select(Evidence.title, Evidence.evidence_type).where(
        Evidence.project_id == project_id
    )
    res_ev = await db.execute(stmt_ev)
    evidence_tags = [f"{r[0]} ({r[1]})" for r in res_ev.all()]

    _, top_dirs_set = normalize_directory_tokens(file_paths)
    top_directories = list(top_dirs_set)

    # 4. Prepare deterministic fallback baseline
    fallback_code, fb_nodes, fb_edges, fb_summary = build_deterministic_mermaid_diagram(
        project_name=project_name,
        dependencies=dependencies,
        evidence_tags=evidence_tags,
        top_directories=top_directories,
    )

    # 5. Attempt LLM generation if configured
    effective_model = model if model is not None else settings.LLM_MODEL
    effective_key = api_key if api_key is not None else settings.FREELLMAPI_API_KEY
    effective_base_url = base_url if base_url is not None else settings.FREELLMAPI_BASE_URL

    if effective_key:
        try:
            user_prompt = format_mermaid_diagram_user_prompt(
                project_name=project_name,
                dependencies=dependencies,
                evidence_tags=evidence_tags,
                top_directories=top_directories,
            )

            kwargs: dict[str, Any] = {
                "model": effective_model,
                "messages": [
                    {"role": "system", "content": MERMAID_DIAGRAM_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "timeout": timeout_seconds,
            }
            if effective_base_url:
                kwargs["api_base"] = effective_base_url
            if effective_key:
                kwargs["api_key"] = effective_key

            response = await asyncio.wait_for(
                litellm.acompletion(**kwargs),
                timeout=timeout_seconds,
            )

            raw_content = response.choices[0].message.content or ""
            clean_content = clean_json_response(raw_content)
            data = json.loads(clean_content)

            mermaid_code = data.get("mermaid_code", "")
            if validate_mermaid_syntax(mermaid_code):
                summary = data.get("summary") or f"Architectural flowchart for {project_name}."
                logger.info("diagram_llm_generation_success", project_id=str(project_id))
                return DiagramResponse(
                    project_id=str(project_id),
                    project_name=project_name,
                    diagram_type=DiagramType.FLOWCHART_TD,
                    mermaid_code=mermaid_code,
                    nodes=fb_nodes,
                    edges=fb_edges,
                    is_fallback=False,
                    summary=summary,
                )
            logger.warning(
                "diagram_invalid_mermaid_syntax",
                project_id=str(project_id),
                code_sample=mermaid_code[:100],
            )
        except Exception as exc:
            logger.warning(
                "diagram_llm_generation_failed_using_fallback",
                project_id=str(project_id),
                error=str(exc),
            )

    # 6. Return deterministic fallback
    logger.info("diagram_using_deterministic_fallback", project_id=str(project_id))
    return DiagramResponse(
        project_id=str(project_id),
        project_name=project_name,
        diagram_type=DiagramType.FLOWCHART_TD,
        mermaid_code=fallback_code,
        nodes=fb_nodes,
        edges=fb_edges,
        is_fallback=True,
        summary=fb_summary,
    )
