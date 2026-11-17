/**
 * REST API client for Mentor Mode Mini Challenges.
 * Connects to /api/v1/mentor/challenges endpoints with runtime unknown-narrowing validation.
 */

import type {
  ChallengeEvaluationResponse,
  GenerateChallengeRequest,
  MiniChallengeDifficulty,
  MiniChallengeResponse,
  SubmitChallengeSolutionRequest,
} from "@/types/challenge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

const VALID_DIFFICULTIES: MiniChallengeDifficulty[] = [
  "foundational",
  "intermediate",
  "advanced",
];

export function validateMiniChallengeResponse(payload: unknown): MiniChallengeResponse {
  if (!isRecord(payload)) {
    throw new Error("Invalid mini-challenge payload: expected an object.");
  }

  const valid =
    typeof payload.challenge_id === "string" &&
    typeof payload.category === "string" &&
    typeof payload.topic === "string" &&
    VALID_DIFFICULTIES.includes(payload.difficulty as MiniChallengeDifficulty) &&
    typeof payload.title === "string" &&
    typeof payload.scenario === "string" &&
    (payload.starter_code === undefined ||
      payload.starter_code === null ||
      typeof payload.starter_code === "string") &&
    typeof payload.language === "string" &&
    Array.isArray(payload.requirements) &&
    payload.requirements.every((r) => typeof r === "string") &&
    Array.isArray(payload.hints) &&
    payload.hints.every((h) => typeof h === "string") &&
    typeof payload.generated_at === "string";

  if (!valid) {
    throw new Error("Mini-challenge response failed runtime schema validation.");
  }

  return payload as unknown as MiniChallengeResponse;
}

export function validateChallengeEvaluationResponse(
  payload: unknown
): ChallengeEvaluationResponse {
  if (!isRecord(payload)) {
    throw new Error("Invalid challenge evaluation payload: expected an object.");
  }

  const valid =
    typeof payload.evaluation_id === "string" &&
    typeof payload.challenge_id === "string" &&
    typeof payload.passed === "boolean" &&
    typeof payload.score === "number" &&
    Number.isFinite(payload.score) &&
    Array.isArray(payload.strengths) &&
    payload.strengths.every((s) => typeof s === "string") &&
    Array.isArray(payload.missing_elements) &&
    payload.missing_elements.every((m) => typeof m === "string") &&
    typeof payload.critique === "string" &&
    typeof payload.model_solution === "string" &&
    typeof payload.weakness_updated === "boolean" &&
    typeof payload.evaluated_at === "string";

  if (!valid) {
    throw new Error("Challenge evaluation response failed runtime schema validation.");
  }

  return payload as unknown as ChallengeEvaluationResponse;
}

export function extractChallengeApiError(body: unknown, status: number): string {
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
  return `Challenge API request failed with HTTP ${status}`;
}

async function requestChallengeApi<T>(
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
    const errorDetail = extractChallengeApiError(rawJson, response.status);
    throw new Error(errorDetail);
  }

  return validator(rawJson);
}

/**
 * Generate an architectural mini-challenge grounded in a topic or weakness ID.
 */
export async function generateMiniChallenge(
  token: string,
  request: GenerateChallengeRequest,
  signal?: AbortSignal
): Promise<MiniChallengeResponse> {
  return requestChallengeApi<MiniChallengeResponse>(
    "/api/v1/mentor/challenges/generate",
    token,
    { method: "POST", body: request, signal },
    validateMiniChallengeResponse
  );
}

/**
 * Fetch a mini-challenge directly generated from an authenticated user's weakness.
 */
export async function getChallengeForWeakness(
  token: string,
  weaknessId: string,
  language: string = "python",
  signal?: AbortSignal
): Promise<MiniChallengeResponse> {
  const query = `?language=${encodeURIComponent(Array.from(language).slice(0, 32).join(""))}`;
  return requestChallengeApi<MiniChallengeResponse>(
    `/api/v1/mentor/challenges/weakness/${encodeURIComponent(weaknessId)}${query}`,
    token,
    { method: "GET", signal },
    validateMiniChallengeResponse
  );
}

/**
 * Submit candidate's code solution for evaluation by the Principal Engineer persona.
 */
export async function submitChallengeSolution(
  token: string,
  request: SubmitChallengeSolutionRequest,
  signal?: AbortSignal
): Promise<ChallengeEvaluationResponse> {
  return requestChallengeApi<ChallengeEvaluationResponse>(
    "/api/v1/mentor/challenges/evaluate",
    token,
    { method: "POST", body: request, signal },
    validateChallengeEvaluationResponse
  );
}
