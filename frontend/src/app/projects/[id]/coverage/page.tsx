"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Layers,
  Loader2,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import { BlindSpotList } from "@/components/domain/BlindSpotList";
import { CoverageScorecard } from "@/components/domain/CoverageScorecard";
import { ModuleHeatmapGrid } from "@/components/domain/ModuleHeatmapGrid";
import { getProjectCoverage } from "@/lib/coverageApi";
import { supabase } from "@/lib/supabase";
import type { FileCoverageItem, ProjectCoverageResponse } from "@/types/coverage";

export default function ProjectCoveragePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [coverage, setCoverage] = useState<ProjectCoverageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "tested" | "untested">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"files" | "blindspots">("files");

  const fetchCoverage = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        router.push("/login");
        return;
      }
      const data = await getProjectCoverage(projectId, session.access_token);
      setCoverage(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load coverage report");
    } finally {
      setLoading(false);
    }
  }, [projectId, router]);

  useEffect(() => {
    fetchCoverage();
  }, [fetchCoverage]);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="font-mono text-sm">Calculating repository defense coverage...</p>
      </div>
    );
  }

  if (error || !coverage) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-6">
        <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mx-auto text-rose-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Coverage Data Unavailable</h2>
        <p className="text-sm text-slate-400 font-mono">{error ?? "Coverage not found."}</p>
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:text-white font-mono text-xs border border-slate-700"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Project Overview
        </Link>
      </div>
    );
  }

  const filteredFiles: FileCoverageItem[] = coverage.files.filter((file) => {
    if (selectedModule && !file.file_path.startsWith(selectedModule)) return false;
    if (statusFilter === "tested" && !file.is_tested) return false;
    if (statusFilter === "untested" && file.is_tested) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      return file.file_path.toLowerCase().includes(q) || file.language.toLowerCase().includes(q);
    }
    return true;
  });

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case "Principal Verified":
        return { color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30", Icon: ShieldCheck };
      case "Substantial Coverage":
        return { color: "text-sky-400 bg-sky-500/10 border-sky-500/30", Icon: Shield };
      default:
        return { color: "text-amber-400 bg-amber-500/10 border-amber-500/30", Icon: ShieldAlert };
    }
  };

  const tierInfo = getTierBadge(coverage.overall_coverage_tier);
  const TierIcon = tierInfo.Icon;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 text-slate-100">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href={`/projects/${projectId}`}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors"
            title="Back to Project"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <Layers className="w-5 h-5 text-emerald-400 flex-shrink-0" />
              <h1 className="text-xl font-bold text-white tracking-tight truncate">
                {coverage.project_name} Defense Coverage
              </h1>
              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-medium border ${tierInfo.color}`}>
                <TierIcon className="w-3.5 h-3.5" />
                {coverage.overall_coverage_tier}
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-1">
              Visualizing defended code paths, directory heatmaps, and untested architectural blind spots.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={fetchCoverage}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Refresh Coverage"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <Link
            href={`/interview/${projectId}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs font-mono transition-colors shadow-md"
          >
            <span>Start Defense</span>
            <Shield className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Executive Scorecards */}
      <CoverageScorecard coverage={coverage} />

      {/* Module Heatmap Grid */}
      <ModuleHeatmapGrid
        modules={coverage.modules}
        selectedModule={selectedModule}
        onSelectModule={setSelectedModule}
      />

      {/* Tab Selector & Controls */}
      <div className="space-y-4 pt-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("files")}
              className={`px-3 py-1.5 rounded-lg font-mono text-xs font-semibold transition-colors ${
                activeTab === "files"
                  ? "bg-slate-800 text-white border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Files Explorer ({filteredFiles.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("blindspots")}
              className={`px-3 py-1.5 rounded-lg font-mono text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                activeTab === "blindspots"
                  ? "bg-slate-800 text-white border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <span>Blind Spots</span>
              <span className="px-1.5 py-0.2 rounded text-[10px] bg-rose-500/20 text-rose-400">
                {coverage.blind_spots.length}
              </span>
            </button>
          </div>

          {activeTab === "files" && (
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter files..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5">
                {(["all", "tested", "untested"] as const).map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    onClick={() => setStatusFilter(filter)}
                    className={`px-2.5 py-1 rounded text-[11px] font-mono capitalize transition-colors ${
                      statusFilter === filter
                        ? "bg-slate-800 text-emerald-400 font-semibold"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Tab Content */}
        {activeTab === "blindspots" ? (
          <BlindSpotList blindSpots={coverage.blind_spots} projectId={projectId} />
        ) : (
          <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/60 divide-y divide-slate-800">
            {filteredFiles.length === 0 ? (
              <div className="p-8 text-center text-slate-400 font-mono text-xs">
                No files matched the active filters.
              </div>
            ) : (
              filteredFiles.map((file) => (
                <div
                  key={file.file_path}
                  className="p-3.5 hover:bg-slate-800/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {file.is_tested ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-slate-600 flex-shrink-0" />
                    )}
                    <span className="text-slate-200 truncate" title={file.file_path}>
                      {file.file_path}
                    </span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">
                      {file.language}
                    </span>
                    <span className="text-slate-500 text-[11px]">{file.total_lines} lines</span>
                  </div>

                  <div className="flex items-center gap-3 text-[11px]">
                    {file.is_tested ? (
                      <>
                        <span className="text-emerald-400">{file.test_count} tests</span>
                        {file.average_score != null && (
                          <span className="text-sky-400">Avg {file.average_score.toFixed(1)}/10</span>
                        )}
                        {file.highest_difficulty && (
                          <span className="px-1.5 py-0.5 rounded uppercase text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            {file.highest_difficulty}
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-rose-400/80">Untested</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
