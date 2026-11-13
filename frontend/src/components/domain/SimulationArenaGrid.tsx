"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Compass,
  Flame,
  Gauge,
  GitCommit,
  GitPullRequest,
  Shield,
  Sparkles,
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

interface SimulationArenaGridProps {
  projectId: string;
}

export function SimulationArenaGrid({ projectId }: SimulationArenaGridProps) {
  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-mono uppercase tracking-wider mb-1">
            <Sparkles className="w-4 h-4" />
            <span>Interactive Defense Arena</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Select a Simulation Engine
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Authenticate your repository comprehension against 6 principal-engineer level defense modes.
          </p>
        </div>

        <Link
          href={`/projects/${projectId}/analytics`}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-emerald-400 hover:text-emerald-300 hover:border-emerald-500/40 transition-colors shrink-0 shadow-sm"
        >
          <BarChart3 className="w-4 h-4" />
          <span>Readiness Telemetry</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* 6-Card Arena Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SIMULATION_MODES.map((mode) => {
          const { Icon } = mode;
          const href = mode.hrefTemplate(projectId);
          return (
            <div
              key={mode.id}
              className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition-all shadow-sm group"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800">
                      <Icon className={`w-5 h-5 ${mode.accentColor}`} />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors">
                        {mode.title}
                      </h3>
                      <span className="text-[11px] font-mono text-slate-400">
                        {mode.focusArea}
                      </span>
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border font-semibold ${mode.badgeStyle}`}
                  >
                    {mode.badgeText}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed font-sans min-h-[48px]">
                  {mode.description}
                </p>
              </div>

              <div className="pt-4 mt-2 border-t border-slate-800/80">
                <Link
                  href={href}
                  className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-xs font-mono text-slate-200 hover:text-white border border-slate-700/80 transition-colors"
                >
                  <span>{mode.buttonLabel}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
