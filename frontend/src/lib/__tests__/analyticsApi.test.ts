import { afterEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  getProjectAnalytics,
  getWorkspaceAnalytics,
  validateProjectAnalyticsResponse,
} from "../analyticsApi";

const ORIGINAL_FETCH = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = ORIGINAL_FETCH;
});

function buildSampleProjectAnalytics(overrides: Record<string, unknown> = {}) {
  return {
    project_id: "proj-1",
    project_name: "RepoDefense",
    overall_readiness_pct: 82.5,
    total_sessions: 4,
    completed_sessions: 3,
    file_coverage_pct: 64.2,
    evidence_coverage_pct: 71.0,
    tech_health_score: 88,
    mode_breakdown: [
      {
        mode: "core_defense",
        label: "Core Defense",
        sessions_total: 2,
        sessions_completed: 2,
        avg_score_pct: 80.0,
        best_score_pct: 85.0,
        pass_rate_pct: 100.0,
      },
      {
        mode: "incident_simulation",
        label: "Incident War Room",
        sessions_total: 1,
        sessions_completed: 1,
        avg_score_pct: 85.0,
        best_score_pct: 85.0,
        pass_rate_pct: 100.0,
      },
    ],
    category_skills: [
      { category: "Architecture", confidence_pct: 84.0, evaluations_count: 2 },
      { category: "Security", confidence_pct: 58.5, evaluations_count: 1 },
    ],
    score_trend: [
      {
        session_id: "s-1",
        mode: "core_defense",
        label: "Core Defense",
        score_pct: 80.0,
        timestamp: "2026-11-12T10:00:00Z",
        topic_or_title: "Auth Middleware",
      },
    ],
    language_distribution: [
      { language: "Python", file_count: 14, total_lines: 1850, line_share_pct: 65.4 },
      { language: "TypeScript", file_count: 9, total_lines: 978, line_share_pct: 34.6 },
    ],
    module_coverage: [
      { module_path: "backend/app/services", coverage_pct: 75.0, tested_files: 6, total_files: 8 },
    ],
    ...overrides,
  };
}

describe("analyticsApi", () => {
  it("getProjectAnalytics encodes projectId, sends Bearer auth, and parses nullable coverage", async () => {
    let capturedUrl = "";
    let capturedAuth = "";
    let capturedSignal: AbortSignal | undefined;

    const controller = new AbortController();
    const payload = buildSampleProjectAnalytics({
      file_coverage_pct: null,
      evidence_coverage_pct: null,
      tech_health_score: null,
    });

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = String(input);
      const headers = new Headers(init?.headers);
      capturedAuth = headers.get("Authorization") ?? "";
      capturedSignal = init?.signal ?? undefined;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch;

    const result = await getProjectAnalytics("proj/with space", "jwt-abc", controller.signal);
    assert.ok(capturedUrl.endsWith("/api/v1/analytics/projects/proj%2Fwith%20space"));
    assert.equal(capturedAuth, "Bearer jwt-abc");
    assert.equal(capturedSignal, controller.signal);
    assert.equal(result.file_coverage_pct, null);
    assert.equal(result.evidence_coverage_pct, null);
    assert.equal(result.tech_health_score, null);
    assert.equal(result.overall_readiness_pct, 82.5);
  });

  it("getWorkspaceAnalytics parses workspace summary cleanly", async () => {
    const wsPayload = {
      total_projects: 2,
      analyzed_projects: 2,
      total_sessions: 5,
      completed_sessions: 4,
      avg_readiness_pct: 76.4,
      mode_breakdown: [],
      recent_trend: [],
    };
    globalThis.fetch = (async () =>
      new Response(JSON.stringify(wsPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })) as typeof fetch;

    const result = await getWorkspaceAnalytics("jwt-ws");
    assert.equal(result.total_projects, 2);
    assert.equal(result.avg_readiness_pct, 76.4);
  });

  it("rejects non-finite score values and invalid mode keys", () => {
    assert.throws(
      () => validateProjectAnalyticsResponse(buildSampleProjectAnalytics({ overall_readiness_pct: Number.NaN })),
      /runtime schema validation/i,
    );
    assert.throws(
      () =>
        validateProjectAnalyticsResponse(
          buildSampleProjectAnalytics({
            score_trend: [
              {
                session_id: "s-bad",
                mode: "unknown_mode",
                label: "Bad",
                score_pct: 50,
                timestamp: "2026-11-12T10:00:00Z",
                topic_or_title: "Bad",
              },
            ],
          }),
        ),
      /runtime schema validation/i,
    );
  });

  it("surfaces FastAPI detail message on HTTP error", async () => {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ detail: "Project not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      })) as typeof fetch;

    await assert.rejects(() => getProjectAnalytics("missing-id", "jwt-abc"), /Project not found/);
  });
});
