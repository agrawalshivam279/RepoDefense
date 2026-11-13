"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowUpRight, Compass, TrendingUp } from "lucide-react";
import type { CategorySkillMetric, ScoreTrendPoint } from "@/types/analytics";

function getScoreBadgeClasses(score: number): string {
  if (score >= 80) return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30";
  if (score >= 70) return "text-cyan-400 bg-cyan-500/10 border-cyan-500/30";
  if (score >= 50) return "text-amber-400 bg-amber-500/10 border-amber-500/30";
  return "text-rose-400 bg-rose-500/10 border-rose-500/30";
}

export function getBarColor(score: number): string {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 70) return "bg-cyan-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-rose-500";
}

function formatTrendDate(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return iso;
  return new Date(parsed).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export interface ReadinessTrendChartProps {
  points: ScoreTrendPoint[];
  projectId: string;
}

export function ReadinessTrendChart({ points, projectId }: ReadinessTrendChartProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const activePoint =
    points.length > 0 ? points[selectedIndex !== null && points[selectedIndex] ? selectedIndex : points.length - 1] : null;

  const geometry = useMemo(() => {
    const width = 620;
    const height = 200;
    const padX = 44;
    const padY = 20;
    const plotW = width - padX * 2;
    const plotH = height - padY * 2;

    const coords = points.map((pt, idx) => {
      const ratioX = points.length === 1 ? 0.5 : idx / (points.length - 1);
      const clampedScore = Math.max(0, Math.min(100, pt.score_pct));
      const x = padX + ratioX * plotW;
      const y = padY + plotH - (clampedScore / 100) * plotH;
      return { x, y, pt, idx };
    });

    const linePath = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
    const areaPath =
      coords.length >= 2
        ? `${linePath} L${coords[coords.length - 1].x.toFixed(1)},${(padY + plotH).toFixed(1)} L${coords[0].x.toFixed(1)},${(padY + plotH).toFixed(1)} Z`
        : "";
    const thresholdY = padY + plotH - 0.7 * plotH;
    return { width, height, padX, padY, plotW, plotH, coords, linePath, areaPath, thresholdY };
  }, [points]);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-white">Readiness Trajectory</h2>
        </div>
        <span className="text-[11px] font-mono text-slate-400">70% pass benchmark (dashed)</span>
      </div>

      {points.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-800 bg-slate-950/50 p-8 text-center space-y-2">
          <p className="text-sm text-slate-400">No scored defense sessions match this view yet.</p>
          <Link
            href={`/interview/${projectId}`}
            className="inline-flex items-center gap-1.5 text-xs font-mono text-emerald-400 hover:text-emerald-300"
          >
            <span>Launch Core Defense</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : (
        <>
          <div className="w-full overflow-x-auto">
            <svg
              viewBox={`0 0 ${geometry.width} ${geometry.height}`}
              className="w-full h-52 min-w-[420px]"
              role="img"
              aria-label="Chronological readiness score trend across defense sessions"
            >
              {[0, 50, 100].map((tick) => {
                const y = geometry.padY + geometry.plotH - (tick / 100) * geometry.plotH;
                return (
                  <g key={tick}>
                    <line
                      x1={geometry.padX}
                      x2={geometry.width - geometry.padX}
                      y1={y}
                      y2={y}
                      stroke="#1e293b"
                      strokeWidth="1"
                    />
                    <text x={geometry.padX - 8} y={y + 4} textAnchor="end" className="fill-slate-500 text-[10px] font-mono">
                      {tick}%
                    </text>
                  </g>
                );
              })}
              <line
                x1={geometry.padX}
                x2={geometry.width - geometry.padX}
                y1={geometry.thresholdY}
                y2={geometry.thresholdY}
                stroke="#10b981"
                strokeWidth="1.2"
                strokeDasharray="4 4"
                opacity="0.7"
              />
              {geometry.areaPath && <path d={geometry.areaPath} fill="rgba(16, 185, 129, 0.12)" />}
              {geometry.coords.length >= 2 && (
                <path d={geometry.linePath} fill="none" stroke="#34d399" strokeWidth="2.5" strokeLinejoin="round" />
              )}
              {geometry.coords.map(({ x, y, pt, idx }) => {
                const isSelected = activePoint?.session_id === pt.session_id;
                return (
                  <g key={`${pt.session_id}-${idx}`}>
                    <circle
                      cx={x}
                      cy={y}
                      r={isSelected ? 6 : 4.5}
                      fill={pt.score_pct >= 70 ? "#34d399" : "#fbbf24"}
                      stroke="#0f172a"
                      strokeWidth="2"
                      tabIndex={0}
                      className="cursor-pointer outline-none"
                      aria-label={`${pt.label}: ${pt.score_pct.toFixed(1)}% on ${pt.topic_or_title}`}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      onFocus={() => setSelectedIndex(idx)}
                    />
                  </g>
                );
              })}
            </svg>
          </div>
          {activePoint && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950/70 px-3.5 py-2 text-xs">
              <div className="flex items-center gap-2 min-w-0">
                <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-slate-800 text-slate-300">
                  {activePoint.label}
                </span>
                <span className="text-slate-200 font-medium truncate">{activePoint.topic_or_title}</span>
              </div>
              <div className="flex items-center gap-3 font-mono">
                <span className="text-slate-400">{formatTrendDate(activePoint.timestamp)}</span>
                <span className={`px-2 py-0.5 rounded border font-semibold ${getScoreBadgeClasses(activePoint.score_pct)}`}>
                  {activePoint.score_pct.toFixed(1)}%
                </span>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

export interface SkillRadarChartProps {
  skills: CategorySkillMetric[];
}

export function SkillRadarChart({ skills }: SkillRadarChartProps) {
  const topSkills = useMemo(() => skills.slice(0, 7), [skills]);
  const weakAreas = useMemo(
    () => [...skills].filter((s) => s.confidence_pct < 70).sort((a, b) => a.confidence_pct - b.confidence_pct).slice(0, 4),
    [skills],
  );

  const radar = useMemo(() => {
    if (topSkills.length < 3) return null;
    const cx = 145;
    const cy = 120;
    const maxR = 76;
    const total = topSkills.length;
    const pointAt = (idx: number, pct: number) => {
      const angle = (Math.PI * 2 * idx) / total - Math.PI / 2;
      const r = (Math.max(0, Math.min(100, pct)) / 100) * maxR;
      return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle), angle };
    };
    const dataPoly = topSkills.map((s, i) => pointAt(i, s.confidence_pct)).map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const rings = [33, 66, 100].map((level) =>
      topSkills.map((_, i) => pointAt(i, level)).map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" "),
    );
    const axes = topSkills.map((s, i) => {
      const outer = pointAt(i, 100);
      const labelPos = pointAt(i, 122);
      const anchor: "start" | "end" | "middle" =
        Math.cos(outer.angle) > 0.2 ? "start" : Math.cos(outer.angle) < -0.2 ? "end" : "middle";
      return { s, outer, labelPos, anchor };
    });
    return { cx, cy, dataPoly, rings, axes };
  }, [topSkills]);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold text-white">Architectural Skill Confidence</h2>
        </div>
        <span className="text-[11px] font-mono text-slate-400">{skills.length} tracked areas</span>
      </div>

      {skills.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-800 bg-slate-950/50 p-8 text-center text-sm text-slate-400">
          Complete defense sessions to map domain and failure-category confidence.
        </p>
      ) : radar ? (
        <svg viewBox="0 0 290 240" className="w-full h-56" role="img" aria-label="Skill confidence radar chart">
          {radar.rings.map((pts, idx) => (
            <polygon key={idx} points={pts} fill="none" stroke="#1e293b" strokeWidth="1" />
          ))}
          {radar.axes.map(({ s, outer, labelPos, anchor }) => (
            <g key={s.category}>
              <line x1={radar.cx} y1={radar.cy} x2={outer.x} y2={outer.y} stroke="#334155" strokeWidth="1" />
              <text x={labelPos.x} y={labelPos.y + 3} textAnchor={anchor} className="fill-slate-300 text-[9px] font-mono">
                {s.category.slice(0, 14)} ({Math.round(s.confidence_pct)}%)
              </text>
            </g>
          ))}
          <polygon points={radar.dataPoly} fill="rgba(6, 182, 212, 0.22)" stroke="#22d3ee" strokeWidth="2" />
        </svg>
      ) : (
        <div className="space-y-3 py-2">
          {skills.map((skill) => (
            <div key={skill.category} className="space-y-1">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-200">{skill.category}</span>
                <span className="text-cyan-400">{skill.confidence_pct.toFixed(1)}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div className={`h-full rounded-full ${getBarColor(skill.confidence_pct)}`} style={{ width: `${skill.confidence_pct}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {weakAreas.length > 0 && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-mono text-amber-300 font-semibold">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Weak Areas (&lt; 70% confidence)</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {weakAreas.map((w) => (
              <span key={w.category} className="px-2 py-0.5 rounded bg-slate-900 border border-amber-500/30 text-[11px] font-mono text-amber-200">
                {w.category}: {w.confidence_pct.toFixed(0)}%
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
