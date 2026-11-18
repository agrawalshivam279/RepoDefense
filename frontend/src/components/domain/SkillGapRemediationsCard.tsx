"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, Flame, Sparkles } from "lucide-react";
import { getPriorityBadge, type RemediationRecommendation } from "@/types/skillGap";

interface SkillGapRemediationsCardProps {
  recommendations: RemediationRecommendation[];
  projectId?: string | null;
}

export function SkillGapRemediationsCard({
  recommendations,
  projectId,
}: SkillGapRemediationsCardProps) {
  if (recommendations.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-6 text-center space-y-2">
        <Sparkles className="mx-auto h-8 w-8 text-emerald-400" />
        <h4 className="text-sm font-semibold text-zinc-200">No Critical Deficits Detected</h4>
        <p className="text-xs text-zinc-400">
          Your skill evaluations currently meet or surpass the target seniority benchmarks.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-6 backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <div>
          <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
            <Flame className="h-4 w-4 text-amber-400" />
            Recommended Remediation Actions
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            Prioritized engineering concepts to target to close senior benchmark deficits.
          </p>
        </div>
        <span className="text-xs text-zinc-500 font-mono">
          {recommendations.length} action items
        </span>
      </div>

      <div className="space-y-3 pt-1">
        {recommendations.map((rec) => {
          const priority = getPriorityBadge(rec.priority);
          const retestHref = projectId ? `/projects/${projectId}/retest` : "/dashboard";

          return (
            <div
              key={`${rec.category}-${rec.topic}`}
              className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 transition-all hover:border-zinc-700 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${priority.className}`}>
                    {priority.label}
                  </span>
                  <h4 className="text-sm font-semibold text-zinc-200">{rec.topic}</h4>
                  <span className="text-[11px] text-zinc-500 capitalize">
                    ({rec.category.replace(/_/g, " ")})
                  </span>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  {rec.rationale}
                </p>
                <div className="text-xs text-indigo-400 font-medium pt-0.5 flex items-center gap-1.5">
                  <BookOpen className="h-3 w-3" />
                  <span>Action: {rec.suggested_action}</span>
                </div>
              </div>

              <div className="shrink-0 flex items-center gap-2">
                <Link
                  href={retestHref}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600/90 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 shadow-sm shadow-indigo-600/20 transition-colors"
                >
                  <span>Remediate</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
