"use client";

import React, { useMemo } from "react";
import type { CategoryGapMetric } from "@/types/skillGap";

interface SkillRadarChartProps {
  categories: CategoryGapMetric[];
  candidateLabel?: string;
  benchmarkLabel?: string;
}

export function SkillRadarChart({
  categories,
  candidateLabel = "Your Proficiency",
  benchmarkLabel = "Target Benchmark",
}: SkillRadarChartProps) {
  const size = 340;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 105;

  const totalAxes = Math.max(categories.length, 3);

  const getCoordinates = (index: number, value: number, maxVal = 100) => {
    const angle = (Math.PI * 2 * index) / totalAxes - Math.PI / 2;
    const factor = Math.min(Math.max(value / maxVal, 0), 1);
    const r = radius * factor;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  const getLabelCoordinates = (index: number) => {
    const angle = (Math.PI * 2 * index) / totalAxes - Math.PI / 2;
    const r = radius + 32;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  // Concentric rings (25, 50, 75, 100)
  const rings = [25, 50, 75, 100];

  const candidatePoints = useMemo(() => {
    return categories
      .map((cat, i) => {
        const { x, y } = getCoordinates(i, cat.current_score);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [categories, totalAxes]);

  const benchmarkPoints = useMemo(() => {
    return categories
      .map((cat, i) => {
        const { x, y } = getCoordinates(i, cat.benchmark_score);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [categories, totalAxes]);

  return (
    <div className="flex flex-col items-center justify-center p-4 rounded-xl border border-zinc-800 bg-zinc-950/60 backdrop-blur-sm">
      <div className="flex items-center gap-6 mb-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" />
          <span className="text-zinc-200 font-medium">{candidateLabel}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full border border-dashed border-indigo-400 bg-indigo-500/20" />
          <span className="text-zinc-400 font-medium">{benchmarkLabel}</span>
        </div>
      </div>

      <svg width={size} height={size} className="overflow-visible select-none">
        {/* Concentric grid rings */}
        {rings.map((ringVal) => {
          const ringPoints = Array.from({ length: totalAxes })
            .map((_, i) => {
              const { x, y } = getCoordinates(i, ringVal);
              return `${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join(" ");
          return (
            <polygon
              key={`ring-${ringVal}`}
              points={ringPoints}
              fill="none"
              stroke="#27272a"
              strokeWidth="1"
              strokeDasharray={ringVal < 100 ? "2,2" : undefined}
            />
          );
        })}

        {/* Axis radial lines */}
        {categories.map((_, i) => {
          const { x, y } = getCoordinates(i, 100);
          return (
            <line
              key={`axis-${i}`}
              x1={cx}
              y1={cy}
              x2={x}
              y2={y}
              stroke="#27272a"
              strokeWidth="1"
            />
          );
        })}

        {/* Benchmark polygon */}
        <polygon
          points={benchmarkPoints}
          fill="rgba(99, 102, 241, 0.15)"
          stroke="#818cf8"
          strokeWidth="1.5"
          strokeDasharray="4,4"
        />

        {/* Candidate polygon */}
        <polygon
          points={candidatePoints}
          fill="rgba(16, 185, 129, 0.25)"
          stroke="#10b981"
          strokeWidth="2"
        />

        {/* Candidate vertex nodes */}
        {categories.map((cat, i) => {
          const { x, y } = getCoordinates(i, cat.current_score);
          return (
            <circle
              key={`cand-node-${cat.category}`}
              cx={x}
              cy={y}
              r="3.5"
              className="fill-emerald-400 stroke-zinc-950 stroke-2"
            >
              <title>{`${cat.category.replace(/_/g, " ")}: ${cat.current_score} pts`}</title>
            </circle>
          );
        })}

        {/* Axis labels */}
        {categories.map((cat, i) => {
          const { x, y } = getLabelCoordinates(i);
          const name = cat.category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
          return (
            <text
              key={`label-${cat.category}`}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-zinc-400 text-[10px] font-medium tracking-tight"
            >
              {name}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
