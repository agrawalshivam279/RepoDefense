/**
 * REST API client functions for Stress Test & What-If Scaling Defense Mode.
 * Connects to FastAPI router at /api/v1/stress-test.
 */

import type {
  GenerateStressScenariosRequest,
  StartStressDefenseRequest,
  StressConstraintType,
  StressDefenseSessionState,
  StressScenarioListResponse,
  SubmitStressAnswerRequest,
} from "@/types/stressTest";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function parseApiError(
  response: Response,
  defaultMessage: string
): Promise<string> {
  try {
    const errorData = await response.json();
    if (typeof errorData?.detail === "string") {
      return errorData.detail;
    }
    if (Array.isArray(errorData?.detail) && errorData.detail[0]?.msg) {
      return errorData.detail[0].msg;
    }
  } catch {
    // Non-JSON error payload
  }
  return `${defaultMessage} (Status ${response.status})`;
}

async function requestStressApi<T>(
  path: string,
  token: string,
  options: { method: "GET" | "POST"; body?: unknown },
  defaultError: string
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}/api/v1/stress-test${path}`, {
    method: options.method,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, defaultError));
  }

  return response.json() as Promise<T>;
}

/**
 * Generates or retrieves catalog of grounded scaling stress test scenarios.
 */
export async function fetchStressScenarios(
  projectId: string,
  token: string,
  constraintType?: StressConstraintType,
  maxScenarios: number = 5
): Promise<StressScenarioListResponse> {
  const payload: GenerateStressScenariosRequest = {
    constraint_type: constraintType || null,
    max_scenarios: maxScenarios,
  };
  return requestStressApi<StressScenarioListResponse>(
    `/projects/${projectId}/scenarios`,
    token,
    { method: "POST", body: payload },
    "Failed to fetch scaling stress scenarios"
  );
}

/**
 * Initiates an interactive scaling defense session for a chosen scenario.
 */
export async function startStressSession(
  projectId: string,
  scenarioId: string,
  token: string
): Promise<StressDefenseSessionState> {
  const payload: StartStressDefenseRequest = { scenario_id: scenarioId };
  return requestStressApi<StressDefenseSessionState>(
    `/projects/${projectId}/sessions/start`,
    token,
    { method: "POST", body: payload },
    "Failed to start stress defense session"
  );
}

/**
 * Retrieves an active or completed stress defense session state.
 */
export async function getStressSession(
  sessionId: string,
  token: string
): Promise<StressDefenseSessionState> {
  return requestStressApi<StressDefenseSessionState>(
    `/sessions/${sessionId}`,
    token,
    { method: "GET" },
    "Failed to retrieve stress defense session"
  );
}

/**
 * Submits candidate architectural scaling defense for evaluation.
 */
export async function submitStressAnswer(
  sessionId: string,
  answer: string,
  token: string
): Promise<StressDefenseSessionState> {
  const payload: SubmitStressAnswerRequest = { answer };
  return requestStressApi<StressDefenseSessionState>(
    `/sessions/${sessionId}/respond`,
    token,
    { method: "POST", body: payload },
    "Failed to submit scaling defense response"
  );
}
