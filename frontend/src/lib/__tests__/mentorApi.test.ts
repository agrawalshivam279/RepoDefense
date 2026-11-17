import { afterEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  explainWeaknessOrTopic,
  extractApiErrorDetail,
  getExplanationForWeakness,
  validateMentorExplanationResponse,
} from "../mentorApi";

const ORIGINAL_FETCH = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = ORIGINAL_FETCH;
});

function buildSampleExplanation(overrides: Record<string, unknown> = {}) {
  return {
    explanation_id: "exp-123",
    category: "concurrency",
    topic: "race_condition_locks",
    architectural_risk: "Read-modify-write lost update risk.",
    core_concept: "Optimistic Concurrency Control",
    mentor_advice: "Protect mutations with atomic expressions or locks.",
    code_examples: [
      {
        title: "Atomic Update Remediation",
        language: "python",
        file_context: "backend/app/services/counter.py",
        before_code: "item.count += 1",
        after_code: "stmt = update(Item).values(count=Item.count + 1)",
        explanation: "Delegates atomicity to the database.",
      },
    ],
    key_takeaways: ["Never read-modify-write without protection."],
    socratic_followup: "How would you handle contention under high write loads?",
    generated_at: "2026-11-17T00:00:00Z",
    ...overrides,
  };
}

describe("mentorApi - Schema Validation", () => {
  it("validates and parses a compliant mentor explanation response", () => {
    const raw = buildSampleExplanation();
    const parsed = validateMentorExplanationResponse(raw);
    assert.equal(parsed.explanation_id, "exp-123");
    assert.equal(parsed.topic, "race_condition_locks");
    assert.equal(parsed.code_examples.length, 1);
    assert.equal(parsed.code_examples[0].title, "Atomic Update Remediation");
  });

  it("throws when payload is not an object", () => {
    assert.throws(
      () => validateMentorExplanationResponse(null),
      /Invalid mentor explanation payload: expected an object\./
    );
    assert.throws(
      () => validateMentorExplanationResponse("string"),
      /Invalid mentor explanation payload: expected an object\./
    );
  });

  it("throws when required string fields are missing", () => {
    const raw = buildSampleExplanation({ topic: 123 });
    assert.throws(
      () => validateMentorExplanationResponse(raw),
      /Mentor explanation response failed runtime schema validation\./
    );
  });

  it("throws when code_examples has invalid snippet structure", () => {
    const raw = buildSampleExplanation({
      code_examples: [{ title: "Broken", before_code: 42 }],
    });
    assert.throws(
      () => validateMentorExplanationResponse(raw),
      /Mentor explanation response failed runtime schema validation\./
    );
  });

  it("throws when key_takeaways contains non-strings", () => {
    const raw = buildSampleExplanation({
      key_takeaways: [123],
    });
    assert.throws(
      () => validateMentorExplanationResponse(raw),
      /Mentor explanation response failed runtime schema validation\./
    );
  });
});

describe("mentorApi - Error Detail Extraction", () => {
  it("extracts string detail message", () => {
    const detail = extractApiErrorDetail({ detail: "Weakness not found" }, 404);
    assert.equal(detail, "Weakness not found");
  });

  it("extracts Pydantic array validation error message", () => {
    const detail = extractApiErrorDetail(
      { detail: [{ msg: "Field required", loc: ["topic"] }] },
      422
    );
    assert.equal(detail, "Field required");
  });

  it("falls back to generic HTTP status description when detail is absent", () => {
    const detail = extractApiErrorDetail(null, 500);
    assert.equal(detail, "Mentor API request failed with HTTP 500");
  });
});

describe("mentorApi - HTTP Client Endpoints", () => {
  it("explainWeaknessOrTopic executes POST with Authorization header and parses result", async () => {
    let capturedUrl = "";
    let capturedMethod = "";
    let capturedHeaders: Record<string, string> = {};
    let capturedBody = "";

    globalThis.fetch = async (input, init) => {
      capturedUrl = String(input);
      capturedMethod = init?.method || "";
      capturedHeaders = (init?.headers || {}) as Record<string, string>;
      capturedBody = String(init?.body || "");

      return new Response(JSON.stringify(buildSampleExplanation()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    };

    const res = await explainWeaknessOrTopic("test-jwt-token", {
      category: "concurrency",
      topic: "race_condition_locks",
    });

    assert.ok(capturedUrl.endsWith("/api/v1/mentor/explain"));
    assert.equal(capturedMethod, "POST");
    assert.equal(capturedHeaders.Authorization, "Bearer test-jwt-token");
    assert.ok(capturedBody.includes("race_condition_locks"));
    assert.equal(res.topic, "race_condition_locks");
  });

  it("getExplanationForWeakness executes GET with query param and URL encoding", async () => {
    let capturedUrl = "";
    let capturedHeaders: Record<string, string> = {};

    globalThis.fetch = async (input, init) => {
      capturedUrl = String(input);
      capturedHeaders = (init?.headers || {}) as Record<string, string>;

      return new Response(JSON.stringify(buildSampleExplanation()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    };

    const res = await getExplanationForWeakness("test-token", "w-123", "python");

    assert.ok(capturedUrl.includes("/api/v1/mentor/explanations/w-123?language=python"));
    assert.equal(capturedHeaders.Authorization, "Bearer test-token");
    assert.equal(res.explanation_id, "exp-123");
  });

  it("throws formatted error when server responds with non-200 code", async () => {
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ detail: "Weakness record not found or access denied." }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });

    await assert.rejects(
      async () => getExplanationForWeakness("test-token", "missing-id"),
      /Weakness record not found or access denied\./
    );
  });
});
