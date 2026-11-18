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

function parseBoolean(val: unknown, fieldName: string): boolean {
  if (typeof val !== "boolean") {
    throw new Error(`Invalid ${fieldName}: expected boolean`);
  }
  return val;
}

function parseNonNegativeInt(val: unknown, fieldName: string): number {
  if (typeof val !== "number" || !Number.isFinite(val) || val < 0) {
    throw new Error(`Invalid ${fieldName}: expected non-negative number`);
  }
  return Math.floor(val);
}

function parseStringArray(val: unknown, fieldName: string): string[] {
  if (!Array.isArray(val) || !val.every((item) => typeof item === "string")) {
    throw new Error(`Invalid ${fieldName}: expected array of strings`);
  }
  return val;
}

function parseOptionalString(val: unknown, fieldName: string): string | null {
  if (val === null || val === undefined) {
    return null;
  }
  if (typeof val !== "string") {
    throw new Error(`Invalid ${fieldName}: expected string or null`);
  }
  return val;
}

function parseDatabaseModelsHealth(raw: unknown): DatabaseModelsHealth {
  if (!isRecord(raw)) {
    throw new Error("Invalid database_models health: expected object");
  }
  return {
    status: parseStatus(raw.status, "database_models.status"),
    user_skills_accessible: parseBoolean(raw.user_skills_accessible, "database_models.user_skills_accessible"),
    candidate_weaknesses_accessible: parseBoolean(
      raw.candidate_weaknesses_accessible,
      "database_models.candidate_weaknesses_accessible"
    ),
    total_user_skills: parseNonNegativeInt(raw.total_user_skills, "database_models.total_user_skills"),
    total_candidate_weaknesses: parseNonNegativeInt(
      raw.total_candidate_weaknesses,
      "database_models.total_candidate_weaknesses"
    ),
    detail: parseOptionalString(raw.detail, "database_models.detail"),
  };
}

function parseBenchmarkProfilesHealth(raw: unknown): BenchmarkProfilesHealth {
  if (!isRecord(raw)) {
    throw new Error("Invalid benchmark_profiles health: expected object");
  }
  return {
    status: parseStatus(raw.status, "benchmark_profiles.status"),
    configured_tiers: parseStringArray(raw.configured_tiers, "benchmark_profiles.configured_tiers"),
    total_categories: parseNonNegativeInt(raw.total_categories, "benchmark_profiles.total_categories"),
    tier_integrity_verified: parseBoolean(raw.tier_integrity_verified, "benchmark_profiles.tier_integrity_verified"),
    detail: parseOptionalString(raw.detail, "benchmark_profiles.detail"),
  };
}

function parseMentorServiceHealth(raw: unknown): MentorServiceHealth {
  if (!isRecord(raw)) {
    throw new Error("Invalid mentor_service health: expected object");
  }
  return {
    status: parseStatus(raw.status, "mentor_service.status"),
    fallbacks_ready: parseBoolean(raw.fallbacks_ready, "mentor_service.fallbacks_ready"),
    supported_fallback_topics: parseStringArray(
      raw.supported_fallback_topics,
      "mentor_service.supported_fallback_topics"
    ),
    detail: parseOptionalString(raw.detail, "mentor_service.detail"),
  };
}

function parseRetestServiceHealth(raw: unknown): RetestServiceHealth {
  if (!isRecord(raw)) {
    throw new Error("Invalid retest_service health: expected object");
  }
  return {
    status: parseStatus(raw.status, "retest_service.status"),
    cache_active: parseBoolean(raw.cache_active, "retest_service.cache_active"),
    cached_question_count: parseNonNegativeInt(raw.cached_question_count, "retest_service.cached_question_count"),
    max_cache_capacity: parseNonNegativeInt(raw.max_cache_capacity, "retest_service.max_cache_capacity"),
    detail: parseOptionalString(raw.detail, "retest_service.detail"),
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
    const json: unknown = await res.json();
    return parseLearningLoopHealthResponse(json);
  }

  let errorMessage = `Learning health check failed with status ${res.status}`;
  try {
    const errorJson: unknown = await res.json();
    if (isRecord(errorJson) && typeof errorJson.detail === "string") {
      errorMessage = errorJson.detail;
    }
  } catch {
    // Keep fallback error string
  }

  throw new Error(errorMessage);
}
