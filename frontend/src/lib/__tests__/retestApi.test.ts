import { afterEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  createRetestSession,
  fetchEligibleWeaknesses,
  submitRetestAnswer,
} from "../retestApi";

const ORIGINAL_FETCH = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = ORIGINAL_FETCH;
});

describe("retestApi - Network & Parsing", () => {
  it("fetches and parses eligible weaknesses list", async () => {
    const mockWeaknesses = {
      total_eligible: 1,
      weaknesses: [
        {
          id: "w-12345",
          project_id: "p-999",
          category: "concurrency",
          topic: "race_conditions",
          severity: "critical",
          original_prompt: "Explain lost updates",
          feedback: "Use OCC or mutex",
          created_at: "2026-11-18T00:00:00Z",
        },
      ],
    };

    globalThis.fetch = async (url, init) => {
      assert.ok(String(url).includes("/api/v1/retest/weaknesses"));
      const auth = (init?.headers as Record<string, string>)?.Authorization;
      assert.equal(auth, "Bearer test-jwt-token");
      return new Response(JSON.stringify(mockWeaknesses), { status: 200 });
    };

    const res = await fetchEligibleWeaknesses("test-jwt-token", "p-999");
    assert.equal(res.total_eligible, 1);
    assert.equal(res.weaknesses.length, 1);
    assert.equal(res.weaknesses[0].topic, "race_conditions");
  });

  it("creates a targeted retest session and parses questions", async () => {
    const mockSession = {
      session_id: "s-abcde123",
      user_id: "u-999",
      project_id: "p-999",
      total_questions: 1,
      questions: [
        {
          question_id: "q-1",
          weakness_id: "w-12345",
          category: "database",
          topic: "connection_pooling",
          severity: "major",
          original_prompt: "Explain connection starvation",
          question_text: "Redesign database pool for 10k req/s",
          architectural_constraint: "100 max connections",
          evaluation_rubric: "Must propose PgBouncer",
        },
      ],
      created_at: "2026-11-18T00:00:00Z",
    };

    globalThis.fetch = async (url, init) => {
      assert.ok(String(url).includes("/api/v1/retest/session"));
      assert.equal(init?.method, "POST");
      const body = JSON.parse(String(init?.body));
      assert.deepEqual(body.weakness_ids, ["w-12345"]);
      return new Response(JSON.stringify(mockSession), { status: 201 });
    };

    const session = await createRetestSession("test-jwt-token", {
      project_id: "p-999",
      weakness_ids: ["w-12345"],
      max_questions: 1,
    });

    assert.equal(session.session_id, "s-abcde123");
    assert.equal(session.total_questions, 1);
    assert.equal(session.questions[0].question_id, "q-1");
  });

  it("submits defense and parses evaluation with weakness resolution", async () => {
    const mockEval = {
      question_id: "q-1",
      weakness_id: "w-12345",
      passed: true,
      score: 85.0,
      feedback: "Strong architectural defense.",
      key_improvements: ["PgBouncer transaction mode", "Bounded pool"],
      remaining_gaps: [],
      weakness_resolved: true,
      updated_proficiency: 65.0,
    };

    globalThis.fetch = async (url, init) => {
      assert.ok(String(url).includes("/api/v1/retest/evaluate"));
      assert.equal(init?.method, "POST");
      return new Response(JSON.stringify(mockEval), { status: 200 });
    };

    const evalRes = await submitRetestAnswer("test-jwt-token", {
      session_id: "s-abcde123",
      question_id: "q-1",
      weakness_id: "w-12345",
      candidate_response: "We deploy PgBouncer in transaction mode.",
    });

    assert.equal(evalRes.passed, true);
    assert.equal(evalRes.score, 85.0);
    assert.equal(evalRes.weakness_resolved, true);
    assert.equal(evalRes.updated_proficiency, 65.0);
  });

  it("throws descriptive error when server returns error status", async () => {
    globalThis.fetch = async () => {
      return new Response("Not Found", { status: 404 });
    };

    await assert.rejects(
      async () => {
        await fetchEligibleWeaknesses("test-jwt-token");
      },
      (err: Error) => {
        assert.ok(err.message.includes("Failed to load weaknesses (404)"));
        return true;
      }
    );
  });
});
