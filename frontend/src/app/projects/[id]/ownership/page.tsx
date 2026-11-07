"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Loader2,
  RefreshCw,
  Search,
  Shield,
  UserCheck,
} from "lucide-react";

import { ContributorLeaderboard } from "@/components/domain/ContributorLeaderboard";
import { FlaggedUnownedAlert } from "@/components/domain/FlaggedUnownedAlert";
import { OwnershipScorecard } from "@/components/domain/OwnershipScorecard";
import { SymbolOwnershipCard } from "@/components/domain/SymbolOwnershipCard";
import { getProjectOwnership } from "@/lib/ownershipApi";
import { supabase } from "@/lib/supabase";
import type { ProjectOwnershipReport, SymbolOwnership } from "@/types/ownership";

export default function ProjectOwnershipPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [report, setReport] = useState<ProjectOwnershipReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [candidateEmail, setCandidateEmail] = useState("");
  const [activeTab, setActiveTab] = useState<"symbols" | "files" | "contributors">("symbols");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchReport = useCallback(
    async (emailOverride?: string) => {
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
        const data = await getProjectOwnership(
          projectId,
          session.access_token,
          emailOverride ?? candidateEmail
        );
        setReport(data);
        if (!candidateEmail && data.candidate_email) {
          setCandidateEmail(data.candidate_email);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load ownership report");
      } finally {
        setLoading(false);
      }
    },
    [projectId, router, candidateEmail]
  );

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="font-mono text-sm">Parsing git blame and calculating symbol ownership...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-6">
        <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mx-auto text-rose-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Ownership Report Unavailable</h2>
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

  const filteredSymbols: SymbolOwnership[] = report.symbols.filter((sym) => {
    if (statusFilter !== "all" && sym.candidate_status !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      return (
        sym.symbol_name.toLowerCase().includes(q) ||
        sym.file_path.toLowerCase().includes(q) ||
        sym.primary_author.toLowerCase().includes(q)
      );
    }
    return true;
  });

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
              <UserCheck className="w-5 h-5 text-emerald-400 flex-shrink-0" />
              <h1 className="text-xl font-bold text-white tracking-tight truncate">
                {report.project_name} Code Ownership
              </h1>
              <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-medium border text-emerald-400 bg-emerald-500/10 border-emerald-500/20">
                {report.candidate_overall_ownership_percentage}% Authored
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-1">
              Deterministic git blame attribution for candidate:{" "}
              <span className="text-emerald-300">{report.candidate_email || "Not specified"}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 px-2 py-1">
            <input
              type="email"
              placeholder="Candidate email..."
              value={candidateEmail}
              onChange={(e) => setCandidateEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && fetchReport(candidateEmail)}
              className="bg-transparent text-xs font-mono text-slate-200 focus:outline-none w-44"
            />
            <button
              type="button"
              onClick={() => fetchReport(candidateEmail)}
              className="text-[11px] font-mono text-emerald-400 hover:text-emerald-300 ml-1"
            >
              Set
            </button>
          </div>
          <button
            type="button"
            onClick={() => fetchReport()}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Refresh Report"
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
      <OwnershipScorecard report={report} />

      {/* Flagged Unowned Load-Bearing Symbols Alert Drawer */}
      <FlaggedUnownedAlert flaggedSymbols={report.flagged_unowned_symbols} />

      {/* Tab Controls */}
      <div className="space-y-4 pt-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("symbols")}
              className={`px-3 py-1.5 rounded-lg font-mono text-xs font-semibold transition-colors ${
                activeTab === "symbols"
                  ? "bg-slate-800 text-white border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Symbols Explorer ({filteredSymbols.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("files")}
              className={`px-3 py-1.5 rounded-lg font-mono text-xs font-semibold transition-colors ${
                activeTab === "files"
                  ? "bg-slate-800 text-white border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              File Ownership ({report.files.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("contributors")}
              className={`px-3 py-1.5 rounded-lg font-mono text-xs font-semibold transition-colors ${
                activeTab === "contributors"
                  ? "bg-slate-800 text-white border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Top Contributors ({report.top_contributors.length})
            </button>
          </div>

          {activeTab === "symbols" && (
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter symbols..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5">
                {(["all", "primary", "collaborator", "minor", "unowned"] as const).map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setStatusFilter(st)}
                    className={`px-2 py-1 rounded text-[11px] font-mono capitalize transition-colors ${
                      statusFilter === st
                        ? "bg-slate-800 text-emerald-400 font-semibold"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Tab Content */}
        {activeTab === "symbols" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filteredSymbols.length === 0 ? (
              <div className="col-span-2 p-8 text-center text-slate-400 font-mono text-xs border border-slate-800 rounded-xl bg-slate-900/60">
                No code symbols matched the active filters.
              </div>
            ) : (
              filteredSymbols.map((sym) => (
                <SymbolOwnershipCard key={sym.symbol_id} symbol={sym} />
              ))
            )}
          </div>
        )}

        {activeTab === "files" && (
          <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/60 divide-y divide-slate-800">
            {report.files.map((file) => (
              <div
                key={file.file_path}
                className="p-3.5 hover:bg-slate-800/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono"
              >
                <div className="min-w-0">
                  <div className="text-slate-200 font-medium truncate">{file.file_path}</div>
                  <div className="text-[11px] text-slate-500">
                    {file.total_lines} lines • Primary: {file.primary_author}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-emerald-400">
                    {file.candidate_lines} lines ({file.candidate_percentage}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "contributors" && (
          <ContributorLeaderboard contributors={report.top_contributors} />
        )}
      </div>
    </div>
  );
}
