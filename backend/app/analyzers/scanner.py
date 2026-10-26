import uuid
from pathlib import Path
from typing import Optional, Sequence

import structlog
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.languages import detect_language
from app.models.analysis import AnalyzedFile
from app.security.sanitizer import sanitize_workspace

logger = structlog.get_logger(__name__)


class FileMetadata(BaseModel):
    """Structural metadata and language classification for a scanned source file."""

    path: str = Field(description="POSIX relative path within workspace sandbox")
    language: str = Field(description="Canonical programming language name")
    total_lines: int = Field(ge=0, description="Total line count")
    size_bytes: int = Field(ge=0, description="File size in bytes")


def count_file_lines(file_path: Path) -> int:
    """Safely counts the total number of lines in a text file.

    Uses UTF-8 decoding with character replacement to ensure resilience against
    unexpected or corrupted byte sequences.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            count = 0
            for _ in f:
                count += 1
            return count
    except Exception as exc:
        logger.warning("file_line_count_failed", path=str(file_path), error=str(exc))
        return 0


def extract_file_metadata(file_path: Path, base_dir: Path) -> FileMetadata:
    """Extracts structural metadata, line count, and language classification for a file.

    Args:
        file_path: Absolute or relative Path pointing to the target file.
        base_dir: Workspace root directory against which relative paths are formed.

    Returns:
        Populated FileMetadata schema instance.
    """
    abs_file = file_path.resolve()
    abs_base = base_dir.resolve()
    rel_posix_path = abs_file.relative_to(abs_base).as_posix()

    size_bytes = abs_file.stat().st_size
    language = detect_language(abs_file)
    total_lines = count_file_lines(abs_file)

    return FileMetadata(
        path=rel_posix_path,
        language=language,
        total_lines=total_lines,
        size_bytes=size_bytes,
    )


def scan_workspace_files(
    base_dir: Path,
    file_paths: Optional[Sequence[Path]] = None,
) -> list[FileMetadata]:
    """Scans and extracts metadata for all sanitized files in a workspace directory.

    Args:
        base_dir: Root temporary repository directory.
        file_paths: Optional pre-filtered list of files. If None, runs sanitize_workspace().

    Returns:
        List of FileMetadata records sorted deterministically by relative path.
    """
    abs_base = base_dir.resolve()

    if file_paths is None:
        sanitization = sanitize_workspace(abs_base)
        target_paths = [abs_base / p for p in sanitization.valid_files]
    else:
        target_paths = [
            p.resolve() if p.is_absolute() else (abs_base / p).resolve()
            for p in file_paths
        ]

    results: list[FileMetadata] = []
    for p in target_paths:
        if p.is_file():
            meta = extract_file_metadata(p, abs_base)
            results.append(meta)

    # Sort deterministically by relative path
    results.sort(key=lambda m: m.path)
    logger.info("workspace_scan_completed", total_scanned=len(results), workspace=str(abs_base))
    return results


async def persist_analyzed_files(
    session: AsyncSession,
    snapshot_id: uuid.UUID,
    files_meta: Sequence[FileMetadata],
) -> list[AnalyzedFile]:
    """Persists a batch of FileMetadata records as AnalyzedFile rows in PostgreSQL.

    Args:
        session: Active asynchronous SQLAlchemy session.
        snapshot_id: UUID of the parent RepositorySnapshot.
        files_meta: Sequence of FileMetadata extracted from workspace.

    Returns:
        List of persisted AnalyzedFile SQLAlchemy models.
    """
    analyzed_records: list[AnalyzedFile] = []
    for meta in files_meta:
        record = AnalyzedFile(
            id=uuid.uuid4(),
            snapshot_id=snapshot_id,
            path=meta.path,
            language=meta.language,
            total_lines=meta.total_lines,
            size_bytes=meta.size_bytes,
        )
        analyzed_records.append(record)

    session.add_all(analyzed_records)
    await session.flush()
    logger.info(
        "analyzed_files_persisted",
        snapshot_id=str(snapshot_id),
        file_count=len(analyzed_records),
    )
    return analyzed_records
