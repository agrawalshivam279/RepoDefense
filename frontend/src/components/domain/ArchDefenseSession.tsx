"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ArrowLeft, Award, CheckCircle2, Loader2, Send, XCircle } from "lucide-react";
import { ArchTopologyPanel } from "@/components/domain/ArchTopologyPanel";
import { submitArchDefenseTurn } from "@/lib/archDefenseApi";
import { supabase } from "@/lib/supabase";
import type { ArchDefenseSessionState, ArchDefenseStage } from "@/types/archDefense";
import type { DiagramEdge, DiagramNode, DiagramResponse, DiagramType } from "@/types/diagram";

const MIN_ANSWER_LENGTH = 1;
const MAX_ANSWER_LENGTH = 8000;

export interface ArchDefenseSessionProps {
  session: ArchDefenseSessionState;
  projectName?: string;
  diagramType?: DiagramType;
  diagramNodes?: DiagramNode[];
  diagramEdges?: DiagramEdge[];
  isDiagramFallback?: boolean;
  onSessionUpdate: (updated: ArchDefenseSessionState) => void;
  onExitSession: () => void;
}

const STAGE_META: Record<ArchDefenseStage, { label: string; className: string }> = {
  TOPIC_ACTIVE: {
    label: "1. Design Claim",
    className: "border-cyan-500/30 bg-cyan-500/10 text-cyan-300",
  },
  TRADEOFF_CHALLENGE: {
    label: "2. Tradeoff Stress Test",
    className: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  },
  COMPLETED: {
    label: "Completed",
    className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  },
};

