"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  Award,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FileCode,
  GitPullRequest,
  Loader2,
  Send,
  Sparkles,
} from "lucide-react";

import { DefenseTurnBubble } from "@/components/domain/DefenseTurnBubble";
import { submitPRDefenseAnswer } from "@/lib/prDefenseApi";
import { supabase } from "@/lib/supabase";
import type { PRDefenseSessionState } from "@/types/prDefense";

interface PRDefenseSessionProps {
  session: PRDefenseSessionState;
  onSessionUpdate: (updated: PRDefenseSessionState) => void;
  onExitSession: () => void;
}

export function PRDefenseSession({
  session,
  onSessionUpdate,
  onExitSession,
}: PRDefenseSessionProps) {
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCitedLines, setShowCitedLines] = useState(true);

  const bottomRef = useRef<HTMLDivElement>(null);
  const isCompleted = session.status === "session_completed";
  const currentIdx = session.current_question_index ?? 0;
  const currentDiffQ = session.diff_questions?.[currentIdx];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session.turns, submitting]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting || answer.trim().length < 5 || isCompleted) return;

    setSubmitting(true);
    setError(null);
    try {
      const { data: { session: authSession } } = await supabase.auth.getSession();
      if (!authSession) throw new Error("Authentication session expired.");

      const updated = await submitPRDefenseAnswer(
        session.session_id,
        answer.trim(),
        authSession.access_token
      );
      onSessionUpdate(updated);
      setAnswer("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit defense answer.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="space-y-4">
      {/* Session Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-zinc-800 bg-zinc-950 p-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onExitSession}
            className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition-colors"
            title="Return to PR diff inspection"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <GitPullRequest className="h-4 w-4 text-rose-400" />
              <h2 className="text-sm font-semibold text-zinc-100">
                PR #{session.pr_number}: {session.pr_title}
              </h2>
              <a
                href={session.pr_html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-500 hover:text-zinc-300"
              >
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <p className="text-xs text-zinc-400">
              Author: <span className="text-zinc-300">@{session.pr_author}</span> · Session:{" "}
              <span className="font-mono text-zinc-400">{session.session_id.slice(0, 8)}...</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1 text-zinc-300">
            Q {Math.min(currentIdx + 1, session.total_questions)}/{session.total_questions}
          </span>
          <span className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-rose-400 capitalize">
            ● {session.status.replace(/_/g, " ")}
          </span>
        </div>
      </div>

      {/* Active Diff Anchor Card */}
      {currentDiffQ && !isCompleted && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 font-mono text-rose-400">
                <FileCode className="h-3 w-3" />
                {currentDiffQ.diff_file_path}
              </span>
              <span className="rounded bg-zinc-800 border border-zinc-700 px-2 py-0.5 font-mono text-zinc-400">
                {currentDiffQ.diff_hunk_header}
              </span>
              <span className="rounded bg-zinc-800/80 px-2 py-0.5 capitalize text-zinc-300">
                {currentDiffQ.change_type}
              </span>
            </div>

            {currentDiffQ.cited_lines?.length > 0 && (
              <button
                type="button"
                onClick={() => setShowCitedLines((prev) => !prev)}
                className="inline-flex items-center gap-1 text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                <span>{showCitedLines ? "Hide" : "Show"} Cited Diff ({currentDiffQ.cited_lines.length})</span>
                {showCitedLines ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              </button>
            )}
          </div>

          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-rose-400" />
              {currentDiffQ.question_text}
            </h3>
            {currentDiffQ.context_hint && (
              <p className="text-xs italic text-zinc-400 font-mono">
                Hint: {currentDiffQ.context_hint}
              </p>
            )}
          </div>

          {/* Quoted Diff Lines Preview */}
          {showCitedLines && currentDiffQ.cited_lines?.length > 0 && (
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-2.5 overflow-x-auto max-h-48 font-mono text-xs space-y-0.5">
              {currentDiffQ.cited_lines.map((line, idx) => {
                const isAdd = line.startsWith("+");
                const isDel = line.startsWith("-");
                return (
                  <div
                    key={idx}
                    className={`px-2 py-0.5 rounded whitespace-pre ${
                      isAdd
                        ? "bg-emerald-950/40 text-emerald-300 border-l-2 border-emerald-500"
                        : isDel
                        ? "bg-rose-950/40 text-rose-300 border-l-2 border-rose-500"
                        : "text-zinc-400"
                    }`}
                  >
                    {line}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Turns Dialogue Transcript */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 space-y-3 min-h-[280px] max-h-[500px] overflow-y-auto">
        {session.turns.map((turn) => (
          <DefenseTurnBubble key={turn.id} turn={turn} />
        ))}
        {submitting && (
          <div className="flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-950/20 p-3 text-xs font-mono text-rose-300 max-w-sm">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Principal Engineer is interrogating your changes...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-400 font-mono">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Answer Input or Completion View */}
      {isCompleted ? (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-6 text-center space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-emerald-500/40 bg-emerald-500/10 text-emerald-400">
            <Award className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-zinc-100">PR Defense Session Completed</h3>
          <p className="text-xs text-zinc-400 max-w-md mx-auto">
            You successfully completed the architectural interrogation for PR #{session.pr_number}. Review the transcript above or return to diff inspection.
          </p>
          <button
            type="button"
            onClick={onExitSession}
            className="inline-flex items-center gap-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 px-4 py-2 text-xs font-semibold text-zinc-200 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Return to PR Overview
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-2">
          <div className="relative">
            <textarea
              rows={3}
              placeholder="Defend your PR design choices... Explain tradeoffs, failure modes, or concurrency mitigations. (Ctrl+Enter to submit)"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={submitting}
              className="w-full rounded-xl border border-zinc-700 bg-zinc-900/90 p-3.5 text-xs text-zinc-100 placeholder-zinc-500 focus:border-rose-500 focus:outline-none disabled:opacity-50"
            />
          </div>
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span>{answer.trim().length} characters (min 5 required)</span>
            <button
              type="submit"
              disabled={submitting || answer.trim().length < 5}
              className="inline-flex items-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-500 px-4 py-2 font-medium text-white transition-colors disabled:opacity-40"
            >
              {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
              Submit Defense
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
