import { describe, it } from "node:test";
import assert from "node:assert";
import {
  createPublicShareToken,
  getPublicDefenseReport,
  getPublicShareInfo,
  revokePublicShare,
} from "../publicReportApi";

describe("publicReportApi - Public Verification & Share Token Client", () => {
  it("fetches unauthenticated verified defense report", async () => {
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = async (input, init) => {
        const url = String(input);
        assert.ok(url.includes("/api/v1/public/reports/rd_token_123"));
        assert.strictEqual(init?.method, "GET");
        // Must NOT require Authorization header for public access
        assert.strictEqual((init?.headers as Record<string, string>)?.Authorization, undefined);

        return {
          ok: true,
          status: 200,
          json: async () => ({
            verification_id: "rd_token_123",
            project_name: "secure-service",
            github_url: "https://github.com/org/secure-service",
            commit_hash: "a1b2c3d4e5f6",
            overall_score: 8.7,
            verdict: "Certified Principal Defense",
            certification_tier: "Certified Principal",
            summary: "Exemplary architectural understanding.",
            category_scores: [
              {
                category: "architecture",
                score: 9.0,
                questions_count: 3,
                status: "passed",
                summary: "Mastered layered patterns",
              },
            ],
            key_strengths: ["Clean modular boundaries"],
            critical_blind_spots: [],
            architecture_primary_pattern: "Modular Monolith",
            tech_health_score: 98,
            total_questions: 3,
            completed_at: "2026-11-19T00:00:00Z",
            verified_at: "2026-11-19T00:05:00Z",
            issuer: "RepoDefense Verifier",
          }),
        } as Response;
      };

      const report = await getPublicDefenseReport("rd_token_123");
      assert.strictEqual(report.verification_id, "rd_token_123");
      assert.strictEqual(report.project_name, "secure-service");
      assert.strictEqual(report.overall_score, 8.7);
      assert.strictEqual(report.certification_tier, "Certified Principal");
      assert.strictEqual(report.category_scores.length, 1);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("handles 404/410 error properly in getPublicDefenseReport", async () => {
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = async () =>
        ({
          ok: false,
          status: 404,
          json: async () => ({ detail: "Public defense report not found or sharing has been revoked." }),
        }) as Response;

      await assert.rejects(
        async () => {
          await getPublicDefenseReport("rd_invalid");
        },
        {
          name: "Error",
          message: "Public defense report not found or sharing has been revoked.",
        }
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("creates public share token with authorization and expiration", async () => {
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = async (input, init) => {
        const url = String(input);
        assert.ok(url.includes("/api/v1/projects/p123/defense/s456/share"));
        assert.strictEqual(init?.method, "POST");
        assert.strictEqual((init?.headers as Record<string, string>)?.Authorization, "Bearer auth-token");
        const body = JSON.parse(init?.body as string);
        assert.strictEqual(body.is_active, true);
        assert.strictEqual(body.expires_in_days, 30);

        return {
          ok: true,
          status: 200,
          json: async () => ({
            session_id: "s456",
            project_id: "p123",
            share_token: "rd_generated_xyz",
            share_url: "http://localhost:3000/verify/rd_generated_xyz",
            badge_url: "http://localhost:8000/api/v1/public/badges/rd_generated_xyz.svg",
            markdown_badge: "[![RepoDefense Certified](badge)](url)",
            html_badge: "<a href='url'><img src='badge' /></a>",
            is_active: true,
            created_at: "2026-11-19T00:00:00Z",
            expires_at: "2026-12-19T00:00:00Z",
          }),
        } as Response;
      };

      const res = await createPublicShareToken("p123", "s456", "auth-token", {
        is_active: true,
        expires_in_days: 30,
      });
      assert.strictEqual(res.share_token, "rd_generated_xyz");
      assert.strictEqual(res.is_active, true);
      assert.strictEqual(res.expires_at, "2026-12-19T00:00:00Z");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("retrieves existing public share credentials", async () => {
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = async (input, init) => {
        const url = String(input);
        assert.ok(url.includes("/api/v1/projects/p123/defense/s456/share"));
        assert.strictEqual(init?.method, "GET");
        assert.strictEqual((init?.headers as Record<string, string>)?.Authorization, "Bearer auth-token");

        return {
          ok: true,
          status: 200,
          json: async () => ({
            session_id: "s456",
            project_id: "p123",
            share_token: "rd_existing",
            share_url: "http://localhost:3000/verify/rd_existing",
            badge_url: "http://localhost:8000/api/v1/public/badges/rd_existing.svg",
            markdown_badge: "[badge](url)",
            html_badge: "<a>badge</a>",
            is_active: true,
            created_at: "2026-11-19T00:00:00Z",
            expires_at: null,
          }),
        } as Response;
      };

      const res = await getPublicShareInfo("p123", "s456", "auth-token");
      assert.strictEqual(res.share_token, "rd_existing");
      assert.strictEqual(res.expires_at, null);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("revokes public share credentials cleanly", async () => {
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = async (input, init) => {
        const url = String(input);
        assert.ok(url.includes("/api/v1/projects/p123/defense/s456/share"));
        assert.strictEqual(init?.method, "DELETE");
        assert.strictEqual((init?.headers as Record<string, string>)?.Authorization, "Bearer auth-token");

        return {
          ok: true,
          status: 200,
          json: async () => ({ revoked: true, session_id: "s456" }),
        } as Response;
      };

      const res = await revokePublicShare("p123", "s456", "auth-token");
      assert.strictEqual(res.revoked, true);
      assert.strictEqual(res.session_id, "s456");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
