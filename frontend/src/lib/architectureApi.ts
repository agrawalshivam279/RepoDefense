import type { ArchitectureReportResponse } from "@/types/architecture";

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
 * Retrieves repository architecture pattern detection, indicator signals, and risk analysis.
 */
export async function getProjectArchitecture(
  projectId: string,
  token: string
): Promise<ArchitectureReportResponse> {
  const url = `${API_BASE}/api/v1/projects/${projectId}/architecture`;

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
      "Failed to retrieve repository architecture report"
    );
    throw new Error(message);
  }

  return response.json();
}
