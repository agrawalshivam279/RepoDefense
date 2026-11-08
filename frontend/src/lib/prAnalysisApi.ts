import type { ParsedFileDiff, PRAnalysisResponse } from "@/types/prAnalysis";

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
    // Non-JSON response
  }
  return `${defaultMessage} (Status ${response.status})`;
}

/**
 * Ingests a GitHub Pull Request URL, fetches its diff via the backend GitHub client,
 * and returns structured diff hunks and file change metrics.
 */
export async function analyzeProjectPR(
  projectId: string,
  prUrl: string,
  token: string
): Promise<PRAnalysisResponse> {
  const url = `${API_BASE}/api/v1/pr/projects/${projectId}/analyze`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ pr_url: prUrl }),
  });

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to analyze GitHub Pull Request"
    );
    throw new Error(message);
  }

  return response.json();
}

/**
 * Parses raw unified diff patch stream directly into structured file diff records and hunks.
 */
export async function parseRawDiff(
  diffText: string
): Promise<ParsedFileDiff[]> {
  const url = `${API_BASE}/api/v1/pr/parse-diff`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ diff_text: diffText }),
  });

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to parse raw unified diff"
    );
    throw new Error(message);
  }

  return response.json();
}
