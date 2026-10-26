export interface Project {
  id: string;
  user_id: string;
  name: string;
  github_url: string;
  default_branch: string;
  status: "pending" | "cloning" | "cloned" | "analyzing" | "analyzed" | "failed";
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  github_url: string;
  name?: string;
  default_branch?: string;
}
