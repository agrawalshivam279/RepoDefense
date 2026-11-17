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
  GraduationCap,
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
  | "analytics"
  | "mentor";

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

  // Telemetry & Learning Insights
  { id: "analytics", label: "Analytics", hrefSuffix: "/analytics", category: "insights", Icon: BarChart3, accentColor: "text-emerald-400" },
  { id: "mentor", label: "Mentor Mode", hrefSuffix: "/mentor", category: "insights", Icon: GraduationCap, accentColor: "text-indigo-400" },
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
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
        }`}
      >
        <Icon className={`h-3.5 w-3.5 ${isActive ? tab.accentColor : "text-slate-400"}`} />
        <span>{tab.label}</span>
      </Link>
    );
  };

  return (
    <div className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 space-y-3">
        {/* Breadcrumb + Metadata Row */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 min-w-0">
            <Link
              href="/dashboard"
              className="hover:text-emerald-400 transition-colors flex items-center gap-1 shrink-0"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Projects</span>
            </Link>
            <ChevronRight className="h-3.5 w-3.5 text-slate-600 shrink-0" />
            <Link
              href={`/projects/${projectId}`}
              className="text-slate-300 hover:text-white font-medium truncate max-w-[200px] sm:max-w-[320px]"
              title={displayName}
            >
              {displayName}
            </Link>
            <ChevronRight className="h-3.5 w-3.5 text-slate-600 shrink-0" />
            <span className="text-emerald-400 font-semibold">{currentTab.label}</span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {statusBadge && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-mono text-emerald-400 border border-emerald-500/20">
                <Shield className="h-3 w-3" />
                {statusBadge}
              </span>
            )}

            {githubUrl && (
              <a
                href={githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono text-slate-400 hover:text-slate-200 transition-colors border border-slate-800 rounded-md px-2 py-1 bg-slate-900/60"
              >
                <GitBranch className="h-3 w-3 text-slate-500" />
                <span>{defaultBranch || "main"}</span>
                <ExternalLink className="h-2.5 w-2.5 opacity-60" />
              </a>
            )}

            {commitHash && (
              <span className="hidden md:inline-flex items-center gap-1 text-[11px] font-mono text-slate-400 border border-slate-800 rounded-md px-2 py-1 bg-slate-900/60">
                <GitCommit className="h-3 w-3 text-slate-500" />
                <span>{commitHash.slice(0, 7)}</span>
              </span>
            )}

            {onRefresh && (
              <button
                type="button"
                onClick={onRefresh}
                disabled={isRefreshing}
                className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors border border-slate-800 disabled:opacity-50"
                title="Refresh project telemetry"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-emerald-400" : ""}`} />
              </button>
            )}

            {rightSlot}
          </div>
        </div>

        {/* Categorized Tab Bar */}
        <div className="flex items-center justify-between gap-4 overflow-x-auto pb-1 no-scrollbar border-t border-slate-800/60 pt-2.5">
          {/* Analysis Group */}
          <div className="flex items-center gap-1 shrink-0">
            <span className="hidden lg:inline text-[10px] font-mono uppercase tracking-wider text-slate-400 mr-1 select-none">
              Analysis
            </span>
            {TABS.filter((t) => t.category === "analysis").map(renderTab)}
          </div>

          <div className="h-4 w-px bg-slate-800 shrink-0 hidden md:block" />

          {/* Arena Group */}
          <div className="flex items-center gap-1 shrink-0">
            <span className="hidden lg:inline text-[10px] font-mono uppercase tracking-wider text-slate-400 mr-1 select-none">
              Arena
            </span>
            {TABS.filter((t) => t.category === "arena").map(renderTab)}
          </div>

          <div className="h-4 w-px bg-slate-800 shrink-0 hidden md:block" />

          {/* Insights Group */}
          <div className="flex items-center gap-1 shrink-0">
            <span className="hidden lg:inline text-[10px] font-mono uppercase tracking-wider text-slate-400 mr-1 select-none">
              Insights
            </span>
            {TABS.filter((t) => t.category === "insights").map(renderTab)}
          </div>
        </div>

        {subtitle && (
          <p className="text-xs text-slate-400 font-normal truncate">{subtitle}</p>
        )}
      </div>
    </div>
  );
}
