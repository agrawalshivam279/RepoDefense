"use client";

import React from "react";
import Link from "next/link";
import { Activity, ArrowUpRight, Code2, FolderGit2, Layers } from "lucide-react";
import { getBarColor } from "@/components/domain/AnalyticsCharts";
import type {
  DefenseModeKey,
  LanguageDistributionItem,
  ModePerformanceMetric,
  ModuleCoveragePoint,
  WorkspaceAnalyticsSummary,
} from "@/types/analytics";

const MODE_ROUTE_SUFFIX: Record<DefenseModeKey, (projectId: string) => string> = {
  core_defense: (id) => `/interview/${id}`,
  pr_defense: (id) => `/projects/${id}/pr-defense`,
  commit_defense: (id) => `/projects/${id}/commit-defense`,
  stress_test: (id) => `/projects/${id}/stress-test`,
  incident_simulation: (id) => `/projects/${id}/incident-simulation`,
  arch_defense: (id) => `/projects/${id}/arch-defense`,
};

const LANG_SWATCHES = [
  "bg-emerald-500",
  "bg-cyan-500",
  "bg-indigo-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-purple-500",
];

function coverageFillClass(pct: number): string {
  if (pct >= 75) return "bg-emerald-500";
  if (pct >= 45) return "bg-sky-500";
  if (pct >= 20) return "bg-amber-500";
  return "bg-rose-500";
}

export interface LanguageBreakdownCardProps {
  items: LanguageDistributionItem[];
}

export function LanguageBreakdownCard({ items }: LanguageBreakdownCardProps) {
  const totalLines = items.reduce((acc, item) => acc + item.total_lines, 0);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-white">Repository Language Footprint</h2>
        </div>
        <span className="text-[11px] font-mono text-slate-400">{totalLines.toLocaleString()} LOC</span>
      </div>

      {items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-800 bg-slate-950/50 p-6 text-center text-sm text-slate-400">
          No analyzed source files indexed for this repository yet.
        </p>
      ) : (
        <>
          <div className="h-3 w-full rounded-full bg-slate-800 overflow-hidden flex">
            {items.map((lang, idx) => (
              <div
                key={lang.language}
                className={LANG_SWATCHES[idx % LANG_SWATCHES.length]}
                style={{ width: `${Math.max(lang.line_share_pct, 1.5)}%` }}
                title={`${lang.language}: ${lang.line_share_pct.toFixed(1)}%`}
              />
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {items.map((lang, idx) => (
              <div
                key={lang.language}
                className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-xs"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${LANG_SWATCHES[idx % LANG_SWATCHES.length]}`} />
                  <span className="font-medium text-slate-200 truncate">{lang.language}</span>
                </div>
                <span className="font-mono text-slate-400 whitespace-nowrap">
                  {lang.line_share_pct.toFixed(1)}% ({lang.file_count}f)
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export interface ModuleCoverageListProps {
  modules: ModuleCoveragePoint[];
}

export function ModuleCoverageList({ modules }: ModuleCoverageListProps) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-white">Module Defense Coverage</h2>
        </div>
        <span className="text-[11px] font-mono text-slate-400">{modules.length} directories</span>
      </div>

      {modules.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-800 bg-slate-950/50 p-6 text-center text-sm text-slate-400">
          Module coverage metrics appear once repository evidence mapping completes.
        </p>
      ) : (
        <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
          {modules.map((mod) => (
            <div key={mod.module_path} className="space-y-1 rounded-lg border border-slate-800/80 bg-slate-950/50 p-2.5">
              <div className="flex items-center justify-between gap-2 text-xs font-mono">
                <span className="text-slate-200 truncate">{mod.module_path}</span>
                <span className="text-slate-300 whitespace-nowrap">
                  {mod.coverage_pct.toFixed(1)}% ({mod.tested_files}/{mod.total_files})
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={`h-full rounded-full ${coverageFillClass(mod.coverage_pct)}`}
                  style={{ width: `${Math.max(0, Math.min(100, mod.coverage_pct))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export interface WorkspaceBenchmarkCardProps {
  projectReadiness: number | null;
  workspace: WorkspaceAnalyticsSummary | null;
}

export function WorkspaceBenchmarkCard({ projectReadiness, workspace }: WorkspaceBenchmarkCardProps) {
  if (!workspace) return null;

  const wsAvg = workspace.avg_readiness_pct;
  const delta =
    projectReadiness !== null && wsAvg !== null ? Number((projectReadiness - wsAvg).toFixed(1)) : null;

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
          <FolderGit2 className="w-4 h-4 text-cyan-400" />
        </div>
        <div>
          <p className="text-xs font-semibold text-white">Workspace Readiness Benchmark</p>
          <p className="text-[11px] font-mono text-slate-400">
            {workspace.analyzed_projects}/{workspace.total_projects} projects analyzed |{" "}
            {workspace.completed_sessions}/{workspace.total_sessions} defense runs completed
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 font-mono text-xs">
        <span className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300">
          Workspace Avg: {wsAvg !== null ? `${wsAvg.toFixed(1)}%` : "Unavailable"}
        </span>
        {delta !== null && (
          <span
            className={`px-2.5 py-1 rounded border font-semibold ${
              delta >= 0
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-amber-500/10 border-amber-500/30 text-amber-400"
            }`}
          >
            {delta >= 0 ? `+${delta.toFixed(1)}%` : `${delta.toFixed(1)}%`} vs workspace
          </span>
        )}
      </div>
    </section>
  );
}

export interface ModePerformanceBarsProps {
  modes: ModePerformanceMetric[];
  projectId: string;
}

export function ModePerformanceBars({ modes, projectId }: ModePerformanceBarsProps) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-white">Performance by Defense Mode</h2>
        </div>
        <span className="text-[11px] font-mono text-slate-400">6 simulation tracks</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {modes.map((m) => {
          const avg = m.avg_score_pct;
          return (
            <div key={m.mode} className="rounded-lg border border-slate-800 bg-slate-950/60 p-3.5 space-y-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-slate-100">{m.label}</span>
                <Link
                  href={MODE_ROUTE_SUFFIX[m.mode](projectId)}
                  className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 hover:text-emerald-300"
                >
                  <span>Open</span>
                  <ArrowUpRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${avg !== null ? getBarColor(avg) : "bg-slate-700"}`}
                  style={{ width: `${avg ?? 0}%` }}
                />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-400">
                <span>{m.sessions_completed}/{m.sessions_total} completed</span>
                <span>
                  Avg: {avg !== null ? `${avg.toFixed(1)}%` : "N/A"} | Pass:{" "}
                  {m.pass_rate_pct !== null ? `${m.pass_rate_pct.toFixed(0)}%` : "N/A"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
