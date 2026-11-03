"use client";

import { AlertTriangle, Award, Bot, FileCode, Lightbulb, ShieldAlert, User } from "lucide-react";
import type { DefenseTurn } from "@/types/defense";

interface DefenseTurnBubbleProps {
  turn: DefenseTurn;
}

export function DefenseTurnBubble({ turn }: DefenseTurnBubbleProps) {
  const isCandidate = turn.role === "candidate";
  const isSystem = turn.role === "system";

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <div className="bg-slate-900/90 border border-emerald-500/40 rounded-xl px-5 py-3 max-w-xl text-center shadow-lg shadow-emerald-950/20">
          <div className="flex items-center justify-center gap-2 text-emerald-400 font-semibold text-sm mb-1">
            <Award className="w-4 h-4" />
            <span>Interview Stage Notice</span>
          </div>
          <p className="text-xs text-slate-300 font-mono leading-relaxed">{turn.content}</p>
        </div>
      </div>
    );
  }

  const isStressTest = turn.stage === "stress_test_active" && turn.role === "interviewer";
  const isMentor = turn.stage === "mentor_active" && turn.role === "interviewer";
  const depthScore = turn.metadata?.depth_score;
  const finalScore = turn.metadata?.final_score;
  const citedFiles = turn.metadata?.cited_files;

  return (
    <div className={`flex flex-col gap-2 ${isCandidate ? "items-end" : "items-start"}`}>
      {/* Header Info */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-400 px-1">
        {isCandidate ? (
          <>
            <span className="text-slate-500">
              {new Date(turn.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
            <span className="font-semibold text-slate-200">You (Candidate)</span>
            <div className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
              <User className="w-3 h-3" />
            </div>
          </>
        ) : (
          <>
            <div className="w-5 h-5 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Bot className="w-3 h-3" />
            </div>
            <span className="font-semibold text-emerald-400">Principal Engineer</span>
            <span className="text-slate-500">
              {new Date(turn.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </>
        )}
      </div>

      {/* Bubble Container */}
      <div
        className={`max-w-3xl rounded-2xl p-4 sm:p-5 text-sm transition-all shadow-sm ${
          isCandidate
            ? "bg-slate-900 border border-slate-800 text-slate-100 rounded-tr-none"
            : isStressTest
            ? "bg-amber-950/20 border border-amber-500/40 text-slate-100 rounded-tl-none shadow-amber-950/10"
            : isMentor
            ? "bg-indigo-950/20 border border-indigo-500/40 text-slate-100 rounded-tl-none shadow-indigo-950/10"
            : "bg-slate-900/80 border border-slate-800 text-slate-100 rounded-tl-none"
        }`}
      >
        {/* Dynamic Context Header inside Interviewer Bubble */}
        {!isCandidate && (isStressTest || isMentor || depthScore !== undefined || finalScore !== undefined) && (
          <div className="flex flex-wrap items-center gap-2 mb-3 pb-3 border-b border-slate-800/80">
            {isStressTest && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
                <ShieldAlert className="w-3 h-3" />
                Production Stress-Test
              </span>
            )}
            {isMentor && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                <Lightbulb className="w-3 h-3" />
                Mentor Guidance & Re-test
              </span>
            )}
            {depthScore !== undefined && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Depth Score: {depthScore}/10
              </span>
            )}
            {finalScore !== undefined && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                Question Score: {finalScore}/10
              </span>
            )}
          </div>
        )}

        {/* Content Body */}
        <div className="whitespace-pre-wrap leading-relaxed font-sans text-slate-200">
          {turn.content}
        </div>

        {/* Cited Files Footer */}
        {citedFiles && citedFiles.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-800/60 flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
              <FileCode className="w-3 h-3 text-slate-500" />
              Anchors:
            </span>
            {citedFiles.map((f, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded bg-slate-800/90 border border-slate-700/60 text-[11px] font-mono text-slate-300"
              >
                {f}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
