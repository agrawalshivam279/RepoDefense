from pathlib import Path


class PathTraversalError(ValueError):
    """Raised when a file path attempts to escape the root sandbox directory."""


def validate_safe_path(base_dir: Path, target_path: Path) -> Path:
    """Validates that target_path strictly resolves within the base_dir sandbox.

    Protects against directory traversal attacks (e.g., '../../etc/passwd')
    and malicious symbolic links pointing outside the sandbox boundary.

    Args:
        base_dir: The root directory of the temporary workspace.
        target_path: The untrusted candidate file or directory path.

    Returns:
        The canonical, fully resolved Path within base_dir.

    Raises:
        PathTraversalError: If target_path resolves outside base_dir.
    """
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve()

    if not resolved_target.is_relative_to(resolved_base):
        raise PathTraversalError(
            f"Path traversal detected: '{target_path}' resolves outside sandbox '{base_dir}'"
        )

    return resolved_target
