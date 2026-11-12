/**
 * REST API client for Architecture Defense Mode.
 * Connects to FastAPI router at /api/v1/arch-defense with strict payload validation.
 */

import type {
  ArchDefenseSessionState,
  ArchDefenseStage,
  ArchDefenseTopic,
  ArchDefenseTurn,
  ArchFocusAreaType,
  ArchTopicListResponse,
  DiagramTarget,
  GenerateArchTopicsRequest,
  StartArchDefenseRequest,
  SubmitArchAnswerRequest,
} from "@/types/archDefense";
import type { DiagramEdge, DiagramNode } from "@/types/diagram";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const VALID_FOCUS_AREAS = new Set<string>([
  "PATTERN_CHOICE",
  "COMPONENT_BOUNDARY",
  "DATA_FLOW_COUPLING",
  "ARCHITECTURAL_RISK",
]);

const VALID_STAGES = new Set<string>([
  "TOPIC_ACTIVE",
  "TRADEOFF_CHALLENGE",
  "COMPLETED",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isDiagramTarget(value: unknown): value is DiagramTarget {
  return (
    isRecord(value) &&
    typeof value.node_id === "string" &&
    typeof value.label === "string" &&
    typeof value.node_type === "string" &&
    (value.subgraph === undefined || value.subgraph === null || typeof value.subgraph === "string") &&
    isStringArray(value.connected_edges)
  );
}

function isDiagramNode(value: unknown): value is DiagramNode {
  return (
    isRecord(value) &&
    typeof value.node_id === "string" &&
    typeof value.label === "string" &&
    typeof value.node_type === "string"
  );
}

function isDiagramEdge(value: unknown): value is DiagramEdge {
  return (
    isRecord(value) &&
    typeof value.source_id === "string" &&
    typeof value.target_id === "string"
  );
}

function isArchTopic(value: unknown): value is ArchDefenseTopic {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.focus_area === "string" &&
    VALID_FOCUS_AREAS.has(value.focus_area) &&
    typeof value.pattern_name === "string" &&
    typeof value.severity_or_confidence === "string" &&
    Array.isArray(value.target_nodes) &&
    value.target_nodes.every(isDiagramTarget) &&
    typeof value.design_claim === "string" &&
    typeof value.interrogation_prompt === "string" &&
    isStringArray(value.expected_tradeoffs) &&
    isStringArray(value.risk_references)
  );
}

function isArchTurn(value: unknown): value is ArchDefenseTurn {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.role === "string" &&
    typeof value.content === "string" &&
    typeof value.stage === "string" &&
    VALID_STAGES.has(value.stage as ArchDefenseStage) &&
    typeof value.timestamp === "string" &&
    isRecord(value.metadata)
  );
}

function validateTopicListResponse(data: unknown): ArchTopicListResponse {
  if (
    !isRecord(data) ||
    typeof data.project_id !== "string" ||
    typeof data.project_name !== "string" ||
    !isRecord(data.primary_pattern) ||
    typeof data.primary_pattern.pattern_name !== "string" ||
    typeof data.primary_pattern.confidence_score !== "number" ||
    typeof data.primary_pattern.tier !== "string" ||
    typeof data.diagram_type !== "string" ||
    typeof data.mermaid_code !== "string" ||
    !Array.isArray(data.nodes) ||
    !data.nodes.every(isDiagramNode) ||
    !Array.isArray(data.edges) ||
    !data.edges.every(isDiagramEdge) ||
    typeof data.is_diagram_fallback !== "boolean" ||
    typeof data.total_topics !== "number" ||
    !Array.isArray(data.topics) ||
    !data.topics.every(isArchTopic)
  ) {
    throw new Error("Malformed architecture defense topic catalog payload");
  }
  return data as unknown as ArchTopicListResponse;
}

function validateSessionState(data: unknown): ArchDefenseSessionState {
  if (
    !isRecord(data) ||
    typeof data.session_id !== "string" ||
    typeof data.project_id !== "string" ||
    !isArchTopic(data.topic) ||
    typeof data.mermaid_code !== "string" ||
    typeof data.diagram_summary !== "string" ||
    typeof data.primary_pattern_name !== "string" ||
    typeof data.stage !== "string" ||
    !VALID_STAGES.has(data.stage) ||
    typeof data.current_turn_index !== "number" ||
    !Array.isArray(data.turns) ||
    !data.turns.every(isArchTurn)
  ) {
    throw new Error("Malformed architecture defense session payload");
  }
  return data as unknown as ArchDefenseSessionState;
}

async function parseApiError(response: Response, fallback: string): Promise<string> {
  try {
    const payload: unknown = await response.json();
    if (isRecord(payload)) {
      if (typeof payload.detail === "string" && payload.detail.trim()) {
        return payload.detail;
      }
      if (Array.isArray(payload.detail)) {
        const msgs = payload.detail
          .map((item) => (isRecord(item) && typeof item.msg === "string" ? item.msg : ""))
          .filter(Boolean);
        if (msgs.length > 0) return msgs.join("; ");
      }
    }
  } catch {
    // Non-JSON response falls back to HTTP status string
  }
  return `${fallback} (HTTP ${response.status})`;
}

async function requestArchApi<T>(
  path: string,
  token: string,
  options: { method: "GET" | "POST"; body?: unknown; signal?: AbortSignal },
  fallbackError: string,
  validate: (data: unknown) => T
): Promise<T> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}/api/v1/arch-defense${path}`, {
    method: options.method,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, fallbackError));
  }

  const json: unknown = await response.json();
  return validate(json);
}

export async function fetchArchDefenseTopics(
  projectId: string,
  token: string,
  focusArea?: ArchFocusAreaType,
  maxTopics: number = 4,
  signal?: AbortSignal
): Promise<ArchTopicListResponse> {
  const payload: GenerateArchTopicsRequest = {
    focus_area: focusArea ?? null,
    max_topics: maxTopics,
  };
  return requestArchApi(
    `/projects/${encodeURIComponent(projectId)}/topics`,
    token,
    { method: "POST", body: payload, signal },
    "Failed to synthesize architecture defense topics",
    validateTopicListResponse
  );
}

export async function startArchDefenseSession(
  projectId: string,
  topicId: string,
  token: string
): Promise<ArchDefenseSessionState> {
  const payload: StartArchDefenseRequest = { topic_id: topicId };
  return requestArchApi(
    `/projects/${encodeURIComponent(projectId)}/sessions/start`,
    token,
    { method: "POST", body: payload },
    "Failed to start architecture defense session",
    validateSessionState
  );
}

export async function getArchDefenseSession(
  sessionId: string,
  token: string,
  signal?: AbortSignal
): Promise<ArchDefenseSessionState> {
  return requestArchApi(
    `/sessions/${encodeURIComponent(sessionId)}`,
    token,
    { method: "GET", signal },
    "Failed to load architecture defense session",
    validateSessionState
  );
}

export async function submitArchDefenseTurn(
  sessionId: string,
  answer: string,
  token: string
): Promise<ArchDefenseSessionState> {
  const payload: SubmitArchAnswerRequest = { answer };
  return requestArchApi(
    `/sessions/${encodeURIComponent(sessionId)}/respond`,
    token,
    { method: "POST", body: payload },
    "Failed to evaluate architecture defense turn",
    validateSessionState
  );
}
