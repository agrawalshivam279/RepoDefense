"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertCircle, CheckCircle2, Gauge, Layers, Loader2, ShieldCheck } from "lucide-react";
import { ReadinessTrendChart, SkillRadarChart } from "@/components/domain/AnalyticsCharts";
import {
  LanguageBreakdownCard,
  ModePerformanceBars,
  ModuleCoverageList,
  WorkspaceBenchmarkCard,
} from "@/components/domain/AnalyticsGroundTruthPanels";
import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { getProjectAnalytics, getWorkspaceAnalytics } from "@/lib/analyticsApi";
import { getProjectOverview } from "@/lib/projectApi";
import { supabase } from "@/lib/supabase";
import type {
  DefenseModeKey,
  ProjectAnalyticsResponse,
  WorkspaceAnalyticsSummary,
} from "@/types/analytics";
import type { ProjectOverviewResponse } from "@/types/project";

function formatPctMetric(value: number | null): string {
  return value === null ? "Unavailable" : `${value.toFixed(1)}%`;
}

export default function ProjectAnalyticsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const projectId = typeof params?.id === "string" ? params.id : "";

  const [overview, setOverview] = useState<ProjectOverviewResponse | null>(null);
  const [analytics, setAnalytics] = useState<ProjectAnalyticsResponse | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceAnalyticsSummary | null>(null);
  const [selectedMode, setSelectedMode] = useState<DefenseModeKey | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isMountedRef = useRef(true);
  const abortRef = useRef<AbortController | null>(null);
  const requestSeqRef = useRef(0);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      abortRef.current?.abort();
    };
  }, []);

  const getAuthToken = useCallback(async (): Promise<string | null> => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
      router.replace("/login");
      return null;
    }
    return token;
  }, [router]);

  const loadDashboard = useCallback(async () => {
    if (!projectId) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const reqId = ++requestSeqRef.current;

    setLoading(true);
    setError(null);

    try {
      const token = await getAuthToken();
      if (!token || !isMountedRef.current || controller.signal.aborted) return;

      const [projectResult, workspaceResult, overviewResult] = await Promise.allSettled([
        getProjectAnalytics(projectId, token, controller.signal),
        getWorkspaceAnalytics(token, controller.signal),
        getProjectOverview(projectId, token),
      ]);

      if (!isMountedRef.current || controller.signal.aborted || reqId !== requestSeqRef.current) {
        return;
      }

      if (projectResult.status === "rejected") {
        const msg =
          projectResult.reason instanceof Error
            ? projectResult.reason.message
            : "Failed to load repository analytics.";
        setError(msg);
      } else {
        setAnalytics(projectResult.value);
      }

      if (workspaceResult.status === "fulfilled") {
        setWorkspace(workspaceResult.value);
      }
      if (overviewResult.status === "fulfilled") {
        setOverview(overviewResult.value);
      }
    } catch (err) {
      if (controller.signal.aborted || !isMountedRef.current) return;
      setError(err instanceof Error ? err.message : "Failed to load analytics dashboard.");
    } finally {
      if (isMountedRef.current && reqId === requestSeqRef.current) {
        setLoading(false);
      }
    }
  }, [projectId, getAuthToken]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const filteredTrend = useMemo(() => {
    if (!analytics) return [];
    if (!selectedMode) return analytics.score_trend;
    return analytics.score_trend.filter((pt) => pt.mode === selectedMode);
  }, [analytics, selectedMode]);

  const kpiCards = useMemo(() => {
    if (!analytics) return [];
    return [
      {
        label: "Overall Readiness",
        value: formatPctMetric(analytics.overall_readiness_pct),
        detail: `${analytics.completed_sessions}/${analytics.total_sessions} defense sessions completed`,
        accent: "text-emerald-400",
        Icon: ShieldCheck,
      },
      {
        label: "File Coverage",
        value: formatPctMetric(analytics.file_coverage_pct),
        detail: "Static repository source files defended",
        accent: "text-cyan-400",
        Icon: Layers,
      },
      {
        label: "Evidence Coverage",
        value: formatPctMetric(analytics.evidence_coverage_pct),
        detail: "Verified AST & runtime evidence hits",
        accent: "text-sky-400",
        Icon: CheckCircle2,
      },
      {
        label: "Tech Health Score",
        value: analytics.tech_health_score === null ? "Unavailable" : `${analytics.tech_health_score}/100`,
        detail: "Static dependency & config hygiene",
        accent: "text-amber-400",
        Icon: Gauge,
      },
    ];
  }, [analytics]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        <ProjectNavHeader
          projectId={projectId}
          projectName={overview?.name ?? analytics?.project_name ?? "Repository"}
          githubUrl={overview?.github_url}
          defaultBranch={overview?.default_branch}
          commitHash={overview?.commit_hash}
          activeTab="analytics"
          statusBadge={overview?.status ?? "analyzed"}
          subtitle="Cross-mode performance telemetry & codebase coverage"
          onRefresh={() => void loadDashboard()}
          isRefreshing={loading}
        />

        {error && (
          <div
            role="alert"
            className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 flex items-start gap-3 text-sm text-rose-200"
          >
            <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-rose-100">Unable to load performance analytics</p>
              <p className="text-xs text-rose-300 font-mono">{error}</p>
            </div>
          </div>
        )}

        {loading && !analytics ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-12 flex flex-col items-center justify-center gap-3 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
            <p className="text-sm font-mono">Aggregating defense telemetry and static coverage...</p>
          </div>
        ) : analytics ? (
          <div className="space-y-6">
            <WorkspaceBenchmarkCard
              projectReadiness={analytics.overall_readiness_pct}
              workspace={workspace}
            />

            <section aria-label="Key Performance Indicators" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              {kpiCards.map(({ label, value, detail, accent, Icon }) => (
                <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">{label}</span>
                    <Icon className={`w-4 h-4 ${accent}`} />
                  </div>
                  <p className={`text-2xl font-bold font-mono ${value === "Unavailable" ? "text-slate-500 text-lg" : "text-white"}`}>
                    {value}
                  </p>
                  <p className="text-[11px] text-slate-400">{detail}</p>
                </div>
              ))}
            </section>

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
              <span className="text-xs font-mono text-slate-300">Filter Trajectory by Simulation Mode:</span>
              <select
                aria-label="Filter score trend by defense mode"
                value={selectedMode}
                onChange={(e) => setSelectedMode(e.target.value as DefenseModeKey | "")}
                className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="">All Defense Modes</option>
                {analytics.mode_breakdown.map((m) => (
                  <option key={m.mode} value={m.mode}>
                    {m.label} ({m.sessions_completed})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <ReadinessTrendChart points={filteredTrend} projectId={projectId} />
              </div>
              <SkillRadarChart skills={analytics.category_skills} />
            </div>

            <ModePerformanceBars modes={analytics.mode_breakdown} projectId={projectId} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <LanguageBreakdownCard items={analytics.language_distribution} />
              <ModuleCoverageList modules={analytics.module_coverage} />
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}
