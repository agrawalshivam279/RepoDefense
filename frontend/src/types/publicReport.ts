export interface PublicCategoryScore {
  category: string;
  score: number;
  questions_count: number;
  status: string;
  summary: string;
}

export interface PublicDefenseReport {
  verification_id: string;
  project_name: string;
  github_url: string;
  commit_hash: string;
  overall_score: number;
  verdict: string;
  certification_tier: string;
  summary: string;
  category_scores: PublicCategoryScore[];
  key_strengths: string[];
  critical_blind_spots: string[];
  architecture_primary_pattern: string | null;
  tech_health_score: number | null;
  total_questions: number;
  completed_at: string;
  verified_at: string;
  issuer: string;
}

export interface PublicShareTokenResponse {
  session_id: string;
  project_id: string;
  share_token: string;
  share_url: string;
  badge_url: string;
  markdown_badge: string;
  html_badge: string;
  is_active: boolean;
  created_at: string;
  expires_at: string | null;
}

export interface CreateShareTokenPayload {
  is_active?: boolean;
  expires_in_days?: number | null;
}
