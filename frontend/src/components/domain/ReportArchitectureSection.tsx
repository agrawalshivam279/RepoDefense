"use client";

import React, { useMemo } from "react";
import {
  Cpu,
  Layers,
  Network,
  Package,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { MermaidViewer } from "@/components/domain/MermaidViewer";
import type { DiagramResponse } from "@/types/diagram";
import type { EnhancedDefenseReportResponse } from "@/types/report";

interface ReportArchitectureSectionProps {
  report: EnhancedDefenseReportResponse;
}

export function ReportArchitectureSection({
  report,
}: ReportArchitectureSectionProps) {
  const {
    architecture_primary_pattern,
    architecture_confidence_tier,
    diagram_mermaid_code,
    tech_health_score,
    tech_flagged_count,
    tech_total_dependencies,
  } = report;

  const diagramPayload: DiagramResponse | null = useMemo(() => {
    if (!diagram_mermaid_code) return null;
    return {
      project_id: report.project_id,
      project_name: "System Topology",
      diagram_type: "flowchart TD",
      mermaid_code: diagram_mermaid_code,
      nodes: [],
      edges: [],
      is_fallback: false,
      summary: `Synthesized architecture flowchart for ${
        architecture_primary_pattern || "repository"
      }.`,
    };
  }, [diagram_mermaid_code, report.project_id, architecture_primary_pattern]);

  const getTierBadge = (tier?: string | null) => {
    switch (tier?.toLowerCase()) {
      case "high":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "moderate":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getTechHealthColor = (score?: number | null) => {
    if (score === undefined || score === null) return "text-slate-400";
    if (score >= 85) return "text-emerald-400";
    if (score >= 70) return "text-amber-400";
    if (score >= 50) return "text-orange-400";
    return "text-rose-400";
  };

  return (
    <div className="space-y-6 pt-4 border-t border-slate-800">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="w-5 h-5 text-purple-400" />
          <h2 className="text-xl font-bold text-white tracking-tight">
            Codebase Ground Truth & System Architecture
          </h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          Deterministic AST & Dependency Audit
        </span>
      </div>

      {/* KPI Cards: Architecture Pattern & Technology Health */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Architecture Pattern Card */}
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">
              Primary Architecture Pattern
            </span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-lg font-bold text-white font-mono truncate">
              {architecture_primary_pattern || "Modular Monolith"}
            </span>
            {architecture_confidence_tier && (
              <span
                className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase font-bold border ${getTierBadge(
                  architecture_confidence_tier
                )}`}
              >
                {architecture_confidence_tier} Confidence
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 font-sans">
            Detected via static directory topologies, AST module imports, and
            load-bearing component patterns.
          </p>
        </div>

        {/* Technology Health Score Card */}
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">
              Technology Stack Health
            </span>
            <Cpu className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline justify-between gap-3">
            <div className="flex items-baseline gap-2">
              <span
                className={`text-3xl font-black font-mono ${getTechHealthColor(
                  tech_health_score
                )}`}
              >
                {tech_health_score !== null && tech_health_score !== undefined
                  ? `${tech_health_score}%`
                  : "N/A"}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Health Score
              </span>
            </div>
            {tech_total_dependencies !== undefined &&
              tech_total_dependencies !== null && (
                <span className="text-xs font-mono text-slate-300">
                  <span
                    className={
                      tech_flagged_count && tech_flagged_count > 0
                        ? "text-rose-400 font-bold"
                        : "text-emerald-400"
                    }
                  >
                    {tech_flagged_count ?? 0}
                  </span>{" "}
                  flagged of {tech_total_dependencies} deps
                </span>
              )}
          </div>
          <p className="text-xs text-slate-400 font-sans">
            Evaluated against known package deprecations, CVE vulnerability
            thresholds, and semver heuristics.
          </p>
        </div>
      </div>

      {/* Embedded Architecture Diagram Flowchart */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Workflow className="w-3.5 h-3.5 text-sky-400" />
          <span>Multi-Tier Architecture Topology Flowchart:</span>
        </div>
        {diagramPayload ? (
          <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-1">
            <MermaidViewer diagram={diagramPayload} />
          </div>
        ) : (
          <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs font-mono text-slate-400">
            System topology flowchart unavailable or not yet generated.
          </div>
        )}
      </div>
    </div>
  );
}
