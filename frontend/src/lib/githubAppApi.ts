import { supabase } from "@/lib/supabase";
import type {
  GitHubAppRepoListResponse,
  GitHubAppStatusResponse,
  PrivateRepoProjectCreate,
} from "@/types/githubApp";
import type { Project } from "@/types/project";

const getApiBaseUrl = (): string => {
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
};

async function getAccessToken(providedToken?: string): Promise<string> {
  if (providedToken) return providedToken;
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error("Authentication required. Please sign in to continue.");
  }
  return session.access_token;
}

/**
 * Retrieves the deployment status and installation URL for the GitHub App.
 */
export async function fetchGitHubAppStatus(): Promise<GitHubAppStatusResponse> {
  const url = `${getApiBaseUrl()}/api/v1/github-app/status`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch GitHub App status (status ${response.status})`);
  }
  return response.json();
}

/**
 * Retrieves all accessible repositories under a specific GitHub App installation ID.
 */
export async function fetchInstallationRepositories(
  installationId: number,
  token?: string
): Promise<GitHubAppRepoListResponse> {
  const accessToken = await getAccessToken(token);
  const url = `${getApiBaseUrl()}/api/v1/github-app/installations/${installationId}/repositories`;

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail || `Request failed with status ${response.status}`;
    if (response.status === 403) {
      throw new Error(`Access Denied: ${detail}`);
    }
    if (response.status === 404) {
      throw new Error(`Installation #${installationId} not found or inaccessible.`);
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return response.json();
}

/**
 * Registers an accessible private repository as a new Project and enqueues background clone.
 */
export async function createPrivateRepoProject(
  payload: PrivateRepoProjectCreate,
  token?: string
): Promise<Project> {
  const accessToken = await getAccessToken(token);
  const url = `${getApiBaseUrl()}/api/v1/github-app/projects`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail || `Failed to register project (status ${response.status})`;

    if (response.status === 409) {
      throw new Error("This repository is already registered in your projects.");
    }
    if (response.status === 403) {
      throw new Error(`Authorization Error: ${detail}`);
    }
    if (response.status === 503) {
      throw new Error("Cloning worker queue is currently offline. Please try again shortly.");
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return response.json();
}
