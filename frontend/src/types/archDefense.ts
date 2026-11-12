/**
 * TypeScript data contracts for Architecture Defense Mode.
 * Mirrors backend Pydantic models from backend/app/schemas/arch_defense.py.
 */

import type { DetectedPattern } from "@/types/architecture";
import type { DiagramEdge, DiagramNode, DiagramType } from "@/types/diagram";

export type ArchFocusAreaType =
  | "PATTERN_CHOICE"
  | "COMPONENT_BOUNDARY"
  | "DATA_FLOW_COUPLING"
  | "ARCHITECTURAL_RISK";

export type ArchDefenseStage =
  | "TOPIC_ACTIVE"
  | "TRADEOFF_CHALLENGE"
  | "COMPLETED";

export interface DiagramTarget {
  node_id: string;
  label: string;
  node_type: string;
  subgraph?: string | null;
  connected_edges: string[];
}

export interface ArchDefenseTopic {
  id: string;
  title: string;
  focus_area: ArchFocusAreaType;
  pattern_name: string;
  severity_or_confidence: string;
  target_nodes: DiagramTarget[];
  design_claim: string;
  interrogation_prompt: string;
  expected_tradeoffs: string[];
  risk_references: string[];
}

export interface ArchDefenseTurn {
  id: string;
  role: "interviewer" | "candidate" | "system" | string;
  content: string;
  stage: ArchDefenseStage;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface ArchDefenseSessionState {
  session_id: string;
  project_id: string;
  topic: ArchDefenseTopic;
  mermaid_code: string;
  diagram_summary: string;
  primary_pattern_name: string;
  stage: ArchDefenseStage;
  current_turn_index: number;
  turns: ArchDefenseTurn[];
  overall_score?: number | null;
  pattern_rationale_solid?: boolean | null;
  boundary_coherence_score?: number | null;
  feedback?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ArchTopicListResponse {
  project_id: string;
  project_name: string;
  primary_pattern: DetectedPattern;
  diagram_type: DiagramType;
  mermaid_code: string;
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  is_diagram_fallback: boolean;
  total_topics: number;
  topics: ArchDefenseTopic[];
}

export interface GenerateArchTopicsRequest {
  focus_area?: ArchFocusAreaType | null;
  max_topics?: number;
  model?: string | null;
  api_key?: string | null;
  base_url?: string | null;
}

export interface StartArchDefenseRequest {
  topic_id: string;
}

export interface SubmitArchAnswerRequest {
  answer: string;
  model?: string | null;
  api_key?: string | null;
  base_url?: string | null;
}
