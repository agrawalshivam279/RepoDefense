import { describe, it } from "node:test";
import assert from "node:assert";
import { fetchSkillGapAnalysis } from "../skillGapApi";

describe("skillGapApi - Network & Parsing", () => {
  it("fetches and parses skill gap analysis payload", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input, init) => {
      const url = String(input);
      assert.ok(url.includes("/api/v1/skills/gap-analysis"));
      assert.ok(url.includes("target_role=staff_principal"));
      assert.ok(url.includes("project_id=p-123"));
      assert.strictEqual((init?.headers as Record<string, string>)?.Authorization, "Bearer mock-token");

      return {
        ok: true,
        status: 200,
        json: async () => ({
          target_role: "staff_principal",
          overall_candidate_score: 78.5,
          overall_benchmark_score: 90.0,
          overall_readiness_pct: 87.2,
          categories: [
            {
              category: "system_architecture",
              current_score: 85.0,
              benchmark_score: 92.0,
              gap_deficit: 7.0,
              status: "moderate_gap",
              weight: 1.3,
              percentile_estimate: 69.3,
            },
          ],
          recommendations: [
            {
              topic: "Microservices",
              category: "system_architecture",
              priority: "high",
              rationale: "Active gap found.",
              unresolved_weakness_count: 1,
              suggested_action: "Targeted re-test.",
            },
          ],
          strengths: ["database_design"],
          critical_gaps: ["concurrency_performance"],
          analyzed_at: "2026-11-18T00:00:00Z",
        }),
      } as Response;
    };

    try {
      const resp = await fetchSkillGapAnalysis("mock-token", "staff_principal", "p-123");
      assert.strictEqual(resp.target_role, "staff_principal");
      assert.strictEqual(resp.overall_readiness_pct, 87.2);
      assert.strictEqual(resp.categories.length, 1);
      assert.strictEqual(resp.categories[0].category, "system_architecture");
      assert.strictEqual(resp.recommendations.length, 1);
      assert.strictEqual(resp.strengths[0], "database_design");
      assert.strictEqual(resp.critical_gaps[0], "concurrency_performance");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("throws descriptive error when server returns error status", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () =>
      ({
        ok: false,
        status: 404,
        json: async () => ({ detail: "Candidate skills not found" }),
      } as Response);

    try {
      await assert.rejects(
        async () => {
          await fetchSkillGapAnalysis("mock-token", "senior_engineer");
        },
        {
          name: "Error",
          message: "Candidate skills not found",
        }
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("rejects malformed payloads missing categories array", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () =>
      ({
        ok: true,
        status: 200,
        json: async () => ({ target_role: "senior_engineer" }),
      } as Response);

    try {
      await assert.rejects(
        async () => {
          await fetchSkillGapAnalysis("mock-token", "senior_engineer");
        },
        {
          name: "Error",
          message: /Malformed skill gap analysis payload/,
        }
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("rejects out-of-bounds scores and invalid enum values", async () => {
    const originalFetch = globalThis.fetch;

    // Out-of-bounds score in category
    globalThis.fetch = async () =>
      ({
        ok: true,
        status: 200,
        json: async () => ({
          target_role: "senior_engineer",
          overall_candidate_score: 50.0,
          overall_benchmark_score: 80.0,
          overall_readiness_pct: 62.5,
          categories: [
            {
              category: "system_architecture",
              current_score: 150.0, // Invalid > 100
              benchmark_score: 85.0,
              gap_deficit: 0.0,
              status: "met",
              weight: 1.0,
              percentile_estimate: 50.0,
            },
          ],
          recommendations: [],
          strengths: [],
          critical_gaps: [],
        }),
      } as Response);

    await assert.rejects(
      async () => {
        await fetchSkillGapAnalysis("mock-token", "senior_engineer");
      },
      {
        name: "Error",
        message: /current_score must be a number between 0 and 100/,
      }
    );

    // Invalid status in category
    globalThis.fetch = async () =>
      ({
        ok: true,
        status: 200,
        json: async () => ({
          target_role: "senior_engineer",
          overall_candidate_score: 50.0,
          overall_benchmark_score: 80.0,
          overall_readiness_pct: 62.5,
          categories: [
            {
              category: "system_architecture",
              current_score: 75.0,
              benchmark_score: 85.0,
              gap_deficit: 10.0,
              status: "unexpected_status", // Invalid
              weight: 1.0,
              percentile_estimate: 50.0,
            },
          ],
          recommendations: [],
          strengths: [],
          critical_gaps: [],
        }),
      } as Response);

    await assert.rejects(
      async () => {
        await fetchSkillGapAnalysis("mock-token", "senior_engineer");
      },
      {
        name: "Error",
        message: /invalid or unsupported status/,
      }
    );

    globalThis.fetch = originalFetch;
  });
});
