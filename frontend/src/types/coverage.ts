/**
 * TypeScript data contracts for repository defense coverage tracking.
 * Mirrors backend Pydantic models from backend/app/schemas/coverage.py.
 */

export type CoverageStatus = "tested" | "partial" | "untested";

export type CoverageTier =
  | "Needs More Defense"
  | "Substantial Coverage"
  | "Principal Verified";

export interface FileCoverageItem {
  file_path: string;
  language: string;
  total_lines: number;
  is_tested: boolean;
  test_count: number;
  associated_evidence_count: number;
  tested_evidence_count: number;
  average_score?: number | null;
  highest_difficulty?: string | null;
}

export interface ModuleCoverageItem {
  module_path: string;
  total_files: number;
  tested_files: number;
  coverage_percentage: number;
  status: CoverageStatus;
}

export interface BlindSpotItem {
  file_path: string;
  evidence_id: string;
  evidence_type: string;
  title: string;
  description: string;
  start_line: number;
  end_line: number;
  priority: "critical" | "high" | "medium" | string;
}

export interface ProjectCoverageResponse {
  project_id: string;
  project_name: string;
  total_files: number;
  tested_files_count: number;
  untested_files_count: number;
  file_coverage_percentage: number;
  total_evidence_items: number;
  tested_evidence_count: number;
  evidence_coverage_percentage: number;
  total_lines_covered: number;
  overall_coverage_tier: CoverageTier;
  modules: ModuleCoverageItem[];
  files: FileCoverageItem[];
  blind_spots: BlindSpotItem[];
}
