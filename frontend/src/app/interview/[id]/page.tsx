"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Award,
  CheckCircle2,
  FileCode,
  Loader2,
  Send,
  Shield,
  Sparkles,
} from "lucide-react";

import { DefenseTurnBubble } from "@/components/domain/DefenseTurnBubble";
import { startDefenseSession, submitDefenseAnswer } from "@/lib/defenseApi";
import { supabase } from "@/lib/supabase";
import type { DefenseSessionState } from "@/types/defense";

export default function DefenseInterviewPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [session, setSession] = useState<DefenseSessionState | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);

  const transcriptBottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    transcriptBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const initSession = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);

    try {
      const {
        data: { session: authSession },
      } = await supabase.auth.getSession();

      if (!authSession) {
        router.push("/login");
        return;
      }

      const newSession = await startDefenseSession(projectId, authSession.access_token, 3);
      setSession(newSession);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start defense session");
    } finally {
      setLoading(false);
    }
  }, [projectId, router]);

  useEffect(() => {
    initSession();
  }, [initSession]);

  useEffect(() => {
    scrollToBottom();
  }, [session?.turns]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session || submitting || answer.trim().length < 5) return;

    setSubmitting(true);
    setError(null);

    try {
      const {
        data: { session: authSession },
      } = await supabase.auth.getSession();

      if (!authSession) {
        router.push("/login");
        return;
      }

      const updatedSession = await submitDefenseAnswer(
        session.session_id,
        answer.trim(),
        authSession.access_token
      );
      setSession(updatedSession);
      setAnswer("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit defense answer");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="font-mono text-sm">Initializing repository defense session...</p>
      </div>
    );
  }

  if (error && !session) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-6">
        <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mx-auto text-rose-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Defense Session Failed</h2>
        <p className="text-sm text-slate-400 font-mono">{error}</p>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:text-white font-mono text-xs border border-slate-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const isCompleted = session?.status === "session_completed";
  const currentIdx = session?.current_question_index ?? 0;
  const currentProgress = session?.questions?.[currentIdx];
  const activeQuestion = currentProgress?.question;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 text-slate-100 flex flex-col min-h-[calc(100vh-5rem)]">
      {/* Navigation & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-400" />
              <h1 className="text-base font-bold text-white tracking-tight">
                Architectural Defense Session
              </h1>
            </div>
            <p className="text-xs font-mono text-slate-400">
              Session ID: <span className="text-slate-300">{session?.session_id.slice(0, 8)}...</span>
            </p>
          </div>
        </div>

        {session && (
          <div className="flex items-center gap-2 self-start sm:self-auto font-mono text-xs">
            <span className="px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
              Question {Math.min(currentIdx + 1, session.total_questions)} of {session.total_questions}
            </span>
            <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 capitalize">
              ● {session.status.replace("_", " ")}
            </span>
          </div>
        )}
      </div>

      {/* Active Question Anchor Card */}
      {activeQuestion && !isCompleted && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 sm:p-5 space-y-3 shadow-md backdrop-blur-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono uppercase font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Sparkles className="w-3 h-3" />
              Target Topic: {activeQuestion.category}
            </span>
            {activeQuestion.cited_files.length > 0 && (
              <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                <FileCode className="w-3.5 h-3.5 text-slate-500" />
                {activeQuestion.cited_files[0]}
              </span>
            )}
          </div>
          <h2 className="text-sm sm:text-base font-semibold text-slate-100 leading-snug">
            {activeQuestion.question_text}
          </h2>
          <p className="text-xs text-slate-400 font-mono italic">
            Grounding Anchor: {activeQuestion.context_hint}
          </p>
        </div>
      )}

      {/* Error Alert Banner if submission fails */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs font-mono flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Dialogue Transcript */}
      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {session?.turns.map((turn) => (
          <DefenseTurnBubble key={turn.id} turn={turn} />
        ))}
        {submitting && (
          <div className="flex items-center gap-2 text-xs font-mono text-emerald-400/80 p-3 bg-slate-900/50 border border-emerald-500/20 rounded-xl max-w-sm">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Principal Engineer is evaluating your defense...</span>
          </div>
        )}
        <div ref={transcriptBottomRef} />
      </div>

      {/* Bottom Action Area: Completion Card or Input Form */}
      {isCompleted ? (
        <div className="bg-emerald-950/20 border border-emerald-500/40 rounded-2xl p-6 text-center space-y-4 mt-auto">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto text-emerald-400">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Defense Session Completed</h3>
            <p className="text-xs font-mono text-slate-400 mt-1">
              You successfully defended your codebase through all technical questions.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 border border-emerald-500/30 text-emerald-400 font-mono text-base font-bold shadow-md">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span>Overall Score: {session?.overall_score ?? "8.0"} / 10.0</span>
          </div>
          <div className="pt-2">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs font-mono transition-colors shadow-lg shadow-emerald-950/30"
            >
              Return to Project Dashboard
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-auto space-y-2 pt-2">
          <div className="relative rounded-xl border border-slate-800 bg-slate-900 focus-within:border-emerald-500/60 transition-colors">
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              disabled={submitting}
              placeholder={
                session?.status === "stress_test_active"
                  ? "Describe your mitigation strategy (e.g. connection pooling, caching, rate limiting, fallbacks)..."
                  : session?.status === "mentor_active"
                  ? "Address the architectural hint and explain your corrected design..."
                  : "Explain and defend your architectural choices with reference to your repository code..."
              }
              rows={3}
              maxLength={5000}
              className="w-full resize-none bg-transparent p-4 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
            />
            <div className="flex items-center justify-between border-t border-slate-800/80 px-4 py-2 text-xs font-mono text-slate-500">
              <span>{answer.length} / 5000 chars (min 5)</span>
              <button
                type="submit"
                disabled={submitting || answer.trim().length < 5}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-1.5 font-semibold text-white transition-colors hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Evaluating...</span>
                  </>
                ) : (
                  <>
                    <span>Submit</span>
                    <Send className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  );
}
