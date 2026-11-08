"""Deterministic unified diff parser engine extracting structured hunks, lines, and metrics."""

import re
from typing import List, Optional, Tuple

from app.schemas.pr_analysis import (
    DiffLineType,
    FileChangeStatus,
    ParsedDiffHunk,
    ParsedDiffLine,
    ParsedFileDiff,
)
from app.security.secrets import redact_secrets

MAX_DIFF_BYTES = 10_000_000  # 10MB max diff payload
MAX_DIFF_LINES = 50_000      # 50k lines ceiling to prevent ReDoS / memory exhaustion

# Matches hunk header: @@ -old_start,old_count +new_start,new_count @@
HUNK_HEADER_RE = re.compile(
    r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(?:[ ]?(.*))?$"
)

# Matches diff header: diff --git a/path b/path
DIFF_HEADER_RE = re.compile(r"^diff\s+--git\s+(?:a/(.+?))\s+(?:b/(.+?))$")


class DiffParsingError(ValueError):
    """Raised when unified diff payload is corrupt, malformed, or exceeds safety quotas."""


def _sanitize_path(raw_path: str) -> str:
    """Sanitizes file paths extracted from diff headers to prevent traversal attacks."""
    clean = raw_path.strip().replace("\\", "/")
    if clean.startswith("a/") or clean.startswith("b/"):
        clean = clean[2:]
    if clean.startswith("/dev/null"):
        return "/dev/null"
    # Prevent traversal escape
    parts = clean.split("/")
    if any(p == ".." or p.startswith("~") for p in parts):
        raise DiffParsingError(f"Path traversal sequence detected in diff path: {raw_path}")
    return clean.lstrip("/")


def _parse_hunk_header(header_line: str) -> Tuple[int, int, int, int, str]:
    """Extracts starting coordinates and length spans from a hunk header line."""
    match = HUNK_HEADER_RE.match(header_line.strip())
    if not match:
        raise DiffParsingError(f"Malformed diff hunk header: {header_line}")
    old_start = int(match.group(1))
    old_lines = int(match.group(2)) if match.group(2) is not None else 1
    new_start = int(match.group(3))
    new_lines = int(match.group(4)) if match.group(4) is not None else 1
    context_heading = (match.group(5) or "").strip()
    return old_start, old_lines, new_start, new_lines, context_heading


def parse_unified_diff(diff_text: str) -> List[ParsedFileDiff]:
    """Parses a complete unified diff text stream into structured file diff records.

    Enforces payload size limits, path sanitization, 1-indexed line tracking,
    and secret redaction across all parsed source lines.
    """
    if not diff_text or not diff_text.strip():
        return []

    if len(diff_text.encode("utf-8")) > MAX_DIFF_BYTES:
        raise DiffParsingError(f"Diff exceeds maximum payload size of {MAX_DIFF_BYTES} bytes.")

    lines = diff_text.splitlines()
    if len(lines) > MAX_DIFF_LINES:
        raise DiffParsingError(f"Diff exceeds maximum line count of {MAX_DIFF_LINES} lines.")

    file_diffs: List[ParsedFileDiff] = []
    current_file: Optional[ParsedFileDiff] = None
    current_hunk: Optional[ParsedDiffHunk] = None
    old_cursor = 0
    new_cursor = 0

    idx = 0
    num_lines = len(lines)

    while idx < num_lines:
        line = lines[idx]

        # 1. New file diff header
        diff_match = DIFF_HEADER_RE.match(line)
        if diff_match:
            if current_hunk and current_file:
                current_file.hunks.append(current_hunk)
                current_hunk = None
            if current_file:
                file_diffs.append(current_file)

            raw_old = diff_match.group(1)
            raw_new = diff_match.group(2)
            clean_old = _sanitize_path(raw_old)
            clean_new = _sanitize_path(raw_new)

            current_file = ParsedFileDiff(
                old_path=clean_old if clean_old != "/dev/null" else None,
                new_path=clean_new if clean_new != "/dev/null" else clean_old,
                status=FileChangeStatus.MODIFIED,
                hunks=[],
                total_additions=0,
                total_deletions=0,
                is_binary=False,
            )
            idx += 1
            continue

        if current_file is None:
            # Skip noise before first diff --git
            idx += 1
            continue

        # 2. Check file mode and rename metadata
        if line.startswith("new file mode") or line.startswith("--- /dev/null"):
            current_file.status = FileChangeStatus.ADDED
            current_file.old_path = None
        elif line.startswith("deleted file mode") or line.startswith("+++ /dev/null"):
            current_file.status = FileChangeStatus.DELETED
        elif line.startswith("similarity index"):
            current_file.status = FileChangeStatus.RENAMED
        elif line.startswith("rename from"):
            current_file.old_path = _sanitize_path(line[11:])
            current_file.status = FileChangeStatus.RENAMED
        elif line.startswith("rename to"):
            current_file.new_path = _sanitize_path(line[9:])
            current_file.status = FileChangeStatus.RENAMED
        elif line.startswith("Binary files ") or "differ" in line:
            current_file.is_binary = True
            current_file.status = FileChangeStatus.BINARY

        # 3. New Hunk Header
        elif line.startswith("@@ "):
            if current_hunk:
                current_file.hunks.append(current_hunk)

            old_start, old_lines_count, new_start, new_lines_count, heading = (
                _parse_hunk_header(line)
            )
            current_hunk = ParsedDiffHunk(
                old_start=old_start,
                old_lines=old_lines_count,
                new_start=new_start,
                new_lines=new_lines_count,
                header=heading,
                lines=[],
                added_count=0,
                deleted_count=0,
            )
            old_cursor = old_start
            new_cursor = new_start

        # 4. Hunk lines
        elif current_hunk is not None:
            if line.startswith("+"):
                redacted = redact_secrets(line[1:])
                current_hunk.lines.append(
                    ParsedDiffLine(
                        line_type=DiffLineType.ADDITION,
                        content=redacted,
                        old_line_number=None,
                        new_line_number=new_cursor,
                    )
                )
                current_hunk.added_count += 1
                current_file.total_additions += 1
                new_cursor += 1
            elif line.startswith("-"):
                redacted = redact_secrets(line[1:])
                current_hunk.lines.append(
                    ParsedDiffLine(
                        line_type=DiffLineType.DELETION,
                        content=redacted,
                        old_line_number=old_cursor,
                        new_line_number=None,
                    )
                )
                current_hunk.deleted_count += 1
                current_file.total_deletions += 1
                old_cursor += 1
            elif line.startswith(" ") or line == "":
                content = line[1:] if line.startswith(" ") else ""
                redacted = redact_secrets(content)
                current_hunk.lines.append(
                    ParsedDiffLine(
                        line_type=DiffLineType.CONTEXT,
                        content=redacted,
                        old_line_number=old_cursor,
                        new_line_number=new_cursor,
                    )
                )
                old_cursor += 1
                new_cursor += 1
            elif line.startswith("\\ No newline at end of file"):
                pass  # Ignore newline annotations

        idx += 1

    # Flush last hunk and file
    if current_hunk and current_file:
        current_file.hunks.append(current_hunk)
    if current_file:
        file_diffs.append(current_file)

    return file_diffs
