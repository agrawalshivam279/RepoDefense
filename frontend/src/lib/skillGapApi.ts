/**
 * REST API client for Skill Gap Analysis in Next.js 15.
 * Connects to /api/v1/skills/gap-analysis with schema validation.
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

function clamp(val: number, min = 0, max = 100): number {
  return Math.min(Math.max(val, min), max);
}

function isRecord(val: unknown): val is Record<string, unknown> {
  return typeof val === "object" && val !== null && !Array.isArray(val);
}

function parseCategoryMetric(raw: unknown): CategoryGapMetric {
  if (!isRecord(raw) || typeof raw.category !== "string") {
    throw new Error("Invalid category gap metric payload");
  }
  const cur = typeof raw.current_score === "number" && Number.isFinite(raw.current_score)
    ? clamp(raw.current_score)
    : 0.0;
  const bench = typeof raw.benchmark_score === "number" && Number.isFinite(raw.benchmark_score)
    ? clamp(raw.benchmark_score)
    : 80.0;
  const def = typeof raw.gap_deficit === "number" && Number.isFinite(raw.gap_deficit)
    ? clamp(raw.gap_deficit, 0, 100)
    : 0.0;
  const wt = typeof raw.weight === "number" && Number.isFinite(raw.weight) ? raw.weight : 1.0;
  const pct = typeof raw.percentile_estimate === "number" && Number.isFinite(raw.percentile_estimate)
    ? clamp(raw.percentile_estimate)
    : 50.0;
  const status: GapStatus = typeof raw.status === "string" && VALID_GAP_STATUSES.has(raw.status as GapStatus)
    ? (raw.status as GapStatus)
    : "moderate_gap";

  return {
    category: raw.category,
    current_score: cur,
    benchmark_score: bench,
    gap_deficit: def,
    status,
    weight: wt,
    percentile_estimate: pct,
  };
}

function parseRecommendation(raw: unknown): RemediationRecommendation {
  if (!isRecord(raw) || typeof raw.topic !== "string") {
    throw new Error("Invalid remediation recommendation payload");
  }
  const priority: RemediationPriority = typeof raw.priority === "string" && VALID_PRIORITIES.has(raw.priority as RemediationPriority)
    ? (raw.priority as RemediationPriority)
    : "medium";

  return {
    topic: raw.topic,
    category: typeof raw.category === "string" ? raw.category : "general",
    priority,
    rationale: typeof raw.rationale === "string" ? raw.rationale : "",
    unresolved_weakness_count: typeof raw.unresolved_weakness_count === "number" ? Math.max(0, raw.unresolved_weakness_count) : 0,
    suggested_action: typeof raw.suggested_action === "string" ? raw.suggested_action : "",
  };
}

function parseSkillGapAnalysis(raw: unknown): SkillGapAnalysisResponse {
  if (!isRecord(raw) || !Array.isArray(raw.categories)) {
    throw new Error("Malformed skill gap analysis payload");
  }

  const overallCand = typeof raw.overall_candidate_score === "number" && Number.isFinite(raw.overall_candidate_score)
    ? clamp(raw.overall_candidate_score)
    : 0.0;
  const overallBench = typeof raw.overall_benchmark_score === "number" && Number.isFinite(raw.overall_benchmark_score)
    ? clamp(raw.overall_benchmark_score)
    : 80.0;
  const overallReadiness = typeof raw.overall_readiness_pct === "number" && Number.isFinite(raw.overall_readiness_pct)
    ? clamp(raw.overall_readiness_pct)
    : 0.0;
  const targetRole: TargetRoleBenchmark = typeof raw.target_role === "string" && VALID_ROLES.has(raw.target_role as TargetRoleBenchmark)
    ? (raw.target_role as TargetRoleBenchmark)
    : "senior_engineer";

  return {
    target_role: targetRole,
    overall_candidate_score: overallCand,
    overall_benchmark_score: overallBench,
    overall_readiness_pct: overallReadiness,
    categories: raw.categories.map(parseCategoryMetric),
    recommendations: Array.isArray(raw.recommendations) ? raw.recommendations.map(parseRecommendation) : [],
    strengths: Array.isArray(raw.strengths) ? raw.strengths.filter((s): s is string => typeof s === "string") : [],
    critical_gaps: Array.isArray(raw.critical_gaps) ? raw.critical_gaps.filter((s): s is string => typeof s === "string") : [],
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
