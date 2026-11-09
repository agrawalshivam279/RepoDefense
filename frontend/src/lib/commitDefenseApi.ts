/**
 * REST API client functions for Git Commit-scoped defense sessions and diff-grounded interview flow.
 * Connects to FastAPI router at /api/v1/commit-defense.
 */

import type {
  CommitAnalysisResponse,
  CommitDefenseSessionState,
} from "@/types/commitDefense";

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
 * Initiates a new Git Commit-scoped defense session by fetching the commit diff,
 * parsing file changes, and synthesizing diff-grounded interview questions.
 */
export async function startCommitDefenseSession(
  projectId: string,
  commitUrlOrHash: string,
  token: string,
  numQuestions: number = 3
): Promise<CommitDefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/commit-defense/projects/${projectId}/start`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        commit_url_or_hash: commitUrlOrHash,
        num_questions: numQuestions,
      }),
    }
  );

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to start commit defense session"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Retrieves the current state of a commit defense session, including active
 * questions, turns transcript, and current stage.
 */
export async function getCommitDefenseSession(
  sessionId: string,
  token: string
): Promise<CommitDefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/commit-defense/sessions/${sessionId}`,
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
      "Failed to retrieve commit defense session"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Submits a candidate's architectural defense or response to pushback/stress-test
 * for the current commit diff-grounded question.
 */
export async function submitCommitDefenseAnswer(
  sessionId: string,
  answer: string,
  token: string
): Promise<CommitDefenseSessionState> {
  const response = await fetch(
    `${API_BASE}/api/v1/commit-defense/sessions/${sessionId}/answer`,
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
      "Failed to submit commit defense answer"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Inspects a Git commit and returns parsed diff hunks and file change statistics
 * without initiating an interview session.
 */
export async function analyzeCommitDiff(
  projectId: string,
  commitUrlOrHash: string,
  token: string
): Promise<CommitAnalysisResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/commit-defense/projects/${projectId}/analyze`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ commit_url_or_hash: commitUrlOrHash }),
    }
  );

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to analyze commit diff"
    );
    throw new Error(message);
  }

  return response.json();
}
