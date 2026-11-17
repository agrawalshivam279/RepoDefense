/**
 * REST API client for Mentor Mode teaching content and code remediation.
 * Connects to /api/v1/mentor endpoints with runtime unknown-narrowing validation.
 */

import type {
  CodeRemediationSnippet,
  MentorExplanationRequest,
  MentorExplanationResponse,
} from "@/types/mentor";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSnippet(value: unknown): value is CodeRemediationSnippet {
  return (
    isRecord(value) &&
    typeof value.title === "string" &&
    typeof value.language === "string" &&
    (value.file_context === undefined ||
      value.file_context === null ||
      typeof value.file_context === "string") &&
    typeof value.before_code === "string" &&
    typeof value.after_code === "string" &&
    typeof value.explanation === "string"
  );
}

export function validateMentorExplanationResponse(
  payload: unknown
): MentorExplanationResponse {
  if (!isRecord(payload)) {
    throw new Error("Invalid mentor explanation payload: expected an object.");
  }

  const valid =
    typeof payload.explanation_id === "string" &&
    typeof payload.category === "string" &&
    typeof payload.topic === "string" &&
    typeof payload.architectural_risk === "string" &&
    typeof payload.core_concept === "string" &&
    typeof payload.mentor_advice === "string" &&
    typeof payload.socratic_followup === "string" &&
    typeof payload.generated_at === "string" &&
    Array.isArray(payload.key_takeaways) &&
    payload.key_takeaways.every((item) => typeof item === "string") &&
    Array.isArray(payload.code_examples) &&
    payload.code_examples.every(isSnippet);

  if (!valid) {
    throw new Error("Mentor explanation response failed runtime schema validation.");
  }

  return payload as unknown as MentorExplanationResponse;
}

export function extractApiErrorDetail(body: unknown, status: number): string {
  if (isRecord(body)) {
    if (typeof body.detail === "string" && body.detail.trim()) {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const first = body.detail[0];
      if (isRecord(first) && typeof first.msg === "string") {
        return first.msg;
      }
    }
  }
  return `Mentor API request failed with HTTP ${status}`;
}

async function requestMentorApi<T>(
  path: string,
  token: string,
  options: {
    method: "GET" | "POST";
    body?: unknown;
    signal?: AbortSignal;
  },
  validator: (data: unknown) => T
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  const rawJson: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const errorDetail = extractApiErrorDetail(rawJson, response.status);
    throw new Error(errorDetail);
  }

  return validator(rawJson);
}

/**
 * Request pedagogical mentor guidance and drop-in code remediation for a topic or weakness ID.
 */
export async function explainWeaknessOrTopic(
  token: string,
  request: MentorExplanationRequest,
  signal?: AbortSignal
): Promise<MentorExplanationResponse> {
  return requestMentorApi<MentorExplanationResponse>(
    "/api/v1/mentor/explain",
    token,
    { method: "POST", body: request, signal },
    validateMentorExplanationResponse
  );
}

/**
 * Fetch mentor guidance directly for an existing recorded weakness.
 */
export async function getExplanationForWeakness(
  token: string,
  weaknessId: string,
  language: string = "python",
  signal?: AbortSignal
): Promise<MentorExplanationResponse> {
  const query = `?language=${encodeURIComponent(Array.from(language).slice(0, 32).join(""))}`;
  return requestMentorApi<MentorExplanationResponse>(
    `/api/v1/mentor/explanations/${encodeURIComponent(weaknessId)}${query}`,
    token,
    { method: "GET", signal },
    validateMentorExplanationResponse
  );
}
