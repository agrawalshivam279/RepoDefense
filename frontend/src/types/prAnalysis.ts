/**
 * TypeScript data contracts for GitHub Pull Request diff analysis and structured patch data.
 */

export type FileChangeStatus = "added" | "modified" | "deleted" | "renamed" | "binary";

export type DiffLineType = "addition" | "deletion" | "context";

export interface ParsedDiffLine {
  line_type: DiffLineType;
  content: string;
  old_line_number: number | null;
  new_line_number: number | null;
}

export interface ParsedDiffHunk {
  old_start: number;
  old_lines: number;
  new_start: number;
  new_lines: number;
  header: string;
  lines: ParsedDiffLine[];
  added_count: number;
  deleted_count: number;
}

export interface ParsedFileDiff {
  old_path: string | null;
  new_path: string;
  status: FileChangeStatus;
  hunks: ParsedDiffHunk[];
  total_additions: number;
  total_deletions: number;
  is_binary: boolean;
}

export interface PRMetadata {
  pr_number: number;
  title: string;
  body?: string | null;
  author: string;
  base_branch: string;
  head_branch: string;
  head_sha: string;
  state?: string;
  html_url: string;
  created_at: string;
}

export interface PRAnalysisResponse {
  metadata: PRMetadata;
  files: ParsedFileDiff[];
  total_files_changed: number;
  total_additions: number;
  total_deletions: number;
  summary_narrative: string;
}

export interface PRAnalysisRequest {
  pr_url: string;
}

export interface RawDiffParseRequest {
  diff_text: string;
}
