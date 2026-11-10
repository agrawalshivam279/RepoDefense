/**
 * REST API client functions for Chaos Engineering & Incident Simulation War Room.
 * Connects to FastAPI router at /api/v1/incident-simulation.
 */

import type {
  FailureCategory,
  IncidentDefenseSessionState,
  ScenarioListResponse,
} from "@/types/incident";

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

/**
 * Generates or retrieves catalog of hypothetical chaos incident scenarios
 * grounded in the project's code symbols and dependencies.
 */
export async function fetchProjectScenarios(
  projectId: string,
  token: string,
  category?: FailureCategory,
  limit: number = 3
): Promise<ScenarioListResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/incident-simulation/projects/${projectId}/scenarios`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        category: category || null,
        limit,
      }),
    }
  );

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to fetch chaos scenarios"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Initiates an interactive incident defense session in the War Room.
 */
export async function startIncidentSession(
  projectId: string,
  token: string,
  scenarioId?: string,
  category?: FailureCategory
): Promise<IncidentDefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/incident-simulation/projects/${projectId}/sessions/start`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        scenario_id: scenarioId || null,
        category: category || null,
      }),
    }
  );

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to launch incident defense session"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Retrieves active incident defense session state by session ID.
 */
export async function getIncidentSession(
  sessionId: string,
  token: string
): Promise<IncidentDefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/incident-simulation/sessions/${sessionId}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to retrieve incident session state"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Submits candidate defense mitigation or triage answer for the active turn.
 */
export async function submitIncidentAnswer(
  sessionId: string,
  answer: string,
  token: string
): Promise<IncidentDefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/incident-simulation/sessions/${sessionId}/respond`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ answer }),
    }
  );

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to submit incident defense response"
    );
    throw new Error(message);
  }

  return response.json();
}
