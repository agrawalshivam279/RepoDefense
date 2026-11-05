"use client";

import { useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  FileCode2,
  Package,
  Layers,
  Sparkles,
  Shield,
  ArrowRight,
} from "lucide-react";
import type { ClaimVerificationResult, EvidenceCitation, VerificationStatus } from "@/types/claim";

interface ClaimVerificationCardProps {
  result: ClaimVerificationResult;
  projectId: string;
  defaultExpanded?: boolean;
}

const STATUS_CONFIG: Record<
  VerificationStatus,
  { label: string; badgeClass: string; icon: typeof CheckCircle2 }
> = {
  supported: {
    label: "Supported by Codebase",
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    icon: CheckCircle2,
  },
  contradicted: {
    label: "Contradicted by Codebase",
    badgeClass: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    icon: XCircle,
  },
  unverifiable: {
    label: "Unverifiable in Codebase",
    badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    icon: HelpCircle,
  },
};

function getCitationIcon(sourceType: string) {
  if (sourceType === "dependency") return Package;
  if (sourceType === "evidence") return Layers;
  return FileCode2;
}

export function ClaimVerificationCard({
  result,
  projectId,
  defaultExpanded = false,
}: ClaimVerificationCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const statusInfo = STATUS_CONFIG[result.status] || STATUS_CONFIG.unverifiable;
  const StatusIcon = statusInfo.icon;
  const confidencePercent = Math.round(result.confidence_score * 100);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4 hover:border-slate-700/80 transition-all shadow-sm">
      {/* Top Header: Category, Status & Confidence */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-semibold border ${statusInfo.badgeClass}`}
          >
            <StatusIcon className="w-3.5 h-3.5" />
            <span>{statusInfo.label}</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400 bg-slate-950 px-2.5 py-1 rounded-md border border-slate-800">
            <span>Confidence:</span>
            <span
              className={`font-bold ${
                result.status === "supported"
                  ? "text-emerald-400"
                  : result.status === "contradicted"
                  ? "text-rose-400"
                  : "text-amber-400"
              }`}
            >
              {confidencePercent}%
            </span>
          </div>
        </div>
      </div>

      {/* Claim Statement */}
      <div>
        <p className="text-sm sm:text-base font-semibold text-white leading-relaxed">
          &ldquo;{result.statement}&rdquo;
        </p>
      </div>

      {/* Principal Engineer Reasoning */}
      {result.reasoning && (
        <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1.5 text-xs">
          <div className="flex items-center gap-1.5 text-slate-300 font-mono font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Principal Engineer Rationale</span>
          </div>
          <p className="text-slate-300 leading-relaxed font-sans">{result.reasoning}</p>
        </div>
      )}

      {/* Citations Toggle */}
      <div className="pt-1">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between py-2 px-3 rounded-lg bg-slate-800/50 hover:bg-slate-800 text-xs font-mono text-slate-300 transition-colors border border-slate-700/40"
        >
          <span className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span>
              Evidence Citations ({result.citations.length})
            </span>
          </span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {/* Citations List */}
        {expanded && (
          <div className="mt-3 space-y-3 pl-1">
            {result.citations.length === 0 ? (
              <p className="text-xs font-mono text-slate-500 py-2">
                No direct code chunks or dependencies matched the verification threshold.
              </p>
            ) : (
              result.citations.map((citation: EvidenceCitation, idx: number) => {
                const CitationIcon = getCitationIcon(citation.source_type);
                const matchPct = Math.round(citation.relevance_score * 100);
                return (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2.5 text-xs font-mono"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-slate-400">
                      <div className="flex items-center gap-2 font-mono text-slate-200">
                        <CitationIcon className="w-3.5 h-3.5 text-slate-400" />
                        <span className="text-emerald-300 font-semibold">{citation.file_path}</span>
                        {citation.start_line && citation.end_line && (
                          <span className="text-slate-500">
                            (L{citation.start_line}–L{citation.end_line})
                          </span>
                        )}
                        {citation.symbol_name && (
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[11px] text-sky-300 border border-slate-700">
                            {citation.symbol_name}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-[11px] uppercase px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                          {citation.source_type}
                        </span>
                        {citation.relevance_score > 0 && (
                          <span className="text-[11px] text-emerald-400 font-bold">
                            {matchPct}% match
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Snippet box */}
                    {citation.snippet && (
                      <pre className="p-2.5 rounded bg-slate-900/90 text-slate-300 text-[11px] overflow-x-auto border border-slate-800/80 leading-relaxed font-mono whitespace-pre-wrap">
                        {citation.snippet}
                      </pre>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* Suggested Interview Questions */}
      {result.suggested_defense_questions.length > 0 && (
        <div className="p-3.5 rounded-lg bg-slate-950/40 border border-slate-800 space-y-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-mono font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-amber-400" />
              Suggested Interview Defense Questions
            </span>
            <Link
              href={`/interview/${projectId}`}
              className="text-[11px] font-mono text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1"
            >
              Defend in Interview <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <ul className="space-y-1.5 text-xs text-slate-300">
            {result.suggested_defense_questions.map((q: string, idx: number) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                <span className="leading-relaxed">&ldquo;{q}&rdquo;</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
