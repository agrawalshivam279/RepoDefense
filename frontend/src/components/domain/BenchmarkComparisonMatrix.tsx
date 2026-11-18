"use client";

import React from "react";
import { CheckCircle, ShieldAlert, Sparkles, TrendingUp } from "lucide-react";
import { getGapStatusBadge, type CategoryGapMetric } from "@/types/skillGap";

interface BenchmarkComparisonMatrixProps {
  categories: CategoryGapMetric[];
}

export function BenchmarkComparisonMatrix({ categories }: BenchmarkComparisonMatrixProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-6 backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <div>
          <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-indigo-400" />
            Category Competency Matrix
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            Technical domain breakdown comparing candidate capability against senior bar.
          </p>
        </div>
        <span className="text-xs text-zinc-500 font-mono">
          {categories.length} categories evaluated
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
        {categories.map((cat) => {
          const badge = getGapStatusBadge(cat.status);
          const name = cat.category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
          const ratio = Math.min(100, Math.round((cat.current_score / Math.max(cat.benchmark_score, 1)) * 100));

          return (
            <div
              key={cat.category}
              className={`rounded-lg border p-3.5 transition-colors bg-zinc-900/40 ${badge.borderClass}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h4 className="text-sm font-semibold text-zinc-200">{name}</h4>
                  <div className="mt-1 flex items-center gap-2 text-xs text-zinc-400">
                    <span>Target: <strong className="text-zinc-300">{cat.benchmark_score}</strong></span>
                    <span>•</span>
                    <span>Weight: <strong className="text-zinc-300">{cat.weight}x</strong></span>
                  </div>
                </div>
                <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold border ${badge.className}`}>
                  {badge.label}
                </span>
              </div>

              {/* Progress bar */}
              <div className="mt-3 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-400">
                    Score: <strong className="text-zinc-200 font-mono">{cat.current_score}</strong> / 100
                  </span>
                  <span className="text-zinc-500 font-mono text-[11px]">
                    {ratio}% of Target
                  </span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      cat.status === "surpassed"
                        ? "bg-emerald-500"
                        : cat.status === "met"
                        ? "bg-indigo-500"
                        : cat.status === "moderate_gap"
                        ? "bg-amber-500"
                        : "bg-rose-500"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, cat.current_score))}%` }}
                  />
                </div>
              </div>

              <div className="mt-2.5 flex items-center justify-between text-[11px] text-zinc-500 border-t border-zinc-800/60 pt-2">
                <span>Percentile: Top {Math.round(100 - cat.percentile_estimate)}%</span>
                {cat.gap_deficit > 0 ? (
                  <span className="text-rose-400 font-medium">Deficit: -{cat.gap_deficit} pts</span>
                ) : (
                  <span className="text-emerald-400 font-medium flex items-center gap-1">
                    <CheckCircle className="h-3 w-3" /> Met Target
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
