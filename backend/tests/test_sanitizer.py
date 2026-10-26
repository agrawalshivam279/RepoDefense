import os
from pathlib import Path

import pytest

from app.security.sanitizer import (
    SecurityLimitExceededError,
    is_binary_content,
    sanitize_workspace,
)
from app.security.secrets import redact_secrets, scan_for_secrets
from app.security.traversal import PathTraversalError, validate_safe_path


def test_path_traversal_detection(tmp_path: Path):
    """Verify that path traversal attempts outside workspace raise PathTraversalError."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    inside_file = workspace / "sub" / "file.py"
    inside_file.parent.mkdir()
    inside_file.write_text("print('safe')", encoding="utf-8")

    # 1. Valid path inside workspace
    safe_path = validate_safe_path(workspace, inside_file)
    assert safe_path == inside_file.resolve()

    # 2. Escaping parent directory via relative traversal
    escape_path = workspace / ".." / "outside.txt"
    with pytest.raises(PathTraversalError):
        validate_safe_path(workspace, escape_path)

    # 3. Outbound symlink pointing outside sandbox (if symlinks supported on platform)
    outside_target = tmp_path / "outside_target.txt"
    outside_target.write_text("classified", encoding="utf-8")
    symlink_path = workspace / "outbound_link"

    try:
        os.symlink(outside_target, symlink_path)
        with pytest.raises(PathTraversalError):
            validate_safe_path(workspace, symlink_path)
    except (OSError, NotImplementedError):
        # On Windows without developer mode/admin rights, symlink creation may require privilege
        pass


def test_secret_detection_and_redaction():
    """Verify that credentials, tokens, and private keys are detected and redacted."""
    sample_code = """
    # AWS Config
    AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
    # GitHub Token
    GH_TOKEN = "ghp_123456789012345678901234567890123456"
    # Custom API Key
    api_key = "my_super_secret_auth_token_987654321"
    # Authorization header
    headers = {"Authorization": "Bearer abcdefghijklmnopqrstuvwxyz123456"}
    # Private Key
    -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEA0Y123456789abcdef...
    -----END RSA PRIVATE KEY-----
    """

    matches = scan_for_secrets(sample_code)
    assert len(matches) >= 4

    rule_names = {m.rule_name for m in matches}
    assert "AWS Access Key ID" in rule_names
    assert "GitHub Token" in rule_names
    assert "Explicit Key Assignment" in rule_names
    assert "Private Key Block" in rule_names

    redacted = redact_secrets(sample_code)
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "ghp_123456789012345678901234567890123456" not in redacted
    assert "my_super_secret_auth_token_987654321" not in redacted
    assert "MIIEowIBAAKCAQEA0Y123456789abcdef" not in redacted
    assert "[REDACTED_SECRET]" in redacted
    assert 'api_key = "[REDACTED_SECRET]"' in redacted


def test_binary_exclusion(tmp_path: Path):
    """Verify detection of binary file extensions and null-byte content."""
    # 1. Plain source code
    text_file = tmp_path / "test.py"
    text_file.write_text("def hello(): return 'world'", encoding="utf-8")
    assert not is_binary_content(text_file)

    # 2. File with binary extension
    bin_ext_file = tmp_path / "artifact.dll"
    bin_ext_file.write_bytes(b"MZ\x90\x00")
    assert is_binary_content(bin_ext_file)

    # 3. Source extension with disguised null bytes
    disguised_file = tmp_path / "malicious.js"
    disguised_file.write_bytes(b"const x = 1;\x00\x01\x02")
    assert is_binary_content(disguised_file)


def test_sanitize_workspace_directory_filtering(tmp_path: Path):
    """Verify that ignored directories, binaries, and invalid extensions are skipped."""
    workspace = tmp_path / "repo"
    workspace.mkdir()

    # Valid source files
    (workspace / "src").mkdir()
    (workspace / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (workspace / "src" / "types.ts").write_text("export type ID = string;", encoding="utf-8")
    (workspace / "README.md").write_text("# Documentation", encoding="utf-8")

    # Ignored vendor / build directories
    (workspace / "node_modules" / "pkg").mkdir(parents=True)
    (workspace / "node_modules" / "pkg" / "index.js").write_text("module.exports = {};")

    (workspace / ".git" / "hooks").mkdir(parents=True)
    (workspace / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh")

    (workspace / "venv" / "lib").mkdir(parents=True)
    (workspace / "venv" / "lib" / "site.py").write_text("# venv file")

    # Binary file
    (workspace / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")

    # Disallowed extension
    (workspace / "binary_backup.xyz").write_text("random payload")

    summary = sanitize_workspace(workspace)

    valid_paths_str = [p.as_posix() for p in summary.valid_files]
    assert "src/main.py" in valid_paths_str
    assert "src/types.ts" in valid_paths_str
    assert "README.md" in valid_paths_str

    # Ignored directories should NOT be in valid_files
    for path in valid_paths_str:
        assert not path.startswith("node_modules")
        assert not path.startswith(".git")
        assert not path.startswith("venv")

    assert summary.valid_file_count == 3
    assert summary.skipped_binaries == 1
    assert summary.skipped_disallowed_exts == 1


def test_sanitize_workspace_quotas(tmp_path: Path):
    """Verify enforcement of file count and cumulative size limit circuit-breakers."""
    workspace = tmp_path / "quota_repo"
    workspace.mkdir()

    # 1. File count limit test
    for i in range(10):
        (workspace / f"file_{i}.py").write_text(f"x = {i}\n", encoding="utf-8")

    with pytest.raises(SecurityLimitExceededError, match="file count limit"):
        sanitize_workspace(workspace, max_files=5)

    # 2. Total size limit test
    large_workspace = tmp_path / "size_repo"
    large_workspace.mkdir()
    (large_workspace / "payload.py").write_text("A" * 500, encoding="utf-8")

    with pytest.raises(SecurityLimitExceededError, match="cumulative size exceeds limit"):
        sanitize_workspace(large_workspace, max_size_bytes=200)
