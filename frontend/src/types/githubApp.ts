/**
 * TypeScript contracts for GitHub App private repository integration.
 */

export interface GitHubAppStatusResponse {
  configured: boolean;
  app_id: string | null;
  app_slug: string | null;
  install_url: string | null;
}

export interface GitHubAppRepoItem {
  id: number;
  name: string;
  full_name: string;
  private: boolean;
  default_branch: string;
  description: string | null;
  clone_url: string;
  html_url: string;
}

export interface GitHubAppRepoListResponse {
  installation_id: number;
  total_count: number;
  repositories: GitHubAppRepoItem[];
}

export interface PrivateRepoProjectCreate {
  full_name: string;
  installation_id: number;
  default_branch?: string;
}
