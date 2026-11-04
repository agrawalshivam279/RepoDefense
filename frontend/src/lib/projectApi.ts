import type { ProjectOverviewResponse } from "@/types/project";

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
    // Non-JSON payload
  }
  return `${defaultMessage} (Status ${response.status})`;
}

/**
 * Retrieves the comprehensive repository analysis overview for a project.
 */
export async function getProjectOverview(
  projectId: string,
  token: string
): Promise<ProjectOverviewResponse> {
  const response = await fetch(`${API_BASE}/api/v1/projects/${projectId}/overview`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const message = await parseApiError(response, "Failed to retrieve project overview");
    throw new Error(message);
  }

  return response.json();
}
