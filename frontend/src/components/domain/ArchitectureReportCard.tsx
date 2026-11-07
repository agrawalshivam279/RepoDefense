"use client";

import { CheckCircle2, Layers, Network, ShieldCheck } from "lucide-react";
import type { DetectedPattern, PatternConfidenceTier } from "@/types/architecture";

interface ArchitectureReportCardProps {
  primaryPattern: DetectedPattern;
  secondaryPatterns: DetectedPattern[];
  totalFiles: number;
}

const TIER_STYLES: Record<
  PatternConfidenceTier,
  { badge: string; border: string; label: string; text: string; bar: string }
> = {
  high: {
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    border: "border-emerald-500/30",
    label: "High Confidence",
    text: "text-emerald-400",
    bar: "bg-emerald-500",
  },
  moderate: {
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    border: "border-amber-500/30",
    label: "Moderate Confidence",
    text: "text-amber-400",
    bar: "bg-amber-500",
  },
  low: {
    badge: "bg-slate-500/10 text-slate-400 border-slate-500/30",
    border: "border-slate-700",
    label: "Low Confidence",
    text: "text-slate-400",
    bar: "bg-slate-500",
  },
};

export function ArchitectureReportCard({
  primaryPattern,
  secondaryPatterns,
  totalFiles,
}: ArchitectureReportCardProps) {
  const tierStyle = TIER_STYLES[primaryPattern.tier] || TIER_STYLES.low;
  const primaryPercentage = Math.round(primaryPattern.confidence_score * 100);

  return (
    <div className={`p-6 rounded-xl bg-slate-900/80 border ${tierStyle.border} shadow-lg space-y-6`}>
      {/* Header with Pattern Name & Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
              Primary Architecture
            </span>
            <span
              className={`px-2.5 py-0.5 rounded text-[11px] font-mono font-medium uppercase border ${tierStyle.badge}`}
            >
              ● {tierStyle.label} ({primaryPercentage}%)
            </span>
          </div>
          <div className="flex items-center gap-2.5 pt-1">
            <Network className={`w-6 h-6 ${tierStyle.text} flex-shrink-0`} />
            <h2 className="text-xl font-bold text-white tracking-tight">
              {primaryPattern.pattern_name}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-slate-400 bg-slate-950/60 px-3.5 py-2 rounded-lg border border-slate-800 self-start sm:self-auto">
          <Layers className="w-4 h-4 text-sky-400" />
          <span>Analyzed {totalFiles.toLocaleString()} files</span>
        </div>
      </div>

      {/* Primary Pattern Confidence Meter */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-slate-400 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Heuristic Match Strength
          </span>
          <span className={`font-semibold ${tierStyle.text}`}>{primaryPercentage}% Match</span>
        </div>
        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full ${tierStyle.bar} transition-all duration-500 rounded-full`}
            style={{ width: `${Math.max(5, primaryPercentage)}%` }}
          />
        </div>
      </div>

      {/* Summary Narrative */}
      <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800/80 text-sm text-slate-300 leading-relaxed font-sans">
        <p>{primaryPattern.summary}</p>
      </div>

      {/* Secondary Patterns */}
      {secondaryPatterns.length > 0 && (
        <div className="space-y-3 pt-2 border-t border-slate-800/80">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <CheckCircle2 className="w-3.5 h-3.5 text-slate-500" />
            <span>Co-existing / Secondary Architectural Signals</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {secondaryPatterns.map((pattern) => {
              const secPercentage = Math.round(pattern.confidence_score * 100);
              const secTier = TIER_STYLES[pattern.tier] || TIER_STYLES.low;

              return (
                <div
                  key={pattern.pattern_type}
                  className="p-3 rounded-lg bg-slate-950/40 border border-slate-800 flex flex-col justify-between space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">{pattern.pattern_name}</span>
                    <span className={`font-mono text-[11px] ${secTier.text}`}>
                      {secPercentage}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${secTier.bar} rounded-full`}
                      style={{ width: `${Math.max(4, secPercentage)}%` }}
                    />
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-1">{pattern.summary}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
