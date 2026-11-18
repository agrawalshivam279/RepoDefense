import { describe, it } from "node:test";
import assert from "node:assert";
import { fetchLearningLoopHealth, parseLearningLoopHealthResponse } from "../learningApi";

describe("learningApi - Diagnostic Health & Telemetry", () => {
  it("fetches and parses 200 OK healthy response", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input, init) => {
      const url = String(input);
      assert.ok(url.includes("/api/v1/health/learning-loop"));
      assert.strictEqual((init?.headers as Record<string, string>)?.Authorization, "Bearer valid-token");

      return {
        ok: true,
        status: 200,
        json: async () => ({
          status: "healthy",
          app: "RepoDefense",
          version: "0.1.0",
          database_models: {
            status: "healthy",
            user_skills_accessible: true,
            candidate_weaknesses_accessible: true,
            total_user_skills: 18,
            total_candidate_weaknesses: 4,
            detail: null,
          },
          benchmark_profiles: {
            status: "healthy",
            configured_tiers: ["mid_level", "senior_engineer", "staff_principal"],
            total_categories: 6,
            tier_integrity_verified: true,
            detail: null,
          },
          mentor_service: {
            status: "healthy",
            fallbacks_ready: true,
            supported_fallback_topics: ["connection_pooling", "rate_limiting"],
            detail: null,
          },
          retest_service: {
            status: "healthy",
            cache_active: true,
            cached_question_count: 5,
            max_cache_capacity: 1000,
            detail: null,
          },
        }),
      } as Response;
    };

    try {
      const report = await fetchLearningLoopHealth("valid-token");
      assert.strictEqual(report.status, "healthy");
      assert.strictEqual(report.database_models.total_user_skills, 18);
      assert.strictEqual(report.benchmark_profiles.configured_tiers.length, 3);
      assert.strictEqual(report.mentor_service.fallbacks_ready, true);
      assert.strictEqual(report.retest_service.cached_question_count, 5);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("fetches and parses 503 response containing diagnostic report", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () =>
      ({
        ok: false,
        status: 503,
        json: async () => ({
          status: "unhealthy",
          app: "RepoDefense",
          version: "0.1.0",
          database_models: {
            status: "unhealthy",
            user_skills_accessible: false,
            candidate_weaknesses_accessible: false,
            total_user_skills: 0,
            total_candidate_weaknesses: 0,
            detail: "Database query failed",
          },
          benchmark_profiles: {
            status: "healthy",
            configured_tiers: ["mid_level", "senior_engineer", "staff_principal"],
            total_categories: 6,
            tier_integrity_verified: true,
            detail: null,
          },
          mentor_service: {
            status: "healthy",
            fallbacks_ready: true,
            supported_fallback_topics: ["connection_pooling"],
            detail: null,
          },
          retest_service: {
            status: "healthy",
            cache_active: true,
            cached_question_count: 0,
            max_cache_capacity: 1000,
            detail: null,
          },
        }),
      } as Response);

    try {
      const report = await fetchLearningLoopHealth("valid-token");
      assert.strictEqual(report.status, "unhealthy");
      assert.strictEqual(report.database_models.status, "unhealthy");
      assert.strictEqual(report.database_models.detail, "Database query failed");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("throws descriptive error when server returns 401 Unauthorized", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () =>
      ({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Could not validate credentials" }),
      } as Response);

    try {
      await assert.rejects(
        async () => {
          await fetchLearningLoopHealth("invalid-token");
        },
        {
          name: "Error",
          message: "Could not validate credentials",
        }
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("rejects malformed payloads with missing root or invalid enums", () => {
    assert.throws(
      () => parseLearningLoopHealthResponse(null),
      /Invalid learning loop health response: root payload must be an object/
    );

    assert.throws(
      () =>
        parseLearningLoopHealthResponse({
          status: "unknown_status",
          database_models: {},
          benchmark_profiles: {},
          mentor_service: {},
          retest_service: {},
        }),
      /Invalid status: unsupported status value/
    );

    assert.throws(
      () =>
        parseLearningLoopHealthResponse({
          status: "healthy",
          database_models: { status: "invalid_db_status" },
          benchmark_profiles: {},
          mentor_service: {},
          retest_service: {},
        }),
      /Invalid database_models\.status: unsupported status value/
    );
  });
});
