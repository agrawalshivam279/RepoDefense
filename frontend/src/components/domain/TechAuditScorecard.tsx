"use client";

import React from "react";
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Info,
  Package,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import type { TechAuditReportResponse } from "@/types/techAudit";

interface TechAuditScorecardProps {
  report: TechAuditReportResponse;
}

export function TechAuditScorecard({ report }: TechAuditScorecardProps) {
  const {
    tech_health_score,
    total_dependencies_audited,
    flagged_dependencies_count,
    critical_count,
    high_count,
    medium_count,
    low_count,
  } = report;

  const getScoreTheme = (score: number) => {
    if (score >= 85) {
      return {
        label: "Excellent Health",
        color: "text-emerald-400",
        border: "border-emerald-500/30",
        bg: "bg-emerald-500/10",
        icon: ShieldCheck,
        description: "Minimal technical debt and high dependency stability.",
      };
    }
    if (score >= 70) {
      return {
        label: "Moderate Health",
        color: "text-amber-400",
        border: "border-amber-500/30",
        bg: "bg-amber-500/10",
        icon: AlertTriangle,
        description: "Minor obsolescence detected; maintenance recommended.",
      };
    }
    if (score >= 50) {
      return {
        label: "Elevated Risk",
        color: "text-orange-400",
        border: "border-orange-500/30",
        bg: "bg-orange-500/10",
        icon: AlertOctagon,
        description: "Outdated frameworks and medium-severity CVE vulnerabilities.",
      };
    }
    return {
      label: "Critical Risk",
      color: "text-rose-400",
      border: "border-rose-500/30",
      bg: "bg-rose-500/10",
      icon: ShieldAlert,
      description: "Severe CVE exposures or fully deprecated packages detected.",
    };
  };

  const theme = getScoreTheme(tech_health_score);
  const StatusIcon = theme.icon;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Primary Health Score Hero Card */}
      <div
        className={`p-6 rounded-2xl bg-slate-900/60 border ${theme.border} ${theme.bg} flex flex-col justify-between`}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Technology Health
          </span>
          <StatusIcon className={`w-5 h-5 ${theme.color}`} />
        </div>

        <div className="my-4 flex items-baseline gap-2">
          <span className={`text-5xl font-black font-mono tracking-tight ${theme.color}`}>
            {tech_health_score}%
          </span>
          <span className="text-sm font-semibold text-slate-300">
            {theme.label}
          </span>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed font-sans">
          {theme.description}
        </p>
      </div>

      {/* Dependency Scan Stats */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Inspection Scope
          </span>
          <Package className="w-5 h-5 text-indigo-400" />
        </div>

        <div className="my-4 space-y-3 font-mono">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Total Scanned:</span>
            <span className="text-white font-bold">{total_dependencies_audited}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Flagged Issues:</span>
            <span
              className={`font-bold ${
                flagged_dependencies_count > 0 ? "text-rose-400" : "text-emerald-400"
              }`}
            >
              {flagged_dependencies_count}
            </span>
          </div>
        </div>

        <div className="text-[11px] font-mono text-slate-500">
          Deterministic semver & static vulnerability heuristics
        </div>
      </div>

      {/* Severity Breakdown Grid */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Severity Tiers
          </span>
          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        </div>

        <div className="my-2 grid grid-cols-2 gap-2.5 font-mono">
          <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-between">
            <span className="text-xs text-rose-300">Critical</span>
            <span className="text-sm font-bold text-rose-400">{critical_count}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-between">
            <span className="text-xs text-orange-300">High</span>
            <span className="text-sm font-bold text-orange-400">{high_count}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between">
            <span className="text-xs text-amber-300">Medium</span>
            <span className="text-sm font-bold text-amber-400">{medium_count}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700 flex items-center justify-between">
            <span className="text-xs text-slate-300">Low</span>
            <span className="text-sm font-bold text-slate-200">{low_count}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-500">
          <Info className="w-3.5 h-3.5 text-slate-400" />
          <span>Weights: Critical -25%, High -15%, Med -8%, Low -3%</span>
        </div>
      </div>
    </div>
  );
}
