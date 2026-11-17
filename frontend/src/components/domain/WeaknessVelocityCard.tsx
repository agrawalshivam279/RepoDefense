"use client";

import React from "react";
import type { WeaknessVelocityMetric } from "@/types/progress";

interface WeaknessVelocityCardProps {
  velocity: WeaknessVelocityMetric;
}

export const WeaknessVelocityCard: React.FC<WeaknessVelocityCardProps> = ({ velocity }) => {
  const {
    total_identified,
    total_resolved,
    resolution_rate_pct,
    critical_resolved,
    critical_total,
    major_resolved,
    major_total,
    minor_resolved,
    minor_total,
    average_resolution_hours,
  } = velocity;

  const formatHours = (hours: number | null): string => {
    if (hours === null || hours === undefined) return "N/A";
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${hours.toFixed(1)}h`;
    return `${(hours / 24).toFixed(1)}d`;
  };

  const getRateColor = (rate: number): string => {
    if (rate >= 75) return "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
    if (rate >= 50) return "text-blue-500 bg-blue-500/10 border-blue-500/20";
    if (rate >= 25) return "text-amber-500 bg-amber-500/10 border-amber-500/20";
    return "text-rose-500 bg-rose-500/10 border-rose-500/20";
  };

  return (
    <div
      className="rounded-xl border border-border/50 bg-card p-6 shadow-sm"
      data-testid="weakness-velocity-card"
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-foreground">Remediation Velocity</h3>
          <p className="text-xs text-muted-foreground">
            Deficiency resolution turnaround and severity clearance
          </p>
        </div>
        <div
          className={`rounded-full border px-3 py-1 text-sm font-semibold ${getRateColor(
            resolution_rate_pct
          )}`}
        >
          {resolution_rate_pct.toFixed(0)}% Resolved
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs text-muted-foreground mb-1">
          <span>
            {total_resolved} of {total_identified} gaps remediated
          </span>
          <span>Avg Turnaround: {formatHours(average_resolution_hours)}</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{ width: `${Math.min(100, Math.max(0, resolution_rate_pct))}%` }}
          />
        </div>
      </div>

      {/* Severity Breakdown Grid */}
      <div className="mt-5 grid grid-cols-3 gap-3">
        {/* Critical */}
        <div className="rounded-lg border border-border/50 bg-muted/20 p-3 text-center">
          <div className="text-[11px] font-medium uppercase tracking-wider text-rose-500">
            Critical
          </div>
          <div className="mt-1 text-lg font-bold text-foreground">
            {critical_resolved}
            <span className="text-xs font-normal text-muted-foreground">/{critical_total}</span>
          </div>
          <div className="mt-0.5 text-[10px] text-muted-foreground">
            {critical_total > 0
              ? `${Math.round((critical_resolved / critical_total) * 100)}%`
              : "0%"}
          </div>
        </div>

        {/* Major */}
        <div className="rounded-lg border border-border/50 bg-muted/20 p-3 text-center">
          <div className="text-[11px] font-medium uppercase tracking-wider text-amber-500">
            Major
          </div>
          <div className="mt-1 text-lg font-bold text-foreground">
            {major_resolved}
            <span className="text-xs font-normal text-muted-foreground">/{major_total}</span>
          </div>
          <div className="mt-0.5 text-[10px] text-muted-foreground">
            {major_total > 0 ? `${Math.round((major_resolved / major_total) * 100)}%` : "0%"}
          </div>
        </div>

        {/* Minor */}
        <div className="rounded-lg border border-border/50 bg-muted/20 p-3 text-center">
          <div className="text-[11px] font-medium uppercase tracking-wider text-blue-500">
            Minor
          </div>
          <div className="mt-1 text-lg font-bold text-foreground">
            {minor_resolved}
            <span className="text-xs font-normal text-muted-foreground">/{minor_total}</span>
          </div>
          <div className="mt-0.5 text-[10px] text-muted-foreground">
            {minor_total > 0 ? `${Math.round((minor_resolved / minor_total) * 100)}%` : "0%"}
          </div>
        </div>
      </div>
    </div>
  );
};
