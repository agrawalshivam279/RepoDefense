/**
 * TypeScript data models for dependency technology audits and obsolescence inspection.
 */

export type AuditSeverity = "critical" | "high" | "medium" | "low";

export type AuditCategory =
  | "deprecated"
  | "security_risk"
  | "outdated"
  | "unmaintained";

export interface AuditedDependencyItem {
  name: string;
  version: string | null;
  is_dev: boolean;
  severity: AuditSeverity;
  category: AuditCategory;
  issue_description: string;
  suggested_alternative: string;
  reference_url?: string | null;
}

export interface TechAuditReportResponse {
  project_id: string;
  project_name: string;
  total_dependencies_audited: number;
  flagged_dependencies_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  tech_health_score: number;
  audited_items: AuditedDependencyItem[];
}
