import uuid
from pathlib import Path
from typing import Optional, Sequence, Union

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.dependencies.base import BaseDependencyParser, DependencyMetadata
from app.analyzers.dependencies.node import NodeDependencyParser
from app.analyzers.dependencies.python import PythonDependencyParser
from app.models.analysis import Dependency

logger = structlog.get_logger(__name__)

_PYTHON_PARSER = PythonDependencyParser()
_NODE_PARSER = NodeDependencyParser()


def get_dependency_parser(file_name: str) -> Optional[BaseDependencyParser]:
    """Resolves the manifest parser based on the filename convention."""
    lower_name = file_name.lower()
    if lower_name == "pyproject.toml":
        return _PYTHON_PARSER
    if lower_name.startswith("requirements") and lower_name.endswith(".txt"):
        return _PYTHON_PARSER
    if lower_name.endswith("requirements.txt"):
        return _PYTHON_PARSER
    if lower_name == "package.json":
        return _NODE_PARSER
    return None


def extract_file_dependencies(
    file_path: Union[Path, str],
    content_bytes: bytes,
) -> list[DependencyMetadata]:
    """Extracts structured dependency records from manifest bytes if parser is registered."""
    path_obj = Path(file_path) if isinstance(file_path, str) else file_path
    parser = get_dependency_parser(path_obj.name)
    if not parser:
        return []

    try:
        content_str = content_bytes.decode("utf-8", errors="replace")
        return parser.parse(content_str, file_path=str(path_obj.as_posix()))
    except Exception as exc:
        logger.error("dependency_extraction_failed", path=str(path_obj), error=str(exc))
        return []


async def persist_dependencies(
    session: AsyncSession,
    project_id: uuid.UUID,
    dependencies: Sequence[DependencyMetadata],
) -> list[Dependency]:
    """Batch persists DependencyMetadata records into PostgreSQL 17.

    Args:
        session: Active asynchronous SQLAlchemy session.
        project_id: Foreign key linking to the parent Project.
        dependencies: Sequence of extracted DependencyMetadata schemas.

    Returns:
        List of created Dependency model instances.
    """
    records: list[Dependency] = []
    for d in dependencies:
        record = Dependency(
            id=uuid.uuid4(),
            project_id=project_id,
            name=d.name,
            version=d.version,
            source_file=d.source_file,
            is_dev=d.is_dev,
        )
        records.append(record)

    session.add_all(records)
    await session.flush()
    logger.info(
        "dependencies_persisted",
        project_id=str(project_id),
        dependency_count=len(records),
    )
    return records


__all__ = [
    "BaseDependencyParser",
    "DependencyMetadata",
    "PythonDependencyParser",
    "NodeDependencyParser",
    "get_dependency_parser",
    "extract_file_dependencies",
    "persist_dependencies",
]
