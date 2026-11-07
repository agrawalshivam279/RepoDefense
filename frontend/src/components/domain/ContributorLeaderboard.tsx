"use client";

import React from "react";
import type { AuthorShare } from "@/types/ownership";

interface ContributorLeaderboardProps {
  contributors: AuthorShare[];
}

export function ContributorLeaderboard({ contributors }: ContributorLeaderboardProps) {
  if (contributors.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400 font-mono text-xs border border-slate-800 rounded-xl bg-slate-900/60">
        No contributor data available.
      </div>
    );
  }

  return (
    <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/60 divide-y divide-slate-800">
      {contributors.map((c, idx) => (
        <div
          key={c.email}
          className="p-4 hover:bg-slate-800/40 transition-colors flex items-center justify-between gap-4 text-xs font-mono"
        >
          <div className="flex items-center gap-3 min-w-0">
            <span className="w-6 text-center text-slate-500 font-bold">#{idx + 1}</span>
            <div className="min-w-0">
              <div className="text-slate-200 font-bold truncate">{c.name}</div>
              <div className="text-[11px] text-slate-400 truncate">{c.email}</div>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-white font-bold">{c.lines_authored.toLocaleString()} lines</div>
            <div className="text-[11px] text-emerald-400">{c.percentage}% of repo</div>
          </div>
        </div>
      ))}
    </div>
  );
}
