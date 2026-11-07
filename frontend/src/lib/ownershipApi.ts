import type { ProjectOwnershipReport } from "@/types/ownership";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function parseApiError(response: Response, defaultMessage: string): Promise<string> {
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
 * Retrieves git code ownership metrics, symbol attribution, and contributor breakdowns.
 */
export async function getProjectOwnership(
  projectId: string,
  token: string,
  candidateEmail?: string
): Promise<ProjectOwnershipReport> {
  let url = `${API_BASE}/api/v1/projects/${projectId}/ownership`;
  if (candidateEmail && candidateEmail.trim()) {
    url += `?candidate_email=${encodeURIComponent(candidateEmail.trim())}`;
  }

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const message = await parseApiError(
      response,
      "Failed to retrieve repository ownership report"
    );
    throw new Error(message);
  }

  return response.json();
}
