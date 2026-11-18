/**
 * REST API client for Targeted Re-Testing in Next.js 15.
 * Connects to /api/v1/retest endpoints with type validation and error handling.
 */

import type {
  EligibleWeaknessItem,
  EligibleWeaknessesResponse,
  RetestEvaluationResponse,
  RetestQuestion,
  SubmitRetestAnswerRequest,
  TargetedRetestSessionCreate,
  TargetedRetestSessionResponse,
} from "@/types/retest";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function isRecord(val: unknown): val is Record<string, unknown> {
  return typeof val === "object" && val !== null && !Array.isArray(val);
}

function parseEligibleItem(raw: unknown): EligibleWeaknessItem {
  if (!isRecord(raw) || typeof raw.id !== "string") {
    throw new Error("Invalid weakness item payload");
  }
  return {
    id: raw.id,
    project_id: typeof raw.project_id === "string" ? raw.project_id : null,
    category: typeof raw.category === "string" ? raw.category : "general",
    topic: typeof raw.topic === "string" ? raw.topic : "unknown",
    severity: typeof raw.severity === "string" ? raw.severity : "minor",
    original_prompt: typeof raw.original_prompt === "string" ? raw.original_prompt : "",
    feedback: typeof raw.feedback === "string" ? raw.feedback : "",
    created_at: typeof raw.created_at === "string" ? raw.created_at : new Date().toISOString(),
  };
}

function parseRetestQuestion(raw: unknown): RetestQuestion {
  if (!isRecord(raw) || typeof raw.question_id !== "string") {
    throw new Error("Invalid retest question payload");
  }
  return {
    question_id: raw.question_id,
    weakness_id: typeof raw.weakness_id === "string" ? raw.weakness_id : "",
    category: typeof raw.category === "string" ? raw.category : "general",
    topic: typeof raw.topic === "string" ? raw.topic : "",
    severity: typeof raw.severity === "string" ? raw.severity : "minor",
    original_prompt: typeof raw.original_prompt === "string" ? raw.original_prompt : "",
    question_text: typeof raw.question_text === "string" ? raw.question_text : "",
    architectural_constraint: typeof raw.architectural_constraint === "string" ? raw.architectural_constraint : "",
    evaluation_rubric: typeof raw.evaluation_rubric === "string" ? raw.evaluation_rubric : "",
  };
}

export async function fetchEligibleWeaknesses(
  token: string,
  projectId?: string,
  category?: string
): Promise<EligibleWeaknessesResponse> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (category) params.set("category", category);

  const qs = params.toString();
  const url = `${API_BASE}/api/v1/retest/weaknesses${qs ? `?${qs}` : ""}`;

  const res = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`Failed to load weaknesses (${res.status}): ${errorBody}`);
  }

  const json: unknown = await res.json();
  if (!isRecord(json) || !Array.isArray(json.weaknesses)) {
    throw new Error("Invalid response format from weaknesses endpoint");
  }

  return {
    total_eligible: typeof json.total_eligible === "number" ? json.total_eligible : 0,
    weaknesses: json.weaknesses.map(parseEligibleItem),
  };
}

export async function createRetestSession(
  token: string,
  payload: TargetedRetestSessionCreate
): Promise<TargetedRetestSessionResponse> {
  const url = `${API_BASE}/api/v1/retest/session`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`Failed to create re-test session (${res.status}): ${errorBody}`);
  }

  const json: unknown = await res.json();
  if (!isRecord(json) || !Array.isArray(json.questions)) {
    throw new Error("Invalid response format from session creation endpoint");
  }

  return {
    session_id: String(json.session_id || ""),
    user_id: String(json.user_id || ""),
    project_id: typeof json.project_id === "string" ? json.project_id : null,
    total_questions: typeof json.total_questions === "number" ? json.total_questions : 0,
    questions: json.questions.map(parseRetestQuestion),
    created_at: typeof json.created_at === "string" ? json.created_at : new Date().toISOString(),
  };
}

export async function submitRetestAnswer(
  token: string,
  payload: SubmitRetestAnswerRequest
): Promise<RetestEvaluationResponse> {
  const url = `${API_BASE}/api/v1/retest/evaluate`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`Failed to evaluate re-test answer (${res.status}): ${errorBody}`);
  }

  const json: unknown = await res.json();
  if (!isRecord(json)) {
    throw new Error("Invalid response from evaluate endpoint");
  }

  return {
    question_id: String(json.question_id || ""),
    weakness_id: String(json.weakness_id || ""),
    passed: Boolean(json.passed),
    score: typeof json.score === "number" ? json.score : 0,
    feedback: String(json.feedback || ""),
    key_improvements: Array.isArray(json.key_improvements)
      ? json.key_improvements.map((s) => String(s))
      : [],
    remaining_gaps: Array.isArray(json.remaining_gaps)
      ? json.remaining_gaps.map((s) => String(s))
      : [],
    weakness_resolved: Boolean(json.weakness_resolved),
    updated_proficiency: typeof json.updated_proficiency === "number" ? json.updated_proficiency : null,
  };
}
