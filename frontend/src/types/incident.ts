/**
 * TypeScript data models and interfaces for Chaos Engineering & Incident Simulation Engine.
 * Corresponds to backend/app/schemas/incident.py.
 */

export type FailureCategory =
  | "DATABASE_OUTAGE"
  | "DEPENDENCY_TIMEOUT"
  | "CACHE_FAILURE"
  | "MESSAGE_BROKER_PARTITION"
  | "RESOURCE_EXHAUSTION"
  | "CONCURRENCY_RACE";

export type IncidentSeverity = "P0_CRITICAL" | "P1_HIGH" | "P2_MEDIUM";

export type IncidentStage = "TRIAGE" | "ESCALATED" | "MITIGATED" | "POSTMORTEM";

export interface ChaosTarget {
  file_path: string;
  symbol_name?: string | null;
  line_start?: number | null;
  line_end?: number | null;
  component_type: string;
}

export interface IncidentScenario {
  id: string;
  title: string;
  category: FailureCategory;
  severity: IncidentSeverity;
  hypothetical_trigger: string;
  symptoms: string[];
  grounded_target: ChaosTarget;
  incident_question: string;
  evaluation_criteria: string[];
}

export interface IncidentDefenseTurn {
  turn_index: number;
  prompt: string;
  candidate_answer?: string | null;
  score?: number | null;
  feedback?: string | null;
  escalation_injected?: string | null;
}

export interface IncidentDefenseSessionState {
  id: string;
  project_id: string;
  scenario: IncidentScenario;
  turns: IncidentDefenseTurn[];
  current_turn_index: number;
  max_turns: number;
  stage: IncidentStage;
  overall_score?: number | null;
  postmortem_summary?: string | null;
}

export interface GenerateScenariosRequest {
  category?: FailureCategory;
  limit?: number;
}

export interface ScenarioListResponse {
  project_id: string;
  total_scenarios: number;
  scenarios: IncidentScenario[];
}

export interface StartIncidentDefenseRequest {
  scenario_id?: string;
  category?: FailureCategory;
}

export interface SubmitIncidentAnswerRequest {
  answer: string;
}
