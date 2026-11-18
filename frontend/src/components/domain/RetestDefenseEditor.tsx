"use client";

import React, { useMemo } from "react";
import { Check, Loader2, Send, Terminal } from "lucide-react";

interface RetestDefenseEditorProps {
  defenseText: string;
  onChangeDefense: (text: string) => void;
  onSubmit: () => void;
  isSubmitting?: boolean;
}

export const RetestDefenseEditor: React.FC<RetestDefenseEditorProps> = ({
  defenseText,
  onChangeDefense,
  onSubmit,
  isSubmitting = false,
}) => {
  const wordCount = useMemo(() => {
    const trimmed = defenseText.trim();
    if (!trimmed) return 0;
    return trimmed.split(/\s+/).length;
  }, [defenseText]);

  const charCount = defenseText.length;
  const meetsMinWords = wordCount >= 30;
  const meetsMinChars = charCount >= 10;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-5 shadow-xl backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <label htmlFor="defense-input" className="text-xs font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
          <Terminal className="h-3.5 w-3.5 text-indigo-400" />
          Your Architectural Defense
        </label>
        <div className="flex items-center gap-3 text-xs">
          <span
            className={`flex items-center gap-1 font-medium ${
              meetsMinWords ? "text-emerald-400" : "text-zinc-500"
            }`}
          >
            {meetsMinWords && <Check className="h-3.5 w-3.5" />}
            {wordCount} / 30 words recommended
          </span>
          <span className="text-zinc-600">|</span>
          <span className="text-zinc-500">{charCount} / 5000 chars</span>
        </div>
      </div>

      <textarea
        id="defense-input"
        rows={6}
        value={defenseText}
        disabled={isSubmitting}
        onChange={(e) => onChangeDefense(e.target.value)}
        placeholder="Defend your architectural redesign. Detail specific trade-offs, concurrency or caching primitives, error handling boundaries, and database isolation strategies..."
        className="w-full resize-y rounded-lg border border-zinc-800 bg-zinc-900/60 p-3.5 text-sm text-zinc-100 placeholder-zinc-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-t border-zinc-800/80 pt-3">
        <p className="text-[11px] text-zinc-500">
          Tip: Ground your defense in concrete system design mechanisms. Address the constraint directly.
        </p>

        <button
          type="button"
          disabled={!meetsMinChars || isSubmitting}
          onClick={onSubmit}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/20 transition-all hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Evaluating Defense...
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Submit Defense
            </>
          )}
        </button>
      </div>
    </div>
  );
};
