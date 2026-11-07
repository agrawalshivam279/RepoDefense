"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Code2,
  FileCode,
  Layers,
  Loader2,
  Package,
  Shield,
  Sparkles,
} from "lucide-react";

import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { TechStackBadgeCloud } from "@/components/domain/TechStackBadgeCloud";
import { getProjectOverview } from "@/lib/projectApi";
import { supabase } from "@/lib/supabase";
import type { ProjectOverviewResponse } from "@/types/project";

const LANGUAGE_COLORS: Record<string, string> = {
  Python: "bg-emerald-500", TypeScript: "bg-blue-500", JavaScript: "bg-amber-400",
  Go: "bg-cyan-500", HTML: "bg-orange-500", CSS: "bg-indigo-500", Rust: "bg-rose-500", Other: "bg-slate-600",
};

export default function ProjectOverviewPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [overview, setOverview] = useState<ProjectOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.push("/login"); return; }
      const data = await getProjectOverview(projectId, session.access_token);
      setOverview(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load project overview");
    } finally {
      setLoading(false);
    }
  }, [projectId, router]);

  useEffect(() => { fetchOverview(); }, [fetchOverview]);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="font-mono text-sm">Loading repository analysis overview...</p>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-6">
        <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mx-auto text-rose-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Project Overview Unavailable</h2>
        <p className="text-sm text-slate-400 font-mono">{error ?? "Project not found."}</p>
        <Link href="/dashboard" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:text-white font-mono text-xs border border-slate-700">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>
      </div>
    );
  }

  const isPending = ["pending", "cloning", "analyzing"].includes(overview.status);
  const { metrics, summary } = overview;
  const statCards = [
    { label: "Source Files", value: metrics.total_files, Icon: FileCode, color: "text-emerald-400" },
    { label: "Lines of Code", value: metrics.total_lines.toLocaleString(), Icon: Code2, color: "text-sky-400" },
    { label: "Dependencies", value: metrics.dependency_count, Icon: Package, color: "text-indigo-400" },
    { label: "Evidence Items", value: metrics.evidence_count, Icon: Shield, color: "text-amber-400" },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 text-slate-100">
      {/* Centralized Phase 2 Navigation Header */}
      <ProjectNavHeader
        projectId={overview.project_id}
        projectName={overview.name}
        githubUrl={overview.github_url}
        defaultBranch={overview.default_branch}
        commitHash={overview.commit_hash}
        activeTab="overview"
        statusBadge={overview.status}
        onRefresh={fetchOverview}
        isRefreshing={loading}
      />

      {/* Ingestion In-Progress Alert */}
      {isPending && (
        <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl flex items-center justify-between gap-3 text-xs font-mono text-blue-300">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
            <span>Repository cloning and AST analysis in progress. Metrics will populate shortly.</span>
          </div>
          <button type="button" onClick={fetchOverview} className="px-3 py-1 rounded bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 border border-blue-500/40">
            Refresh
          </button>
        </div>
      )}

      {/* Quantitative Metric Scorecards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map(({ label, value, Icon, color }) => (
          <div key={label} className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-1 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-mono">
              <span>{label}</span>
              <Icon className={`w-4 h-4 ${color}`} />
            </div>
            <div className="text-2xl font-bold font-mono text-white">{value}</div>
          </div>
        ))}
      </div>

      {/* Language Distribution Breakdown */}
      {metrics.languages.length > 0 && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span className="font-semibold text-slate-200">Language Distribution</span>
            <span>{metrics.languages.length} languages detected</span>
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden flex">
            {metrics.languages.map((l) => {
              const pct = metrics.total_lines > 0 ? (l.total_lines / metrics.total_lines) * 100 : 0;
              const color = LANGUAGE_COLORS[l.language] || LANGUAGE_COLORS.Other;
              return <div key={l.language} style={{ width: `${pct}%` }} className={`h-full ${color}`} title={`${l.language}: ${pct.toFixed(1)}%`} />;
            })}
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-1 text-xs font-mono">
            {metrics.languages.map((l) => {
              const color = LANGUAGE_COLORS[l.language] || LANGUAGE_COLORS.Other;
              const pct = metrics.total_lines > 0 ? (l.total_lines / metrics.total_lines) * 100 : 0;
              return (
                <div key={l.language} className="flex items-center gap-1.5 text-slate-300">
                  <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
                  <span>{l.language}</span>
                  <span className="text-slate-500">({pct.toFixed(0)}%)</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AI Architectural Overview */}
      {summary && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-7 space-y-5 shadow-sm">
          <div className="flex items-center gap-2.5 text-emerald-400 border-b border-slate-800 pb-3">
            <Sparkles className="w-5 h-5" />
            <h3 className="text-sm font-bold uppercase tracking-wider font-mono">AI Architectural Synthesis</h3>
          </div>
          <div className="space-y-2">
            <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">{summary.title}</h2>
            <p className="text-xs sm:text-sm text-slate-300 italic font-mono">&ldquo;{summary.tagline}&rdquo;</p>
          </div>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans">{summary.narrative}</p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-2">
            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider font-mono text-slate-200">
                Key Load-Bearing Components
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {summary.key_components.map((c, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-slate-950/60 border border-amber-500/20 rounded-xl p-4 space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider font-mono text-amber-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" /> Target Defense Stress Points
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {summary.potential_defense_topics.map((t, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Tech Stack & Dependencies Cloud */}
      <TechStackBadgeCloud
        detectedFrameworks={summary?.detected_frameworks || []}
        primaryLanguage={summary?.primary_language || (metrics.languages[0]?.language ?? "Unknown")}
        architecturalStyle={summary?.architectural_style || "Modular Architecture"}
        dependencies={overview.dependencies}
      />
    </div>
  );
}
