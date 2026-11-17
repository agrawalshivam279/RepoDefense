"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Check,
  Copy,
  Loader2,
  RefreshCw,
  Send,
  Terminal,
} from "lucide-react";

interface ChallengeEditorProps {
  challengeId?: string;
  starterCode?: string | null;
  language: string;
  isSubmitting: boolean;
  onSubmit: (solutionCode: string) => void;
  className?: string;
}

export function ChallengeEditor({
  challengeId,
  starterCode,
  language,
  isSubmitting,
  onSubmit,
  className = "",
}: ChallengeEditorProps) {
  const initial = starterCode || "# Implement your architectural refactoring here\n";
  const [code, setCode] = useState<string>(initial);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    setCode(starterCode || "# Implement your architectural refactoring here\n");
  }, [challengeId, starterCode]);

  const handleReset = () => {
    setCode(initial);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Non-blocking clipboard error
    }
  };

  const lines = code.split("\n");
  const lineCount = lines.length;
  const trimmed = code.trim();
  const charCount = Array.from(trimmed).length;
  const isTooShort = charCount < 10;

  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-slate-950 flex flex-col overflow-hidden shadow-2xl ${className}`}
    >
      {/* Editor Top Bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/80">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-indigo-400" />
          <span className="text-xs font-semibold text-slate-200">
            Architectural Solution Workspace
          </span>
          <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400 border border-slate-700/60 uppercase">
            {language}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 hover:border-slate-700 transition-colors"
            title="Copy current code"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleReset}
            disabled={isSubmitting || code === initial}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 hover:border-slate-700 disabled:opacity-40 transition-colors"
            title="Reset to starter code"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Editor Body */}
      <div className="relative flex flex-1 min-h-[320px] max-h-[500px] overflow-auto bg-slate-950 font-mono text-xs">
        {/* Line Numbers Gutter */}
        <div className="select-none py-3 px-3 text-right bg-slate-900/40 text-slate-600 border-r border-slate-800/80 font-mono text-xs shrink-0 w-12">
          {lines.map((_, i) => (
            <div key={i} className="leading-6">
              {i + 1}
            </div>
          ))}
        </div>

        {/* Textarea */}
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          disabled={isSubmitting}
          aria-label="Candidate solution code"
          spellCheck={false}
          className="flex-1 w-full bg-transparent p-3 text-slate-200 placeholder-slate-600 focus:outline-none resize-none leading-6 font-mono text-xs overflow-y-auto selection:bg-indigo-900/60"
          placeholder="Refactor the starter code to satisfy all architectural requirements..."
        />
      </div>

      {/* Editor Status & Submit Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 border-t border-slate-800 bg-slate-900/60">
        <div className="flex items-center gap-4 text-xs text-slate-400">
          <span>
            {lineCount} {lineCount === 1 ? "line" : "lines"}
          </span>
          <span>&bull;</span>
          <span>{charCount} characters</span>
          {isTooShort && (
            <span className="flex items-center gap-1 text-amber-400 text-[11px]">
              <AlertTriangle className="h-3.5 w-3.5" />
              Minimum 10 characters required
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => onSubmit(code)}
          disabled={isSubmitting || isTooShort}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-950/50 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Evaluating Architectural Defense...</span>
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              <span>Submit Solution for Evaluation</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
