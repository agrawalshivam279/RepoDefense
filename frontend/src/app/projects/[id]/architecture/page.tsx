"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FolderTree,
  Loader2,
  Network,
  ShieldAlert,
} from "lucide-react";

import { ArchitectureReportCard } from "@/components/domain/ArchitectureReportCard";
import { ArchitecturalRisksCard } from "@/components/domain/ArchitecturalRisksCard";
import { MermaidViewer } from "@/components/domain/MermaidViewer";
import { PatternIndicatorList } from "@/components/domain/PatternIndicatorList";
import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { getProjectArchitecture } from "@/lib/architectureApi";
import { getProjectDiagram } from "@/lib/diagramApi";
import { supabase } from "@/lib/supabase";
import type { ArchitectureReportResponse } from "@/types/architecture";
import type { DiagramResponse } from "@/types/diagram";

export default function ProjectArchitecturePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [report, setReport] = useState<ArchitectureReportResponse | null>(null);
  const [diagram, setDiagram] = useState<DiagramResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
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
      const token = session.access_token;
      const [reportData, diagramData] = await Promise.all([
        getProjectArchitecture(projectId, token),
        getProjectDiagram(projectId, token).catch(() => null),
      ]);
      setReport(reportData);
      setDiagram(diagramData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load architecture report");
    } finally {
      setLoading(false);
    }
  }, [projectId, router]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="font-mono text-sm">Evaluating directory topologies & architecture patterns...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-6">
        <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mx-auto text-rose-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Architecture Report Unavailable</h2>
        <p className="text-sm text-slate-400 font-mono">{error ?? "Report not found."}</p>
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:text-white font-mono text-xs border border-slate-700"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Project Overview
        </Link>
      </div>
    );
  }

  const primaryConfidence = Math.round(report.primary_pattern.confidence_score * 100);
  const sortedDirectories = Object.entries(report.directory_summary).sort((a, b) => b[1] - a[1]);
  const maxDirCount = Math.max(...Object.values(report.directory_summary), 1);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 text-slate-100">
      {/* Centralized Phase 2 Navigation Header */}
      <ProjectNavHeader
        projectId={projectId}
        projectName={report.project_name}
        activeTab="architecture"
        statusBadge={report.primary_pattern.pattern_name}
        subtitle="Static topology classification, structural patterns & architecture diagrams"
        onRefresh={fetchReport}
        isRefreshing={loading}
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>Primary Pattern</span>
            <Network className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-lg font-bold text-white truncate">
            {report.primary_pattern.pattern_name}
          </div>
          <div className="text-[11px] font-mono text-emerald-400">{primaryConfidence}% Match Score</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>Confidence Tier</span>
            <CheckCircle2 className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-lg font-bold text-white capitalize">{report.primary_pattern.tier} Tier</div>
          <div className="text-[11px] font-mono text-slate-400">Deterministic Signals</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>Files Analyzed</span>
            <FolderTree className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-lg font-bold text-white">{report.total_files_analyzed.toLocaleString()}</div>
          <div className="text-[11px] font-mono text-slate-400">{sortedDirectories.length} Directory Clusters</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>Identified Risks</span>
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-lg font-bold text-white">{report.architectural_risks.length}</div>
          <div className="text-[11px] font-mono text-amber-400">
            {report.architectural_risks.length === 0 ? "Clean Architecture" : "Requires Defense Prep"}
          </div>
        </div>
      </div>

      {/* Hero Architecture Report Card */}
      <ArchitectureReportCard
        primaryPattern={report.primary_pattern}
        secondaryPatterns={report.secondary_patterns}
        totalFiles={report.total_files_analyzed}
      />

      {/* Interactive Mermaid Architecture Flowchart */}
      {diagram && <MermaidViewer diagram={diagram} />}

      {/* Indicators and Risks Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        <PatternIndicatorList
          indicators={report.primary_pattern.indicators}
          patternName={report.primary_pattern.pattern_name}
        />
        <ArchitecturalRisksCard risks={report.architectural_risks} />
      </div>

      {/* Directory Topology Breakdown */}
      {sortedDirectories.length > 0 && (
        <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 shadow-md space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <FolderTree className="w-4 h-4 text-sky-400" />
                Repository Directory Distribution
              </h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Source file clusters recognized during static architectural topology scan
              </p>
            </div>
            <span className="text-xs font-mono text-slate-400">{sortedDirectories.length} directories</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {sortedDirectories.map(([dirName, count]) => {
              const percentage = Math.round((count / maxDirCount) * 100);
              return (
                <div key={dirName} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-semibold text-slate-200 truncate">{dirName}/</span>
                    <span className="text-slate-400">{count} files</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-sky-500 rounded-full" style={{ width: `${Math.max(6, percentage)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
