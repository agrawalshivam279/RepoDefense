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

export type VerificationStatus = "supported" | "contradicted" | "unverifiable";

export interface EvidenceCitation {
  file_path: string;
  start_line?: number | null;
  end_line?: number | null;
  symbol_name?: string | null;
  snippet: string;
  relevance_score: number;
  source_type: "code_chunk" | "evidence" | "dependency" | string;
}

export interface ClaimVerificationResult {
  claim_id: string;
  statement: string;
  status: VerificationStatus;
  confidence_score: number;
  reasoning: string;
  citations: EvidenceCitation[];
  suggested_defense_questions: string[];
}

export interface BatchClaimVerificationResponse {
  project_id: string;
  total_claims: number;
  verified_claims: ClaimVerificationResult[];
  summary_counts: Record<string, number>;
}
