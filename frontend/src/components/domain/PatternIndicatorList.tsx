"use client";

import { useState } from "react";
import { FolderTree, Package, Shield, Sparkles } from "lucide-react";
import type { PatternIndicator } from "@/types/architecture";

interface PatternIndicatorListProps {
  indicators: PatternIndicator[];
  patternName: string;
}

const TYPE_CONFIG: Record<
  string,
  { label: string; badge: string; icon: typeof FolderTree }
> = {
  directory: {
    label: "Directory Signal",
    badge: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
    icon: FolderTree,
  },
  dependency: {
    label: "Dependency Signal",
    badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    icon: Package,
  },
  evidence: {
    label: "Evidence Signal",
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    icon: Shield,
  },
};

export function PatternIndicatorList({ indicators, patternName }: PatternIndicatorListProps) {
  const [filterType, setFilterType] = useState<string>("all");

  const filteredIndicators = indicators.filter((ind) => {
    if (filterType === "all") return true;
    return ind.indicator_type === filterType;
  });

  return (
    <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 shadow-md space-y-5">
      {/* Header and Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            Pattern Detection Indicators
          </h3>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Deterministic signals supporting {patternName}
          </p>
        </div>

        <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-mono">
          {["all", "directory", "dependency", "evidence"].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setFilterType(t)}
              className={`px-2.5 py-1 rounded capitalize transition-colors ${
                filterType === t
                  ? "bg-slate-800 text-emerald-400 font-medium"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Indicators List */}
      {filteredIndicators.length === 0 ? (
        <div className="py-8 text-center text-xs font-mono text-slate-500">
          No indicators found for filter: {filterType}
        </div>
      ) : (
        <div className="space-y-3">
          {filteredIndicators.map((ind, idx) => {
            const config = TYPE_CONFIG[ind.indicator_type] || {
              label: ind.indicator_type,
              badge: "bg-slate-500/10 text-slate-400 border-slate-500/20",
              icon: Sparkles,
            };
            const Icon = config.icon;
            const weightPercentage = Math.round(ind.weight * 100);

            return (
              <div
                key={`${ind.indicator_type}-${idx}`}
                className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-2 hover:border-slate-700/80 transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono border ${config.badge}`}
                    >
                      <Icon className="w-3 h-3" />
                      {config.label}
                    </span>
                    <span className="text-xs text-slate-300 font-medium truncate">
                      {ind.description}
                    </span>
                  </div>

                  <span className="font-mono text-[11px] text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 flex-shrink-0">
                    +{weightPercentage}% weight
                  </span>
                </div>

                {/* Matched Items Cloud */}
                {ind.matched_items.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="text-[10px] font-mono text-slate-500 mr-1">Matches:</span>
                    {ind.matched_items.map((item, itemIdx) => (
                      <span
                        key={itemIdx}
                        className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