export function ArchDefenseSession({
  session,
  projectName,
  diagramType = "flowchart TD",
  diagramNodes = [],
  diagramEdges = [],
  isDiagramFallback = false,
  onSessionUpdate,
  onExitSession,
}: ArchDefenseSessionProps) {
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isMountedRef = useRef(true);
  const activeSessionIdRef = useRef(session.session_id);
  const submitRequestIdRef = useRef(0);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    activeSessionIdRef.current = session.session_id;
    submitRequestIdRef.current += 1;
    setAnswer("");
    setSubmitting(false);
    setError(null);
  }, [session.session_id]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session.turns.length, session.stage]);

  const diagramPayload = useMemo<DiagramResponse>(
    () => ({
      project_id: session.project_id,
      project_name: projectName ?? session.primary_pattern_name,
      diagram_type: diagramType,
      mermaid_code: session.mermaid_code,
      nodes: diagramNodes,
      edges: diagramEdges,
      is_fallback: isDiagramFallback,
      summary: session.diagram_summary,
    }),
    [session, projectName, diagramType, diagramNodes, diagramEdges, isDiagramFallback]
  );

  const stageMeta = STAGE_META[session.stage];
  const isCompleted = session.stage === "COMPLETED";
  const trimmedAnswer = answer.trim();
  const charCount = Array.from(trimmedAnswer).length;
  const canSubmit =
    !isCompleted && !submitting && charCount >= MIN_ANSWER_LENGTH && charCount <= MAX_ANSWER_LENGTH;

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!canSubmit) return;

    const requestId = ++submitRequestIdRef.current;
    const targetSessionId = session.session_id;
    setSubmitting(true);
    setError(null);

    try {
      const { data: authData } = await supabase.auth.getSession();
      const token = authData.session?.access_token;
      if (!token) {
        if (isMountedRef.current && submitRequestIdRef.current === requestId) {
          setError("Authentication session expired. Please sign in again.");
          setSubmitting(false);
        }
        return;
      }

      const updated = await submitArchDefenseTurn(targetSessionId, trimmedAnswer, token);
      if (
        !isMountedRef.current ||
        activeSessionIdRef.current !== targetSessionId ||
        submitRequestIdRef.current !== requestId
      ) {
        return;
      }

      setAnswer("");
      onSessionUpdate(updated);
    } catch (err) {
      if (
        isMountedRef.current &&
        activeSessionIdRef.current === targetSessionId &&
        submitRequestIdRef.current === requestId
      ) {
        setError(err instanceof Error ? err.message : "Failed to evaluate architectural defense.");
      }
    } finally {
      if (
        isMountedRef.current &&
        activeSessionIdRef.current === targetSessionId &&
        submitRequestIdRef.current === requestId
      ) {
        setSubmitting(false);
      }
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <ArchTopologyPanel
        diagram={diagramPayload}
        primaryPatternName={session.primary_pattern_name}
        focusArea={session.topic.focus_area}
        targetNodes={session.topic.target_nodes}
        expectedTradeoffs={session.topic.expected_tradeoffs}
        riskReferences={session.topic.risk_references}
      />

      <section className="flex flex-col rounded-xl border border-zinc-800 bg-zinc-900/70 lg:col-span-7">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 px-5 py-4">
          <div className="min-w-0">
            <button
              type="button"
              onClick={onExitSession}
              className="mb-1 inline-flex items-center gap-1.5 text-xs font-medium text-zinc-400 transition hover:text-zinc-200"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              All Defense Topics
            </button>
            <h2 className="truncate text-base font-semibold text-zinc-100">{session.topic.title}</h2>
          </div>
          <span className={`rounded-full border px-3 py-1 text-xs font-medium ${stageMeta.className}`}>
            {stageMeta.label}
          </span>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-5" style={{ maxHeight: "540px" }}>
          {session.turns.map((turn) => {
            const isCandidate = turn.role === "candidate";
            const isSystem = turn.role === "system";
            const roleLabel = isCandidate ? "You (Candidate)" : isSystem ? "System Evaluation" : "Principal Architect";
            const cardTone = isCandidate
              ? "ml-8 border-cyan-500/25 bg-cyan-500/10 text-zinc-100"
              : isSystem
                ? "border-amber-500/25 bg-amber-500/5 text-amber-100"
                : "mr-8 border-zinc-800 bg-zinc-950/80 text-zinc-200";
            return (
              <div key={turn.id} className={`rounded-xl border p-4 text-sm ${cardTone}`}>
                <div className="mb-1.5 flex items-center justify-between text-[11px] font-medium uppercase tracking-wider text-zinc-400">
                  <span>{roleLabel}</span>
                  <span>{STAGE_META[turn.stage]?.label ?? turn.stage}</span>
                </div>
                <p className="whitespace-pre-wrap leading-relaxed">{turn.content}</p>
              </div>
            );
          })}

          {isCompleted && (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-emerald-300">
                  <Award className="h-5 w-5" />
                  <h3 className="text-sm font-semibold uppercase tracking-wider">Architecture Defense Verdict</h3>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                  {typeof session.overall_score === "number" && (
                    <span className="rounded-md border border-emerald-500/40 bg-zinc-950 px-2.5 py-1 text-emerald-300">
                      Overall: {session.overall_score}/10
                    </span>
                  )}
                  {typeof session.boundary_coherence_score === "number" && (
                    <span className="rounded-md border border-cyan-500/40 bg-zinc-950 px-2.5 py-1 text-cyan-300">
                      Coherence: {session.boundary_coherence_score}/10
                    </span>
                  )}
                </div>
              </div>

              <div className="mb-3 flex items-center gap-2 text-xs">
                {session.pattern_rationale_solid ? (
                  <span className="inline-flex items-center gap-1.5 text-emerald-300">
                    <CheckCircle2 className="h-4 w-4" />
                    Pattern rationale verified against topology
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-amber-300">
                    <XCircle className="h-4 w-4" />
                    Pattern rationale needs stronger boundary justification
                  </span>
                )}
              </div>

              {session.feedback && (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-200">{session.feedback}</p>
              )}
            </div>
          )}
          <div ref={transcriptEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="border-t border-zinc-800 bg-zinc-950/60 p-4">
          {error && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}
          <textarea
            aria-label="Architectural defense response"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => {
              if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                e.preventDefault();
                void handleSubmit();
              }
            }}
            disabled={isCompleted || submitting}
            rows={4}
            placeholder={
              isCompleted
                ? "Defense completed. Choose another topic to continue."
                : "Defend your component boundaries, coupling choices, and tradeoff mitigation..."
            }
            className="w-full resize-y rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-sm text-zinc-100 placeholder-zinc-500 focus:border-cyan-500/60 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <span className={`text-xs ${charCount > MAX_ANSWER_LENGTH ? "text-rose-400" : "text-zinc-500"}`}>
              {charCount} / {MAX_ANSWER_LENGTH} chars (Ctrl+Enter to submit)
            </span>
            <button
              type="submit"
              disabled={!canSubmit}
              className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              <span>{isCompleted ? "Defense Finished" : "Submit Defense"}</span>
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
