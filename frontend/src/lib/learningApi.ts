/**
 * REST API client for Phase 4 Learning Loop Diagnostic Telemetry in Next.js 15.
 * Connects to /api/v1/health/learning-loop with strict schema validation.
 */

import type {
  BenchmarkProfilesHealth,
  ComponentHealthStatus,
  DatabaseModelsHealth,
  LearningLoopHealthResponse,
  MentorServiceHealth,
  RetestServiceHealth,
} from "@/types/learning";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

const VALID_STATUSES = new Set<ComponentHealthStatus>(["healthy", "degraded", "unhealthy"]);

function isRecord(val: unknown): val is Record<string, unknown> {
  return typeof val === "object" && val !== null && !Array.isArray(val);
}

function parseStatus(val: unknown, fieldName: string): ComponentHealthStatus {
  if (typeof val !== "string" || !VALID_STATUSES.has(val as ComponentHealthStatus)) {
    throw new Error(`Invalid ${fieldName}: unsupported status value`);
  }
  return val as ComponentHealthStatus;
}

function parseDatabaseModelsHealth(raw: unknown): DatabaseModelsHealth {
  if (!isRecord(raw)) {
    throw new Error("Invalid database_models health: expected object");
  }
  return {
    status: parseStatus(raw.status, "database_models.status"),
    user_skills_accessible: Boolean(raw.user_skills_accessible),
    candidate_weaknesses_accessible: Boolean(raw.candidate_weaknesses_accessible),
    total_user_skills: typeof raw.total_user_skills === "number" ? Math.max(0, raw.total_user_skills) : 0,
    total_candidate_weaknesses:
      typeof raw.total_candidate_weaknesses === "number" ? Math.max(0, raw.total_candidate_weaknesses) : 0,
    detail: typeof raw.detail === "string" ? raw.detail : null,
  };
}

function parseBenchmarkProfilesHealth(raw: unknown): BenchmarkProfilesHealth {
  if (!isRecord(raw)) {
    throw new Error("Invalid benchmark_profiles health: expected object");
  }
  return {
    status: parseStatus(raw.status, "benchmark_profiles.status"),
    configured_tiers: Array.isArray(raw.configured_tiers)
      ? raw.configured_tiers.filter((t): t is string => typeof t === "string")
      : [],
    total_categories: typeof raw.total_categories === "number" ? Math.max(0, raw.total_categories) : 0,
    tier_integrity_verified: Boolean(raw.tier_integrity_verified),
    detail: typeof raw.detail === "string" ? raw.detail : null,
  };
}

function parseMentorServiceHealth(raw: unknown): MentorServiceHealth {
  if (!isRecord(raw)) {
    throw new Error("Invalid mentor_service health: expected object");
  }
  return {
    status: parseStatus(raw.status, "mentor_service.status"),
    fallbacks_ready: Boolean(raw.fallbacks_ready),
    supported_fallback_topics: Array.isArray(raw.supported_fallback_topics)
      ? raw.supported_fallback_topics.filter((t): t is string => typeof t === "string")
      : [],
    detail: typeof raw.detail === "string" ? raw.detail : null,
  };
}

function parseRetestServiceHealth(raw: unknown): RetestServiceHealth {
  if (!isRecord(raw)) {
    throw new Error("Invalid retest_service health: expected object");
  }
  return {
    status: parseStatus(raw.status, "retest_service.status"),
    cache_active: Boolean(raw.cache_active),
    cached_question_count: typeof raw.cached_question_count === "number" ? Math.max(0, raw.cached_question_count) : 0,
    max_cache_capacity: typeof raw.max_cache_capacity === "number" ? Math.max(0, raw.max_cache_capacity) : 1000,
    detail: typeof raw.detail === "string" ? raw.detail : null,
  };
}

export function parseLearningLoopHealthResponse(data: unknown): LearningLoopHealthResponse {
  if (!isRecord(data)) {
    throw new Error("Invalid learning loop health response: root payload must be an object");
  }

  return {
    status: parseStatus(data.status, "status"),
    app: typeof data.app === "string" ? data.app : "RepoDefense",
    version: typeof data.version === "string" ? data.version : "0.1.0",
    database_models: parseDatabaseModelsHealth(data.database_models),
    benchmark_profiles: parseBenchmarkProfilesHealth(data.benchmark_profiles),
    mentor_service: parseMentorServiceHealth(data.mentor_service),
    retest_service: parseRetestServiceHealth(data.retest_service),
  };
}

/**
 * Fetches the diagnostic health and operational telemetry for the Phase 4 Learning Loop.
 */
export async function fetchLearningLoopHealth(token: string): Promise<LearningLoopHealthResponse> {
  const url = `${API_BASE}/api/v1/health/learning-loop`;
  const res = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
    cache: "no-store",
  });

  // Both 200 OK and 503 Service Unavailable return a diagnostic LearningLoopHealthResponse
  if (res.status === 200 || res.status === 503) {
    const json = await res.json();
    return parseLearningLoopHealthResponse(json);
  }

  let errorMessage = `Learning health check failed with status ${res.status}`;
  try {
    const errorJson = await res.json();
    if (isRecord(errorJson) && typeof errorJson.detail === "string") {
      errorMessage = errorJson.detail;
    }
  } catch {
    // Keep fallback error string
  }

  throw new Error(errorMessage);
}
