/**
 * REST API client functions for PR-scoped defense sessions and diff-grounded interview flow.
 * Connects to FastAPI router at /api/v1/pr-defense.
 */

import type { PRDefenseSessionState } from "@/types/prDefense";

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
 * Initiates a new PR-scoped defense session by fetching the GitHub PR diff,
 * parsing file changes, and synthesizing diff-grounded interview questions.
 */
export async function startPRDefenseSession(
  projectId: string,
  prUrl: string,
  token: string,
  numQuestions: number = 3
): Promise<PRDefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/pr-defense/projects/${projectId}/start`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        pr_url: prUrl,
        num_questions: numQuestions,
      }),
    }
  );

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to start PR defense session"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Retrieves the current state of a PR defense session, including active
 * questions, turns transcript, and current stage.
 */
export async function getPRDefenseSession(
  sessionId: string,
  token: string
): Promise<PRDefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/pr-defense/sessions/${sessionId}`,
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
      "Failed to retrieve PR defense session"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Submits a candidate's architectural defense or response to pushback/stress-test
 * for the current diff-grounded question.
 */
export async function submitPRDefenseAnswer(
  sessionId: string,
  answer: string,
  token: string
): Promise<PRDefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/pr-defense/sessions/${sessionId}/answer`,
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
      "Failed to submit PR defense answer"
    );
    throw new Error(message);
  }

  return response.json();
}
