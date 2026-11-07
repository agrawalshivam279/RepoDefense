import type { DiagramResponse } from "@/types/diagram";

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
 * Retrieves the repository architecture Mermaid diagram and structured topology.
 */
export async function getProjectDiagram(
  projectId: string,
  token: string
): Promise<DiagramResponse> {
  const url = `${API_BASE}/api/v1/projects/${projectId}/diagram`;

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
      "Failed to retrieve repository architecture diagram"
    );
    throw new Error(message);
  }

  return response.json();
}
