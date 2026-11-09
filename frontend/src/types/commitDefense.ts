/**
 * TypeScript data contracts for Git Commit defense sessions and diff-grounded questions.
 * Mirrors FastAPI backend schemas in app/schemas/commit_defense.py.
 */

import type {
  DefenseQuestionProgress,
  DefenseSessionState,
  DefenseStage,
  DefenseTurn,
  DifficultyLevel,
  QuestionCategory,
  SubmitAnswerRequest,
} from "./defense";
import type { ParsedFileDiff } from "./prAnalysis";
import type { DiffChangeType, DiffGroundedQuestion } from "./prDefense";

export interface CommitMetadata {
  /** Commit SHA (7 to 40 hex chars) */
  commit_hash: string;
  /** Commit author display name */
  author_name: string;
  /** Commit author email address */
  author_email?: string | null;
  /** ISO 8601 commit timestamp */
  committed_at: string;
  /** Commit message subject/summary */
  message: string;
  /** Web URL for the commit on GitHub */
  html_url: string;
  /** Total added lines across this commit */
  total_additions: number;
  /** Total deleted lines across this commit */
  total_deletions: number;
  /** Count of changed files */
  total_files: number;
}

export interface CommitAnalysisResponse {
  /** Metadata and stats for the inspected commit */
  metadata: CommitMetadata;
  /** Parsed diffs per file */
  files: ParsedFileDiff[];
  /** Total count of changed files */
  total_files_changed: number;
  /** Total additions across all files */
  total_additions: number;
  /** Total deletions across all files */
  total_deletions: number;
  /** Concise textual summary of changes */
  summary_narrative: string;
}

export interface CommitGroundedQuestion extends DiffGroundedQuestion {
  /** Commit SHA anchoring this question */
  commit_hash: string;
}

export interface CommitDefenseSessionState extends DefenseSessionState {
  /** Git commit hash (SHA) */
  commit_hash: string;
  /** Commit message subject */
  commit_message: string;
  /** Author of the commit */
  commit_author: string;
  /** GitHub URL for this commit */
  commit_html_url: string;
  /** Serialized narrative summary of commit changes */
  commit_analysis_summary: string;
  /** Ordered list of diff-grounded questions for this commit */
  diff_questions: CommitGroundedQuestion[];
}

export interface StartCommitDefenseRequest {
  /** GitHub commit URL or a 7-40 char commit SHA */
  commit_url_or_hash: string;
  /** Number of diff-grounded defense questions to generate (1-5) */
  num_questions?: number;
}

export type {
  DefenseQuestionProgress,
  DefenseStage,
  DefenseTurn,
  DifficultyLevel,
  ParsedFileDiff,
  QuestionCategory,
  SubmitAnswerRequest,
  DiffChangeType,
};
