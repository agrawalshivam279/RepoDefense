/**
 * REST API client for Cross-Mode Performance Analytics.
 * Connects to /api/v1/analytics with runtime unknown-narrowing validation.
 */

import type {
  CategorySkillMetric,
  DefenseModeKey,
  LanguageDistributionItem,
  ModePerformanceMetric,
  ModuleCoveragePoint,
  ProjectAnalyticsResponse,
  ScoreTrendPoint,
  WorkspaceAnalyticsSummary,
} from "@/types/analytics";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const VALID_DEFENSE_MODES: ReadonlySet<string> = new Set<DefenseModeKey>([
  "core_defense",
  "pr_defense",
  "commit_defense",
  "stress_test",
  "incident_simulation",
  "arch_defense",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isNullableFiniteNumber(value: unknown): value is number | null {
  return value === null || isFiniteNumber(value);
}

function isNonNegInt(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function isModeMetric(value: unknown): value is ModePerformanceMetric {
  return (
    isRecord(value) &&
    typeof value.mode === "string" &&
    VALID_DEFENSE_MODES.has(value.mode) &&
    typeof value.label === "string" &&
    isNonNegInt(value.sessions_total) &&
    isNonNegInt(value.sessions_completed) &&
    isNullableFiniteNumber(value.avg_score_pct) &&
    isNullableFiniteNumber(value.best_score_pct) &&
    isNullableFiniteNumber(value.pass_rate_pct)
  );
}

function isTrendPoint(value: unknown): value is ScoreTrendPoint {
  return (
    isRecord(value) &&
    typeof value.session_id === "string" &&
    typeof value.mode === "string" &&
    VALID_DEFENSE_MODES.has(value.mode) &&
    typeof value.label === "string" &&
    isFiniteNumber(value.score_pct) &&
    typeof value.timestamp === "string" &&
    typeof value.topic_or_title === "string"
  );
}

function isCategorySkill(value: unknown): value is CategorySkillMetric {
  return (
    isRecord(value) &&
    typeof value.category === "string" &&
    isFiniteNumber(value.confidence_pct) &&
    isNonNegInt(value.evaluations_count)
  );
}

function isLanguageItem(value: unknown): value is LanguageDistributionItem {
  return (
    isRecord(value) &&
    typeof value.language === "string" &&
    isNonNegInt(value.file_count) &&
    isNonNegInt(value.total_lines) &&
    isFiniteNumber(value.line_share_pct)
  );
}

function isModuleCoverage(value: unknown): value is ModuleCoveragePoint {
  return (
    isRecord(value) &&
    typeof value.module_path === "string" &&
    isFiniteNumber(value.coverage_pct) &&
    isNonNegInt(value.tested_files) &&
    isNonNegInt(value.total_files)
  );
}

export function validateProjectAnalyticsResponse(payload: unknown): ProjectAnalyticsResponse {
  if (!isRecord(payload)) {
    throw new Error("Invalid project analytics payload: expected object.");
  }
  const valid =
    typeof payload.project_id === "string" &&
    typeof payload.project_name === "string" &&
    isNullableFiniteNumber(payload.overall_readiness_pct) &&
    isNonNegInt(payload.total_sessions) &&
    isNonNegInt(payload.completed_sessions) &&
    isNullableFiniteNumber(payload.file_coverage_pct) &&
    isNullableFiniteNumber(payload.evidence_coverage_pct) &&
    isNullableFiniteNumber(payload.tech_health_score) &&
    Array.isArray(payload.mode_breakdown) &&
    payload.mode_breakdown.every(isModeMetric) &&
    Array.isArray(payload.category_skills) &&
    payload.category_skills.every(isCategorySkill) &&
    Array.isArray(payload.score_trend) &&
    payload.score_trend.every(isTrendPoint) &&
    Array.isArray(payload.language_distribution) &&
    payload.language_distribution.every(isLanguageItem) &&
    Array.isArray(payload.module_coverage) &&
    payload.module_coverage.every(isModuleCoverage);

  if (!valid) {
    throw new Error("Project analytics response failed runtime schema validation.");
  }
  return payload as unknown as ProjectAnalyticsResponse;
}

export function validateWorkspaceAnalyticsSummary(payload: unknown): WorkspaceAnalyticsSummary {
  if (!isRecord(payload)) {
    throw new Error("Invalid workspace analytics payload: expected object.");
  }
  const valid =
    isNonNegInt(payload.total_projects) &&
    isNonNegInt(payload.analyzed_projects) &&
    isNonNegInt(payload.total_sessions) &&
    isNonNegInt(payload.completed_sessions) &&
    isNullableFiniteNumber(payload.avg_readiness_pct) &&
    Array.isArray(payload.mode_breakdown) &&
    payload.mode_breakdown.every(isModeMetric) &&
    Array.isArray(payload.recent_trend) &&
    payload.recent_trend.every(isTrendPoint);

  if (!valid) {
    throw new Error("Workspace analytics summary failed runtime schema validation.");
  }
  return payload as unknown as WorkspaceAnalyticsSummary;
}

function extractApiErrorDetail(body: unknown, status: number): string {
  if (isRecord(body)) {
    if (typeof body.detail === "string" && body.detail.trim()) {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const first = body.detail[0];
      if (isRecord(first) && typeof first.msg === "string") {
        return first.msg;
      }
    }
  }
  return `Analytics API request failed with HTTP ${status}`;
}

async function requestAnalyticsApi<T>(
  path: string,
  token: string,
  validator: (data: unknown) => T,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
    signal,
  });

  let parsedBody: unknown = null;
  try {
    parsedBody = await response.json();
  } catch {
    if (!response.ok) {
      throw new Error(`Analytics API request failed with HTTP ${response.status}`);
    }
    throw new Error("Analytics API returned non-JSON response.");
  }

  if (!response.ok) {
    throw new Error(extractApiErrorDetail(parsedBody, response.status));
  }
  return validator(parsedBody);
}

export async function getProjectAnalytics(
  projectId: string,
  token: string,
  signal?: AbortSignal,
): Promise<ProjectAnalyticsResponse> {
  const safeId = encodeURIComponent(projectId);
  return requestAnalyticsApi(
    `/api/v1/analytics/projects/${safeId}`,
    token,
    validateProjectAnalyticsResponse,
    signal,
  );
}

export async function getWorkspaceAnalytics(
  token: string,
  signal?: AbortSignal,
): Promise<WorkspaceAnalyticsSummary> {
  return requestAnalyticsApi(
    "/api/v1/analytics/workspace",
    token,
    validateWorkspaceAnalyticsSummary,
    signal,
  );
}
