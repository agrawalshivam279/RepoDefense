"use client";

import React from "react";
import Link from "next/link";
import { CheckCircle2, GraduationCap, RotateCcw } from "lucide-react";

interface RetestCompletionCardProps {
  onRestart: () => void;
}

export function RetestCompletionCard({ onRestart }: RetestCompletionCardProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-8 text-center space-y-6">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
        <CheckCircle2 className="h-8 w-8" />
      </div>
      <div className="space-y-2">
        <h2 className="text-xl font-bold text-zinc-100">Targeted Re-Test Completed</h2>
        <p className="text-sm text-zinc-400 max-w-md mx-auto">
          Passed weaknesses have been marked resolved in your profile and skill proficiency scores updated.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
        <button
          type="button"
          onClick={onRestart}
          className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-xs font-semibold text-zinc-200 hover:bg-zinc-800"
        >
          <RotateCcw className="h-4 w-4" /> Retest More Weaknesses
        </button>
        <Link
          href="/dashboard/progress"
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 shadow-md shadow-indigo-600/20"
        >
          <GraduationCap className="h-4 w-4" /> View Skill Progress Dashboard
        </Link>
      </div>
    </div>
  );
}
