"use client";

import React from "react";
import {
  Activity,
  Cpu,
  Layers,
  Lock,
  Scale,
  Sparkles,
} from "lucide-react";
import type { CategoryScore } from "@/types/report";
import type { QuestionCategory } from "@/types/defense";

interface CategoryScorecardProps {
  categoryScore: CategoryScore;
}

const CATEGORY_META: Record<
  QuestionCategory,
  { label: string; icon: React.ComponentType<{ className?: string }> }
> = {
  architecture: { label: "Architecture & Design", icon: Layers },
  scalability: { label: "Scalability & Concurrency", icon: Cpu },
  reliability: { label: "Reliability & Resiliency", icon: Activity },
  security: { label: "Security & Access Control", icon: Lock },
  tradeoffs: { label: "Engineering Tradeoffs", icon: Scale },
};

function getStatusBadge(status: string) {
  const norm = status.toLowerCase();
  if (norm === "passed") {
    return {
      label: "Passed",
      className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    };
  }
  if (norm === "needs_work") {
    return {
      label: "Needs Work",
      className: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    };
  }
  return {
    label: "Remediated",
    className: "bg-sky-500/10 text-sky-400 border-sky-500/30",
  };
}

export function CategoryScorecard({ categoryScore }: CategoryScorecardProps) {
  const meta = CATEGORY_META[categoryScore.category] ?? {
    label: categoryScore.category,
    icon: Sparkles,
  };
  const IconComponent = meta.icon;
  const statusBadge = getStatusBadge(categoryScore.status);
  const scorePercent = Math.min(100, Math.max(0, (categoryScore.score / 10) * 100));

  const barColor =
    categoryScore.score >= 7.5
      ? "bg-emerald-500"
      : categoryScore.score >= 5.0
      ? "bg-sky-500"
      : "bg-amber-500";

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4 hover:border-slate-700/80 transition-colors shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
            <IconComponent className="w-4 h-4 text-emerald-400" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-tight">{meta.label}</h4>
            <span className="text-[11px] font-mono text-slate-500">
              {categoryScore.questions_count} {categoryScore.questions_count === 1 ? "question" : "questions"}
            </span>
          </div>
        </div>
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono uppercase font-semibold border ${statusBadge.className}`}
        >
          {statusBadge.label}
        </span>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-slate-400">Score</span>
          <span className="font-bold text-slate-200">{categoryScore.score.toFixed(1)} / 10.0</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${scorePercent}%` }}
          />
        </div>
      </div>

      <p className="text-xs text-slate-300 leading-relaxed font-sans border-t border-slate-800/80 pt-3">
        {categoryScore.summary}
      </p>
    </div>
  );
}
