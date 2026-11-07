"use client";

import React from "react";
import { Code2, ShieldAlert, UserCheck, Users } from "lucide-react";
import type { ProjectOwnershipReport } from "@/types/ownership";

interface OwnershipScorecardProps {
  report: ProjectOwnershipReport;
}

export function OwnershipScorecard({ report }: OwnershipScorecardProps) {
  const cards = [
    {
      label: "Candidate Line Ownership",
      value: `${report.candidate_overall_ownership_percentage}%`,
      subtitle: "Of cataloged source lines",
      icon: UserCheck,
      color: "text-emerald-400",
    },
    {
      label: "Authored Symbols",
      value: `${report.candidate_authored_symbols}`,
      subtitle: `${report.candidate_authored_symbols} of ${report.total_symbols_analyzed} symbols defended`,
      icon: Code2,
      color: "text-sky-400",
    },
    {
      label: "Flagged Unowned",
      value: `${report.flagged_unowned_symbols.length}`,
      subtitle: "Critical evidence candidate didn't write",
      icon: ShieldAlert,
      color: "text-rose-400",
    },
    {
      label: "Total Contributors",
      value: `${report.top_contributors.length}`,
      subtitle: "Distinct git blame authors",
      icon: Users,
      color: "text-indigo-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map((c) => {
        const Icon = c.icon;
        return (
          <div
            key={c.label}
            className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-1 shadow-sm"
          >
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>{c.label}</span>
              <Icon className={`w-4 h-4 ${c.color}`} />
            </div>
            <div className="text-2xl font-bold text-white font-mono">{c.value}</div>
            <p className="text-[11px] font-mono text-slate-500">{c.subtitle}</p>
          </div>
        );
      })}
    </div>
  );
}
