"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Compass,
  FileCode,
  Flame,
  FolderGit2,
  GraduationCap,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { fetchLearningLoopHealth } from "@/lib/learningApi";
import type { LearningLoopHealthResponse } from "@/types/learning";
import { LearningHubBreadcrumbs } from "@/components/domain/LearningHubBreadcrumbs";
import { LearningNavGroup } from "@/components/domain/LearningNavGroup";
import { LearningHealthStatusCard } from "@/components/domain/LearningHealthStatusCard";

const CORE_MODULES = [
  {
    id: "progress",
    title: "Skill Progression & Mastery Telemetry",
    badge: "Milestone 4.4",
    description: "Track architectural proficiency growth, remediation velocity, and domain trajectories over time.",
    href: "/dashboard/progress",
    icon: TrendingUp,
    accentClass: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    cta: "View Progression",
  },
  {
    id: "skill-gap",
    title: "Senior Benchmark & Skill Gap Visualizer",
    badge: "Milestone 4.6",
    description: "Compare your codebase defense abilities against Mid, Senior, and Staff/Principal industry baselines.",
    href: "/dashboard/skill-gap",
    icon: Target,
    accentClass: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
    cta: "Inspect Gaps & Radar",
  },
  {
    id: "mentor",
    title: "Mentor Mode & Architectural Explanations",
    badge: "Milestone 4.2",
    description: "Receive deep Principal Engineer teaching on tricky distributed bottlenecks, race conditions, and patterns.",
    href: "/dashboard",
    icon: GraduationCap,
    accentClass: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    cta: "Select Project for Mentor",
  },
  {
    id: "retest",
    title: "Targeted Re-Testing & Deficit Resolution",
    badge: "Milestone 4.5",
    description: "Survive rigorous oral-style follow-up challenges to resolve detected weaknesses and level up competencies.",
    href: "/dashboard",
    icon: RotateCcw,
    accentClass: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
    cta: "Select Project to Re-Test",
  },
];

const LOOP_STEPS = [
  { step: "1", title: "Evidence", desc: "AST & Git parsing extracts load-bearing code" },
  { step: "2", title: "Defense", desc: "Oral architectural questions probe tradeoffs" },
  { step: "3", title: "Deficit", desc: "Automated weakness logging across 6 domains" },
  { step: "4", title: "Mentor", desc: "Principal Engineer guidance & code remediations" },
  { step: "5", title: "Re-Test", desc: "Targeted follow-up questions verify retention" },
  { step: "6", title: "Mastery", desc: "Weakness resolution & proficiency boost (+10)" },
];

export default function LearningHubPage() {
  const [healthReport, setHealthReport] = useState<LearningLoopHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setHealthError("Please sign in to inspect diagnostic telemetry");
        return;
      }

      const report = await fetchLearningLoopHealth(session.access_token);
      setHealthReport(report);
    } catch (err: unknown) {
      setHealthError(err instanceof Error ? err.message : "Failed to probe learning loop subsystems");
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  return (
    <div className="min-h-screen bg-black text-zinc-100 pb-16">
      {/* Top Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-20">
        <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8 space-y-3">
          <LearningHubBreadcrumbs
            items={[
              {
                label: "Learning Hub",
                icon: Compass,
                isCurrent: true,
              },
            ]}
          />
          <LearningNavGroup activeModule="hub" healthStatus={healthReport?.status ?? null} />
        </div>
      </header>

      {/* Main Body */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
        {/* Hero Section */}
        <div className="rounded-2xl border border-zinc-800 bg-gradient-to-br from-zinc-900 via-zinc-950 to-zinc-900/40 p-6 sm:p-8 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-mono text-emerald-400">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Phase 4: Continuous Learning & Remediation</span>
            </div>
            <span className="text-xs font-mono text-zinc-500">6 Domains • 3 Seniority Tiers</span>
          </div>

          <div className="space-y-2 max-w-3xl">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              Prove, Learn, and Level Up Your Engineering Craft
            </h1>
            <p className="text-sm text-zinc-400 leading-relaxed">
              RepoDefense does not just test you — it turns every blind spot into verifiable mastery.
              Explore your skill trajectories, benchmark against senior engineers, and resolve detected
              deficits through targeted re-testing.
            </p>
          </div>

          {/* 6-Stage Loop Visualizer */}
          <div className="pt-4 border-t border-zinc-800/80">
            <h2 className="text-xs font-mono text-zinc-400 uppercase tracking-wider mb-3">
              The 6-Stage Closed Remediation Loop
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              {LOOP_STEPS.map((s) => (
                <div
                  key={s.step}
                  className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-2.5 text-center space-y-1"
                >
                  <span className="text-[10px] font-mono font-bold text-emerald-400">Step {s.step}</span>
                  <p className="text-xs font-bold text-zinc-200">{s.title}</p>
                  <p className="text-[11px] text-zinc-500 leading-tight">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Live Subsystem Health Card */}
        <LearningHealthStatusCard
          healthReport={healthReport}
          loading={healthLoading}
          error={healthError}
          onRefresh={loadHealth}
        />

        {/* Module Launchpads */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-zinc-100 flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-emerald-400" />
              <span>Learning Workspaces & Tools</span>
            </h2>
            <span className="text-xs font-mono text-zinc-500">All Modules Integrated</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {CORE_MODULES.map((mod) => {
              const Icon = mod.icon;
              return (
                <div
                  key={mod.id}
                  className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 flex flex-col justify-between space-y-4 hover:border-zinc-700 transition-all group"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-lg border ${mod.accentClass}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-zinc-800 bg-zinc-900 text-zinc-400">
                        {mod.badge}
                      </span>
                    </div>

                    <div className="space-y-1.5">
                      <h3 className="text-sm font-bold text-zinc-100 group-hover:text-white transition-colors">
                        {mod.title}
                      </h3>
                      <p className="text-xs text-zinc-400 leading-relaxed">
                        {mod.description}
                      </p>
                    </div>
                  </div>

                  <Link
                    href={mod.href}
                    className="inline-flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/80 px-3.5 py-2 text-xs font-mono font-medium text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors"
                  >
                    <span>{mod.cta}</span>
                    <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
                  </Link>
                </div>
              );
            })}
          </div>
        </div>

        {/* Project Context Callout */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-800 text-zinc-300">
              <FolderGit2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-bold text-zinc-200">Need repository-specific defenses?</p>
              <p className="text-xs text-zinc-400">
                Mentor Mode and Targeted Re-Testing run in the context of your ingested GitHub projects.
              </p>
            </div>
          </div>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-400 hover:bg-emerald-300 px-4 py-2 text-xs font-semibold text-zinc-950 transition-colors shrink-0"
          >
            <span>Open Projects Dashboard</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </main>
    </div>
  );
}
