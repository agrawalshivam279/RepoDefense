"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  HelpCircle,
  Loader2,
  RotateCcw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
} from "lucide-react";

import { CategoryScorecard } from "@/components/domain/CategoryScorecard";
import { getDefenseReport } from "@/lib/defenseApi";
import { supabase } from "@/lib/supabase";
import type { DefenseReportResponse } from "@/types/report";

function getVerdictMeta(verdict: string, score: number) {
  if (score >= 7.5 || verdict.toLowerCase().includes("certified")) {
    return {
      title: verdict || "Certified Principal Defense",
      color: "emerald",
      badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      bannerClass: "bg-emerald-950/20 border-emerald-500/30",
      scoreClass: "text-emerald-400 border-emerald-500/40 bg-emerald-950/40",
      Icon: ShieldCheck,
    };
  }
  if (score >= 5.0 || verdict.toLowerCase().includes("solid")) {
    return {
      title: verdict || "Solid Architectural Defense",
      color: "sky",
      badgeClass: "bg-sky-500/10 text-sky-400 border-sky-500/30",
      bannerClass: "bg-sky-950/20 border-sky-500/30",
      scoreClass: "text-sky-400 border-sky-500/40 bg-sky-950/40",
      Icon: Shield,
    };
  }
  return {
    title: verdict || "Architectural Remediation Required",
    color: "amber",
    badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    bannerClass: "bg-amber-950/20 border-amber-500/30",
    scoreClass: "text-amber-400 border-amber-500/40 bg-amber-950/40",
    Icon: ShieldAlert,
  };
}

export default function DefenseReportPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params?.id as string;

  const [report, setReport] = useState<DefenseReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const { data: { session: authSession } } = await supabase.auth.getSession();
      if (!authSession) {
        router.push("/login");
        return;
      }
      const data = await getDefenseReport(sessionId, authSession.access_token);
      setReport(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load defense report");
    } finally {
      setLoading(false);
    }
  }, [sessionId, router]);

  useEffect(() => { fetchReport(); }, [fetchReport]);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="font-mono text-sm">Synthesizing architectural evaluation report...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-6">
        <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mx-auto text-rose-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Defense Report Unavailable</h2>
        <p className="text-sm text-slate-400 font-mono">{error ?? "Report data could not be found."}</p>
        <Link href="/dashboard" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:text-white font-mono text-xs border border-slate-700">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>
      </div>
    );
  }

  const verdictMeta = getVerdictMeta(report.verdict, report.overall_score);
  const VerdictIcon = verdictMeta.Icon;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 text-slate-100">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors" title="Back to Dashboard">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-400" />
              <h1 className="text-lg font-bold text-white tracking-tight">Architectural Defense Debrief</h1>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-slate-400 mt-0.5">
              <span>Session: <span className="text-slate-300">{report.session_id.slice(0, 8)}...</span></span>
              <span>•</span>
              <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(report.completed_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs">
          <Link href={`/interview/${report.project_id}`} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition-colors">
            <RotateCcw className="w-3.5 h-3.5" /> Start New Defense
          </Link>
          <Link href="/dashboard" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors">
            Dashboard
          </Link>
        </div>
      </div>

      {/* Executive Verdict Banner */}
      <div className={`rounded-2xl border p-6 sm:p-8 backdrop-blur-sm shadow-lg ${verdictMeta.bannerClass}`}>
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono uppercase font-bold border ${verdictMeta.badgeClass}`}>
                <VerdictIcon className="w-3.5 h-3.5" /> {verdictMeta.title}
              </span>
              <span className="text-xs font-mono text-slate-400">
                {report.total_questions} questions defended
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Evaluation & Defense Verdict
            </h2>
            <p className="text-sm text-slate-300 max-w-3xl leading-relaxed">
              {report.summary}
            </p>
          </div>
          <div className="flex-shrink-0 flex items-center gap-4 border-t lg:border-t-0 lg:border-l border-slate-800 pt-4 lg:pt-0 lg:pl-8">
            <div className={`w-24 h-24 rounded-2xl border-2 flex flex-col items-center justify-center font-mono ${verdictMeta.scoreClass}`}>
              <span className="text-2xl sm:text-3xl font-black">{report.overall_score.toFixed(1)}</span>
              <span className="text-[10px] uppercase tracking-wider opacity-80">Score / 10</span>
            </div>
          </div>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h3 className="text-base font-bold text-white tracking-tight">Architectural Domain Performance</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">{report.category_scores.length} Categories Analyzed</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {report.category_scores.map((cs) => (
            <CategoryScorecard key={cs.category} categoryScore={cs} />
          ))}
        </div>
      </div>

      {/* Strengths & Critical Blind Spots */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Key Strengths */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center gap-2.5 text-emerald-400 border-b border-slate-800 pb-3">
            <CheckCircle2 className="w-5 h-5" />
            <h3 className="text-sm font-bold uppercase tracking-wider font-mono">Key Architectural Strengths</h3>
          </div>
          <ul className="space-y-3">
            {report.key_strengths.length > 0 ? (
              report.key_strengths.map((strength, i) => (
                <li key={i} className="flex items-start gap-2.5 text-xs text-slate-300 leading-relaxed">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                  <span>{strength}</span>
                </li>
              ))
            ) : (
              <li className="text-xs text-slate-500 font-mono">No specific high-scoring strengths recorded.</li>
            )}
          </ul>
        </div>

        {/* Critical Blind Spots */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center gap-2.5 text-amber-400 border-b border-slate-800 pb-3">
            <AlertCircle className="w-5 h-5" />
            <h3 className="text-sm font-bold uppercase tracking-wider font-mono">Critical Blind Spots Uncovered</h3>
          </div>
          <ul className="space-y-3">
            {report.critical_blind_spots.length > 0 ? (
              report.critical_blind_spots.map((spot, i) => (
                <li key={i} className="flex items-start gap-2.5 text-xs text-slate-300 leading-relaxed">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                  <span>{spot}</span>
                </li>
              ))
            ) : (
              <li className="text-xs text-slate-500 font-mono">No critical vulnerabilities identified.</li>
            )}
          </ul>
        </div>
      </div>

      {/* Actionable Engineering Recommendations */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center gap-2.5 text-sky-400 border-b border-slate-800 pb-3">
          <Terminal className="w-5 h-5" />
          <h3 className="text-sm font-bold uppercase tracking-wider font-mono">Actionable Engineering Mitigations</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {report.actionable_recommendations.map((rec, i) => (
            <div key={i} className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-start gap-3">
              <span className="w-5 h-5 rounded-md bg-sky-500/10 border border-sky-500/20 text-sky-400 font-mono text-xs flex items-center justify-center flex-shrink-0 font-bold">
                {i + 1}
              </span>
              <p className="text-xs text-slate-300 leading-relaxed font-sans">{rec}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
