import { afterEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  fetchArchDefenseTopics,
  getArchDefenseSession,
  startArchDefenseSession,
  submitArchDefenseTurn,
} from "../archDefenseApi";

const ORIGINAL_FETCH = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = ORIGINAL_FETCH;
});

function buildSampleTopic() {
  return {
    id: "topic-1",
    title: "Modular Monolith Boundary Isolation",
    focus_area: "COMPONENT_BOUNDARY",
    pattern_name: "Modular Monolith",
    severity_or_confidence: "HIGH",
    target_nodes: [
      {
        node_id: "api_gw",
        label: "FastAPI Router",
        node_type: "backend",
        subgraph: "app/api",
        connected_edges: ["FastAPI Router -> AuthService"],
      },
    ],
    design_claim: "Routers delegate business logic exclusively to typed service modules.",
    interrogation_prompt: "Why isolate routers from SQLAlchemy models directly?",
    expected_tradeoffs: ["Extra mapping boilerplate vs testability"],
    risk_references: ["Tight coupling across domain boundaries"],
  };
}

function buildSampleSession(stage = "TOPIC_ACTIVE") {
  return {
    session_id: "sess-123",
    project_id: "proj/1",
    topic: buildSampleTopic(),
    mermaid_code: "flowchart TD\n  A[API] --> B[Service]",
    diagram_summary: "Two-tier service topology",
    primary_pattern_name: "Modular Monolith",
    stage,
    current_turn_index: 0,
    turns: [
      {
        id: "turn-1",
        role: "interviewer",
        content: "Defend the router-service boundary.",
        stage,
        timestamp: "2026-11-12T10:00:00Z",
        metadata: {},
      },
    ],
    overall_score: stage === "COMPLETED" ? 9 : null,
    pattern_rationale_solid: stage === "COMPLETED" ? true : null,
    boundary_coherence_score: stage === "COMPLETED" ? 8 : null,
    feedback: stage === "COMPLETED" ? "Strong boundary defense." : null,
    created_at: "2026-11-12T10:00:00Z",
    updated_at: "2026-11-12T10:01:00Z",
  };
}

describe("archDefenseApi", () => {
  it("fetchArchDefenseTopics posts validated request and parses topic catalog", async () => {
    let capturedUrl = "";
    let capturedInit: RequestInit | undefined;
    const ac = new AbortController();

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = String(input);
      capturedInit = init;
      return new Response(
        JSON.stringify({
          project_id: "proj/1",
          project_name: "RepoDefense",
          primary_pattern: { pattern_name: "Modular Monolith", confidence_score: 0.92, tier: "Primary" },
          diagram_type: "flowchart TD",
          mermaid_code: "flowchart TD\n  A --> B",
          nodes: [{ node_id: "A", label: "API", node_type: "backend" }],
          edges: [{ source_id: "A", target_id: "B" }],
          is_diagram_fallback: false,
          total_topics: 1,
          topics: [buildSampleTopic()],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }) as typeof fetch;

    const result = await fetchArchDefenseTopics("proj/1", "tok-abc", "COMPONENT_BOUNDARY", 6, ac.signal);
    assert.match(capturedUrl, /\/api\/v1\/arch-defense\/projects\/proj%2F1\/topics$/);
    assert.equal(capturedInit?.method, "POST");
    assert.equal(capturedInit?.signal, ac.signal);
    assert.equal(capturedInit?.body, JSON.stringify({ focus_area: "COMPONENT_BOUNDARY", max_topics: 6 }));
    assert.equal(result.topics.length, 1);
    assert.equal(result.primary_pattern.pattern_name, "Modular Monolith");
  });

  it("fetchArchDefenseTopics rejects malformed topic payloads", async () => {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ project_id: "p1", topics: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })) as typeof fetch;

    await assert.rejects(
      () => fetchArchDefenseTopics("p1", "tok"),
      /Malformed architecture defense topic catalog payload/
    );
  });

  it("startArchDefenseSession validates session response and surfaces string HTTP detail", async () => {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ detail: "Topic not found for project" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      })) as typeof fetch;

    await assert.rejects(() => startArchDefenseSession("p1", "missing", "tok"), /Topic not found for project/);

    globalThis.fetch = (async () =>
      new Response(JSON.stringify(buildSampleSession("TOPIC_ACTIVE")), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })) as typeof fetch;

    const session = await startArchDefenseSession("p1", "topic-1", "tok");
    assert.equal(session.session_id, "sess-123");
    assert.equal(session.stage, "TOPIC_ACTIVE");
  });

  it("getArchDefenseSession propagates AbortSignal and URL-encodes sessionId", async () => {
    let capturedUrl = "";
    const ac = new AbortController();
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = String(input);
      assert.equal(init?.method, "GET");
      assert.equal(init?.signal, ac.signal);
      return new Response(JSON.stringify(buildSampleSession("TRADEOFF_CHALLENGE")), { status: 200 });
    }) as typeof fetch;

    const session = await getArchDefenseSession("sess/42", "tok", ac.signal);
    assert.match(capturedUrl, /\/api\/v1\/arch-defense\/sessions\/sess%2F42$/);
    assert.equal(session.stage, "TRADEOFF_CHALLENGE");
  });

  it("submitArchDefenseTurn handles 422 array errors and rejects invalid stage values", async () => {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ detail: [{ msg: "String should have at least 1 character" }] }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      })) as typeof fetch;

    await assert.rejects(() => submitArchDefenseTurn("sess-123", "", "tok"), /String should have at least 1 character/);

    globalThis.fetch = (async () =>
      new Response(JSON.stringify(buildSampleSession("INVALID_STAGE")), { status: 200 })) as typeof fetch;

    await assert.rejects(
      () => submitArchDefenseTurn("sess-123", "Because boundaries matter.", "tok"),
      /Malformed architecture defense session payload/
    );
  });
});
