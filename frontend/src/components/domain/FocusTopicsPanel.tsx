"use client";

import React from "react";
import Link from "next/link";
import type { TopicMasteryItem } from "@/types/progress";

interface FocusTopicsPanelProps {
  topImproved: TopicMasteryItem[];
  needsFocus: TopicMasteryItem[];
}

export const FocusTopicsPanel: React.FC<FocusTopicsPanelProps> = ({ topImproved, needsFocus }) => {
  const formatTopic = (t: string) => {
    return t
      .replace(/_/g, " ")
      .split(" ")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  };

  return (
    <div
      className="grid grid-cols-1 gap-6 lg:grid-cols-2"
      data-testid="focus-topics-panel"
    >
      {/* Top Improved Topics */}
      <div className="rounded-xl border border-border/50 bg-card p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              <span className="text-emerald-500">▲</span> Top Strengths & Improvements
            </h3>
            <p className="text-xs text-muted-foreground">
              Highest scoring technical competencies and resolved areas
            </p>
          </div>
          <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-500">
            {topImproved.length} Mastered
          </span>
        </div>

        {topImproved.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            No mastered topics yet. Continue successfully defending architectural decisions to build strengths.
          </p>
        ) : (
          <div className="space-y-3">
            {topImproved.map((item) => (
              <div
                key={`${item.category}-${item.topic}`}
                className="flex items-center justify-between rounded-lg border border-border/40 bg-muted/20 p-3"
              >
                <div>
                  <div className="font-medium text-sm text-foreground">
                    {formatTopic(item.topic)}
                  </div>
                  <div className="text-xs text-muted-foreground capitalize">
                    {item.category} • {item.evaluations} evaluations
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold text-emerald-500">
                    {item.proficiency_score.toFixed(0)}%
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {item.pass_rate_pct.toFixed(0)}% pass
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Areas Needing Focus */}
      <div className="rounded-xl border border-border/50 bg-card p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              <span className="text-rose-500">▼</span> Recommended Focus Topics
            </h3>
            <p className="text-xs text-muted-foreground">
              Vulnerabilities and architectural blind spots requiring re-testing
            </p>
          </div>
          <span className="rounded-full bg-rose-500/10 px-2.5 py-0.5 text-xs font-medium text-rose-500">
            {needsFocus.length} Attention Needed
          </span>
        </div>

        {needsFocus.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            Zero identified deficiencies! All evaluated topics currently meet senior proficiency standards.
          </p>
        ) : (
          <div className="space-y-3">
            {needsFocus.map((item) => (
              <div
                key={`${item.category}-${item.topic}`}
                className="flex items-center justify-between rounded-lg border border-border/40 bg-muted/20 p-3"
              >
                <div>
                  <div className="font-medium text-sm text-foreground">
                    {formatTopic(item.topic)}
                  </div>
                  <div className="text-xs text-muted-foreground capitalize">
                    {item.category} • {item.evaluations} evaluations
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-sm font-semibold text-rose-500">
                      {item.proficiency_score.toFixed(0)}%
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      {item.pass_rate_pct.toFixed(0)}% pass
                    </div>
                  </div>
                  <Link
                    href={`/dashboard?focus_topic=${encodeURIComponent(item.topic)}`}
                    className="rounded bg-rose-500/10 px-2.5 py-1 text-xs font-medium text-rose-500 hover:bg-rose-500/20"
                  >
                    Re-Test
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
