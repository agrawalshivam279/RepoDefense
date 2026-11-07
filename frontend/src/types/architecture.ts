/**
 * TypeScript data contracts for repository architecture patterns, signals, and health risks.
 * Mirrors backend Pydantic models from backend/app/schemas/architecture.py.
 */

export type ArchitecturePatternType =
  | "modular_monolith"
  | "mvc"
  | "clean_architecture"
  | "layered_architecture"
  | "event_driven"
  | "microservices"
  | "serverless_jamstack"
  | "unstructured";

export type PatternConfidenceTier = "high" | "moderate" | "low";

export interface PatternIndicator {
  indicator_type: "directory" | "dependency" | "evidence" | string;
  description: string;
  weight: number;
  matched_items: string[];
}

export interface DetectedPattern {
  pattern_type: ArchitecturePatternType;
  pattern_name: string;
  confidence_score: number;
  tier: PatternConfidenceTier;
  summary: string;
  indicators: PatternIndicator[];
}

export interface ArchitecturalRisk {
  risk_id: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  recommendation: string;
}

export interface ArchitectureReportResponse {
  project_id: string;
  project_name: string;
  primary_pattern: DetectedPattern;
  secondary_patterns: DetectedPattern[];
  all_patterns: DetectedPattern[];
  architectural_risks: ArchitecturalRisk[];
  directory_summary: Record<string, number>;
  total_files_analyzed: number;
}
