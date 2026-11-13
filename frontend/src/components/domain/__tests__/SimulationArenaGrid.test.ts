import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  SIMULATION_MODES,
  parseSimulationReadiness,
} from "../SimulationArenaGrid";

describe("SimulationArenaGrid Catalog & Route Builders", () => {
  it("defines all 6 canonical RepoDefense simulation modes", () => {
    assert.equal(SIMULATION_MODES.length, 6);

    const modeIds = SIMULATION_MODES.map((m) => m.id);
    const expectedIds = [
      "core_defense",
      "pr_defense",
      "commit_defense",
      "incident_simulation",
      "stress_test",
      "arch_defense",
    ];

    assert.deepEqual(modeIds, expectedIds);
  });

  it("ensures each mode has complete required metadata", () => {
    for (const mode of SIMULATION_MODES) {
      assert.ok(mode.title.length > 0, `Mode ${mode.id} has empty title`);
      assert.ok(mode.badgeText.length > 0, `Mode ${mode.id} has empty badge`);
      assert.ok(mode.focusArea.length > 0, `Mode ${mode.id} has empty focus area`);
      assert.ok(mode.description.length > 0, `Mode ${mode.id} has empty description`);
      assert.ok(mode.buttonLabel.length > 0, `Mode ${mode.id} has empty button label`);
      assert.ok(mode.accentColor.startsWith("text-"), `Mode ${mode.id} has invalid accent color`);
      assert.ok(typeof mode.Icon === "function" || typeof mode.Icon === "object");
    }
  });

  it("constructs accurate target URLs for a given project ID", () => {
    const testProjectId = "project-xyz-789";

    const expectedPaths: Record<string, string> = {
      core_defense: `/interview/${testProjectId}`,
      pr_defense: `/projects/${testProjectId}/pr-defense`,
      commit_defense: `/projects/${testProjectId}/commit-defense`,
      incident_simulation: `/projects/${testProjectId}/incident-simulation`,
      stress_test: `/projects/${testProjectId}/stress-test`,
      arch_defense: `/projects/${testProjectId}/arch-defense`,
    };

    for (const mode of SIMULATION_MODES) {
      const generatedUrl = mode.hrefTemplate(testProjectId);
      assert.equal(
        generatedUrl,
        expectedPaths[mode.id],
        `URL mismatch for mode ${mode.id}`
      );
    }
  });

  it("parses active session counts accurately from simulation readiness API payload", () => {
    const mockPayload = {
      status: "healthy",
      simulations: {
        core_defense: { active_sessions: 3, capacity_limit: 100, status: "operational" },
        pr_defense: { active_sessions: 1, capacity_limit: 100, status: "operational" },
        incident_simulation: { active_sessions: 5, capacity_limit: 50, status: "operational" },
      },
      total_active_sessions: 9,
    };

    const counts = parseSimulationReadiness(mockPayload);
    assert.equal(counts.core_defense, 3);
    assert.equal(counts.pr_defense, 1);
    assert.equal(counts.incident_simulation, 5);
    assert.equal(counts.stress_test, undefined);
  });

  it("gracefully handles invalid, null, or malformed readiness payloads", () => {
    assert.deepEqual(parseSimulationReadiness(null), {});
    assert.deepEqual(parseSimulationReadiness(undefined), {});
    assert.deepEqual(parseSimulationReadiness("not-an-object"), {});
    assert.deepEqual(parseSimulationReadiness({ status: "healthy" }), {});
    assert.deepEqual(parseSimulationReadiness({ simulations: null }), {});
  });
});
