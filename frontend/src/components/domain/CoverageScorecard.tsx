"use client";

import React from "react";
import { Code2, FileCode, Flame, ShieldCheck } from "lucide-react";
import type { ProjectCoverageResponse } from "@/types/coverage";

interface CoverageScorecardProps {
  coverage: ProjectCoverageResponse;
}

export function CoverageScorecard({ coverage }: CoverageScorecardProps) {
  const cards = [
    {
      label: "Files Defended",
      value: `${coverage.file_coverage_percentage}%`,
      subtitle: `${coverage.tested_files_count} / ${coverage.total_files} cataloged files`,
      icon: FileCode,
      color: "text-emerald-400",
    },
    {
      label: "Evidence Defended",
      value: `${coverage.evidence_coverage_percentage}%`,
      subtitle: `${coverage.tested_evidence_count} / ${coverage.total_evidence_items} architectural items`,
      icon: ShieldCheck,
      color: "text-sky-400",
    },
    {
      label: "Lines Defended",
      value: coverage.total_lines_covered.toLocaleString(),
      subtitle: "LOC across defended files",
      icon: Code2,
      color: "text-indigo-400",
    },
    {
      label: "Blind Spots",
      value: `${coverage.blind_spots.length}`,
      subtitle: "Untested critical components",
      icon: Flame,
      color: "text-rose-400",
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
