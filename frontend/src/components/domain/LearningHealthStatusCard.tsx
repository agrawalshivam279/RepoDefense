"use client";

import React from "react";
import {
  Activity,
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Database,
  GraduationCap,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import type { ComponentHealthStatus, LearningLoopHealthResponse } from "@/types/learning";

export interface LearningHealthStatusCardProps {
  healthReport: LearningLoopHealthResponse | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  className?: string;
}

function getBadge(status: ComponentHealthStatus) {
  switch (status) {
    case "healthy":
      return {
        label: "Operational",
        icon: CheckCircle2,
        pillClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      };
    case "degraded":
      return {
        label: "Degraded",
        icon: AlertTriangle,
        pillClass: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      };
    case "unhealthy":
    default:
      return {
        label: "Outage",
        icon: ShieldAlert,
        pillClass: "bg-rose-500/10 text-rose-400 border-rose-500/20",
      };
  }
}

export function LearningHealthStatusCard({
  healthReport,
  loading,
  error,
  onRefresh,
  className = "",
}: LearningHealthStatusCardProps) {
  const overallBadge = healthReport ? getBadge(healthReport.status) : null;
  const OverallIcon = overallBadge?.icon || Activity;

  return (
    <div className={`rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-5 ${className}`}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
              <span>Phase 4 Subsystem Diagnostic Telemetry</span>
              {overallBadge && (
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-mono border ${overallBadge.pillClass}`}
                >
                  <OverallIcon className="h-3 w-3" />
                  <span>{overallBadge.label}</span>
                </span>
              )}
            </h2>
            <p className="text-xs text-zinc-400">
              Live operational readiness for weakness tracking, mentor mode, benchmark catalog & re-testing
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-mono text-zinc-300 hover:text-zinc-100 hover:border-zinc-700 transition-colors disabled:opacity-50"
          title="Run live diagnostic health probe"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Probe Subsystems</span>
        </button>
      </div>

      {/* Error Notice */}
      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Subsystem Metric Grid */}
      {healthReport && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
          {/* 1. Database Models */}
          <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/50 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
                <Database className="h-3.5 w-3.5 text-emerald-400" />
                <span>Skills Database</span>
              </div>
              <span
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  getBadge(healthReport.database_models.status).pillClass
                }`}
              >
                {getBadge(healthReport.database_models.status).label}
              </span>
            </div>
            <div className="text-xs text-zinc-300 space-y-1">
              <div className="flex justify-between font-mono">
                <span className="text-zinc-500">Skills Tracked:</span>
                <span className="font-semibold text-zinc-200">
                  {healthReport.database_models.total_user_skills}
                </span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-zinc-500">Active Deficits:</span>
                <span className="font-semibold text-zinc-200">
                  {healthReport.database_models.total_candidate_weaknesses}
                </span>
              </div>
            </div>
          </div>

          {/* 2. Benchmark Profiles */}
          <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/50 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
                <BookOpen className="h-3.5 w-3.5 text-indigo-400" />
                <span>Benchmark Profiles</span>
              </div>
              <span
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  getBadge(healthReport.benchmark_profiles.status).pillClass
                }`}
              >
                {getBadge(healthReport.benchmark_profiles.status).label}
              </span>
            </div>
            <div className="text-xs text-zinc-300 space-y-1">
              <div className="flex justify-between font-mono">
                <span className="text-zinc-500">Configured Tiers:</span>
                <span className="font-semibold text-zinc-200">
                  {healthReport.benchmark_profiles.configured_tiers.length} Tiers
                </span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-zinc-500">Domain Metrics:</span>
                <span className="font-semibold text-zinc-200">
                  {healthReport.benchmark_profiles.total_categories} Categories
                </span>
              </div>
            </div>
          </div>

          {/* 3. Mentor Service */}
          <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/50 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
                <GraduationCap className="h-3.5 w-3.5 text-purple-400" />
                <span>Mentor Engine</span>
              </div>
              <span
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  getBadge(healthReport.mentor_service.status).pillClass
                }`}
              >
                {getBadge(healthReport.mentor_service.status).label}
              </span>
            </div>
            <div className="text-xs text-zinc-300 space-y-1">
              <div className="flex justify-between font-mono">
                <span className="text-zinc-500">Offline Fallbacks:</span>
                <span className="font-semibold text-zinc-200">
                  {healthReport.mentor_service.fallbacks_ready ? "Ready" : "Disabled"}
                </span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-zinc-500">Fallback Topics:</span>
                <span className="font-semibold text-zinc-200">
                  {healthReport.mentor_service.supported_fallback_topics.length} Supported
                </span>
              </div>
            </div>
          </div>

          {/* 4. Retest Service */}
          <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/50 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
                <RotateCcw className="h-3.5 w-3.5 text-cyan-400" />
                <span>Re-Test Cache</span>
              </div>
              <span
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  getBadge(healthReport.retest_service.status).pillClass
                }`}
              >
                {getBadge(healthReport.retest_service.status).label}
              </span>
            </div>
            <div className="text-xs text-zinc-300 space-y-1">
              <div className="flex justify-between font-mono">
                <span className="text-zinc-500">Cached Questions:</span>
                <span className="font-semibold text-zinc-200">
                  {healthReport.retest_service.cached_question_count}
                </span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-zinc-500">Capacity Limit:</span>
                <span className="font-semibold text-zinc-200">
                  {healthReport.retest_service.max_cache_capacity} Max
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
