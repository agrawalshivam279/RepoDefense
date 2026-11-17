"use client";

import React, { useState } from "react";
import type { ProficiencyTrendPoint } from "@/types/progress";

interface LearningTimelineChartProps {
  timeline: ProficiencyTrendPoint[];
  selectedDays?: number;
  onDaysChange?: (days: number) => void;
  isLoading?: boolean;
}

export const LearningTimelineChart: React.FC<LearningTimelineChartProps> = ({
  timeline,
  selectedDays = 30,
  onDaysChange,
  isLoading = false,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<ProficiencyTrendPoint | null>(null);

  const dayOptions = [
    { label: "7D", value: 7 },
    { label: "14D", value: 14 },
    { label: "30D", value: 30 },
    { label: "All", value: 0 },
  ];

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border/50 bg-card p-6 shadow-sm">
        <div className="h-64 animate-pulse rounded bg-muted/40" />
      </div>
    );
  }

  if (!timeline || timeline.length === 0) {
    return (
      <div className="rounded-xl border border-border/50 bg-card p-6 text-center shadow-sm">
        <h3 className="text-base font-semibold text-foreground">Proficiency Over Time</h3>
        <p className="mt-4 text-sm text-muted-foreground">
          No historical evaluation data recorded yet. Complete architectural defense sessions to
          generate your learning timeline.
        </p>
      </div>
    );
  }

  // Chart Dimensions & Coordinate calculations
  const width = 640;
  const height = 220;
  const paddingX = 40;
  const paddingY = 30;

  const chartW = width - paddingX * 2;
  const chartH = height - paddingY * 2;

  const points = timeline.map((pt, idx) => {
    const x =
      timeline.length > 1
        ? paddingX + (idx / (timeline.length - 1)) * chartW
        : width / 2;
    const y = height - paddingY - (pt.average_proficiency / 100) * chartH;
    return { ...pt, x, y };
  });

  const pathD = points.reduce((acc, pt, i) => {
    return i === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
  }, "");

  const areaD =
    points.length > 1
      ? `${pathD} L ${points[points.length - 1].x} ${height - paddingY} L ${points[0].x} ${
          height - paddingY
        } Z`
      : "";

  return (
    <div className="rounded-xl border border-border/50 bg-card p-6 shadow-sm" data-testid="learning-timeline-chart">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4">
        <div>
          <h3 className="text-base font-semibold text-foreground">Proficiency Progression Curve</h3>
          <p className="text-xs text-muted-foreground">
            Telemetry tracking daily defense scores and weakness remediations
          </p>
        </div>

        {onDaysChange && (
          <div className="flex items-center gap-1 rounded-lg border border-border/60 bg-muted/30 p-1">
            {dayOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => onDaysChange(opt.value)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                  selectedDays === opt.value
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="relative mt-2 overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full min-w-[500px]">
          <defs>
            <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.3" />
              <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((val) => {
            const y = height - paddingY - (val / 100) * chartH;
            return (
              <g key={val}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  stroke="currentColor"
                  strokeOpacity="0.08"
                  strokeDasharray="3 3"
                />
                <text
                  x={paddingX - 8}
                  y={y + 3}
                  textAnchor="end"
                  className="fill-muted-foreground text-[10px]"
                >
                  {val}%
                </text>
              </g>
            );
          })}

          {/* Fill Area */}
          {areaD && <path d={areaD} fill="url(#curveGradient)" />}

          {/* Main Curve */}
          <path
            d={pathD}
            fill="none"
            stroke="hsl(var(--primary))"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data Points */}
          {points.map((pt, idx) => (
            <circle
              key={idx}
              cx={pt.x}
              cy={pt.y}
              r={hoveredPoint?.date === pt.date ? 6 : 4}
              className={`cursor-pointer transition-all ${
                hoveredPoint?.date === pt.date
                  ? "fill-primary stroke-background stroke-2"
                  : "fill-primary/80"
              }`}
              onMouseEnter={() => setHoveredPoint(pt)}
              onMouseLeave={() => setHoveredPoint(null)}
              data-testid={`point-${pt.date}`}
            />
          ))}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredPoint && (
          <div className="pointer-events-none absolute left-1/2 top-4 -translate-x-1/2 rounded-lg border border-border bg-popover/95 px-3 py-2 text-xs shadow-md backdrop-blur">
            <div className="font-semibold text-foreground">{hoveredPoint.date}</div>
            <div className="text-primary">
              Proficiency: {hoveredPoint.average_proficiency.toFixed(1)}%
            </div>
            <div className="text-muted-foreground">
              Evaluations: {hoveredPoint.evaluations_count} (Passed: {hoveredPoint.passed_count})
            </div>
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>{timeline[0]?.date}</span>
        <span className="font-medium text-foreground">
          Latest: {timeline[timeline.length - 1]?.average_proficiency.toFixed(1)}%
        </span>
        <span>{timeline[timeline.length - 1]?.date}</span>
      </div>
    </div>
  );
};
