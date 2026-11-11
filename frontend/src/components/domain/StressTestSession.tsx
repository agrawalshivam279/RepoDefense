"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileCode,
  Gauge,
  Loader2,
  RotateCcw,
  Send,
  ShieldAlert,
} from "lucide-react";

import {
  CONSTRAINT_LABELS,
  StressSeverityBadge,
  StressTurnTranscript,
} from "@/components/domain/StressTurnTranscript";
import { submitStressAnswer } from "@/lib/stressTestApi";
import { supabase } from "@/lib/supabase";
import type { StressDefenseSessionState } from "@/types/stressTest";

const MIN_ANSWER_LENGTH = 5;
const MAX_ANSWER_LENGTH = 5000;

interface StressTestSessionProps {
  session: StressDefenseSessionState;
  onSessionUpdate: (updated: StressDefenseSessionState) => void;
  onExitSession: () => void;
}

export function StressTestSession({
  session,
  onSessionUpdate,
  onExitSession,
}: StressTestSessionProps) {
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTradeoffs, setShowTradeoffs] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const isCompleted = session.stage === "COMPLETED";
  const trimmedLength = answer.trim().length;
  const isAnswerInvalid =
    trimmedLength < MIN_ANSWER_LENGTH || trimmedLength > MAX_ANSWER_LENGTH;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session.turns, submitting]);

  const submitCurrentAnswer = async () => {
    if (submitting || isAnswerInvalid || isCompleted) return;
    setSubmitting(true);
    setError(null);
    try {
      const {
        data: { session: authSession },
      } = await supabase.auth.getSession();
      if (!authSession) throw new Error("Authentication required. Please log in.");
      const updated = await submitStressAnswer(
        session.session_id,
        answer.trim(),
        authSession.access_token
      );
      onSessionUpdate(updated);
      setAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit scaling defense");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void submitCurrentAnswer();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      void submitCurrentAnswer();
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-amber-900/50 bg-gradient-to-r from-amber-950/30 via-zinc-950 to-zinc-950 p-4">
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={onExitSession}
            aria-label="Exit Stress Test"
            className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
            title="Return to scenario catalog"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <StressSeverityBadge severity={session.scenario.severity} />
              <span className="rounded bg-zinc-900 border border-zinc-800 px-2 py-0.5 font-mono text-[11px] text-amber-300">
                {CONSTRAINT_LABELS[session.scenario.constraint_type]}
              </span>
              <span className="rounded bg-zinc-900 border border-zinc-700 px-2 py-0.5 font-mono text-[11px] text-zinc-300 uppercase">
                {session.stage.replace(/_/g, " ")}
              </span>
            </div>
            <h2 className="text-sm font-semibold text-zinc-100 truncate">
              {session.scenario.title}
            </h2>
          </div>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-zinc-400 flex-shrink-0">
          <Gauge className="h-3.5 w-3.5 text-amber-400" />
          <span>Turn {session.current_turn_index + 1}</span>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono border-b border-zinc-800/80 pb-2.5">
          <div className="flex flex-wrap items-center gap-2 text-zinc-300">
            <FileCode className="h-3.5 w-3.5 text-amber-400" />
            <span>{session.scenario.target.file_path}</span>
            <span className="text-amber-300">:: {session.scenario.target.symbol_name}</span>
            <span className="rounded bg-zinc-900 px-1.5 py-0.5 text-[11px] text-zinc-400">
              L{session.scenario.target.line_range} · {session.scenario.target.component_type}
            </span>
          </div>
          {session.scenario.expected_tradeoffs.length > 0 && (
            <button
              type="button"
              onClick={() => setShowTradeoffs((prev) => !prev)}
              className="inline-flex items-center gap-1 text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              <span>{showTradeoffs || isCompleted ? "Hide" : "Reveal"} Tradeoff Checkpoints</span>
              {showTradeoffs || isCompleted ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>
          )}
        </div>
        <p className="text-xs text-zinc-300 leading-relaxed">
          {session.scenario.context_description}
        </p>
        {(showTradeoffs || isCompleted) && session.scenario.expected_tradeoffs.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {session.scenario.expected_tradeoffs.map((tradeoff, idx) => (
              <span
                key={idx}
                className="rounded bg-amber-950/30 border border-amber-800/40 px-2 py-0.5 text-[11px] text-amber-200"
              >
                {tradeoff}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 space-y-4 max-h-[500px] overflow-y-auto">
        <StressTurnTranscript turns={session.turns} submitting={submitting} />
        <div ref={bottomRef} />
      </div>

      {isCompleted ? (
        <div className="rounded-xl border border-emerald-500/40 bg-gradient-to-b from-emerald-950/30 to-zinc-950 p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-base">
                <CheckCircle2 className="h-5 w-5" /> Stress Test Defense Concluded
              </div>
              <span className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-300">
                <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
                Bottleneck Detection:{" "}
                {session.bottleneck_identified ? "Identified" : "Missed / Incomplete"}
              </span>
            </div>
            <div className="text-right">
              <span className="text-2xl font-bold font-mono text-emerald-300">
                {session.overall_score ?? 0}
              </span>
              <span className="text-xs text-zinc-400">/10</span>
            </div>
          </div>
          {session.feedback && (
            <p className="text-xs text-zinc-300 leading-relaxed bg-zinc-900/70 p-4 rounded-lg border border-zinc-800">
              {session.feedback}
            </p>
          )}
          <button
            type="button"
            onClick={onExitSession}
            className="inline-flex items-center gap-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-100 px-4 py-2 text-xs font-medium transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Test Another Scenario
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 space-y-3">
          {error && (
            <div
              role="alert"
              className="flex items-center gap-2 rounded-lg border border-rose-800/40 bg-rose-950/30 p-3 text-xs text-rose-300"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-semibold text-zinc-300">
              Your Scaling Defense & Architecture Tradeoffs:
            </span>
            <span>
              Min {MIN_ANSWER_LENGTH} · Max {MAX_ANSWER_LENGTH.toLocaleString()} chars · Ctrl+Enter
            </span>
          </div>
          <textarea
            aria-label="Scaling defense and bottleneck mitigation response"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={handleKeyDown}
            maxLength={MAX_ANSWER_LENGTH}
            disabled={submitting}
            placeholder="Specify exact bottlenecks, pooling/caching/indexing mechanisms, and consistency or cost tradeoffs..."
            rows={4}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-sm text-zinc-200 focus:outline-none focus:border-amber-500 disabled:opacity-50 resize-y"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-500 font-mono">
              {answer.length}/{MAX_ANSWER_LENGTH} chars
            </span>
            <button
              type="submit"
              disabled={submitting || isAnswerInvalid}
              className="inline-flex items-center gap-2 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-medium px-4 py-2 text-xs transition-colors"
            >
              {submitting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
              {submitting ? "Evaluating..." : "Submit Scaling Defense"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
