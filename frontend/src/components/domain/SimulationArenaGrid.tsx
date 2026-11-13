"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import {
  SIMULATION_MODES,
  type SimulationArenaMode,
  parseSimulationReadiness,
} from "../../types/simulationArena";

export {
  SIMULATION_MODES,
  type SimulationArenaMode,
  parseSimulationReadiness,
};

interface SimulationArenaGridProps {
  projectId: string;
}

export function SimulationArenaGrid({ projectId }: SimulationArenaGridProps) {
  const [sessionCounts, setSessionCounts] = useState<Record<string, number> | null>(null);
  const [loadingCounts, setLoadingCounts] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<boolean>(false);

  const fetchSessionCounts = useCallback((signal?: AbortSignal) => {
    setLoadingCounts(true);
    setFetchError(false);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/api/v1/health/simulations`, { signal })
      .then((res) => {
        if (!res.ok) throw new Error("Health check failed");
        return res.json();
      })
      .then((data: unknown) => {
        setSessionCounts(parseSimulationReadiness(data));
        setLoadingCounts(false);
      })
      .catch((err: Error) => {
        if (err.name !== "AbortError") {
          setFetchError(true);
          setLoadingCounts(false);
        }
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchSessionCounts(controller.signal);
    return () => {
      controller.abort();
    };
  }, [fetchSessionCounts]);

  const totalActive = sessionCounts
    ? Object.values(sessionCounts).reduce((acc, n) => acc + n, 0)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-mono uppercase tracking-wider mb-1">
            <Sparkles className="w-4 h-4" />
            <span>Interactive Defense Arena</span>
            {sessionCounts && totalActive > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30">
                {totalActive} Active System-wide
              </span>
            )}
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Select a Simulation Engine
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Authenticate your repository comprehension against 6 principal-engineer level defense modes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {fetchError && (
            <button
              type="button"
              onClick={() => fetchSessionCounts()}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[11px] font-mono text-amber-300 hover:bg-amber-500/20 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Counts</span>
            </button>
          )}

          <Link
            href={`/projects/${projectId}/analytics`}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-emerald-400 hover:text-emerald-300 hover:border-emerald-500/40 transition-colors shrink-0 shadow-sm"
          >
            <BarChart3 className="w-4 h-4" />
            <span>Readiness Telemetry</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* 6-Card Arena Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SIMULATION_MODES.map((mode) => {
          const { Icon } = mode;
          const href = mode.hrefTemplate(projectId);
          const activeCount = sessionCounts ? sessionCounts[mode.id] : undefined;

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

                {/* Active Sessions Counter */}
                <div className="pt-2 flex items-center justify-between text-[11px] font-mono border-t border-slate-800/50">
                  <span className="text-slate-500">Live Engine</span>
                  {loadingCounts ? (
                    <span className="text-slate-500 animate-pulse text-[10px]">
                      Checking...
                    </span>
                  ) : typeof activeCount === "number" ? (
                    <span className="flex items-center gap-1.5">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          activeCount > 0
                            ? "bg-emerald-400 animate-pulse"
                            : "bg-slate-600"
                        }`}
                      />
                      <span
                        className={
                          activeCount > 0
                            ? "text-emerald-400 font-semibold"
                            : "text-slate-400"
                        }
                      >
                        {activeCount} active
                      </span>
                    </span>
                  ) : (
                    <span className="text-slate-500 text-[10px]">Ready</span>
                  )}
                </div>
              </div>

              <div className="pt-4 mt-3 border-t border-slate-800/80">
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
