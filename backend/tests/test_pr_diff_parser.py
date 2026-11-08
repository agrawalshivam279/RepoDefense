"""Hermetic unit and integration tests for GitHub PR diff parser engine and REST API."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.analyzers.diff_parser import (
    DiffParsingError,
    _sanitize_path,
    parse_unified_diff,
)
from app.api.v1.pull_requests import (
    analyze_project_pr_endpoint,
    parse_github_pr_url,
    parse_raw_diff_endpoint,
)
from app.models.project import Project, User
from app.schemas.pr_analysis import (
    DiffLineType,
    FileChangeStatus,
    PRAnalysisRequest,
    PRMetadata,
    RawDiffParseRequest,
)

SAMPLE_MODIFIED_DIFF = """diff --git a/backend/app/main.py b/backend/app/main.py
index 1234567..89abcdef 100644
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -10,4 +10,5 @@ def initialize():
     pass
-    old_call()
+    new_call_1()
+    new_call_2()
     return True
"""

SAMPLE_MULTI_FILE_DIFF = """diff --git a/backend/app/new_service.py b/backend/app/new_service.py
new file mode 100644
index 0000000..1122334
--- /dev/null
+++ b/backend/app/new_service.py
@@ -0,0 +1,3 @@
+def new_feature():
+    return "active"
+
diff --git a/backend/app/old_helper.py b/backend/app/old_helper.py
deleted file mode 100644
index 5566778..0000000
--- a/backend/app/old_helper.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def deprecated():
-    pass
diff --git a/assets/logo.png b/assets/logo.png
new file mode 100644
index 0000000..9988776
Binary files /dev/null and b/assets/logo.png differ
"""


def test_parse_github_pr_url():
    """Verify validation and extraction of owner, repo, and PR number from GitHub PR URLs."""
    owner, repo, pr_num = parse_github_pr_url("https://github.com/acme/repodefense/pull/42")
    assert owner == "acme" and repo == "repodefense" and pr_num == 42

    owner2, repo2, pr_num2 = parse_github_pr_url("http://github.com/my-org/my.repo/pull/105/files")
    assert owner2 == "my-org" and repo2 == "my.repo" and pr_num2 == 105

    with pytest.raises(HTTPException) as exc1:
        parse_github_pr_url("https://gitlab.com/acme/repo/pull/1")
    assert exc1.value.status_code == 400

    with pytest.raises(HTTPException) as exc2:
        parse_github_pr_url("https://github.com/acme/repo/issues/42")
    assert exc2.value.status_code == 400


def test_path_sanitization():
    """Verify path traversal prevention on diff header filenames."""
    assert _sanitize_path("a/src/main.py") == "src/main.py"
    assert _sanitize_path("b/docs/README.md") == "docs/README.md"
    assert _sanitize_path("/dev/null") == "/dev/null"

    with pytest.raises(DiffParsingError):
        _sanitize_path("a/../../../etc/passwd")


def test_parse_single_file_modification_diff():
    """Verify parsing unified diff with additions, deletions, context, and 1-indexed lines."""
    files = parse_unified_diff(SAMPLE_MODIFIED_DIFF)
    assert len(files) == 1
    f = files[0]
    assert f.new_path == "backend/app/main.py"
    assert f.old_path == "backend/app/main.py"
    assert f.status == FileChangeStatus.MODIFIED
    assert f.total_additions == 2
    assert f.total_deletions == 1
    assert not f.is_binary

    assert len(f.hunks) == 1
    hunk = f.hunks[0]
    assert hunk.old_start == 10 and hunk.new_start == 10
    assert hunk.added_count == 2 and hunk.deleted_count == 1
    assert hunk.header == "def initialize():"

    types = [line.line_type for line in hunk.lines]
    assert types == [
        DiffLineType.CONTEXT,
        DiffLineType.DELETION,
        DiffLineType.ADDITION,
        DiffLineType.ADDITION,
        DiffLineType.CONTEXT,
    ]

    # Verify line numbers
    del_line = hunk.lines[1]
    assert del_line.old_line_number == 11 and del_line.new_line_number is None
    add_line1 = hunk.lines[2]
    assert add_line1.old_line_number is None and add_line1.new_line_number == 11
    add_line2 = hunk.lines[3]
    assert add_line2.new_line_number == 12


def test_parse_multi_file_and_binary_diff():
    """Verify parsing added, deleted, and binary files in a multi-file diff."""
    files = parse_unified_diff(SAMPLE_MULTI_FILE_DIFF)
    assert len(files) == 3

    added_file = files[0]
    assert added_file.new_path == "backend/app/new_service.py"
    assert added_file.old_path is None
    assert added_file.status == FileChangeStatus.ADDED
    assert added_file.total_additions == 3

    deleted_file = files[1]
    assert deleted_file.new_path == "backend/app/old_helper.py"
    assert deleted_file.status == FileChangeStatus.DELETED
    assert deleted_file.total_deletions == 2

    binary_file = files[2]
    assert binary_file.new_path == "assets/logo.png"
    assert binary_file.status == FileChangeStatus.BINARY
    assert binary_file.is_binary is True


def test_secret_redaction_in_diff():
    """Verify that credentials in changed diff lines are automatically redacted."""
    diff_with_secret = """diff --git a/config.py b/config.py
