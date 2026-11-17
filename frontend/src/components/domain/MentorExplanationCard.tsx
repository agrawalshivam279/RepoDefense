"use client";

import React from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Compass,
  GraduationCap,
  HelpCircle,
  Lightbulb,
  Sparkles,
} from "lucide-react";
import type { MentorExplanationResponse } from "@/types/mentor";
import { CodeRemediationViewer } from "./CodeRemediationViewer";

interface MentorExplanationCardProps {
  explanation: MentorExplanationResponse;
  onRetestRequest?: () => void;
  className?: string;
}

export function MentorExplanationCard({
  explanation,
  onRetestRequest,
  className = "",
}: MentorExplanationCardProps) {
  const formattedDate = new Date(explanation.generated_at).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={`space-y-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-5 md:p-7 shadow-2xl backdrop-blur-sm ${className}`}
    >
      {/* Session Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-400 border border-indigo-500/20">
              <GraduationCap className="h-3.5 w-3.5" />
              Mentor Mode
            </span>
            <span className="inline-flex items-center rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-mono uppercase text-slate-300">
              {explanation.category}
            </span>
          </div>
          <h3 className="text-xl md:text-2xl font-bold tracking-tight text-white capitalize">
            {explanation.topic.replace(/_/g, " ")}
          </h3>
        </div>

        <div className="text-right text-xs text-slate-500 font-mono">
          <span>Synthesized {formattedDate}</span>
        </div>
      </div>

      {/* Grid: Architectural Risk & Core Concept */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Architectural Risk Card */}
        <div className="rounded-xl border border-rose-900/30 bg-rose-950/10 p-4 space-y-2">
          <div className="flex items-center gap-2 text-rose-400 font-semibold text-sm">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>Root Cause & Architectural Risk</span>
          </div>
          <p className="text-xs text-rose-200/90 leading-relaxed font-normal">
            {explanation.architectural_risk}
          </p>
        </div>

        {/* Core Concept Card */}
        <div className="rounded-xl border border-indigo-900/30 bg-indigo-950/10 p-4 space-y-2">
          <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
            <Compass className="h-4 w-4 shrink-0" />
            <span>Core Design Principle</span>
          </div>
          <p className="text-xs text-indigo-200/90 leading-relaxed font-normal">
            {explanation.core_concept}
          </p>
        </div>
      </div>

      {/* Mentor Pedagogical Advice */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 md:p-5 space-y-2.5">
        <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
          <BookOpen className="h-4 w-4 text-indigo-400" />
          <span>Principal Engineer Walkthrough</span>
        </div>
        <p className="text-xs md:text-sm text-slate-300 leading-relaxed">
          {explanation.mentor_advice}
        </p>
      </div>

      {/* Drop-in Code Remediations */}
      {explanation.code_examples && explanation.code_examples.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
            <Sparkles className="h-4 w-4 text-amber-400" />
            <span>Drop-in Architectural Code Remediation</span>
          </div>
          <div className="space-y-4">
            {explanation.code_examples.map((snippet, idx) => (
              <CodeRemediationViewer key={`${snippet.title}-${idx}`} snippet={snippet} />
            ))}
          </div>
        </div>
      )}

      {/* Key Takeaways */}
      {explanation.key_takeaways && explanation.key_takeaways.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 space-y-2.5">
          <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
            <Lightbulb className="h-4 w-4 text-amber-400" />
            <span>Key Engineering Takeaways</span>
          </div>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-300">
            {explanation.key_takeaways.map((takeaway, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span className="leading-snug">{takeaway}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Socratic Re-Test Challenge Box */}
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 md:p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 text-amber-300 font-semibold text-sm">
            <HelpCircle className="h-4 w-4 shrink-0 text-amber-400" />
            <span>Socratic Re-Test Challenge</span>
          </div>
          <p className="text-xs text-amber-200/90 leading-relaxed">
            {explanation.socratic_followup}
          </p>
        </div>

        {onRetestRequest && (
          <button
            type="button"
            onClick={onRetestRequest}
            className="shrink-0 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs px-4 py-2 transition-colors shadow-sm"
          >
            Launch Re-Test
          </button>
        )}
      </div>
    </div>
  );
}
