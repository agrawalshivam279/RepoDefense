/**
 * TypeScript contracts for Mentor Mode teaching content and code remediation.
 * Mirrors backend/app/schemas/mentor.py.
 */

export interface CodeRemediationSnippet {
  title: string;
  language: string;
  file_context?: string | null;
  before_code: string;
  after_code: string;
  explanation: string;
}

export interface MentorExplanationRequest {
  weakness_id?: string;
  category?: string;
  topic?: string;
  question_prompt?: string;
  candidate_response?: string;
  feedback?: string;
  code_context?: string;
  language?: string;
  model?: string;
  llm_base_url?: string;
  llm_api_key?: string;
}

export interface MentorExplanationResponse {
  explanation_id: string;
  category: string;
  topic: string;
  architectural_risk: string;
  core_concept: string;
  mentor_advice: string;
  code_examples: CodeRemediationSnippet[];
  key_takeaways: string[];
  socratic_followup: string;
  generated_at: string;
}

export type RemediationViewMode = "split" | "unified";
export type ActiveCodeTab = "before" | "after";

export interface QuickTopicOption {
  title: string;
  category: string;
  topic: string;
  description: string;
  iconName: "database" | "lock" | "flame" | "gauge" | "layers";
}

export const QUICK_MENTOR_TOPICS: QuickTopicOption[] = [
  {
    title: "Connection Pooling",
    category: "scalability",
    topic: "connection_pooling",
    description: "Prevent database socket starvation under concurrent load",
    iconName: "database",
  },
  {
    title: "Concurrency & Locks",
    category: "concurrency",
    topic: "race_condition_locks",
    description: "Prevent lost updates with atomic updates & OCC",
    iconName: "lock",
  },
  {
    title: "Cache Stampedes",
    category: "scalability",
    topic: "cache_stampede",
    description: "Prevent thundering herds during cache TTL expirations",
    iconName: "flame",
  },
  {
    title: "Rate Limiting",
    category: "security",
    topic: "rate_limiting",
    description: "Throttle bursts with sliding window counters",
    iconName: "gauge",
  },
  {
    title: "Domain Decoupling",
    category: "architecture",
    topic: "domain_service_coupling",
    description: "Decouple domain business logic from I/O boundaries",
    iconName: "layers",
  },
];
