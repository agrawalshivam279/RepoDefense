"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, Clock, FileCode, Flame, Loader2, RotateCcw, Send } from "lucide-react";

import { IncidentPostmortemCard } from "@/components/domain/IncidentPostmortemCard";
import { IncidentScenarioCard, SeverityBadge } from "@/components/domain/IncidentScenarioCard";
import { IncidentTurnTranscript } from "@/components/domain/IncidentTurnTranscript";
import {
  fetchProjectScenarios,
  startIncidentSession,
  submitIncidentAnswer,
} from "@/lib/incidentApi";
import { supabase } from "@/lib/supabase";
import type { FailureCategory, IncidentDefenseSessionState, IncidentScenario } from "@/types/incident";

interface IncidentWarRoomProps {
  projectId: string;
}

const MIN_ANSWER_LENGTH = 10;
const MAX_ANSWER_LENGTH = 5000;

const CATEGORIES: { label: string; value: FailureCategory | "" }[] = [
  { label: "All Categories", value: "" },
  { label: "Database Outage", value: "DATABASE_OUTAGE" },
  { label: "Dependency Timeout", value: "DEPENDENCY_TIMEOUT" },
  { label: "Cache Failure", value: "CACHE_FAILURE" },
  { label: "Broker Partition", value: "MESSAGE_BROKER_PARTITION" },
  { label: "Resource Exhaustion", value: "RESOURCE_EXHAUSTION" },
  { label: "Concurrency Race", value: "CONCURRENCY_RACE" },
];

