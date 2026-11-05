/**
 * TypeScript definitions and contracts for interactive defense sessions.
 * Mirrors FastAPI backend schemas in app/schemas/defense.py.
 */

export type DefenseStage =
  | "initializing"
  | "question_active"
  | "evaluating_defense"
  | "pushback_active"
  | "stress_test_active"
  | "mentor_active"
  | "question_completed"
  | "session_completed";

export type DifficultyLevel = "foundational" | "intermediate" | "advanced";

export type TurnRole = "interviewer" | "candidate" | "system";

export type QuestionCategory =
  | "architecture"
  | "scalability"
  | "reliability"
  | "security"
  | "tradeoffs";

export interface DefenseTurn {
  id: string;
  role: TurnRole;
  content: string;
  stage: DefenseStage;
  timestamp: string;
  metadata?: {
    depth_score?: number;
    grounding_verified?: boolean;
    is_vague?: boolean;
    difficulty?: DifficultyLevel | string;
    final_score?: number;
    overall_score?: number;
    feedback?: string;
    question_id?: string;
    category?: string;
    cited_files?: string[];
    [key: string]: unknown;
  };
}

export interface GroundedQuestion {
  id: string;
  category: QuestionCategory;
  question_text: string;
  context_hint: string;
  cited_evidence_ids: string[];
  cited_files: string[];
}

export interface DefenseQuestionProgress {
  question: GroundedQuestion;
  status: DefenseStage;
  difficulty?: DifficultyLevel;
  initial_defense?: string;
  defense_score?: number;
  pushback_prompt?: string;
  pushback_response?: string;
  pushback_count?: number;
  stress_test_prompt?: string;
  stress_test_response?: string;
  mentor_hint?: string;
  retest_question?: string;
  retest_response?: string;
  final_score?: number;
  feedback?: string;
}

export interface DefenseSessionState {
  session_id: string;
  project_id: string;
  status: DefenseStage;
  current_question_index: number;
  current_difficulty?: DifficultyLevel;
  topic_confidence?: Record<string, number>;
  total_questions: number;
  questions: DefenseQuestionProgress[];
  turns: DefenseTurn[];
  overall_score?: number;
  created_at: string;
  updated_at: string;
}

export interface StartDefenseRequest {
  num_questions?: number;
  custom_categories?: string[];
}

export interface SubmitAnswerRequest {
  answer: string;
}
