"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Sparkles,
  Loader2,
  RefreshCw,
  Search,
  Shield,
  FileText,
  AlertCircle,
} from "lucide-react";
import { ClaimVerificationCard } from "@/components/domain/ClaimVerificationCard";
import { verifyProjectClaims } from "@/lib/claimApi";
import { getProjectOverview } from "@/lib/projectApi";
import { supabase } from "@/lib/supabase";
import type {
  BatchClaimVerificationResponse,
  ClaimVerificationResult,
  TechnicalClaim,
} from "@/types/claim";
import type { ProjectOverviewResponse } from "@/types/project";

const SAMPLE_CLAIMS: TechnicalClaim[] = [
  { id: "s-1", statement: "Engineered FastAPI backend services using PostgreSQL 17 and pgvector.", category: "database", technologies: ["FastAPI", "PostgreSQL", "pgvector"], verifiable: true },
  { id: "s-2", statement: "Built multi-language AST code parser using Tree-sitter for syntax analysis.", category: "architecture", technologies: ["Tree-sitter", "Python"], verifiable: true },
  { id: "s-3", statement: "Implemented asynchronous background job processing with Celery and RabbitMQ.", category: "infrastructure", technologies: ["Celery", "RabbitMQ"], verifiable: true },
  { id: "s-4", statement: "Designed JWT bearer authentication guards with Supabase Auth integration.", category: "security", technologies: ["Supabase", "JWT"], verifiable: true },
];

export default function ProjectClaimsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [project, setProject] = useState<ProjectOverviewResponse | null>(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [claims] = useState<TechnicalClaim[]>(SAMPLE_CLAIMS);
  const [verification, setVerification] = useState<BatchClaimVerificationResponse | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    setLoadingProject(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.push("/login"); return; }
      const data = await getProjectOverview(projectId, session.access_token);
      setProject(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project details");
    } finally {
      setLoadingProject(false);
    }
  }, [projectId, router]);

  useEffect(() => { loadProject(); }, [loadProject]);

  const runVerification = async () => {
    if (!projectId || claims.length === 0) return;
    setVerifying(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.push("/login"); return; }
      const res = await verifyProjectClaims(projectId, claims, session.access_token);
      setVerification(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification request failed");
    } finally {
      setVerifying(false);
    }
  };

  const filteredResults: ClaimVerificationResult[] = (verification?.verified_claims || []).filter((item) => {
    const matchesStatus = statusFilter === "all" || item.status === statusFilter;
    const q = searchQuery.toLowerCase().trim();
    return matchesStatus && (!q || item.statement.toLowerCase().includes(q));
  });

  if (loadingProject) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="font-mono text-sm">Loading project verification workspace...</p>
      </div>
    );
  }

  const supported = verification?.summary_counts?.supported ?? 0;
  const contradicted = verification?.summary_counts?.contradicted ?? 0;
  const unverifiable = verification?.summary_counts?.unverifiable ?? 0;
  const total = verification?.total_claims ?? 0;
  const matchRate = total > 0 ? Math.round((supported / total) * 100) : 0;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <Link
            href={`/projects/${projectId}`}
            className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-emerald-400 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Project Overview
          </Link>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2.5">
            <span>Claim Grounding Inspector</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 font-mono font-medium">
              Phase 2: Differentiation
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 font-sans">
            Verify resume claims against codebase truth using pgvector embeddings and AST symbols.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href={`/interview/${projectId}`}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs font-mono transition-colors shadow-sm"
          >
            <Shield className="w-3.5 h-3.5" /> Start Defense
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs font-mono text-rose-300 flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Verification Action Bar or Summary */}
      {!verification ? (
        <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-5 text-center max-w-2xl mx-auto">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto text-emerald-400">
            <Sparkles className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-white">Ready to Verify Claims</h2>
            <p className="text-xs text-slate-400">
              Evaluating {claims.length} technical claims against {project?.name || "repository"} code.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={runVerification}
              disabled={verifying}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-mono text-xs font-bold transition-all shadow-md"
            >
              {verifying ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-emerald-300" />
                  <span>Grounding against Codebase...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Run Claim Verification</span>
                </>
              )}
            </button>
            <Link
              href="/claims"
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs border border-slate-700"
            >
              <FileText className="w-3.5 h-3.5" /> Upload Custom Resume
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/80 space-y-1">
              <span className="text-[11px] font-mono uppercase text-slate-400">Evaluated</span>
              <p className="text-xl font-black text-white">{total}</p>
            </div>
            <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-1">
              <span className="text-[11px] font-mono uppercase text-emerald-400">Supported</span>
              <p className="text-xl font-black text-emerald-400">{supported}</p>
            </div>
            <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-500/5 space-y-1">
              <span className="text-[11px] font-mono uppercase text-rose-400">Contradicted</span>
              <p className="text-xl font-black text-rose-400">{contradicted}</p>
            </div>
            <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-1">
              <span className="text-[11px] font-mono uppercase text-amber-400">Unverifiable</span>
              <p className="text-xl font-black text-amber-400">{unverifiable}</p>
            </div>
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/80 space-y-1 col-span-2 sm:col-span-1">
              <span className="text-[11px] font-mono uppercase text-slate-400">Support Rate</span>
              <p className="text-xl font-black text-sky-400">{matchRate}%</p>
            </div>
          </div>

          {/* Filter & Search Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
            <div className="flex items-center gap-1.5 overflow-x-auto">
              {[
                { key: "all", label: `All (${total})` },
                { key: "supported", label: `Supported (${supported})` },
                { key: "contradicted", label: `Contradicted (${contradicted})` },
                { key: "unverifiable", label: `Unverifiable (${unverifiable})` },
              ].map((f) => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setStatusFilter(f.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                    statusFilter === f.key
                      ? "bg-slate-700 text-white font-bold"
                      : "text-slate-400 hover:text-white hover:bg-slate-800"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <div className="relative w-full sm:w-56">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search statements..."
                  className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
              <button
                type="button"
                onClick={runVerification}
                disabled={verifying}
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors"
                title="Re-run verification"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${verifying ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>

          {/* Results List */}
          <div className="space-y-4">
            {filteredResults.length === 0 ? (
              <div className="p-8 rounded-xl border border-slate-800 bg-slate-900/30 text-center text-xs font-mono text-slate-500">
                No claims match the active status or search filter.
              </div>
            ) : (
              filteredResults.map((result) => (
                <ClaimVerificationCard
                  key={result.claim_id}
                  result={result}
                  projectId={projectId}
                  defaultExpanded={result.status === "supported"}
                />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
