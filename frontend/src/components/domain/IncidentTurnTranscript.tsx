"use client";

import { ShieldAlert, Zap } from "lucide-react";
import type { IncidentDefenseTurn } from "@/types/incident";

interface IncidentTurnTranscriptProps {
  turns: IncidentDefenseTurn[];
}

export function IncidentTurnTranscript({ turns }: IncidentTurnTranscriptProps) {
  return (
    <div className="space-y-4">
      {turns.map((turn) => (
        <div key={turn.turn_index} className="space-y-3">
          {/* SRE Challenge Prompt */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-rose-400 flex items-center gap-1.5">
                <ShieldAlert className="h-3.5 w-3.5" /> Principal SRE Challenge (Turn {turn.turn_index})
              </span>
              {turn.score !== null && turn.score !== undefined && (
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-zinc-800 text-emerald-400 font-bold">
                  Score: {turn.score}/100
                </span>
              )}
            </div>
            <p className="text-sm text-zinc-200 leading-relaxed font-sans">{turn.prompt}</p>
          </div>

          {/* Candidate Answer & Feedback */}
          {turn.candidate_answer && (
            <div className="rounded-xl border border-zinc-800/80 bg-zinc-950 p-4 space-y-2 ml-6">
              <div className="text-xs font-semibold text-zinc-400">Candidate Defense & Mitigation:</div>
              <p className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">{turn.candidate_answer}</p>
              {turn.feedback && (
                <div className="rounded-lg bg-zinc-900/80 border border-zinc-800 p-3 mt-2 text-xs text-zinc-300">
                  <span className="text-rose-400 font-semibold">SRE Evaluation: </span>{turn.feedback}
                </div>
              )}
            </div>
          )}

          {/* Cascading Failure Escalation */}
          {turn.escalation_injected && (
            <div className="rounded-xl border border-amber-600/40 bg-amber-950/20 p-4 space-y-1.5 ml-6">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
                <Zap className="h-3.5 w-3.5" /> Cascading Failure Escalation Injected
              </div>
              <p className="text-xs text-amber-200">{turn.escalation_injected}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
