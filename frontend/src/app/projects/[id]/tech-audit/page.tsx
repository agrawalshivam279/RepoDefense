"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Cpu,
  Layers,
  Loader2,
  Network,
  PackageCheck,
  RefreshCw,
  Shield,
  Sparkles,
  UserCheck,
} from "lucide-react";

import { AuditedDependencyList } from "@/components/domain/AuditedDependencyList";
import { TechAuditScorecard } from "@/components/domain/TechAuditScorecard";
import { getProjectTechAudit } from "@/lib/techAuditApi";
import { supabase } from "@/lib/supabase";
import type { TechAuditReportResponse } from "@/types/techAudit";

export default function ProjectTechAuditPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [report, setReport] = useState<TechAuditReportResponse | null>(null);
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
      const data = await getProjectTechAudit(projectId, session.access_token);
      setReport(data);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load technology health audit"
      );
    } finally {
      setLoading(false);
    }
  }, [projectId, router]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
          <span className="text-sm font-mono text-slate-400">
            Auditing dependency stack & checking CVE thresholds...
          </span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          <Link
            href={`/projects/${projectId}`}
            className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white font-mono"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Project</span>
          </Link>

          <div className="p-6 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 space-y-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-rose-400 shrink-0" />
              <div>
                <h3 className="font-semibold text-white">Audit Evaluation Error</h3>
                <p className="text-sm text-slate-300">
                  {error || "Unable to retrieve dependency audit."}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={fetchReport}
              className="px-4 py-2 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/30 text-xs font-mono"
            >
              Retry Audit
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Navigation Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <Link
              href={`/projects/${projectId}`}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 transition-colors"
              title="Back to Overview"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <PackageCheck className="w-5 h-5 text-emerald-400" />
                <h1 className="text-xl font-bold text-white font-mono">
                  Technology & Dependency Audit
                </h1>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                {report.project_name} • Obsolescence, CVE thresholds, & modern alternatives
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={fetchReport}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors"
              title="Refresh Audit"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <Link
              href={`/projects/${projectId}/claims`}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white font-semibold text-xs font-mono transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span>Claims</span>
            </Link>
            <Link
              href={`/projects/${projectId}/coverage`}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white font-semibold text-xs font-mono transition-colors"
            >
              <Layers className="w-3.5 h-3.5 text-sky-400" />
              <span>Coverage</span>
            </Link>
            <Link
              href={`/projects/${projectId}/ownership`}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white font-semibold text-xs font-mono transition-colors"
            >
              <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
              <span>Ownership</span>
            </Link>
            <Link
              href={`/projects/${projectId}/architecture`}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white font-semibold text-xs font-mono transition-colors"
            >
              <Network className="w-3.5 h-3.5 text-purple-400" />
              <span>Architecture</span>
            </Link>
            <Link
              href={`/interview/${projectId}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs font-mono transition-colors shadow-md"
            >
              <span>Start Defense</span>
              <Shield className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Scorecard Hero */}
        <TechAuditScorecard report={report} />

        {/* Flagged Dependencies Section */}
        <div className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-mono">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <h2 className="text-base font-bold text-white">
                Dependency Inspection & Remediation
              </h2>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {report.flagged_dependencies_count} flagged of{" "}
              {report.total_dependencies_audited} total
            </span>
          </div>

          <AuditedDependencyList items={report.audited_items} />
        </div>
      </div>
    </div>
  );
}
