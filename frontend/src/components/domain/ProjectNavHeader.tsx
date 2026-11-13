"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  ChevronRight,
  Compass,
  ExternalLink,
  FileCode,
  Flame,
  Gauge,
  GitBranch,
  GitCommit,
  GitPullRequest,
  Layers,
  Network,
  PackageCheck,
  RefreshCw,
  Shield,
  Sparkles,
  UserCheck,
} from "lucide-react";

export type ProjectNavTab =
  | "overview"
  | "claims"
  | "coverage"
  | "ownership"
  | "architecture"
  | "tech-audit"
  | "pr-defense"
  | "commit-defense"
  | "incident-simulation"
  | "stress-test"
  | "arch-defense"
  | "analytics";

export type TabCategory = "analysis" | "arena" | "insights";

export interface ProjectNavHeaderProps {
  projectId: string;
  projectName?: string | null;
  githubUrl?: string | null;
  defaultBranch?: string | null;
  commitHash?: string | null;
  activeTab: ProjectNavTab;
  statusBadge?: string | null;
  subtitle?: string | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  rightSlot?: React.ReactNode;
}

interface NavTabItem {
  id: ProjectNavTab;
  label: string;
  hrefSuffix: string;
  category: TabCategory;
  Icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
}

const TABS: NavTabItem[] = [
  // Static Analysis
  { id: "overview", label: "Overview", hrefSuffix: "", category: "analysis", Icon: FileCode, accentColor: "text-emerald-400" },
  { id: "claims", label: "Claims", hrefSuffix: "/claims", category: "analysis", Icon: Sparkles, accentColor: "text-emerald-400" },
  { id: "coverage", label: "Coverage", hrefSuffix: "/coverage", category: "analysis", Icon: Layers, accentColor: "text-sky-400" },
  { id: "ownership", label: "Ownership", hrefSuffix: "/ownership", category: "analysis", Icon: UserCheck, accentColor: "text-indigo-400" },
  { id: "architecture", label: "Architecture", hrefSuffix: "/architecture", category: "analysis", Icon: Network, accentColor: "text-purple-400" },
  { id: "tech-audit", label: "Tech Audit", hrefSuffix: "/tech-audit", category: "analysis", Icon: PackageCheck, accentColor: "text-amber-400" },

  // Interactive Defense Arena
  { id: "pr-defense", label: "PR Defense", hrefSuffix: "/pr-defense", category: "arena", Icon: GitPullRequest, accentColor: "text-rose-400" },
  { id: "commit-defense", label: "Commit Defense", hrefSuffix: "/commit-defense", category: "arena", Icon: GitCommit, accentColor: "text-emerald-400" },
  { id: "incident-simulation", label: "War Room", hrefSuffix: "/incident-simulation", category: "arena", Icon: Flame, accentColor: "text-rose-400" },
  { id: "stress-test", label: "Stress Test", hrefSuffix: "/stress-test", category: "arena", Icon: Gauge, accentColor: "text-amber-400" },
  { id: "arch-defense", label: "Arch Defense", hrefSuffix: "/arch-defense", category: "arena", Icon: Compass, accentColor: "text-cyan-400" },

  // Telemetry & Insights
  { id: "analytics", label: "Analytics", hrefSuffix: "/analytics", category: "insights", Icon: BarChart3, accentColor: "text-emerald-400" },
];

export function ProjectNavHeader({
  projectId,
  projectName = "Repository",
  githubUrl,
  defaultBranch,
  commitHash,
  activeTab,
  statusBadge,
  subtitle,
  onRefresh,
  isRefreshing = false,
  rightSlot,
}: ProjectNavHeaderProps) {
  const currentTab = TABS.find((t) => t.id === activeTab) || TABS[0];
  const displayName = projectName || "Repository";

  const renderTab = (tab: NavTabItem) => {
    const isActive = tab.id === activeTab;
    const Icon = tab.Icon;
    return (
      <Link
        key={tab.id}
        href={`/projects/${projectId}${tab.hrefSuffix}`}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all whitespace-nowrap ${
          isActive
            ? "bg-slate-800 text-white border border-slate-700 shadow-sm font-semibold"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent"
        }`}
      >
        <Icon className={`w-3.5 h-3.5 ${isActive ? tab.accentColor : "text-slate-500"}`} />
        <span>{tab.label}</span>
      </Link>
    );
  };

  return (
    <div className="space-y-4 border-b border-slate-800 pb-5">
      {/* Breadcrumb Trail */}
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs font-mono text-slate-400">
        <Link href="/dashboard" className="hover:text-slate-200 transition-colors">
          Dashboard
        </Link>
        <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
        <Link href={`/projects/${projectId}`} className="hover:text-slate-200 transition-colors truncate max-w-[180px]">
          {displayName}
        </Link>
        <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
        <span className="text-emerald-400 font-semibold">{currentTab.label}</span>
      </nav>

      {/* Top Header Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-start sm:items-center gap-3">
          <Link
            href="/dashboard"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 transition-colors shrink-0 mt-0.5 sm:mt-0"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">{displayName}</h1>
              {statusBadge && (
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                  {statusBadge}
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-slate-400">
              {githubUrl && (
                <a
                  href={githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-slate-200 inline-flex items-center gap-1 transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>GitHub</span>
                </a>
              )}
              {defaultBranch && (
                <span className="inline-flex items-center gap-1 text-slate-400">
                  <GitBranch className="w-3 h-3 text-slate-500" />
                  <span>{defaultBranch}</span>
                </span>
              )}
              {commitHash && (
                <span className="inline-flex items-center gap-1 text-slate-400 font-mono">
                  <GitCommit className="w-3 h-3 text-slate-500" />
                  <span>{commitHash.slice(0, 7)}</span>
                </span>
              )}
              {subtitle && (
                <>
                  <span>•</span>
                  <span className="text-slate-400">{subtitle}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Action Controls & Defense CTA */}
        <div className="flex flex-wrap items-center gap-2 self-start lg:self-auto">
          {rightSlot}
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors disabled:opacity-50"
              title="Refresh Analysis"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-emerald-400" : ""}`} />
            </button>
          )}
          <Link
            href={`/interview/${projectId}`}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs font-mono transition-colors shadow-md"
          >
            <span>Start Defense</span>
            <Shield className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Grouped Navigation Tabs Bar */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1.5 pt-2 border-t border-slate-800/80">
        {/* Analysis Group */}
        <div className="flex items-center gap-1 shrink-0">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold px-1 hidden xl:inline">
            Analysis
          </span>
          {TABS.filter((t) => t.category === "analysis").map(renderTab)}
        </div>

        <div className="h-4 w-px bg-slate-800 mx-1 shrink-0" />

        {/* Defense Arena Group */}
        <div className="flex items-center gap-1 shrink-0">
          <span className="text-[10px] font-mono uppercase tracking-wider text-rose-400/70 font-semibold px-1 hidden xl:inline">
            Arena
          </span>
          {TABS.filter((t) => t.category === "arena").map(renderTab)}
        </div>

        <div className="h-4 w-px bg-slate-800 mx-1 shrink-0" />

        {/* Insights Group */}
        <div className="flex items-center gap-1 shrink-0">
          <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400/70 font-semibold px-1 hidden xl:inline">
            Insights
          </span>
          {TABS.filter((t) => t.category === "insights").map(renderTab)}
        </div>
      </div>
    </div>
  );
}
