/**
 * TypeScript data contracts for Cross-Mode Performance Analytics Dashboard.
 * Mirrors Pydantic v2 schemas in backend/app/schemas/analytics.py 1:1.
 */

export type DefenseModeKey =
  | "core_defense"
  | "pr_defense"
  | "commit_defense"
  | "stress_test"
  | "incident_simulation"
  | "arch_defense";

export interface ModePerformanceMetric {
  mode: DefenseModeKey;
  label: string;
  sessions_total: number;
  sessions_completed: number;
  avg_score_pct: number | null;
  best_score_pct: number | null;
  pass_rate_pct: number | null;
}

export interface ScoreTrendPoint {
  session_id: string;
  mode: DefenseModeKey;
  label: string;
  score_pct: number;
  timestamp: string;
  topic_or_title: string;
}

export interface CategorySkillMetric {
  category: string;
  confidence_pct: number;
  evaluations_count: number;
}

export interface LanguageDistributionItem {
  language: string;
  file_count: number;
  total_lines: number;
  line_share_pct: number;
}

export interface ModuleCoveragePoint {
  module_path: string;
  coverage_pct: number;
  tested_files: number;
  total_files: number;
}

export interface ProjectAnalyticsResponse {
  project_id: string;
  project_name: string;
  overall_readiness_pct: number | null;
  total_sessions: number;
  completed_sessions: number;
  file_coverage_pct: number | null;
  evidence_coverage_pct: number | null;
  tech_health_score: number | null;
  mode_breakdown: ModePerformanceMetric[];
  category_skills: CategorySkillMetric[];
  score_trend: ScoreTrendPoint[];
  language_distribution: LanguageDistributionItem[];
  module_coverage: ModuleCoveragePoint[];
}

export interface WorkspaceAnalyticsSummary {
  total_projects: number;
  analyzed_projects: number;
  total_sessions: number;
  completed_sessions: number;
  avg_readiness_pct: number | null;
  mode_breakdown: ModePerformanceMetric[];
  recent_trend: ScoreTrendPoint[];
}