index 1111111..2222222 100644
--- a/config.py
+++ b/config.py
@@ -1,2 +1,3 @@
 context_line = True
+GH_TOKEN = "ghp_123456789012345678901234567890123456"
"""
    files = parse_unified_diff(diff_with_secret)
    assert len(files) == 1
    added_line = files[0].hunks[0].lines[1]
    assert "[REDACTED_SECRET]" in added_line.content
    assert "ghp_123456" not in added_line.content


def test_empty_diff_returns_empty_list():
    """Verify empty diff strings return empty list gracefully."""
    assert parse_unified_diff("") == []
    assert parse_unified_diff("   \n\n  ") == []


def _drive_coro(coro):
    """Hermetic coroutine runner that avoids socket-bound event loops in sandboxed environments."""
    stack = [coro]
    val = None
    exc = None
    while stack:
        current = stack[-1]
        try:
            if exc is not None:
                to_send = current.throw(exc)
                exc = None
            else:
                to_send = current.send(val)
                val = None
            if hasattr(to_send, "send"):
                stack.append(to_send)
        except StopIteration as stop:
            val = stop.value
            stack.pop()
        except Exception as e:
            exc = e
            stack.pop()
    if exc is not None:
        raise exc
    return val


def test_parse_raw_diff_endpoint_direct():
    """Verify parse_raw_diff_endpoint parses raw patch payload."""
    req = RawDiffParseRequest(diff_text=SAMPLE_MODIFIED_DIFF)
    files = _drive_coro(parse_raw_diff_endpoint(req))
    assert len(files) == 1
    assert files[0].new_path == "backend/app/main.py"
    assert files[0].total_additions == 2
    assert files[0].total_deletions == 1


def test_parse_raw_diff_endpoint_error():
    """Verify parse_raw_diff_endpoint raises 422 on invalid diff with path traversal."""
    req = RawDiffParseRequest(diff_text="diff --git a/../../etc/passwd b/../../etc/passwd\n")
    with pytest.raises(HTTPException) as exc_info:
        _drive_coro(parse_raw_diff_endpoint(req))
    assert exc_info.value.status_code == 422


def test_analyze_project_pr_endpoint_project_not_found():
    """Verify analyze_project_pr_endpoint raises 404 when project does not exist."""
    proj_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = User(id=user_id, email="dev@repodefense.dev")
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    req = PRAnalysisRequest(pr_url="https://github.com/acme/repo/pull/1")
    with pytest.raises(HTTPException) as exc_info:
        _drive_coro(
            analyze_project_pr_endpoint(
                project_id=proj_id,
                payload=req,
                current_user=mock_user,
                db=mock_db,
            )
        )
    assert exc_info.value.status_code == 404
    assert f"Project with ID '{proj_id}' not found" in exc_info.value.detail


def test_analyze_project_pr_endpoint_success():
    """Verify analyze_project_pr_endpoint succeeds and formats metrics with mocked GitHub PR."""
    proj_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = User(id=user_id, email="dev@repodefense.dev")
    mock_project = Project(
        id=proj_id,
        user_id=user_id,
        name="TestRepo",
        github_url="https://github.com/acme/repo",
    )
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_project
    mock_db.execute.return_value = mock_res

    mock_meta = PRMetadata(
        pr_number=12,
        title="Add feature X",
        author="alice",
        base_branch="main",
        head_branch="feat/x",
        head_sha="abcdef123456",
        html_url="https://github.com/acme/repo/pull/12",
        created_at="2026-11-08T00:00:00Z",
    )

    with patch(
        "app.api.v1.pull_requests.fetch_github_pr_data",
        new=AsyncMock(return_value=(mock_meta, SAMPLE_MODIFIED_DIFF)),
    ):
        req = PRAnalysisRequest(pr_url="https://github.com/acme/repo/pull/12")
        resp = _drive_coro(
            analyze_project_pr_endpoint(
                project_id=proj_id,
                payload=req,
                current_user=mock_user,
                db=mock_db,
            )
        )
        assert resp.metadata.pr_number == 12
        assert resp.total_files_changed == 1
        assert resp.total_additions == 2
        assert resp.total_deletions == 1
        assert "Pull Request #12" in resp.summary_narrative
