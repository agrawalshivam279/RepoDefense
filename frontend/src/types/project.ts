export interface Project {
  id: string;
  user_id: string;
  name: string;
  github_url: string;
  default_branch: string;
  status: "pending" | "cloning" | "cloned" | "analyzing" | "analyzed" | "failed";
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  github_url: string;
  name?: string;
  default_branch?: string;
}

export interface DependencyOverviewItem {
  name: string;
  version?: string | null;
  source_file: string;
  is_dev: boolean;
}

export interface LanguageMetric {
  language: string;
  file_count: number;
  total_lines: number;
}

export interface RepositoryOverviewMetrics {
  total_files: number;
  total_lines: number;
  languages: LanguageMetric[];
  dependency_count: number;
  evidence_count: number;
}

export interface ProjectSummary {
  title: string;
  tagline: string;
  primary_language: string;
  detected_frameworks: string[];
  architectural_style: string;
  key_components: string[];
  potential_defense_topics: string[];
  narrative: string;
}

export interface ProjectOverviewResponse {
  project_id: string;
  name: string;
  github_url: string;
  default_branch: string;
  status: string;
  created_at: string;
  updated_at: string;
  commit_hash?: string | null;
  summary?: ProjectSummary | null;
  metrics: RepositoryOverviewMetrics;
  dependencies: DependencyOverviewItem[];
}
