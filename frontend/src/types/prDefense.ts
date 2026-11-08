/**
 * TypeScript data contracts for Pull Request defense sessions and diff-grounded questions.
 * Mirrors FastAPI backend schemas in app/schemas/pr_defense.py.
 */

import type {
  DefenseQuestionProgress,
  DefenseSessionState,
  DefenseStage,
  DefenseTurn,
  DifficultyLevel,
  GroundedQuestion,
  QuestionCategory,
  SubmitAnswerRequest,
} from "./defense";

export type DiffChangeType = "addition" | "deletion" | "modification";

export interface DiffGroundedQuestion extends GroundedQuestion {
  /** Repository-relative path of the file changed in this PR */
  diff_file_path: string;
  /** Unified diff hunk header identifying the changed region (@@ -old +new @@) */
  diff_hunk_header: string;
  /** Nature of the change: 'addition', 'deletion', or 'modification' */
  change_type: DiffChangeType | string;
  /** Actual diff lines ('+' additions or '-' deletions) quoted as evidence */
  cited_lines: string[];
}

export interface PRDefenseSessionState extends DefenseSessionState {
  /** GitHub Pull Request number */
  pr_number: number;
  /** Title of the Pull Request */
  pr_title: string;
  /** GitHub web URL for the Pull Request */
  pr_html_url: string;
  /** GitHub login of the PR author */
  pr_author: string;
  /** Serialized narrative summary of the PR diff */
  pr_analysis_summary: string;
  /** Ordered list of diff-grounded defense questions */
  diff_questions: DiffGroundedQuestion[];
}

export interface StartPRDefenseRequest {
  /** Public GitHub Pull Request URL */
  pr_url: string;
  /** Number of diff-grounded defense questions to generate (1-5) */
  num_questions?: number;
}

export type {
  DefenseQuestionProgress,
  DefenseStage,
  DefenseTurn,
  DifficultyLevel,
  QuestionCategory,
  SubmitAnswerRequest,
};
