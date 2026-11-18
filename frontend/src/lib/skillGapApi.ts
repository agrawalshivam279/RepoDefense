/**
 * REST API client for Skill Gap Analysis in Next.js 15.
 * Connects to /api/v1/skills/gap-analysis with strict schema validation.
 */

import type {
  CategoryGapMetric,
  GapStatus,
  RemediationPriority,
  RemediationRecommendation,
  SkillGapAnalysisResponse,
  TargetRoleBenchmark,
} from "@/types/skillGap";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

const VALID_GAP_STATUSES = new Set<GapStatus>(["surpassed", "met", "moderate_gap", "critical_gap"]);
const VALID_PRIORITIES = new Set<RemediationPriority>(["critical", "high", "medium", "low"]);
const VALID_ROLES = new Set<TargetRoleBenchmark>(["mid_level", "senior_engineer", "staff_principal"]);

function isRecord(val: unknown): val is Record<string, unknown> {
  return typeof val === "object" && val !== null && !Array.isArray(val);
}

function isValidScore(val: unknown): val is number {
  return typeof val === "number" && Number.isFinite(val) && val >= 0 && val <= 100;
}

function parseCategoryMetric(raw: unknown): CategoryGapMetric {
  if (!isRecord(raw) || typeof raw.category !== "string" || raw.category.trim().length === 0) {
    throw new Error("Invalid category gap metric payload: missing or invalid category");
  }
  if (!isValidScore(raw.current_score)) {
    throw new Error("Invalid category gap metric payload: current_score must be a number between 0 and 100");
  }
  if (!isValidScore(raw.benchmark_score)) {
    throw new Error("Invalid category gap metric payload: benchmark_score must be a number between 0 and 100");
  }
  if (!isValidScore(raw.gap_deficit)) {
    throw new Error("Invalid category gap metric payload: gap_deficit must be a number between 0 and 100");
  }
  if (typeof raw.weight !== "number" || !Number.isFinite(raw.weight) || raw.weight < 0) {
    throw new Error("Invalid category gap metric payload: weight must be a non-negative number");
  }
  if (!isValidScore(raw.percentile_estimate)) {
    throw new Error("Invalid category gap metric payload: percentile_estimate must be a number between 0 and 100");
  }
  if (typeof raw.status !== "string" || !VALID_GAP_STATUSES.has(raw.status as GapStatus)) {
    throw new Error("Invalid category gap metric payload: invalid or unsupported status");
  }

  return {
    category: raw.category,
    current_score: raw.current_score,
    benchmark_score: raw.benchmark_score,
    gap_deficit: raw.gap_deficit,
    status: raw.status as GapStatus,
    weight: raw.weight,
    percentile_estimate: raw.percentile_estimate,
  };
}

function parseRecommendation(raw: unknown): RemediationRecommendation {
  if (!isRecord(raw) || typeof raw.topic !== "string" || raw.topic.trim().length === 0) {
    throw new Error("Invalid remediation recommendation payload: missing or invalid topic");
  }
  if (typeof raw.category !== "string" || raw.category.trim().length === 0) {
    throw new Error("Invalid remediation recommendation payload: missing or invalid category");
  }
  if (typeof raw.priority !== "string" || !VALID_PRIORITIES.has(raw.priority as RemediationPriority)) {
    throw new Error("Invalid remediation recommendation payload: invalid or unsupported priority");
  }
  if (typeof raw.rationale !== "string") {
    throw new Error("Invalid remediation recommendation payload: rationale must be a string");
  }
  if (
    typeof raw.unresolved_weakness_count !== "number" ||
    !Number.isFinite(raw.unresolved_weakness_count) ||
    raw.unresolved_weakness_count < 0
  ) {
    throw new Error("Invalid remediation recommendation payload: unresolved_weakness_count must be a non-negative integer");
  }
  if (typeof raw.suggested_action !== "string") {
    throw new Error("Invalid remediation recommendation payload: suggested_action must be a string");
  }

  return {
    topic: raw.topic,
    category: raw.category,
    priority: raw.priority as RemediationPriority,
    rationale: raw.rationale,
    unresolved_weakness_count: raw.unresolved_weakness_count,
    suggested_action: raw.suggested_action,
  };
}

function parseSkillGapAnalysis(raw: unknown): SkillGapAnalysisResponse {
  if (!isRecord(raw) || !Array.isArray(raw.categories)) {
    throw new Error("Malformed skill gap analysis payload: missing categories array");
  }
  if (typeof raw.target_role !== "string" || !VALID_ROLES.has(raw.target_role as TargetRoleBenchmark)) {
    throw new Error("Malformed skill gap analysis payload: invalid or unsupported target_role");
  }
  if (!isValidScore(raw.overall_candidate_score)) {
    throw new Error("Malformed skill gap analysis payload: overall_candidate_score must be a number between 0 and 100");
  }
  if (!isValidScore(raw.overall_benchmark_score)) {
    throw new Error("Malformed skill gap analysis payload: overall_benchmark_score must be a number between 0 and 100");
  }
  if (!isValidScore(raw.overall_readiness_pct)) {
    throw new Error("Malformed skill gap analysis payload: overall_readiness_pct must be a number between 0 and 100");
  }
  if (!Array.isArray(raw.recommendations)) {
    throw new Error("Malformed skill gap analysis payload: recommendations must be an array");
  }
  if (!Array.isArray(raw.strengths) || !raw.strengths.every((s) => typeof s === "string")) {
    throw new Error("Malformed skill gap analysis payload: strengths must be an array of strings");
  }
  if (!Array.isArray(raw.critical_gaps) || !raw.critical_gaps.every((s) => typeof s === "string")) {
    throw new Error("Malformed skill gap analysis payload: critical_gaps must be an array of strings");
  }

  return {
    target_role: raw.target_role as TargetRoleBenchmark,
    overall_candidate_score: raw.overall_candidate_score,
    overall_benchmark_score: raw.overall_benchmark_score,
    overall_readiness_pct: raw.overall_readiness_pct,
    categories: raw.categories.map(parseCategoryMetric),
    recommendations: raw.recommendations.map(parseRecommendation),
    strengths: raw.strengths,
    critical_gaps: raw.critical_gaps,
    analyzed_at: typeof raw.analyzed_at === "string" ? raw.analyzed_at : new Date().toISOString(),
  };
}

export async function fetchSkillGapAnalysis(
  token: string,
  targetRole: TargetRoleBenchmark = "senior_engineer",
  projectId?: string | null
): Promise<SkillGapAnalysisResponse> {
  const params = new URLSearchParams();
  params.set("target_role", targetRole);
  if (projectId) params.set("project_id", projectId);

  const res = await fetch(`${API_BASE}/api/v1/skills/gap-analysis?${params.toString()}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    let msg = `Skill gap analysis request failed (${res.status})`;
    try {
      const errJson: unknown = await res.json();
      if (isRecord(errJson) && typeof errJson.detail === "string") {
        msg = errJson.detail;
      }
    } catch {
      // ignore JSON parse error on error response
    }
    throw new Error(msg);
  }

  const json: unknown = await res.json();
  return parseSkillGapAnalysis(json);
}
