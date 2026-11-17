"use client";

import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  Code2,
  HelpCircle,
  Lightbulb,
  ShieldAlert,
} from "lucide-react";
import {
  getDifficultyStyle,
  type MiniChallengeResponse,
} from "@/types/challenge";

interface MiniChallengeCardProps {
  challenge: MiniChallengeResponse;
  className?: string;
}

export function MiniChallengeCard({ challenge, className = "" }: MiniChallengeCardProps) {
  const [checkedRequirements, setCheckedRequirements] = useState<Record<number, boolean>>({});
  const [revealedHints, setRevealedHints] = useState<Record<number, boolean>>({});
  const [hintsExpanded, setHintsExpanded] = useState<boolean>(false);

  // Reset interactive criteria and hints when challenge identity changes
  useEffect(() => {
    setCheckedRequirements({});
    setRevealedHints({});
    setHintsExpanded(false);
  }, [challenge.challenge_id]);

  const diffStyle = getDifficultyStyle(challenge.difficulty);

  const toggleReq = (idx: number) => {
    setCheckedRequirements((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const toggleHint = (idx: number) => {
    setRevealedHints((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const totalReqs = challenge.requirements.length;
  const completedReqs = Object.values(checkedRequirements).filter(Boolean).length;
  const progressPct = totalReqs > 0 ? Math.round((completedReqs / totalReqs) * 100) : 0;

  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm p-6 space-y-6 shadow-xl ${className}`}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold border ${diffStyle.badgeClass}`}
            >
              {diffStyle.label}
            </span>
            <span className="rounded-full bg-slate-800/80 px-2.5 py-0.5 text-[11px] font-medium text-slate-300 border border-slate-700/60 uppercase tracking-wider">
              {challenge.category}
            </span>
            <span className="flex items-center gap-1 text-[11px] text-slate-400 font-mono">
              <Code2 className="h-3.5 w-3.5 text-indigo-400" />
              {challenge.language}
            </span>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-white mt-1">
            {challenge.title}
          </h2>
        </div>

        {totalReqs > 0 && (
          <div className="flex items-center gap-3 shrink-0 self-start sm:self-center bg-slate-950/60 px-3 py-1.5 rounded-xl border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Criteria Checklist</span>
            <div className="flex items-center gap-1.5">
              <div className="w-16 h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <span className="text-xs font-mono font-semibold text-indigo-400">
                {completedReqs}/{totalReqs}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Scenario / Problem Statement */}
      <div className="rounded-xl border border-slate-800/90 bg-slate-950/70 p-4 space-y-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 uppercase tracking-wider">
          <ShieldAlert className="h-4 w-4 text-amber-400" />
          <span>Production Incident / Failure Scenario</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
          {challenge.scenario}
        </p>
      </div>

      {/* Acceptance Criteria */}
      {totalReqs > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span>Architectural Acceptance Criteria</span>
          </h3>
          <ul className="space-y-2">
            {challenge.requirements.map((req, idx) => {
              const isChecked = !!checkedRequirements[idx];
              return (
                <li key={idx}>
                  <button
                    type="button"
                    onClick={() => toggleReq(idx)}
                    className={`w-full text-left flex items-start gap-3 p-3 rounded-xl border transition-all text-xs ${
                      isChecked
                        ? "border-emerald-500/40 bg-emerald-950/20 text-emerald-200"
                        : "border-slate-800 bg-slate-950/50 text-slate-300 hover:border-slate-700"
                    }`}
                  >
                    {isChecked ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                    ) : (
                      <Circle className="h-4 w-4 text-slate-600 shrink-0 mt-0.5" />
                    )}
                    <span className={isChecked ? "line-through opacity-80" : ""}>{req}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Socratic Hints */}
      {challenge.hints.length > 0 && (
        <div className="rounded-xl border border-indigo-900/30 bg-indigo-950/15 p-4 space-y-3">
          <button
            type="button"
            onClick={() => setHintsExpanded(!hintsExpanded)}
            className="w-full flex items-center justify-between text-xs font-semibold text-indigo-300 uppercase tracking-wider hover:text-indigo-200 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-indigo-400" />
              <span>Socratic Guidance & Hints ({challenge.hints.length})</span>
            </div>
            {hintsExpanded ? (
              <ChevronDown className="h-4 w-4 text-indigo-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-indigo-400" />
            )}
          </button>

          {hintsExpanded && (
            <div className="space-y-2 pt-2 border-t border-indigo-900/40">
              {challenge.hints.map((hint, idx) => {
                const isRevealed = !!revealedHints[idx];
                return (
                  <div
                    key={idx}
                    className="rounded-lg border border-indigo-900/40 bg-slate-950/60 p-3 text-xs"
                  >
                    {isRevealed ? (
                      <div className="flex items-start gap-2 text-indigo-200 leading-relaxed">
                        <span className="font-mono text-indigo-400 font-bold shrink-0">
                          #{idx + 1}
                        </span>
                        <span>{hint}</span>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => toggleHint(idx)}
                        className="w-full text-left flex items-center justify-between text-slate-400 hover:text-indigo-300 transition-colors"
                      >
                        <span className="flex items-center gap-1.5 font-medium">
                          <HelpCircle className="h-3.5 w-3.5" />
                          Hint #{idx + 1}: Click to reveal
                        </span>
                        <span className="text-[10px] uppercase font-semibold text-indigo-400/80">
                          Reveal
                        </span>
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
