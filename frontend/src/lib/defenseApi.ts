import type { DefenseSessionState } from "@/types/defense";
import type { EvidenceItem } from "@/types/evidence";
import type {
  DefenseReportResponse,
  EnhancedDefenseReportResponse,
} from "@/types/report";

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
 * Initializes a new evidence-grounded defense session for a repository.
 */
export async function startDefenseSession(
  projectId: string,
  token: string,
  numQuestions: number = 3
): Promise<DefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/projects/${projectId}/defense/start`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        num_questions: numQuestions,
      }),
    }
  );

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to start defense session"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Submits candidate defense or stress-test answer to the interview state machine.
 */
export async function submitDefenseAnswer(
  sessionId: string,
  answer: string,
  token: string
): Promise<DefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/defense/sessions/${sessionId}/turn`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        answer,
      }),
    }
  );

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to submit defense answer"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Retrieves the current state of a defense interview session.
 */
export async function getDefenseSession(
  sessionId: string,
  token: string
): Promise<DefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/defense/sessions/${sessionId}`,
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
      "Failed to retrieve defense session"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Retrieves load-bearing evidence items for a project repository.
 */
export async function getProjectEvidence(
  projectId: string,
  token: string
): Promise<EvidenceItem[]> {
  const response = await fetch(
    `${API_BASE}/api/v1/projects/${projectId}/evidence`,
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
      "Failed to retrieve project evidence"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Fetches the synthesized evaluation report for a completed defense session.
 */
export async function getDefenseReport(
  sessionId: string,
  token: string
): Promise<DefenseReportResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/defense/sessions/${sessionId}/report`,
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
      "Failed to retrieve defense report"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Fetches the enhanced evaluation report (including architecture topology and tech audit).
 */
export async function getEnhancedDefenseReport(
  sessionId: string,
  token: string
): Promise<EnhancedDefenseReportResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/defense/sessions/${sessionId}/enhanced-report`,
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
      "Failed to retrieve enhanced defense report"
    );
    throw new Error(message);
  }

  return response.json();
}
