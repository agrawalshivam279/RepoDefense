"use client";

import { Activity, Award, Bot, Loader2, User, Zap } from "lucide-react";

import type {
  StressConstraintType,
  StressDefenseTurn,
  StressSeverity,
} from "@/types/stressTest";

export const CONSTRAINT_LABELS: Record<StressConstraintType, string> = {
  CONCURRENCY_SPIKE: "Concurrency Spike",
  DATA_VOLUME_100X: "100x Data Volume",
  MEMORY_PRESSURE: "Memory Pressure",
  NETWORK_LATENCY_JITTER: "Network Latency Jitter",
  DB_CONNECTION_STARVATION: "DB Pool Starvation",
};

const SEVERITY_STYLES: Record<StressSeverity, string> = {
  EXTREME: "bg-rose-500/10 text-rose-400 border-rose-500/30",
  SEVERE: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  MODERATE: "bg-sky-500/10 text-sky-400 border-sky-500/30",
};

export function StressSeverityBadge({ severity }: { severity: StressSeverity }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-mono font-semibold uppercase ${SEVERITY_STYLES[severity]}`}
    >
      <Activity className="h-3 w-3" />
      {severity}
    </span>
  );
}

function TurnBubble({ turn }: { turn: StressDefenseTurn }) {
  const depthScore = typeof turn.metadata?.depth_score === "number" ? turn.metadata.depth_score : null;
  const overallScore = typeof turn.metadata?.overall_score === "number" ? turn.metadata.overall_score : null;
  const scalingSound = typeof turn.metadata?.scaling_sound === "boolean" ? turn.metadata.scaling_sound : null;
  const tradeoffsAck =
    typeof turn.metadata?.tradeoffs_acknowledged === "boolean" ? turn.metadata.tradeoffs_acknowledged : null;

  if (turn.role === "system") {
    return (
      <div className="my-2 rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
            <Award className="h-4 w-4" /> Scaling Defense Evaluation Notice
          </span>
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono">
            {overallScore !== null && (
              <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-emerald-300 font-bold">
                Score: {overallScore}/10
              </span>
            )}
            {scalingSound !== null && (
              <span className="rounded bg-zinc-900 border border-zinc-800 px-2 py-0.5 text-zinc-300">
                Strategy: {scalingSound ? "Sound" : "Needs Depth"}
              </span>
            )}
            {tradeoffsAck !== null && (
              <span className="rounded bg-zinc-900 border border-zinc-800 px-2 py-0.5 text-zinc-300">
                Tradeoffs: {tradeoffsAck ? "Addressed" : "Missed"}
              </span>
            )}
          </div>
        </div>
        <p className="text-xs text-zinc-200 whitespace-pre-wrap leading-relaxed font-mono">{turn.content}</p>
      </div>
    );
  }

  const isCandidate = turn.role === "candidate";
  const isFollowUp = turn.stage === "FOLLOW_UP_CONSTRAINED" && !isCandidate;

  return (
    <div className={`flex flex-col gap-1.5 ${isCandidate ? "items-end" : "items-start"}`}>
      <div className="flex items-center gap-2 text-xs font-mono text-zinc-400 px-1">
        {isCandidate ? (
          <>
            <span className="font-semibold text-zinc-200">You (Candidate)</span>
            <User className="h-3.5 w-3.5 text-zinc-400" />
          </>
        ) : (
          <>
            <Bot className={`h-3.5 w-3.5 ${isFollowUp ? "text-amber-400" : "text-sky-400"}`} />
            <span className={`font-semibold ${isFollowUp ? "text-amber-400" : "text-sky-400"}`}>
              Principal Infrastructure Architect
            </span>
          </>
        )}
      </div>
      <div
        className={`max-w-3xl rounded-xl border p-4 text-sm space-y-2 ${
          isCandidate
            ? "border-zinc-800 bg-zinc-900 text-zinc-100 rounded-tr-none"
            : isFollowUp
            ? "border-amber-500/40 bg-amber-950/20 text-zinc-100 rounded-tl-none"
            : "border-zinc-800 bg-zinc-900/80 text-zinc-100 rounded-tl-none"
        }`}
      >
        {!isCandidate && (isFollowUp || depthScore !== null) && (
          <div className="flex flex-wrap items-center gap-2 pb-2 border-b border-zinc-800/80 text-[11px] font-mono">
            {isFollowUp && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/30 px-2.5 py-0.5 text-amber-300">
                <Zap className="h-3 w-3" /> Secondary Constraint Escalation
              </span>
            )}
            {depthScore !== null && (
              <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-emerald-300">
                Stage 1 Depth: {depthScore}/10
              </span>
            )}
          </div>
        )}
        <p className="whitespace-pre-wrap leading-relaxed text-zinc-200">{turn.content}</p>
      </div>
    </div>
  );
}

interface StressTurnTranscriptProps {
  turns: StressDefenseTurn[];
  submitting: boolean;
}

export function StressTurnTranscript({ turns, submitting }: StressTurnTranscriptProps) {
  return (
    <>
      {turns.map((turn) => (
        <TurnBubble key={turn.id} turn={turn} />
      ))}
      {submitting && (
        <div className="flex items-center gap-2 rounded-xl border border-amber-500/20 bg-amber-950/20 p-3 text-xs font-mono text-amber-300 max-w-sm">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>Evaluating scaling strategy and tradeoffs...</span>
        </div>
      )}
    </>
  );
}
