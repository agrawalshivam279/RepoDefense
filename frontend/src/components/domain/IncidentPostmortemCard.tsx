"use client";

import { CheckCircle2, RotateCcw } from "lucide-react";

interface IncidentPostmortemCardProps {
  overallScore?: number | null;
  postmortemSummary?: string | null;
  onSimulateAnother: () => void;
}

export function IncidentPostmortemCard({
  overallScore,
  postmortemSummary,
  onSimulateAnother,
}: IncidentPostmortemCardProps) {
  return (
    <div className="rounded-xl border border-emerald-500/40 bg-gradient-to-b from-emerald-950/30 to-zinc-950 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-emerald-400 font-semibold text-base">
          <CheckCircle2 className="h-5 w-5" /> Incident Resolved & Postmortem Published
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold font-mono text-emerald-300">{overallScore ?? 0}</span>
          <span className="text-xs text-zinc-400">/100</span>
        </div>
      </div>
      <p className="text-xs text-zinc-300 leading-relaxed bg-zinc-900/60 p-4 rounded-lg border border-zinc-800">
        {postmortemSummary}
      </p>
      <button
        type="button"
        onClick={onSimulateAnother}
        className="flex items-center gap-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-100 px-4 py-2 text-xs font-medium transition-colors"
      >
        <RotateCcw className="h-3.5 w-3.5" /> Simulate Another Incident
      </button>
    </div>
  );
}
