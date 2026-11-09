"use client";

import { Activity, AlertOctagon, AlertTriangle, Code2, Flame, Loader2 } from "lucide-react";
import type { IncidentScenario, IncidentSeverity } from "@/types/incident";

interface IncidentScenarioCardProps {
  scenario: IncidentScenario;
  onSelect: (scenarioId: string) => void;
  starting: boolean;
}

export function SeverityBadge({ severity }: { severity: IncidentSeverity }) {
  if (severity === "P0_CRITICAL") {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-rose-500/10 px-2 py-0.5 text-xs font-semibold text-rose-400 border border-rose-500/20">
        <AlertOctagon className="h-3 w-3" /> P0 CRITICAL
      </span>
    );
  }
  if (severity === "P1_HIGH") {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-400 border border-amber-500/20">
        <AlertTriangle className="h-3 w-3" /> P1 HIGH
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded bg-yellow-500/10 px-2 py-0.5 text-xs font-semibold text-yellow-400 border border-yellow-500/20">
      <Activity className="h-3 w-3" /> P2 MEDIUM
    </span>
  );
}

export function IncidentScenarioCard({ scenario, onSelect, starting }: IncidentScenarioCardProps) {
  return (
    <div className="flex flex-col justify-between rounded-xl border border-zinc-800/80 bg-zinc-950/80 p-5 hover:border-rose-700/50 transition-all space-y-4">
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <SeverityBadge severity={scenario.severity} />
          <span className="font-mono text-[10px] rounded bg-zinc-900 px-2 py-0.5 text-zinc-400 border border-zinc-800">
            {scenario.category}
          </span>
        </div>
        <h3 className="font-semibold text-zinc-100 text-base leading-snug">{scenario.title}</h3>
        <p className="text-xs text-zinc-400 leading-relaxed">{scenario.hypothetical_trigger}</p>
        
        <div className="rounded-lg bg-zinc-900/60 p-3 space-y-2 border border-zinc-800/40 text-xs font-mono">
          <div className="flex items-center gap-1.5 text-zinc-300">
            <Code2 className="h-3.5 w-3.5 text-rose-400" />
            <span className="truncate">{scenario.grounded_target.file_path}</span>
          </div>
          {scenario.grounded_target.symbol_name && (
            <div className="text-[11px] text-zinc-400 pl-5">
              Target: <span className="text-rose-300">{scenario.grounded_target.symbol_name}</span>
            </div>
          )}
        </div>
      </div>

      <button
        type="button"
        disabled={starting}
        onClick={() => onSelect(scenario.id)}
        className="w-full flex items-center justify-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-medium py-2 text-xs transition-colors shadow-lg shadow-rose-950/40"
      >
        {starting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Flame className="h-3.5 w-3.5" />}
        Launch Incident Defense
      </button>
    </div>
  );
}
