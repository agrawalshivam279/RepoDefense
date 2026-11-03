/**
 * TypeScript definitions and contracts for architectural evidence items.
 * Mirrors FastAPI backend schemas in app/schemas/evidence.py.
 */

export type EvidenceType =
  | "framework"
  | "database"
  | "auth"
  | "api_endpoint"
  | "queue"
  | "infrastructure"
  | "architecture";

export interface EvidenceItem {
  id: string;
  project_id: string;
  evidence_type: EvidenceType;
  title: string;
  description: string;
  file_path: string;
  start_line: number;
  end_line: number;
}
