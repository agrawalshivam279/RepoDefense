export type ClaimCategory =
  | "architecture"
  | "scalability"
  | "performance"
  | "database"
  | "security"
  | "framework"
  | "infrastructure";

export interface TechnicalClaim {
  id: string;
  statement: string;
  category: ClaimCategory;
  technologies: string[];
  verifiable: boolean;
  source_context?: string;
}

export interface ClaimExtractionResponse {
  claims: TechnicalClaim[];
  total_claims: number;
  source_char_count: number;
  technologies_detected: string[];
}
