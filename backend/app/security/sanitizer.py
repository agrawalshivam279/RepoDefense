import os
from pathlib import Path

from pydantic import BaseModel, Field

from app.security.traversal import validate_safe_path

# Security Limits
MAX_REPO_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB hard limit
MAX_FILE_COUNT: int = 10_000                  # 10,000 files limit
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024   # 10 MB single file cap

IGNORED_DIRS: set[str] = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "target",
    "vendor",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

BINARY_EXTENSIONS: set[str] = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".iso",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".mp4",
    ".mp3",
    ".wav",
    ".pdf",
    ".pyc",
    ".pyo",
    ".pyd",
    ".wasm",
    ".class",
    ".jar",
}

ALLOWED_EXTENSIONS: set[str] = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".go",
    ".java",
    ".rs",
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".sql",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".txt",
    ".sh",
    ".bash",
    ".zsh",
    ".dockerignore",
    ".env.example",
    ".gitignore",
}

ALLOWED_FILENAMES: set[str] = {
    "dockerfile",
    "makefile",
    "gemfile",
    "procfile",
    "license",
    "readme",
}


class SecurityLimitExceededError(ValueError):
    """Raised when repository size or file count violates safety quotas."""


class SanitizationSummary(BaseModel):
    """Metrics and file manifests resulting from repository sanitization."""

    valid_files: list[Path] = Field(
        description="List of sanitized relative file paths safe for AST analysis"
    )
    total_files_scanned: int = Field(description="Total files encountered in workspace")
    valid_file_count: int = Field(description="Number of accepted source files")
    total_bytes: int = Field(description="Cumulative byte size of accepted files")
    skipped_binaries: int = Field(description="Number of binary files excluded")
    skipped_disallowed_exts: int = Field(description="Files skipped due to extension filter")


def is_binary_content(file_path: Path) -> bool:
    """Detects whether a file contains binary content rather than source text."""
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            # Null byte check (standard git/linux heuristic for binary data)
            if b"\x00" in chunk:
                return True
            # Attempt UTF-8 decoding on the probed chunk
            chunk.decode("utf-8")
            return False
    except (UnicodeDecodeError, OSError):
        return True


def sanitize_workspace(
    workspace_dir: Path,
    max_size_bytes: int = MAX_REPO_SIZE_BYTES,
    max_files: int = MAX_FILE_COUNT,
) -> SanitizationSummary:
    """Recursively walks a repository workspace, applying strict security boundaries.

    Enforces path traversal defenses, ignores vendor/build noise, skips binaries,
    and terminates if resource limits (size or file count) are breached.

    Args:
        workspace_dir: Root directory of the repository workspace.
        max_size_bytes: Maximum allowed cumulative byte size across all files.
        max_files: Maximum allowed number of files in the workspace.

    Returns:
        SanitizationSummary detailing accepted files and skipped items.

    Raises:
        SecurityLimitExceededError: If file count or repository size exceeds thresholds.
        PathTraversalError: If any path escapes the workspace root boundary.
    """
    resolved_root = validate_safe_path(workspace_dir, workspace_dir)

    valid_files: list[Path] = []
    total_files_scanned = 0
    total_bytes = 0
    skipped_binaries = 0
    skipped_disallowed = 0

    for root, dirs, files in os.walk(resolved_root, followlinks=False):
        # Exclude ignored directories in-place to avoid descending into vendor noise
        dirs[:] = [
            d for d in dirs
            if d not in IGNORED_DIRS and not d.startswith(".git")
        ]

        current_dir_path = Path(root)
        validate_safe_path(resolved_root, current_dir_path)

        for filename in files:
            total_files_scanned += 1
            if total_files_scanned > max_files:
                raise SecurityLimitExceededError(
                    f"Repository exceeds maximum file count limit ({max_files:,} files)"
                )

            file_path = current_dir_path / filename
            safe_file = validate_safe_path(resolved_root, file_path)

            try:
                stat = safe_file.stat()
                file_size = stat.st_size
            except OSError:
                continue

            # Skip individual files that exceed single-file cap
            if file_size > MAX_FILE_SIZE_BYTES:
                skipped_disallowed += 1
                continue

            total_bytes += file_size
            if total_bytes > max_size_bytes:
                limit_mb = max_size_bytes // (1024 * 1024)
                raise SecurityLimitExceededError(
                    f"Repository cumulative size exceeds limit ({limit_mb} MB)"
                )

            # 1. Binary inspection (extension and null byte content)
            if is_binary_content(safe_file):
                skipped_binaries += 1
                continue

            # 2. Extension and filename validation
            lower_ext = safe_file.suffix.lower()
            lower_name = safe_file.name.lower()

            if lower_ext not in ALLOWED_EXTENSIONS and lower_name not in ALLOWED_FILENAMES:
                skipped_disallowed += 1
                continue

            # Store path relative to workspace root
            valid_files.append(safe_file.relative_to(resolved_root))

    return SanitizationSummary(
        valid_files=valid_files,
        total_files_scanned=total_files_scanned,
        valid_file_count=len(valid_files),
        total_bytes=total_bytes,
        skipped_binaries=skipped_binaries,
        skipped_disallowed_exts=skipped_disallowed,
    )
