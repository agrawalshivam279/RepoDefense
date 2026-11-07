/**
 * TypeScript data contracts for repository code ownership and author attribution.
 * Mirrors backend Pydantic models from backend/app/schemas/ownership.py.
 */

export type OwnershipStatus = "primary" | "collaborator" | "minor" | "unowned";

export interface AuthorShare {
  name: string;
  email: string;
  lines_authored: number;
  percentage: number;
}

export interface SymbolOwnership {
  symbol_id: string;
  symbol_name: string;
  symbol_type: string;
  file_path: string;
  start_line: number;
  end_line: number;
  total_lines: number;
  primary_author: string;
  candidate_ownership_percentage: number;
  candidate_status: OwnershipStatus;
  authors: AuthorShare[];
  is_architectural_evidence: boolean;
  evidence_type?: string | null;
}

export interface FileOwnershipSummary {
  file_path: string;
  total_lines: number;
  primary_author: string;
  candidate_percentage: number;
  candidate_lines: number;
  authors: AuthorShare[];
}

export interface ProjectOwnershipReport {
  project_id: string;
  project_name: string;
  candidate_email: string;
  total_symbols_analyzed: number;
  candidate_authored_symbols: number;
  candidate_overall_ownership_percentage: number;
  flagged_unowned_symbols: SymbolOwnership[];
  symbols: SymbolOwnership[];
  files: FileOwnershipSummary[];
  top_contributors: AuthorShare[];
}
