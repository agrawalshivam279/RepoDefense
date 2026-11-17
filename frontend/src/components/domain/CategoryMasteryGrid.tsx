"use client";

import React from "react";
import type { CategoryProgressDelta } from "@/types/progress";

interface CategoryMasteryGridProps {
  categories: CategoryProgressDelta[];
}

export const CategoryMasteryGrid: React.FC<CategoryMasteryGridProps> = ({ categories }) => {
  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "mastered":
        return {
          label: "Mastered",
          classes: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
        };
      case "proficient":
        return {
          label: "Proficient",
          classes: "text-blue-500 bg-blue-500/10 border-blue-500/20",
        };
      case "improving":
        return {
          label: "Improving",
          classes: "text-amber-500 bg-amber-500/10 border-amber-500/20",
        };
      case "needs_focus":
      default:
        return {
          label: "Needs Focus",
          classes: "text-rose-500 bg-rose-500/10 border-rose-500/20",
        };
    }
  };

  const formatCategoryName = (cat: string) => {
    return cat
      .replace(/_/g, " ")
      .split(" ")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  };

  if (!categories || categories.length === 0) {
    return (
      <div className="rounded-xl border border-border/50 bg-card p-6 text-center shadow-sm">
        <h3 className="text-base font-semibold text-foreground">Category Mastery Breakdown</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          No category evaluations recorded yet. Run simulations across architecture, security, or
          database systems.
        </p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border border-border/50 bg-card p-6 shadow-sm"
      data-testid="category-mastery-grid"
    >
      <div className="mb-4">
        <h3 className="text-base font-semibold text-foreground">Category Mastery Breakdown</h3>
        <p className="text-xs text-muted-foreground">
          Domain-specific technical competence and evaluation track record
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map((cat) => {
          const badge = getStatusBadge(cat.status);
          return (
            <div
              key={cat.category}
              className="flex flex-col justify-between rounded-lg border border-border/60 bg-muted/20 p-4 transition-colors hover:border-border"
              data-testid={`category-card-${cat.category}`}
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-foreground">
                    {formatCategoryName(cat.category)}
                  </span>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${badge.classes}`}
                  >
                    {badge.label}
                  </span>
                </div>

                <div className="mt-3">
                  <div className="flex justify-between text-xs text-muted-foreground mb-1">
                    <span>Proficiency</span>
                    <span className="font-medium text-foreground">
                      {cat.current_proficiency.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-300"
                      style={{
                        width: `${Math.min(100, Math.max(0, cat.current_proficiency))}%`,
                      }}
                    />
                  </div>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-border/40 pt-3 text-xs text-muted-foreground">
                <span>
                  Pass Rate:{" "}
                  <strong className="text-foreground">{cat.pass_rate_pct.toFixed(0)}%</strong> (
                  {cat.passed_evaluations}/{cat.total_evaluations})
                </span>
                <span>
                  Gaps:{" "}
                  <strong className="text-foreground">
                    {cat.resolved_weaknesses}/{cat.total_weaknesses}
                  </strong>
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
