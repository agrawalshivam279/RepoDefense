"use client";

import React from "react";
import {
  AlertCircle,
  ArrowRight,
  Award,
  CheckCircle2,
  RefreshCw,
  TrendingUp,
  XCircle,
} from "lucide-react";
import type { RetestEvaluationResponse } from "@/types/retest";

interface RetestEvaluationModalProps {
  evaluation: RetestEvaluationResponse;
  currentIndex: number;
  totalQuestions: number;
  onNextQuestion: () => void;
  onFinishSession: () => void;
}

export const RetestEvaluationModal: React.FC<RetestEvaluationModalProps> = ({
  evaluation,
  currentIndex,
  totalQuestions,
  onNextQuestion,
  onFinishSession,
}) => {
  const isLastQuestion = currentIndex + 1 >= totalQuestions;
  const isPassed = evaluation.passed;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/90 p-6 shadow-2xl backdrop-blur-md space-y-6">
      {/* Score and Status Banner */}
      <div
        className={`rounded-xl border p-5 ${
          isPassed
            ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-400"
            : "border-rose-500/30 bg-rose-950/20 text-rose-400"
        }`}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            {isPassed ? (
              <CheckCircle2 className="h-8 w-8 text-emerald-400 shrink-0" />
            ) : (
              <XCircle className="h-8 w-8 text-rose-400 shrink-0" />
            )}
            <div>
              <h3 className="text-base font-bold text-zinc-100 sm:text-lg">
                {isPassed ? "Defense Passed — Weakness Remediated" : "Defense Incomplete — Gaps Remain"}
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                {isPassed
                  ? "Your architectural solution satisfied production constraints and rubrics."
                  : "The proposed defense lacked critical isolation, scaling, or boundary details."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 self-start sm:self-center">
            <div className="text-right">
              <span className="text-2xl font-black text-zinc-100">{evaluation.score}</span>
              <span className="text-xs text-zinc-500"> / 100</span>
              <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold">
                Evaluation Score
              </div>
            </div>
          </div>
        </div>

        {/* Database Resolution & Skill Delta Banner */}
        {evaluation.weakness_resolved && (
          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-emerald-500/20 pt-3 text-xs text-emerald-300">
            <span className="flex items-center gap-1.5 font-semibold">
              <Award className="h-4 w-4 text-emerald-400" />
              Weakness Marked Resolved
            </span>
            {evaluation.updated_proficiency !== null && evaluation.updated_proficiency !== undefined && (
              <span className="flex items-center gap-1.5 rounded bg-emerald-500/10 px-2 py-0.5 font-bold text-emerald-400 border border-emerald-500/20">
                <TrendingUp className="h-3.5 w-3.5" />
                Updated Skill Proficiency: {evaluation.updated_proficiency}%
              </span>
            )}
          </div>
        )}
      </div>

      {/* Mentor Feedback Text */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
          Principal Engineer Feedback
        </h4>
        <p className="rounded-lg border border-zinc-800/80 bg-zinc-900/40 p-4 text-xs leading-relaxed text-zinc-300">
          {evaluation.feedback}
        </p>
      </div>

      {/* Key Improvements & Remaining Gaps Grid */}
      <div className="grid gap-4 sm:grid-cols-2">
        {evaluation.key_improvements.length > 0 && (
          <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/30 p-4 space-y-2">
            <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" /> Demonstrated Strengths
            </span>
            <ul className="space-y-1.5 text-xs text-zinc-300">
              {evaluation.key_improvements.map((imp, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <span className="text-emerald-500 mt-0.5">•</span>
                  <span>{imp}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {evaluation.remaining_gaps.length > 0 && (
          <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/30 p-4 space-y-2">
            <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
              <AlertCircle className="h-4 w-4" /> Remaining Gaps to Study
            </span>
            <ul className="space-y-1.5 text-xs text-zinc-300">
              {evaluation.remaining_gaps.map((gap, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <span className="text-amber-500 mt-0.5">•</span>
                  <span>{gap}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-end gap-3 border-t border-zinc-800/80 pt-4">
        {isLastQuestion ? (
          <button
            type="button"
            onClick={onFinishSession}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-500 transition-all"
          >
            <CheckCircle2 className="h-4 w-4" />
            Complete Re-Test Session
          </button>
        ) : (
          <button
            type="button"
            onClick={onNextQuestion}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-500 transition-all"
          >
            Next Question ({currentIndex + 1} of {totalQuestions})
            <ArrowRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
};
