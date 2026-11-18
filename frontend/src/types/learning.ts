import React from "react";

export type ComponentHealthStatus = "healthy" | "degraded" | "unhealthy";

export interface DatabaseModelsHealth {
  status: ComponentHealthStatus;
  user_skills_accessible: boolean;
  candidate_weaknesses_accessible: boolean;
  total_user_skills: number;
  total_candidate_weaknesses: number;
  detail: string | null;
}

export interface BenchmarkProfilesHealth {
  status: ComponentHealthStatus;
  configured_tiers: string[];
  total_categories: number;
  tier_integrity_verified: boolean;
  detail: string | null;
}

export interface MentorServiceHealth {
  status: ComponentHealthStatus;
  fallbacks_ready: boolean;
  supported_fallback_topics: string[];
  detail: string | null;
}

export interface RetestServiceHealth {
  status: ComponentHealthStatus;
  cache_active: boolean;
  cached_question_count: number;
  max_cache_capacity: number;
  detail: string | null;
}

export interface LearningLoopHealthResponse {
  status: ComponentHealthStatus;
  app: string;
  version: string;
  database_models: DatabaseModelsHealth;
  benchmark_profiles: BenchmarkProfilesHealth;
  mentor_service: MentorServiceHealth;
  retest_service: RetestServiceHealth;
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ComponentType<{ className?: string }>;
  isCurrent?: boolean;
}

export type LearningModuleId = "progress" | "skill-gap" | "mentor" | "retest";

export interface LearningModuleItem {
  id: LearningModuleId;
  title: string;
  shortLabel: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  category: "telemetry" | "benchmarking" | "remediation" | "evaluation";
}
