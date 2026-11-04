/**
 * TypeScript definitions and contracts for defense interview evaluation reports.
 * Mirrors FastAPI backend schemas in app/schemas/report.py.
 */

import type { QuestionCategory } from "./defense";

export type CategoryEvaluationStatus = "passed" | "needs_work" | "remediated";

export interface CategoryScore {
  category: QuestionCategory;
  score: number;
  questions_count: number;
  status: CategoryEvaluationStatus | string;
  summary: string;
}

export interface DefenseReportResponse {
  session_id: string;
  project_id: string;
  overall_score: number;
  verdict: string;
  summary: string;
  category_scores: CategoryScore[];
  key_strengths: string[];
  critical_blind_spots: string[];
  actionable_recommendations: string[];
  total_questions: number;
  completed_at: string;
}
