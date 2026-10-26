"""Security and Untrusted Input Sanitization Package for RepoDefense."""

from app.security.sanitizer import (
    ALLOWED_EXTENSIONS,
    BINARY_EXTENSIONS,
    IGNORED_DIRS,
    MAX_FILE_COUNT,
    MAX_FILE_SIZE_BYTES,
    MAX_REPO_SIZE_BYTES,
    SanitizationSummary,
    SecurityLimitExceededError,
    is_binary_content,
    sanitize_workspace,
)
from app.security.secrets import SecretMatch, redact_secrets, scan_for_secrets
from app.security.traversal import PathTraversalError, validate_safe_path

__all__ = [
    "ALLOWED_EXTENSIONS",
    "BINARY_EXTENSIONS",
    "IGNORED_DIRS",
    "MAX_FILE_COUNT",
    "MAX_FILE_SIZE_BYTES",
    "MAX_REPO_SIZE_BYTES",
    "PathTraversalError",
    "SanitizationSummary",
    "SecurityLimitExceededError",
    "SecretMatch",
    "is_binary_content",
    "redact_secrets",
    "sanitize_workspace",
    "scan_for_secrets",
    "validate_safe_path",
]
