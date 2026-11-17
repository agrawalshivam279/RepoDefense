"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  Award,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Code2,
  Copy,
  GraduationCap,
  Sparkles,
  XCircle,
} from "lucide-react";
import type { ChallengeEvaluationResponse } from "@/types/challenge";

interface SolutionEvaluationViewerProps {
  evaluation: ChallengeEvaluationResponse;
  onRetry?: () => void;
  onNextChallenge?: () => void;
  className?: string;
}

export function SolutionEvaluationViewer({
  evaluation,
  onRetry,
  onNextChallenge,
  className = "",
}: SolutionEvaluationViewerProps) {
  const [modelSolutionOpen, setModelSolutionOpen] = useState<boolean>(!evaluation.passed);
  const [copiedSolution, setCopiedSolution] = useState<boolean>(false);

  const handleCopyModel = async () => {
    try {
      await navigator.clipboard.writeText(evaluation.model_solution);
      setCopiedSolution(true);
      setTimeout(() => setCopiedSolution(false), 2000);
    } catch {
      // Non-blocking
    }
  };

  const isPassed = evaluation.passed;
  const score = Math.round(evaluation.score * 10) / 10;

  return (
    <div
      className={`rounded-2xl border p-6 space-y-6 shadow-2xl backdrop-blur-sm transition-all ${
        isPassed
          ? "border-emerald-500/30 bg-emerald-950/10"
          : "border-amber-500/30 bg-amber-950/10"
      } ${className}`}
    >
      {/* Top Banner & Score */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-start sm:items-center gap-3">
          <div
            className={`rounded-xl p-2.5 border ${
              isPassed
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-amber-500/10 border-amber-500/30 text-amber-400"
            }`}
          >
            {isPassed ? <CheckCircle2 className="h-6 w-6" /> : <AlertTriangle className="h-6 w-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-semibold uppercase tracking-wider ${
                  isPassed ? "text-emerald-400" : "text-amber-400"
                }`}
              >
                {isPassed ? "Defense Succeeded" : "Architectural Revision Needed"}
              </span>
              {evaluation.weakness_updated && (
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-300 border border-emerald-500/20 flex items-center gap-1">
                  <Award className="h-3 w-3" />
                  Weakness Resolved
                </span>
              )}
            </div>
            <h3 className="text-xl font-bold tracking-tight text-white mt-0.5">
              {isPassed ? "Production Standard Verified" : "Key Constraints Unmet"}
            </h3>
          </div>
        </div>

        {/* Score Dial */}
        <div className="flex items-center gap-3 self-start sm:self-auto bg-slate-950/80 px-4 py-2 rounded-xl border border-slate-800">
          <div className="text-right">
            <span className="text-[10px] uppercase font-bold text-slate-500 block">Score</span>
            <span
              className={`text-2xl font-black font-mono leading-none ${
                score >= 75 ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {score}
            </span>
          </div>
          <span className="text-xs text-slate-500 font-mono">/ 100</span>
        </div>
      </div>

      {/* Principal Critique */}
      <div className="rounded-xl border border-slate-800/90 bg-slate-950/80 p-4 space-y-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-400">
          <GraduationCap className="h-4 w-4" />
          <span>Principal Engineer Feedback & Critique</span>
        </div>
        <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-line">
          {evaluation.critique}
        </p>
      </div>

      {/* Strengths & Missing Elements Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Strengths */}
        <div className="rounded-xl border border-emerald-900/30 bg-emerald-950/15 p-4 space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400">
            <CheckCircle2 className="h-4 w-4" />
            <span>Identified Strengths ({evaluation.strengths.length})</span>
          </div>
          {evaluation.strengths.length > 0 ? (
            <ul className="space-y-1.5">
              {evaluation.strengths.map((str, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs text-emerald-200/90">
                  <span className="text-emerald-400 font-bold shrink-0 mt-0.5">&bull;</span>
                  <span>{str}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500 italic">No specific strengths recognized.</p>
          )}
        </div>

        {/* Missing Elements */}
        <div className="rounded-xl border border-rose-900/30 bg-rose-950/15 p-4 space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-rose-400">
            <XCircle className="h-4 w-4" />
            <span>Missing / Incomplete Elements ({evaluation.missing_elements.length})</span>
          </div>
          {evaluation.missing_elements.length > 0 ? (
            <ul className="space-y-1.5">
              {evaluation.missing_elements.map((elem, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs text-rose-200/90">
                  <span className="text-rose-400 font-bold shrink-0 mt-0.5">&bull;</span>
                  <span>{elem}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-emerald-400/80 italic flex items-center gap-1">
              <Check className="h-3.5 w-3.5" />
              All essential production criteria satisfied.
            </p>
          )}
        </div>
      </div>

      {/* Model Reference Solution Accordion */}
      {evaluation.model_solution && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/90 overflow-hidden">
          <div className="flex items-center justify-between p-3.5 bg-slate-900/70 border-b border-slate-800">
            <button
              type="button"
              onClick={() => setModelSolutionOpen(!modelSolutionOpen)}
              className="flex items-center gap-2 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
            >
              <Code2 className="h-4 w-4 text-indigo-400" />
              <span>Production Reference Solution</span>
              {modelSolutionOpen ? (
                <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
              )}
            </button>

            <button
              type="button"
              onClick={handleCopyModel}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-[11px] text-slate-400 hover:text-slate-200"
            >
              {copiedSolution ? (
                <>
                  <Check className="h-3 w-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Copy Reference</span>
                </>
              )}
            </button>
          </div>

          {modelSolutionOpen && (
            <pre className="p-4 font-mono text-xs text-slate-300 overflow-x-auto leading-relaxed bg-slate-950">
              {evaluation.model_solution}
            </pre>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          >
            Refactor & Re-submit
          </button>
        )}
        {onNextChallenge && (
          <button
            type="button"
            onClick={onNextChallenge}
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 shadow-lg shadow-indigo-950/40 transition-colors"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Generate Next Challenge</span>
          </button>
        )}
      </div>
    </div>
  );
}
