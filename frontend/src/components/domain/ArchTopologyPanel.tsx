"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp, Compass, GitBranch, Layers } from "lucide-react";
import { MermaidViewer } from "@/components/domain/MermaidViewer";
import type { ArchFocusAreaType, DiagramTarget } from "@/types/archDefense";
import type { DiagramResponse } from "@/types/diagram";

export const ARCH_FOCUS_META: Record<ArchFocusAreaType, { label: string; badgeClass: string }> = {
  PATTERN_CHOICE: {
    label: "Pattern Choice",
    badgeClass: "border-cyan-500/30 bg-cyan-500/10 text-cyan-300",
  },
  COMPONENT_BOUNDARY: {
    label: "Component Boundary",
    badgeClass: "border-indigo-500/30 bg-indigo-500/10 text-indigo-300",
  },
  DATA_FLOW_COUPLING: {
    label: "Data Flow Coupling",
    badgeClass: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  },
  ARCHITECTURAL_RISK: {
    label: "Architectural Risk",
    badgeClass: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  },
};

export interface ArchTopologyPanelProps {
  diagram: DiagramResponse;
  primaryPatternName: string;
  focusArea: ArchFocusAreaType;
  targetNodes: DiagramTarget[];
  expectedTradeoffs: string[];
  riskReferences: string[];
}

export function ArchTopologyPanel({
  diagram,
  primaryPatternName,
  focusArea,
  targetNodes,
  expectedTradeoffs,
  riskReferences,
}: ArchTopologyPanelProps) {
  const [showRubricHints, setShowRubricHints] = useState(false);

  return (
    <aside className="space-y-4 lg:sticky lg:top-20 lg:col-span-5 lg:self-start">
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-300">
            <Compass className="h-4 w-4" />
            <span>Architecture Topology</span>
          </div>
          <span className="rounded-md border border-zinc-700 bg-zinc-950 px-2 py-0.5 text-[11px] font-medium text-zinc-300">
            {primaryPatternName}
          </span>
        </div>
        <MermaidViewer diagram={diagram} />
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-300">
            <Layers className="h-3.5 w-3.5 text-cyan-400" />
            Target Diagram Nodes
          </h3>
          <span className="text-xs text-zinc-500">{ARCH_FOCUS_META[focusArea].label}</span>
        </div>

        <div className="space-y-2">
          {targetNodes.map((node) => (
            <div key={node.node_id} className="rounded-lg border border-zinc-800 bg-zinc-950/80 p-2.5 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono font-semibold text-zinc-100">{node.label}</span>
                <div className="flex items-center gap-1.5">
                  {node.subgraph && (
                    <span className="rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 text-[10px] text-zinc-400">
                      {node.subgraph}
                    </span>
                  )}
                  <span className="rounded border border-cyan-500/20 bg-cyan-500/10 px-1.5 py-0.5 text-[10px] font-medium text-cyan-300">
                    {node.node_type}
                  </span>
                </div>
              </div>
              {node.connected_edges.length > 0 && (
                <div className="mt-1.5 flex items-center gap-1 text-[11px] text-zinc-400">
                  <GitBranch className="h-3 w-3 shrink-0 text-zinc-500" />
                  <span className="truncate">{node.connected_edges.join(", ")}</span>
                </div>
              )}
            </div>
          ))}
        </div>

        <button
          type="button"
          aria-expanded={showRubricHints}
          onClick={() => setShowRubricHints((prev) => !prev)}
          className="mt-3 flex w-full items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs font-medium text-zinc-300 transition hover:border-zinc-700"
        >
          <span>Architectural Hints &amp; Risk References</span>
          {showRubricHints ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>

        {showRubricHints && (
          <div className="mt-2 space-y-2 rounded-lg border border-zinc-800 bg-zinc-950/70 p-3 text-xs text-zinc-300">
            {expectedTradeoffs.length > 0 && (
              <div>
                <p className="mb-1 font-semibold text-zinc-200">Expected Tradeoffs</p>
                <ul className="list-inside list-disc space-y-1 text-zinc-400">
                  {expectedTradeoffs.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {riskReferences.length > 0 && (
              <div>
                <p className="mb-1 font-semibold text-amber-300">Linked Risks</p>
                <ul className="list-inside list-disc space-y-1 text-zinc-400">
                  {riskReferences.map((risk, idx) => (
                    <li key={idx}>{risk}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
