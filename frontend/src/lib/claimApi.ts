import type {
  BatchClaimVerificationResponse,
  ClaimExtractionResponse,
  TechnicalClaim,
} from "@/types/claim";

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
 * Extracts technical claims from raw resume text.
 */
export async function extractClaimsFromText(
  text: string,
  token?: string
): Promise<ClaimExtractionResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/api/v1/claims/extract`, {
    method: "POST",
    headers,
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const message = await parseApiError(response, "Failed to extract technical claims");
    throw new Error(message);
  }

  return response.json();
}

/**
 * Uploads a PDF resume file to extract technical claims.
 */
export async function uploadResumeFile(
  file: File,
  token?: string
): Promise<ClaimExtractionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/api/v1/claims/upload`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const message = await parseApiError(response, "Failed to upload and parse resume");
    throw new Error(message);
  }

  return response.json();
}

/**
 * Verifies extracted technical claims against project codebase truth.
 */
export async function verifyProjectClaims(
  projectId: string,
  claims: TechnicalClaim[],
  token?: string,
  topKChunks = 5,
  minSimilarityThreshold = 0.4
): Promise<BatchClaimVerificationResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/api/v1/projects/${projectId}/claims/verify`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      claims,
      top_k_chunks: topKChunks,
      min_similarity_threshold: minSimilarityThreshold,
    }),
  });

  if (!response.ok) {
    const message = await parseApiError(response, "Failed to verify claims against codebase");
    throw new Error(message);
  }

  return response.json();
}
