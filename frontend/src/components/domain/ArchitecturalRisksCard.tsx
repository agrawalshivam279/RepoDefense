"use client";

import { AlertTriangle, CheckCircle2, Lightbulb, ShieldAlert } from "lucide-react";
import type { ArchitecturalRisk } from "@/types/architecture";

interface ArchitecturalRisksCardProps {
  risks: ArchitecturalRisk[];
}

const SEVERITY_CONFIG: Record<
  string,
  { badge: string; text: string; label: string }
> = {
  critical: {
    badge: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    text: "text-rose-400",
    label: "Critical",
  },
  high: {
    badge: "bg-orange-500/10 text-orange-400 border-orange-500/30",
    text: "text-orange-400",
    label: "High Severity",
  },
  medium: {
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    text: "text-amber-400",
    label: "Medium Severity",
  },
  low: {
    badge: "bg-sky-500/10 text-sky-400 border-sky-500/30",
    text: "text-sky-400",
    label: "Low Severity",
  },
};

export function ArchitecturalRisksCard({ risks }: ArchitecturalRisksCardProps) {
  return (
    <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 shadow-md space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            Architectural Risks & Blind Spots
          </h3>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Structural smells the Principal Engineer persona may probe in defense
          </p>
        </div>

        <span
          className={`px-2.5 py-0.5 rounded text-xs font-mono font-medium border ${
            risks.length > 0
              ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
              : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
          }`}
        >
          {risks.length} {risks.length === 1 ? "Risk" : "Risks"} Flagged
        </span>
      </div>

      {/* Content */}
      {risks.length === 0 ? (
        <div className="p-6 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-center space-y-2">
          <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
          <h4 className="text-sm font-semibold text-white">No Architectural Smells Flagged</h4>
          <p className="text-xs text-slate-400 font-mono max-w-md mx-auto">
            The repository exhibits clean layer boundaries, modular service abstractions, and clear
            asynchronous task isolation.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {risks.map((risk) => {
            const severity = SEVERITY_CONFIG[risk.severity] || SEVERITY_CONFIG.medium;

            return (
              <div
                key={risk.risk_id}
                className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-3 hover:border-slate-700/80 transition-colors"
              >
                {/* Risk Title & Severity Badge */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`w-4 h-4 ${severity.text} flex-shrink-0`} />
                    <span className="text-sm font-semibold text-white">{risk.title}</span>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded text-[11px] font-mono border self-start sm:self-auto ${severity.badge}`}
                  >
                    ● {severity.label}
                  </span>
                </div>

                {/* Risk Description */}
                <p className="text-xs text-slate-300 font-sans leading-relaxed">
                  {risk.description}
                </p>

                {/* Actionable Recommendation */}
                <div className="p-3 rounded bg-slate-900/90 border border-slate-800/80 flex items-start gap-2.5 text-xs text-slate-300">
                  <Lightbulb className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-amber-300 mr-1">Recommendation:</span>
                    <span>{risk.recommendation}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
