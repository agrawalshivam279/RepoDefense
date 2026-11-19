import { afterEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  createPrivateRepoProject,
  fetchGitHubAppStatus,
  fetchInstallationRepositories,
} from "../githubAppApi";

const ORIGINAL_FETCH = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = ORIGINAL_FETCH;
});

describe("githubAppApi - GitHub App Private Repo Client", () => {
  it("fetches deployment status and installation url", async () => {
    globalThis.fetch = async (input) => {
      const url = String(input);
      assert.ok(url.includes("/api/v1/github-app/status"));
      return {
        ok: true,
        status: 200,
        json: async () => ({
          configured: true,
          app_id: "123456",
          app_slug: "repodefense-app",
          install_url: "https://github.com/apps/repodefense-app/installations/new",
        }),
      } as Response;
    };

    const status = await fetchGitHubAppStatus();
    assert.strictEqual(status.configured, true);
    assert.strictEqual(status.app_id, "123456");
    assert.ok(status.install_url?.includes("repodefense-app"));
  });

  it("throws descriptive error when status endpoint fails", async () => {
    globalThis.fetch = async () => {
      return {
        ok: false,
        status: 500,
      } as Response;
    };

    await assert.rejects(
      async () => fetchGitHubAppStatus(),
      /Failed to fetch GitHub App status \(status 500\)/
    );
  });

  it("fetches accessible repositories for an installation with authorization token", async () => {
    globalThis.fetch = async (input, init) => {
      const url = String(input);
      assert.ok(url.includes("/api/v1/github-app/installations/98765/repositories"));
      assert.strictEqual(
        (init?.headers as Record<string, string>)?.Authorization,
        "Bearer test-access-token"
      );

      return {
        ok: true,
        status: 200,
        json: async () => ({
          installation_id: 98765,
          total_count: 2,
          repositories: [
            {
              id: 101,
              name: "private-core",
              full_name: "acme/private-core",
              private: true,
              default_branch: "main",
              description: "Core backend service",
              clone_url: "https://github.com/acme/private-core.git",
              html_url: "https://github.com/acme/private-core",
            },
            {
              id: 102,
              name: "public-docs",
              full_name: "acme/public-docs",
              private: false,
              default_branch: "main",
              description: "Documentation",
              clone_url: "https://github.com/acme/public-docs.git",
              html_url: "https://github.com/acme/public-docs",
            },
          ],
        }),
      } as Response;
    };

    const result = await fetchInstallationRepositories(98765, "test-access-token");
    assert.strictEqual(result.installation_id, 98765);
    assert.strictEqual(result.total_count, 2);
    assert.strictEqual(result.repositories[0].name, "private-core");
    assert.strictEqual(result.repositories[0].private, true);
  });

  it("handles 403 access denied when querying unauthorized installation", async () => {
    globalThis.fetch = async () => {
      return {
        ok: false,
        status: 403,
        json: async () => ({
          detail: "You are not authorized to access this GitHub App installation",
        }),
      } as Response;
    };

    await assert.rejects(
      async () => fetchInstallationRepositories(11111, "test-token"),
      /Access Denied: You are not authorized/
    );
  });

  it("handles 404 when installation does not exist", async () => {
    globalThis.fetch = async () => {
      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: "Not found" }),
      } as Response;
    };

    await assert.rejects(
      async () => fetchInstallationRepositories(99999, "test-token"),
      /Installation #99999 not found/
    );
  });

  it("creates private project and handles 409 conflict & 503 offline", async () => {
    // 1. Successful creation
    globalThis.fetch = async (input, init) => {
      const body = JSON.parse(String(init?.body));
      assert.strictEqual(body.full_name, "acme/private-core");
      assert.strictEqual(body.installation_id, 98765);
      return {
        ok: true,
        status: 201,
        json: async () => ({
          id: "proj-uuid-123",
          user_id: "user-uuid-456",
          name: "private-core",
          github_url: "https://github.com/acme/private-core",
          default_branch: "main",
          status: "pending",
          created_at: "2026-11-19T00:00:00Z",
          updated_at: "2026-11-19T00:00:00Z",
        }),
      } as Response;
    };

    const project = await createPrivateRepoProject(
      { full_name: "acme/private-core", installation_id: 98765 },
      "test-token"
    );
    assert.strictEqual(project.id, "proj-uuid-123");
    assert.strictEqual(project.name, "private-core");

    // 2. 409 Conflict
    globalThis.fetch = async () => ({
      ok: false,
      status: 409,
      json: async () => ({ detail: "Conflict" }),
    } as Response);

    await assert.rejects(
      async () =>
        createPrivateRepoProject(
          { full_name: "acme/private-core", installation_id: 98765 },
          "test-token"
        ),
      /already registered/
    );

    // 3. 503 Service Unavailable
    globalThis.fetch = async () => ({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Queue unavailable" }),
    } as Response);

    await assert.rejects(
      async () =>
        createPrivateRepoProject(
          { full_name: "acme/private-core", installation_id: 98765 },
          "test-token"
        ),
      /worker queue is currently offline/
    );
  });
});
