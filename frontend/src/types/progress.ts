/**
 * Candidate skill progress, velocity, and improvement telemetry types.
 * Matches backend schemas from backend/app/schemas/progress.py.
 */

export interface ProficiencyTrendPoint {
  date: string; // YYYY-MM-DD
  average_proficiency: number; // 0.0 - 100.0
  evaluations_count: number;
  passed_count: number;
}

export interface WeaknessVelocityMetric {
  total_identified: number;
  total_resolved: number;
  resolution_rate_pct: number;
  critical_resolved: number;
  critical_total: number;
  major_resolved: number;
  major_total: number;
  minor_resolved: number;
  minor_total: number;
  average_resolution_hours: number | null;
}

export type MasteryStatus = "mastered" | "proficient" | "improving" | "needs_focus";

export interface CategoryProgressDelta {
  category: string;
  current_proficiency: number;
  total_evaluations: number;
  passed_evaluations: number;
  pass_rate_pct: number;
  total_weaknesses: number;
  resolved_weaknesses: number;
  status: MasteryStatus | string;
}

export interface TopicMasteryItem {
  topic: string;
  category: string;
  proficiency_score: number;
  evaluations: number;
  pass_rate_pct: number;
  last_evaluated_at?: string | null;
}

export interface UserProgressOverviewResponse {
  overall_proficiency: number;
  total_evaluations: number;
  total_passed: number;
  overall_pass_rate_pct: number;
  active_skills_count: number;
  mastered_skills_count: number;
  learning_streak_days: number;
  weakness_velocity: WeaknessVelocityMetric;
  category_deltas: CategoryProgressDelta[];
  recent_timeline: ProficiencyTrendPoint[];
  top_improved_topics: TopicMasteryItem[];
  needs_focus_topics: TopicMasteryItem[];
}
