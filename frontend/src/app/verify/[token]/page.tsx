"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertCircle,
  Award,
  CheckCircle2,
  Copy,
  ExternalLink,
  GitCommit,
  Layers,
  Loader2,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { getPublicDefenseReport } from "@/lib/publicReportApi";
import type { PublicDefenseReport } from "@/types/publicReport";

function getTierMeta(tier: string) {
  const t = tier.toLowerCase();
  if (t.includes("principal") || t.includes("certified")) {
    return {
      badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      bannerClass: "border-emerald-500/40 bg-emerald-950/20",
      scoreClass: "text-emerald-400 border-emerald-500/30 bg-emerald-950/50",
      Icon: ShieldCheck,
    };
  }
  if (t.includes("solid") || t.includes("architect")) {
    return {
      badgeClass: "bg-sky-500/10 text-sky-400 border-sky-500/30",
      bannerClass: "border-sky-500/40 bg-sky-950/20",
      scoreClass: "text-sky-400 border-sky-500/30 bg-sky-950/50",
      Icon: Shield,
    };
  }
  return {
    badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    bannerClass: "border-amber-500/40 bg-amber-950/20",
    scoreClass: "text-amber-400 border-amber-500/30 bg-amber-950/50",
    Icon: ShieldAlert,
  };
}

export default function PublicVerifyPage() {
  const params = useParams();
  const token = params?.token as string;

  const [report, setReport] = useState<PublicDefenseReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!token) return;
    let isMounted = true;
    getPublicDefenseReport(token)
      .then((data) => { if (isMounted) setReport(data); })
      .catch((err: unknown) => {
        if (isMounted) setError(err instanceof Error ? err.message : "Verification record unavailable");
      })
      .finally(() => { if (isMounted) setLoading(false); });
    return () => { isMounted = false; };
  }, [token]);

  const copyVerificationId = async () => {
    if (!report) return;
    await navigator.clipboard.writeText(report.verification_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-slate-400 space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="font-mono text-sm">Verifying cryptographic credential against codebase snapshot...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full p-6 rounded-2xl bg-slate-900 border border-slate-800 text-center space-y-4 shadow-xl">
          <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight">Credential Verification Failed</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            {error || "This defense report link is invalid, expired, or has been revoked by the author."}
          </p>
          <Link href="/" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition-colors">
            Return to RepoDefense
          </Link>
        </div>
      </div>
    );
  }

  const tierMeta = getTierMeta(report.certification_tier);
  const TierIcon = tierMeta.Icon;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Brand Nav */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-30 px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-emerald-400" />
          <span className="font-bold tracking-tight text-white text-sm sm:text-base">RepoDefense <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 ml-1">Verified Credential</span></span>
        </Link>
        <span className="text-xs font-mono text-slate-400 hidden sm:inline-flex items-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Tamper-Proof AST Verification
        </span>
      </header>

      {/* Main Verification Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-8 space-y-6">
        {/* Verification Certificate Header */}
        <div className={`rounded-2xl border p-6 sm:p-8 shadow-xl ${tierMeta.bannerClass} space-y-6`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold uppercase border ${tierMeta.badgeClass}`}>
                  <TierIcon className="w-3.5 h-3.5" /> {report.certification_tier}
                </span>
                <span className="text-xs font-mono text-slate-400">
                  {report.total_questions} Questions Defended
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight pt-1">
                {report.project_name}
              </h1>
            </div>
            <div className={`p-4 rounded-xl border flex flex-col items-center justify-center min-w-[120px] ${tierMeta.scoreClass}`}>
              <span className="text-3xl font-black tracking-tight">{report.overall_score}</span>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Score / 10.0</span>
            </div>
          </div>

          {/* Metadata Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-0.5">
              <span className="text-slate-400 text-[10px]">Verified Commit</span>
              <div className="flex items-center gap-1 text-slate-200">
                <GitCommit className="w-3.5 h-3.5 text-sky-400" />
                <span>{report.commit_hash.slice(0, 7)}</span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-0.5">
              <span className="text-slate-400 text-[10px]">Architecture Pattern</span>
              <div className="flex items-center gap-1 text-slate-200 truncate">
                <Layers className="w-3.5 h-3.5 text-amber-400" />
                <span className="truncate">{report.architecture_primary_pattern || "Modular"}</span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-0.5">
              <span className="text-slate-400 text-[10px]">Tech Health</span>
              <div className="flex items-center gap-1 text-slate-200">
                <Award className="w-3.5 h-3.5 text-emerald-400" />
                <span>{report.tech_health_score !== null ? `${report.tech_health_score}/100` : "N/A"}</span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-0.5">
              <span className="text-slate-400 text-[10px]">Verification Token</span>
              <button
                type="button"
                onClick={copyVerificationId}
                className="flex items-center gap-1 text-slate-200 hover:text-emerald-400 transition-colors w-full text-left"
                title="Click to copy Verification Token"
              >
                <Copy className="w-3.5 h-3.5 shrink-0 text-slate-400" />
                <span className="truncate">{copied ? "Copied!" : report.verification_id.slice(0, 10)}...</span>
              </button>
            </div>
          </div>

          {/* Evaluator Verdict Summary */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800/80 space-y-1.5">
            <span className="text-[11px] font-mono text-emerald-400 uppercase tracking-wider font-semibold">
              Principal Engineer Assessment Verdict
            </span>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans">
              {report.summary}
            </p>
          </div>
        </div>

        {/* Category Breakdown */}
        {report.category_scores.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-mono font-semibold text-slate-300 uppercase tracking-wider">
              Categorical Competency Breakdown
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {report.category_scores.map((cat) => (
                <div key={cat.category} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono uppercase font-bold text-slate-200">{cat.category}</span>
                    <span className={`text-xs font-mono px-2 py-0.5 rounded-full border ${cat.score >= 7.0 ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : cat.score >= 5.0 ? "text-sky-400 bg-sky-500/10 border-sky-500/20" : "text-amber-400 bg-amber-500/10 border-amber-500/20"}`}>
                      {cat.score.toFixed(1)} / 10.0
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">{cat.summary}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Demonstrated Strengths */}
        {report.key_strengths.length > 0 && (
          <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-2.5">
            <div className="flex items-center gap-2 text-xs font-mono font-semibold text-emerald-400">
              <Sparkles className="w-4 h-4" /> Demonstrated Technical Strengths
            </div>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-300">
              {report.key_strengths.map((str, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <span>{str}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Trust Footer */}
        <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono text-slate-400 text-center sm:text-left">
          <span>Verified by {report.issuer} • Grounded in Static Code AST & pgvector Embeddings</span>
          {report.github_url && (
            <a href={report.github_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300">
              View Candidate Repo <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </main>
    </div>
  );
}
