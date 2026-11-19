import type {
  CreateShareTokenPayload,
  PublicDefenseReport,
  PublicShareTokenResponse,
} from "@/types/publicReport";

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
    // Non-JSON error body fallback
  }
  return `${defaultMessage} (Status ${response.status})`;
}

/**
 * Retrieves unauthenticated verified defense report by cryptographic share token.
 */
export async function getPublicDefenseReport(shareToken: string): Promise<PublicDefenseReport> {
  const res = await fetch(`${API_BASE}/api/v1/public/reports/${encodeURIComponent(shareToken)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const errorMsg = await parseApiError(res, "Failed to load public defense report");
    throw new Error(errorMsg);
  }

  return (await res.json()) as PublicDefenseReport;
}

/**
 * Creates or updates public share credentials for an authenticated user's defense session.
 */
export async function createPublicShareToken(
  projectId: string,
  sessionId: string,
  token: string,
  payload?: CreateShareTokenPayload
): Promise<PublicShareTokenResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/projects/${encodeURIComponent(projectId)}/defense/${encodeURIComponent(sessionId)}/share`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload || { is_active: true }),
    }
  );

  if (!res.ok) {
    const errorMsg = await parseApiError(res, "Failed to generate public share token");
    throw new Error(errorMsg);
  }

  return (await res.json()) as PublicShareTokenResponse;
}

/**
 * Retrieves existing public share credentials for an authenticated defense session.
 */
export async function getPublicShareInfo(
  projectId: string,
  sessionId: string,
  token: string
): Promise<PublicShareTokenResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/projects/${encodeURIComponent(projectId)}/defense/${encodeURIComponent(sessionId)}/share`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
      },
    }
  );

  if (!res.ok) {
    const errorMsg = await parseApiError(res, "Failed to retrieve public share info");
    throw new Error(errorMsg);
  }

  return (await res.json()) as PublicShareTokenResponse;
}

/**
 * Revokes public sharing access for a defense session.
 */
export async function revokePublicShare(
  projectId: string,
  sessionId: string,
  token: string
): Promise<{ revoked: boolean; session_id: string }> {
  const res = await fetch(
    `${API_BASE}/api/v1/projects/${encodeURIComponent(projectId)}/defense/${encodeURIComponent(sessionId)}/share`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!res.ok) {
    const errorMsg = await parseApiError(res, "Failed to revoke public share link");
    throw new Error(errorMsg);
  }

  return (await res.json()) as { revoked: boolean; session_id: string };
}
