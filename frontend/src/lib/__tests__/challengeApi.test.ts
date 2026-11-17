import { afterEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  extractChallengeApiError,
  generateMiniChallenge,
  getChallengeForWeakness,
  submitChallengeSolution,
  validateChallengeEvaluationResponse,
  validateMiniChallengeResponse,
} from "../challengeApi";

const ORIGINAL_FETCH = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = ORIGINAL_FETCH;
});

function buildSampleChallenge(overrides: Record<string, unknown> = {}) {
  return {
    challenge_id: "c1234567-89ab-cdef-0123-456789abcdef",
    category: "scalability",
    topic: "connection_pooling",
    difficulty: "intermediate",
    title: "Database Connection Starvation",
    scenario: "Connection pool exhaustion under load.",
    starter_code: "async def handle(): pass",
    language: "python",
    requirements: ["Use connection pool", "Enforce timeout"],
    hints: ["Use asyncpg.create_pool", "Handle PoolTimeout"],
    generated_at: "2026-11-17T00:00:00Z",
    ...overrides,
  };
}

function buildSampleEvaluation(overrides: Record<string, unknown> = {}) {
  return {
    evaluation_id: "e1234567-89ab-cdef-0123-456789abcdef",
    challenge_id: "c1234567-89ab-cdef-0123-456789abcdef",
    passed: true,
    score: 88.5,
    strengths: ["Implemented acquire timeout", "Safe exception handling"],
    missing_elements: [],
    critique: "Well-structured resilient connection pooling.",
    model_solution: "async def handle(pool): pass",
    weakness_updated: true,
    evaluated_at: "2026-11-17T00:00:00Z",
    ...overrides,
  };
}

describe("challengeApi - Schema Validation", () => {
  it("validates and parses a compliant mini-challenge response", () => {
    const raw = buildSampleChallenge();
    const parsed = validateMiniChallengeResponse(raw);
    assert.equal(parsed.challenge_id, raw.challenge_id);
    assert.equal(parsed.difficulty, "intermediate");
    assert.equal(parsed.requirements.length, 2);
  });

  it("throws when challenge payload is not an object or has invalid difficulty", () => {
    assert.throws(
      () => validateMiniChallengeResponse(null),
      /Invalid mini-challenge payload: expected an object\./
    );
    assert.throws(
      () => validateMiniChallengeResponse(buildSampleChallenge({ difficulty: "super_hard" })),
      /Mini-challenge response failed runtime schema validation\./
    );
  });

  it("validates and parses a compliant challenge evaluation response", () => {
    const raw = buildSampleEvaluation();
    const parsed = validateChallengeEvaluationResponse(raw);
    assert.equal(parsed.passed, true);
    assert.equal(parsed.score, 88.5);
    assert.equal(parsed.weakness_updated, true);
  });

  it("throws when score is non-finite (NaN or Infinity)", () => {
    assert.throws(
      () => validateChallengeEvaluationResponse(buildSampleEvaluation({ score: Number.NaN })),
      /Challenge evaluation response failed runtime schema validation\./
    );
    assert.throws(
      () => validateChallengeEvaluationResponse(buildSampleEvaluation({ score: Number.POSITIVE_INFINITY })),
      /Challenge evaluation response failed runtime schema validation\./
    );
  });
});

describe("challengeApi - Error Extraction", () => {
  it("extracts detail string, validation array, and fallback status", () => {
    assert.equal(extractChallengeApiError({ detail: "Weakness not found" }, 404), "Weakness not found");
    assert.equal(
      extractChallengeApiError({ detail: [{ msg: "Field required" }] }, 422),
      "Field required"
    );
    assert.equal(extractChallengeApiError(null, 500), "Challenge API request failed with HTTP 500");
  });
});

describe("challengeApi - Network Calls", () => {
  it("calls generateMiniChallenge with auth header and parses result", async () => {
    const sample = buildSampleChallenge();
    globalThis.fetch = (async (url: RequestInfo | URL, init?: RequestInit) => {
      assert.match(String(url), /\/api\/v1\/mentor\/challenges\/generate$/);
      assert.equal(init?.method, "POST");
      const headers = init?.headers as Record<string, string>;
      assert.equal(headers.Authorization, "Bearer mock-token");
      return new Response(JSON.stringify(sample), { status: 200 });
    }) as unknown as typeof fetch;

    const res = await generateMiniChallenge("mock-token", {
      topic: "connection_pooling",
      category: "scalability",
    });
    assert.equal(res.topic, "connection_pooling");
    assert.equal(res.requirements.length, 2);
  });

  it("calls getChallengeForWeakness with encoded id", async () => {
    const sample = buildSampleChallenge();
    globalThis.fetch = (async (url: RequestInfo | URL) => {
      assert.match(String(url), /\/api\/v1\/mentor\/challenges\/weakness\/w-123/);
      return new Response(JSON.stringify(sample), { status: 200 });
    }) as unknown as typeof fetch;

    const res = await getChallengeForWeakness("mock-token", "w-123");
    assert.equal(res.challenge_id, sample.challenge_id);
  });

  it("calls submitChallengeSolution and returns evaluation", async () => {
    const sampleEval = buildSampleEvaluation();
    globalThis.fetch = (async (url: RequestInfo | URL, init?: RequestInit) => {
      assert.match(String(url), /\/api\/v1\/mentor\/challenges\/evaluate$/);
      assert.equal(init?.method, "POST");
      return new Response(JSON.stringify(sampleEval), { status: 200 });
    }) as unknown as typeof fetch;

    const res = await submitChallengeSolution("mock-token", {
      challenge_id: sampleEval.challenge_id,
      category: "scalability",
      topic: "connection_pooling",
      scenario: "Connection pool exhaustion.",
      requirements: ["Use connection pool"],
      candidate_solution: "async def handle(pool): pass",
    });
    assert.equal(res.passed, true);
    assert.equal(res.score, 88.5);
  });

  it("handles HTTP error throwing message", async () => {
    globalThis.fetch = (async () => {
      return new Response(JSON.stringify({ detail: "Topic mismatch" }), { status: 400 });
    }) as unknown as typeof fetch;

    await assert.rejects(
      async () => {
        await submitChallengeSolution("mock-token", {
          challenge_id: "c1",
          category: "scalability",
          topic: "mismatch",
          scenario: "S",
          requirements: [],
          candidate_solution: "pass",
        });
      },
      /Topic mismatch/
    );
  });
});
