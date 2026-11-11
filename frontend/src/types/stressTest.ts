/**
 * TypeScript data models and interfaces for Stress Test & What-If Mode.
 * Corresponds to backend/app/schemas/stress_test.py.
 */

export type StressConstraintType =
  | "CONCURRENCY_SPIKE"
  | "DATA_VOLUME_100X"
  | "MEMORY_PRESSURE"
  | "NETWORK_LATENCY_JITTER"
  | "DB_CONNECTION_STARVATION";

export type StressSeverity = "MODERATE" | "SEVERE" | "EXTREME";

export type StressSessionStage =
  | "SCENARIO_ACTIVE"
  | "FOLLOW_UP_CONSTRAINED"
  | "COMPLETED";

export interface StressTarget {
  symbol_name: string;
  file_path: string;
  line_range: string;
  component_type: string;
}

export interface StressTestScenario {
  id: string;
  title: string;
  constraint_type: StressConstraintType;
  severity: StressSeverity;
  target: StressTarget;
  context_description: string;
  hypothetical_prompt: string;
  expected_tradeoffs: string[];
  cited_evidence_ids: string[];
}

export interface StressDefenseTurn {
  id: string;
  role: "interviewer" | "candidate" | "system" | string;
  content: string;
  stage: StressSessionStage;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface StressEvaluationOutput {
  depth_score: number;
  bottleneck_identified: boolean;
  scaling_strategy_sound: boolean;
  tradeoffs_acknowledged: boolean;
  feedback: string;
  follow_up_constraint?: string | null;
  is_terminal: boolean;
}

export interface StressDefenseSessionState {
  session_id: string;
  project_id: string;
  scenario: StressTestScenario;
  stage: StressSessionStage;
  current_turn_index: number;
  turns: StressDefenseTurn[];
  overall_score?: number | null;
  bottleneck_identified?: boolean | null;
  feedback?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GenerateStressScenariosRequest {
  constraint_type?: StressConstraintType | null;
  max_scenarios?: number;
}

export interface StressScenarioListResponse {
  project_id: string;
  total_scenarios: number;
  scenarios: StressTestScenario[];
}

export interface StartStressDefenseRequest {
  scenario_id: string;
}

export interface SubmitStressAnswerRequest {
  answer: string;
}
