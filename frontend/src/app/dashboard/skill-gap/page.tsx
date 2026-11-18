"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  GraduationCap,
  Loader2,
  RefreshCw,
  Sparkles,
  Target,
} from "lucide-react";
import { BenchmarkComparisonMatrix } from "@/components/domain/BenchmarkComparisonMatrix";
import { SkillGapRemediationsCard } from "@/components/domain/SkillGapRemediationsCard";
import { SkillRadarChart } from "@/components/domain/SkillRadarChart";
import { fetchSkillGapAnalysis } from "@/lib/skillGapApi";
import { supabase } from "@/lib/supabase";
import {
  getRoleDisplayName,
  type SkillGapAnalysisResponse,
  type TargetRoleBenchmark,
} from "@/types/skillGap";

export default function SkillGapPage() {
  const [data, setData] = useState<SkillGapAnalysisResponse | null>(null);
  const [targetRole, setTargetRole] = useState<TargetRoleBenchmark>("senior_engineer");
  const [projectId, setProjectId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadCounter, setReloadCounter] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;
    async function fetchUserProjects() {
      try {
        const { data: authData } = await supabase.auth.getSession();
        const token = authData.session?.access_token;
        if (!token) return;
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/v1/projects`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const rawProjects: unknown = await res.json();
        if (!cancelled && Array.isArray(rawProjects) && rawProjects.length > 0) {
          const first = rawProjects[0];
          if (
            typeof first === "object" &&
            first !== null &&
            "id" in first &&
            typeof first.id === "string" &&
            first.id.trim().length > 0
          ) {
            setProjectId(first.id);
          }
        }
      } catch {
        // non-blocking fallback
      }
    }
    fetchUserProjects();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadData = useCallback(async (role: TargetRoleBenchmark, isCancelled?: () => boolean) => {
    setLoading(true);
    setError(null);
    try {
      const { data: authData } = await supabase.auth.getSession();
      const token = authData.session?.access_token;
      if (!token) {
        window.location.href = "/login";
        return;
      }

      const res = await fetchSkillGapAnalysis(token, role);
      if (isCancelled?.()) return;
      setData(res);
    } catch (err) {
      if (!isCancelled?.()) {
        setError(err instanceof Error ? err.message : "Failed to load skill gap analysis");
      }
    } finally {
      if (!isCancelled?.()) setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadData(targetRole, () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [targetRole, reloadCounter, loadData]);

  const allAtOrAbove = Boolean(data && data.categories.length > 0 && data.categories.every((c) => c.gap_deficit <= 0));

  return (
    <div className="min-h-screen bg-black text-zinc-100">
      {/* Navigation Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-20">
        <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard/progress"
              className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Progress Dashboard</span>
            </Link>
            <span className="text-zinc-700">/</span>
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                <Target className="h-4 w-4" />
              </div>
              <h1 className="text-sm font-bold text-zinc-100">
                Senior Benchmark & Skill Gap Analysis
              </h1>
            </div>
          </div>

          {/* Role Benchmark Selector */}
          <div className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/80 p-1">
            {(
              [
                ["mid_level", "Mid-Level"],
                ["senior_engineer", "Senior"],
                ["staff_principal", "Staff / Principal"],
              ] as const
            ).map(([val, label]) => (
              <button
                key={val}
                type="button"
                onClick={() => setTargetRole(val)}
                className={`rounded-md px-3 py-1 text-xs font-semibold transition-all ${
                  targetRole === val
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => setReloadCounter((c) => c + 1)}
              className="inline-flex items-center gap-1 rounded bg-red-500/20 px-2.5 py-1 font-semibold text-red-200 hover:bg-red-500/30"
            >
              <RefreshCw className="h-3 w-3" /> Retry
            </button>
          </div>
        )}

        {loading && !data ? (
          <div className="flex min-h-[400px] items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
          </div>
        ) : data ? (
          data.categories.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-12 text-center space-y-4 backdrop-blur-sm">
              <Sparkles className="mx-auto h-12 w-12 text-indigo-400" />
              <h2 className="text-base font-bold text-zinc-100">No Assessment Data Available</h2>
              <p className="text-xs text-zinc-400 max-w-md mx-auto leading-relaxed">
                Complete repository defense interviews to benchmark your architectural competencies across system design, security, and scalability against senior standards.
              </p>
              <div className="pt-2">
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors shadow-sm shadow-indigo-600/30"
                >
                  <span>Go to Repositories</span>
                </Link>
              </div>
            </div>
          ) : (
            <>
              {/* Top Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5 backdrop-blur-sm">
                  <span className="text-xs text-zinc-400 font-medium">Role Readiness</span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-3xl font-extrabold text-zinc-100 font-mono">
                      {data.overall_readiness_pct}%
                    </span>
                    <span className="text-xs text-indigo-400">vs {getRoleDisplayName(data.target_role)}</span>
                  </div>
                  <div className="mt-3 h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-indigo-500 transition-all duration-300"
                      style={{ width: `${Math.min(100, Math.max(5, data.overall_readiness_pct))}%` }}
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5 backdrop-blur-sm">
                  <span className="text-xs text-zinc-400 font-medium">Your Composite Score</span>
                  <div className="mt-2 text-3xl font-extrabold text-emerald-400 font-mono">
                    {data.overall_candidate_score}
                    <span className="text-sm font-normal text-zinc-500"> / 100</span>
                  </div>
                  <p className="mt-2 text-[11px] text-zinc-500">
                    Weighted across all assessed architectural categories
                  </p>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5 backdrop-blur-sm">
                  <span className="text-xs text-zinc-400 font-medium">Target Benchmark</span>
                  <div className="mt-2 text-3xl font-extrabold text-indigo-400 font-mono">
                    {data.overall_benchmark_score}
                    <span className="text-sm font-normal text-zinc-500"> / 100</span>
                  </div>
                  <p className="mt-2 text-[11px] text-zinc-500">
                    Standard expected bar for {getRoleDisplayName(data.target_role)}
                  </p>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5 backdrop-blur-sm">
                  <span className="text-xs text-zinc-400 font-medium">Domain Health</span>
                  <div className="mt-2 flex items-center gap-3">
                    <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>{data.strengths.length} Met</span>
                    </div>
                    <span className="text-zinc-600">|</span>
                    <div className="flex items-center gap-1.5 text-xs text-rose-400 font-semibold">
                      <Sparkles className="h-4 w-4" />
                      <span>{data.critical_gaps.length} Gaps</span>
                    </div>
                  </div>
                  <p className="mt-2 text-[11px] text-zinc-500">
                    {allAtOrAbove ? "All domains at or above target benchmark" : "Targeted re-tests available to close deficits"}
                  </p>
                </div>
              </div>

              {/* Radar Visualizer & Comparison Matrix */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                <div className="lg:col-span-5 space-y-4">
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5 backdrop-blur-sm">
                    <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2 mb-1">
                      <GraduationCap className="h-4 w-4 text-emerald-400" />
                      Architectural Competency Radar
                    </h3>
                    <p className="text-xs text-zinc-400 mb-4">
                      Visual comparison of your demonstrated skills against the target engineering baseline.
                    </p>
                    <SkillRadarChart
                      categories={data.categories}
                      candidateLabel="Candidate Score"
                      benchmarkLabel={`${getRoleDisplayName(data.target_role)} Bar`}
                    />
                  </div>
                </div>

                <div className="lg:col-span-7">
                  <BenchmarkComparisonMatrix categories={data.categories} />
                </div>
              </div>

              {/* Prioritized Remediations Roadmap */}
              <SkillGapRemediationsCard
                recommendations={data.recommendations}
                projectId={projectId}
              />
            </>
          )
        ) : null}
      </main>
    </div>
  );
}