export function IncidentWarRoom({ projectId }: IncidentWarRoomProps) {
  const [scenarios, setScenarios] = useState<IncidentScenario[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<FailureCategory | "">("");
  const [loadingScenarios, setLoadingScenarios] = useState(false);
  const [session, setSession] = useState<IncidentDefenseSessionState | null>(null);
  const [startingSession, setStartingSession] = useState(false);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const latestRequestRef = useRef(0);

  const getAuthToken = useCallback(async () => {
    const { data: { session: authSession } } = await supabase.auth.getSession();
    if (!authSession) throw new Error("Authentication required. Please log in.");
    return authSession.access_token;
  }, []);

  const loadScenarios = useCallback(async () => {
    const requestId = ++latestRequestRef.current;
    setLoadingScenarios(true);
    setError(null);
    try {
      const token = await getAuthToken();
      const res = await fetchProjectScenarios(
        projectId,
        token,
        selectedCategory || undefined,
        4
      );
      if (requestId === latestRequestRef.current) setScenarios(res.scenarios);
    } catch (err) {
      if (requestId === latestRequestRef.current) {
        setError(err instanceof Error ? err.message : "Failed to load scenarios");
      }
    } finally {
      if (requestId === latestRequestRef.current) setLoadingScenarios(false);
    }
  }, [projectId, selectedCategory, getAuthToken]);

  useEffect(() => {
    loadScenarios();
    return () => {
      latestRequestRef.current += 1;
    };
  }, [loadScenarios]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.turns, submitting]);

  const handleResetSession = () => {
    setSession(null);
    setError(null);
  };

  const handleStartSession = async (scenarioId: string) => {
    setStartingSession(true);
    setError(null);
    try {
      const token = await getAuthToken();
      const newSession = await startIncidentSession(projectId, token, scenarioId);
      setSession(newSession);
      setAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to launch War Room session");
    } finally {
      setStartingSession(false);
    }
  };

  const trimmedLength = answer.trim().length;
  const isAnswerInvalid =
    trimmedLength < MIN_ANSWER_LENGTH || trimmedLength > MAX_ANSWER_LENGTH;

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session || submitting || isAnswerInvalid) return;
    setSubmitting(true);
    setError(null);
    try {
      const token = await getAuthToken();
      const updated = await submitIncidentAnswer(session.id, answer.trim(), token);
      setSession(updated);
      setAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit defense response");
    } finally {
      setSubmitting(false);
    }
  };

  const errorBanner = error ? (
    <div
      role="alert"
      className="rounded-lg border border-rose-800/40 bg-rose-950/30 p-4 text-xs text-rose-300"
    >
      {error}
    </div>
  ) : null;

  if (!session) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-rose-950/40 bg-gradient-to-r from-rose-950/20 via-zinc-950 to-zinc-950 p-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500"></span>
              </span>
              <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
                <Flame className="h-5 w-5 text-rose-500" /> SRE Incident War Room
              </h2>
            </div>
            <p className="text-sm text-zinc-400">
              Hypothetical production outages synthesized directly from this repository&apos;s code symbols and architecture.
            </p>
          </div>
          <select
            aria-label="Filter scenarios by failure category"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value as FailureCategory | "")}
            className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-rose-500"
          >
            {CATEGORIES.map((c) => (
              <option key={c.label} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        {errorBanner}

        {loadingScenarios ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-400">
            <Loader2 className="h-8 w-8 animate-spin text-rose-500" />
            <p className="text-sm font-mono">Synthesizing chaos scenarios from repository AST...</p>
          </div>
        ) : scenarios.length === 0 ? (
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-8 text-center space-y-3">
            <p className="text-sm text-zinc-300">
              No chaos scenarios available{selectedCategory ? " for this failure category" : ""}.
            </p>
            <button
              type="button"
              onClick={loadScenarios}
              className="inline-flex items-center gap-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-100 px-3 py-1.5 text-xs font-medium transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Retry Synthesis
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {scenarios.map((sc) => (
              <IncidentScenarioCard
                key={sc.id}
                scenario={sc}
                onSelect={handleStartSession}
                starting={startingSession}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* War Room Alert Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-rose-900/60 bg-gradient-to-r from-rose-950/50 via-zinc-950 to-zinc-950 p-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleResetSession}
            aria-label="Exit War Room"
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
            title="Exit War Room"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <SeverityBadge severity={session.scenario.severity} />
              <span className="font-mono text-xs text-rose-300 font-semibold uppercase">{session.stage}</span>
            </div>
            <h2 className="text-sm font-semibold text-zinc-100 line-clamp-1">{session.scenario.title}</h2>
          </div>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-zinc-400">
          <Clock className="h-3.5 w-3.5" />
          <span>Turn {session.current_turn_index} of {session.max_turns}</span>
        </div>
      </div>

      {/* Target Anchor & Symptoms Inspector */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-4 space-y-3">
        <div className="flex items-center justify-between text-xs font-mono text-zinc-400 border-b border-zinc-800/80 pb-2">
          <span className="flex items-center gap-1.5 text-zinc-300">
            <FileCode className="h-3.5 w-3.5 text-rose-400" />
            {session.scenario.grounded_target.file_path}
          </span>
          {session.scenario.grounded_target.symbol_name && (
            <span className="text-rose-400">symbol: {session.scenario.grounded_target.symbol_name}</span>
          )}
        </div>
        <div className="space-y-1">
          <div className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Telemetry Symptoms:</div>
          <div className="flex flex-wrap gap-1.5">
            {session.scenario.symptoms.map((symptom, idx) => (
              <span key={idx} className="rounded bg-rose-950/40 border border-rose-900/40 px-2 py-0.5 text-[11px] text-rose-300">
                ⚠️ {symptom}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Turns Dialogue Transcript */}
      <IncidentTurnTranscript turns={session.turns} />

      {errorBanner}

      {session.stage === "POSTMORTEM" ? (
        <IncidentPostmortemCard
          overallScore={session.overall_score}
          postmortemSummary={session.postmortem_summary}
          onSimulateAnother={handleResetSession}
        />
      ) : (
        <form onSubmit={handleSubmitAnswer} className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-semibold text-zinc-300">Your Architectural Defense & Mitigation:</span>
            <span>Min {MIN_ANSWER_LENGTH} · Max {MAX_ANSWER_LENGTH.toLocaleString()} chars</span>
          </div>
          <textarea
            aria-label="Architectural defense and mitigation response"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            maxLength={MAX_ANSWER_LENGTH}
            disabled={submitting}
            placeholder="Explain how your code mitigates this failure, what safeguards exist (retries, timeouts, pools, caches), or propose an architectural fix..."
            rows={4}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-sm text-zinc-200 focus:outline-none focus:border-rose-500 disabled:opacity-50 resize-y"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-500 font-mono">{answer.length}/{MAX_ANSWER_LENGTH} chars</span>
            <button
              type="submit"
              disabled={submitting || isAnswerInvalid}
              className="flex items-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-medium px-4 py-2 text-xs transition-colors shadow-lg shadow-rose-950/40"
            >
              {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
              Submit Defense Mitigation
            </button>
          </div>
        </form>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
