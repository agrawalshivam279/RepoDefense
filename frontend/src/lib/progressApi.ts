/**
 * REST API client for Candidate Skill Progress & Improvement Telemetry.
 * Connects to /api/v1/progress endpoints with runtime type-narrowing validation.
 */

import type {
  CategoryProgressDelta,
  ProficiencyTrendPoint,
  UserProgressOverviewResponse,
} from "@/types/progress";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function validateTrendPoint(p: unknown): ProficiencyTrendPoint {
  if (
    !isRecord(p) ||
    typeof p.date !== "string" ||
    typeof p.average_proficiency !== "number" ||
    typeof p.evaluations_count !== "number" ||
    typeof p.passed_count !== "number"
  ) {
    throw new Error("Invalid trend point payload");
  }
  return {
    date: p.date,
    average_proficiency: p.average_proficiency,
    evaluations_count: p.evaluations_count,
    passed_count: p.passed_count,
  };
}

export function validateProgressOverview(payload: unknown): UserProgressOverviewResponse {
  if (!isRecord(payload)) {
    throw new Error("Invalid progress overview: expected an object");
  }

  const wv = payload.weakness_velocity;
  if (!isRecord(wv) || typeof wv.total_identified !== "number") {
    throw new Error("Invalid weakness_velocity in overview payload");
  }

  return {
    overall_proficiency: typeof payload.overall_proficiency === "number" ? payload.overall_proficiency : 0,
    total_evaluations: typeof payload.total_evaluations === "number" ? payload.total_evaluations : 0,
    total_passed: typeof payload.total_passed === "number" ? payload.total_passed : 0,
    overall_pass_rate_pct: typeof payload.overall_pass_rate_pct === "number" ? payload.overall_pass_rate_pct : 0,
    active_skills_count: typeof payload.active_skills_count === "number" ? payload.active_skills_count : 0,
    mastered_skills_count: typeof payload.mastered_skills_count === "number" ? payload.mastered_skills_count : 0,
    learning_streak_days: typeof payload.learning_streak_days === "number" ? payload.learning_streak_days : 0,
    weakness_velocity: {
      total_identified: Number(wv.total_identified) || 0,
      total_resolved: Number(wv.total_resolved) || 0,
      resolution_rate_pct: Number(wv.resolution_rate_pct) || 0,
      critical_resolved: Number(wv.critical_resolved) || 0,
      critical_total: Number(wv.critical_total) || 0,
      major_resolved: Number(wv.major_resolved) || 0,
      major_total: Number(wv.major_total) || 0,
      minor_resolved: Number(wv.minor_resolved) || 0,
      minor_total: Number(wv.minor_total) || 0,
      average_resolution_hours:
        typeof wv.average_resolution_hours === "number" ? wv.average_resolution_hours : null,
    },
    category_deltas: Array.isArray(payload.category_deltas)
      ? (payload.category_deltas as CategoryProgressDelta[])
      : [],
    recent_timeline: Array.isArray(payload.recent_timeline)
      ? payload.recent_timeline.map(validateTrendPoint)
      : [],
    top_improved_topics: Array.isArray(payload.top_improved_topics)
      ? (payload.top_improved_topics as any[])
      : [],
    needs_focus_topics: Array.isArray(payload.needs_focus_topics)
      ? (payload.needs_focus_topics as any[])
      : [],
  };
}

async function requestProgressApi<T>(
  endpoint: string,
  token: string,
  options: { method: "GET" | "POST"; signal?: AbortSignal },
  validator: (raw: unknown) => T
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    Authorization: `Bearer ${token}`,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: options.method,
    headers,
    signal: options.signal,
  });

  const rawJson: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const msg =
      isRecord(rawJson) && typeof rawJson.detail === "string"
        ? rawJson.detail
        : `Progress API error (${response.status})`;
    throw new Error(msg);
  }

  return validator(rawJson);
}

export async function fetchProgressOverview(
  token: string,
  signal?: AbortSignal
): Promise<UserProgressOverviewResponse> {
  return requestProgressApi<UserProgressOverviewResponse>(
    "/api/v1/progress/overview",
    token,
    { method: "GET", signal },
    validateProgressOverview
  );
}

export async function fetchProgressTimeline(
  token: string,
  days: number = 30,
  signal?: AbortSignal
): Promise<ProficiencyTrendPoint[]> {
  const query = `?days=${encodeURIComponent(days)}`;
  return requestProgressApi<ProficiencyTrendPoint[]>(
    `/api/v1/progress/timeline${query}`,
    token,
    { method: "GET", signal },
    (raw) => {
      if (!Array.isArray(raw)) throw new Error("Expected array of timeline points");
      return raw.map(validateTrendPoint);
    }
  );
}

export async function fetchProgressCategories(
  token: string,
  signal?: AbortSignal
): Promise<CategoryProgressDelta[]> {
  return requestProgressApi<CategoryProgressDelta[]>(
    "/api/v1/progress/categories",
    token,
    { method: "GET", signal },
    (raw) => {
      if (!Array.isArray(raw)) throw new Error("Expected array of category deltas");
      return raw as CategoryProgressDelta[];
    }
  );
}
