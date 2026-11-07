/**
 * TypeScript data contracts for Mermaid architecture diagrams.
 * Mirrors backend Pydantic models from backend/app/schemas/diagram.py.
 */

export type DiagramType = "flowchart TD" | "flowchart LR";

export interface DiagramNode {
  node_id: string;
  label: string;
  node_type: "frontend" | "backend" | "database" | "queue" | "external" | "service" | string;
  subgraph?: string | null;
}

export interface DiagramEdge {
  source_id: string;
  target_id: string;
  label?: string | null;
  style?: string | null;
}

export interface DiagramResponse {
  project_id: string;
  project_name: string;
  diagram_type: DiagramType;
  mermaid_code: string;
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  is_fallback: boolean;
  summary: string;
}
