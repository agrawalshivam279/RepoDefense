/**
 * TypeScript contracts for Mentor Mode Mini Challenges.
 * Mirrors backend/app/schemas/challenge.py.
 */

export type MiniChallengeDifficulty = "foundational" | "intermediate" | "advanced";

export interface MiniChallengeResponse {
  challenge_id: string;
  category: string;
  topic: string;
  difficulty: MiniChallengeDifficulty;
  title: string;
  scenario: string;
  starter_code?: string | null;
  language: string;
  requirements: string[];
  hints: string[];
  generated_at: string;
}

export interface GenerateChallengeRequest {
  weakness_id?: string;
  topic?: string;
  category?: string;
  difficulty?: MiniChallengeDifficulty;
  language?: string;
  code_context?: string;
  model?: string;
  llm_base_url?: string;
  llm_api_key?: string;
}

export interface SubmitChallengeSolutionRequest {
  challenge_id: string;
  weakness_id?: string;
  category: string;
  topic: string;
  scenario: string;
  requirements: string[];
  candidate_solution: string;
  language?: string;
  model?: string;
  llm_base_url?: string;
  llm_api_key?: string;
}

export interface ChallengeEvaluationResponse {
  evaluation_id: string;
  challenge_id: string;
  passed: boolean;
  score: number;
  strengths: string[];
  missing_elements: string[];
  critique: string;
  model_solution: string;
  weakness_updated: boolean;
  evaluated_at: string;
}

export interface DifficultyBadgeStyle {
  label: string;
  badgeClass: string;
}

export function getDifficultyStyle(difficulty: MiniChallengeDifficulty): DifficultyBadgeStyle {
  switch (difficulty) {
    case "foundational":
      return {
        label: "Foundational",
        badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      };
    case "advanced":
      return {
        label: "Advanced",
        badgeClass: "bg-rose-500/10 text-rose-400 border-rose-500/30",
      };
    case "intermediate":
    default:
      return {
        label: "Intermediate",
        badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
      };
  }
}
