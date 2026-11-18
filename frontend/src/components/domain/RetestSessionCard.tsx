"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileText,
  HelpCircle,
  ShieldAlert,
} from "lucide-react";
import type { RetestQuestion } from "@/types/retest";
import { getCategoryBadge, getSeverityBadge } from "@/types/retest";

interface RetestSessionCardProps {
  question: RetestQuestion;
  currentIndex: number;
  totalQuestions: number;
}

export const RetestSessionCard: React.FC<RetestSessionCardProps> = ({
  question,
  currentIndex,
  totalQuestions,
}) => {
  const [showOriginal, setShowOriginal] = useState<boolean>(false);
  const [showRubric, setShowRubric] = useState<boolean>(false);

  const sev = getSeverityBadge(question.severity);
  const cat = getCategoryBadge(question.category);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-6 shadow-xl backdrop-blur-sm space-y-5">
      {/* Question Header & Badges */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-zinc-800/80 pb-4">
        <div className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600/20 text-xs font-bold text-indigo-400 border border-indigo-500/30">
            {currentIndex + 1}
          </span>
          <span className="text-xs font-medium text-zinc-400">
            Question {currentIndex + 1} of {totalQuestions}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${sev.className}`}>
            {sev.label}
          </span>
          <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${cat.className}`}>
            {cat.label}
          </span>
          <span className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-xs text-zinc-300 capitalize">
            {question.topic.replace(/_/g, " ")}
          </span>
        </div>
      </div>

      {/* Primary Question Body */}
      <div>
        <h3 className="text-base font-semibold leading-relaxed text-zinc-100 sm:text-lg">
          {question.question_text}
        </h3>
      </div>

      {/* Production Constraint Banner */}
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-amber-300">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0 text-amber-400 mt-0.5" />
          <div className="space-y-1">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-400">
              Architectural Constraint
            </span>
            <p className="text-xs leading-relaxed text-zinc-300">
              {question.architectural_constraint}
            </p>
          </div>
        </div>
      </div>

      {/* Collapsible Drawers */}
      <div className="space-y-2 border-t border-zinc-800/80 pt-4">
        {/* Original Weakness Prompt Accordion */}
        <div className="rounded-lg border border-zinc-800/60 bg-zinc-900/40">
          <button
            type="button"
            aria-expanded={showOriginal}
            aria-controls="original-context-panel"
            onClick={() => setShowOriginal(!showOriginal)}
            className="flex w-full items-center justify-between px-3.5 py-2.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <span className="flex items-center gap-2">
              <ShieldAlert className="h-3.5 w-3.5 text-zinc-500" />
              Original Failure Context
            </span>
            {showOriginal ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          {showOriginal && (
            <div
              id="original-context-panel"
              className="border-t border-zinc-800/60 px-3.5 py-3 text-xs leading-relaxed text-zinc-400 space-y-2"
            >
              <div>
                <span className="font-semibold text-zinc-300">Original Question: </span>
                {question.original_prompt}
              </div>
            </div>
          )}
        </div>

        {/* Expected Criteria Rubric Accordion */}
        <div className="rounded-lg border border-zinc-800/60 bg-zinc-900/40">
          <button
            type="button"
            aria-expanded={showRubric}
            aria-controls="rubric-criteria-panel"
            onClick={() => setShowRubric(!showRubric)}
            className="flex w-full items-center justify-between px-3.5 py-2.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <span className="flex items-center gap-2">
              <HelpCircle className="h-3.5 w-3.5 text-indigo-400" />
              Expected Architectural Criteria
            </span>
            {showRubric ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          {showRubric && (
            <div
              id="rubric-criteria-panel"
              className="border-t border-zinc-800/60 px-3.5 py-3 text-xs leading-relaxed text-zinc-300"
            >
              <div className="flex items-start gap-2">
                <FileText className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                <p>{question.evaluation_rubric}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
