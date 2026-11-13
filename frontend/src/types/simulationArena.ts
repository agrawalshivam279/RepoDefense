import React from "react";
import {
  Compass,
  Flame,
  Gauge,
  GitCommit,
  GitPullRequest,
  Shield,
} from "lucide-react";

export interface SimulationArenaMode {
  id: string;
  title: string;
  badgeText: string;
  badgeStyle: string;
  focusArea: string;
  description: string;
  hrefTemplate: (id: string) => string;
  buttonLabel: string;
  Icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
}

export interface ModeStatusItem {
  active_sessions: number;
  capacity_limit?: number | null;
  status?: string;
}

export interface SimulationReadinessPayload {
  status: string;
  modes?: Record<string, ModeStatusItem>;
  simulations?: Record<string, ModeStatusItem>;
  total_active_simulations?: number;
}

export function parseSimulationReadiness(
  data: unknown
): Record<string, number> {
  const counts: Record<string, number> = {};
  if (typeof data === "object" && data !== null) {
    const obj = data as Record<string, unknown>;
    const modesDict = (obj.modes || obj.simulations) as
      | Record<string, ModeStatusItem>
      | undefined;
    if (modesDict && typeof modesDict === "object") {
      for (const [key, val] of Object.entries(modesDict)) {
        if (typeof val?.active_sessions === "number") {
          counts[key] = val.active_sessions;
        }
      }
    }
  }
  return counts;
}

export const SIMULATION_MODES: SimulationArenaMode[] = [
  {
    id: "core_defense",
    title: "Core Oral Defense",
    badgeText: "Core MVP",
    badgeStyle: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    focusArea: "Deep Code Comprehension",
    description:
      "Evidence-grounded architectural defense with adaptive follow-ups, depth scoring, and AI pushback.",
    hrefTemplate: (id) => `/interview/${id}`,
    buttonLabel: "Launch Oral Defense",
    Icon: Shield,
    accentColor: "text-emerald-400",
  },
  {
    id: "pr_defense",
    title: "Pull Request Defense",
    badgeText: "Diff Grounded",
    badgeStyle: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    focusArea: "Change Rationalization",
    description:
      "Diff-scoped interrogation focusing strictly on why code changes were made across modified hunks.",
    hrefTemplate: (id) => `/projects/${id}/pr-defense`,
    buttonLabel: "Launch PR Defense",
    Icon: GitPullRequest,
    accentColor: "text-rose-400",
  },
  {
    id: "commit_defense",
    title: "Git Commit Defense",
    badgeText: "Commit Scoped",
    badgeStyle: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    focusArea: "Atomic Integrity",
    description:
      "Single commit SHA interrogation examining change context, author intent, and potential blast radius.",
    hrefTemplate: (id) => `/projects/${id}/commit-defense`,
    buttonLabel: "Launch Commit Defense",
    Icon: GitCommit,
    accentColor: "text-emerald-400",
  },
  {
    id: "incident_simulation",
    title: "Incident War Room",
    badgeText: "Chaos SRE",
    badgeStyle: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    focusArea: "Resilience Engineering",
    description:
      "Production chaos failure simulation testing real-time triage, system mitigations, and postmortems.",
    hrefTemplate: (id) => `/projects/${id}/incident-simulation`,
    buttonLabel: "Enter War Room",
    Icon: Flame,
    accentColor: "text-rose-400",
  },
  {
    id: "stress_test",
    title: "Stress Test & What-If",
    badgeText: "Scaling Defense",
    badgeStyle: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    focusArea: "Concurrency & Bottlenecks",
    description:
      "Hypothetical 10x–100x traffic scaling constraints interrogating bottlenecks and connection saturation.",
    hrefTemplate: (id) => `/projects/${id}/stress-test`,
    buttonLabel: "Start Stress Test",
    Icon: Gauge,
    accentColor: "text-amber-400",
  },
  {
    id: "arch_defense",
    title: "Architecture Defense",
    badgeText: "Topology Defense",
    badgeStyle: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    focusArea: "System Tradeoffs",
    description:
      "Interactive Mermaid diagram-linked interrogation challenging component boundaries and architectural risks.",
    hrefTemplate: (id) => `/projects/${id}/arch-defense`,
    buttonLabel: "Defend Architecture",
    Icon: Compass,
    accentColor: "text-cyan-400",
  },
];
