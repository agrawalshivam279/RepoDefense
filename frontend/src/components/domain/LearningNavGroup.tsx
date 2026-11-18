"use client";

import React from "react";
import Link from "next/link";
import { Compass, Sparkles, Target, TrendingUp } from "lucide-react";
import type { ComponentHealthStatus } from "@/types/learning";

export interface LearningNavGroupProps {
  activeModule?: "hub" | "progress" | "skill-gap";
  healthStatus?: ComponentHealthStatus | null;
  className?: string;
}

const MODULES = [
  {
    id: "hub" as const,
    label: "Learning Hub",
    href: "/dashboard/learning",
    icon: Compass,
    accentClass: "text-emerald-400",
  },
  {
    id: "progress" as const,
    label: "Skill Progress",
    href: "/dashboard/progress",
    icon: TrendingUp,
    accentClass: "text-emerald-400",
  },
  {
    id: "skill-gap" as const,
    label: "Senior Benchmarks",
    href: "/dashboard/skill-gap",
    icon: Target,
    accentClass: "text-indigo-400",
  },
];

export function LearningNavGroup({
  activeModule,
  healthStatus,
  className = "",
}: LearningNavGroupProps) {
  return (
    <div className={`flex flex-wrap items-center justify-between gap-3 ${className}`}>
      {/* Module Pill Tabs */}
      <nav aria-label="Learning Loop Navigation" className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/80 p-1">
        {MODULES.map((mod) => {
          const isActive = mod.id === activeModule;
          const Icon = mod.icon;

          return (
            <Link
              key={mod.id}
              href={mod.href}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-mono font-medium transition-all ${
                isActive
                  ? "bg-zinc-800 text-white shadow-sm font-semibold border border-zinc-700"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              <Icon className={`h-3.5 w-3.5 ${isActive ? mod.accentClass : "text-zinc-500"}`} />
              <span>{mod.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Operational Diagnostic Status Pill */}
      {healthStatus && (
        <div
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-mono border ${
            healthStatus === "healthy"
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : healthStatus === "degraded"
              ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
              : "bg-rose-500/10 border-rose-500/20 text-rose-400"
          }`}
          title={`Phase 4 Learning Loop Subsystem Status: ${healthStatus}`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              healthStatus === "healthy"
                ? "bg-emerald-400 animate-pulse"
                : healthStatus === "degraded"
                ? "bg-amber-400"
                : "bg-rose-400"
            }`}
          />
          <Sparkles className="h-3 w-3" />
          <span className="capitalize">{healthStatus} Telemetry</span>
        </div>
      )}
    </div>
  );
}
