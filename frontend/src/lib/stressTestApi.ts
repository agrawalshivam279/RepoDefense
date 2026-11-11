/**
 * REST API client functions for Stress Test & What-If Scaling Defense Mode.
 * Connects to FastAPI router at /api/v1/stress-test.
 */

import type {
  GenerateStressScenariosRequest,
  StartStressDefenseRequest,
  StressConstraintType,
  StressDefenseSessionState,
  StressDefenseTurn,
  StressScenarioListResponse,
  StressSessionStage,
  StressTarget,
  StressTestScenario,
  SubmitStressAnswerRequest,
} from "@/types/stressTest";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const VALID_CONSTRAINTS = new Set<string>([
  "CONCURRENCY_SPIKE",
  "DATA_VOLUME_100X",
  "MEMORY_PRESSURE",
  "NETWORK_LATENCY_JITTER",
  "DB_CONNECTION_STARVATION",
]);

const VALID_SEVERITIES = new Set<string>(["MODERATE", "SEVERE", "EXTREME"]);
const VALID_STAGES = new Set<string>([
  "SCENARIO_ACTIVE",
  "FOLLOW_UP_CONSTRAINED",
  "COMPLETED",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isStressTarget(value: unknown): value is StressTarget {
  return (
    isRecord(value) &&
    typeof value.symbol_name === "string" &&
    typeof value.file_path === "string" &&
    typeof value.line_range === "string" &&
    typeof value.component_type === "string"
  );
}

function isStressScenario(value: unknown): value is StressTestScenario {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.constraint_type === "string" &&
    VALID_CONSTRAINTS.has(value.constraint_type) &&
    typeof value.severity === "string" &&
    VALID_SEVERITIES.has(value.severity) &&
    isStressTarget(value.target) &&
    typeof value.context_description === "string" &&
    typeof value.hypothetical_prompt === "string" &&
    isStringArray(value.expected_tradeoffs) &&
    isStringArray(value.cited_evidence_ids)
  );
}

function isStressTurn(value: unknown): value is StressDefenseTurn {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.role === "string" &&
    typeof value.content === "string" &&
    typeof value.stage === "string" &&
    VALID_STAGES.has(value.stage) &&
    typeof value.timestamp === "string" &&
    isRecord(value.metadata)
  );
}

function validateScenarioListResponse(
  payload: unknown
): StressScenarioListResponse {
  if (
    !isRecord(payload) ||
    typeof payload.project_id !== "string" ||
    typeof payload.total_scenarios !== "number" ||
    !Array.isArray(payload.scenarios) ||
    !payload.scenarios.every(isStressScenario)
  ) {
    throw new Error("Invalid scaling scenario catalog response from server");
  }
  return {
    project_id: payload.project_id,
    total_scenarios: payload.total_scenarios,
    scenarios: payload.scenarios,
  };
}

function validateStressSessionState(
  payload: unknown
): StressDefenseSessionState {
  if (
    !isRecord(payload) ||
    typeof payload.session_id !== "string" ||
    typeof payload.project_id !== "string" ||
    !isStressScenario(payload.scenario) ||
    typeof payload.stage !== "string" ||
    !VALID_STAGES.has(payload.stage) ||
    typeof payload.current_turn_index !== "number" ||
    !Array.isArray(payload.turns) ||
    !payload.turns.every(isStressTurn) ||
    typeof payload.created_at !== "string" ||
    typeof payload.updated_at !== "string"
  ) {
    throw new Error("Invalid stress defense session response from server");
  }
  return {
    session_id: payload.session_id,
    project_id: payload.project_id,
    scenario: payload.scenario,
    stage: payload.stage as StressSessionStage,
    current_turn_index: payload.current_turn_index,
    turns: payload.turns,
    overall_score:
      typeof payload.overall_score === "number" || payload.overall_score === null
        ? payload.overall_score
        : undefined,
    bottleneck_identified:
      typeof payload.bottleneck_identified === "boolean" ||
      payload.bottleneck_identified === null
        ? payload.bottleneck_identified
        : undefined,
    feedback:
      typeof payload.feedback === "string" || payload.feedback === null
        ? payload.feedback
        : undefined,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
  };
}

async function parseApiError(
  response: Response,
  defaultMessage: string
): Promise<string> {
  try {
    const errorData: unknown = await response.json();
    if (isRecord(errorData)) {
      if (typeof errorData.detail === "string") {
        return errorData.detail;
      }
      if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
        const firstIssue: unknown = errorData.detail[0];
        if (isRecord(firstIssue) && typeof firstIssue.msg === "string") {
          return firstIssue.msg;
        }
      }
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
  defaultError: string,
  validate: (payload: unknown) => T
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

  const data: unknown = await response.json();
  return validate(data);
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
    "Failed to fetch scaling stress scenarios",
    validateScenarioListResponse
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
    "Failed to start stress defense session",
    validateStressSessionState
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
    "Failed to retrieve stress defense session",
    validateStressSessionState
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
    "Failed to submit scaling defense response",
    validateStressSessionState
  );
}
