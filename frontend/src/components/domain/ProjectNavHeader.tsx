"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ChevronRight,
  ExternalLink,
  FileCode,
  GitBranch,
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
  | "tech-audit";

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

const TABS: {
  id: ProjectNavTab;
  label: string;
  hrefSuffix: string;
  Icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
}[] = [
  { id: "overview", label: "Overview", hrefSuffix: "", Icon: FileCode, accentColor: "text-emerald-400" },
  { id: "claims", label: "Claims", hrefSuffix: "/claims", Icon: Sparkles, accentColor: "text-emerald-400" },
  { id: "coverage", label: "Coverage", hrefSuffix: "/coverage", Icon: Layers, accentColor: "text-sky-400" },
  { id: "ownership", label: "Ownership", hrefSuffix: "/ownership", Icon: UserCheck, accentColor: "text-indigo-400" },
  { id: "architecture", label: "Architecture", hrefSuffix: "/architecture", Icon: Network, accentColor: "text-purple-400" },
  { id: "tech-audit", label: "Tech Audit", hrefSuffix: "/tech-audit", Icon: PackageCheck, accentColor: "text-amber-400" },
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

      {/* Primary Header Row */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/dashboard"
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <Shield className="w-5 h-5 text-emerald-400 flex-shrink-0" />
              <h1 className="text-xl font-bold text-white tracking-tight truncate">{displayName}</h1>
              {statusBadge && (
                <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-medium uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  ● {statusBadge}
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-slate-400">
              {githubUrl && (
                <a
                  href={githubUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-emerald-400 transition-colors inline-flex items-center gap-1"
                >
                  <span>{githubUrl.replace("https://github.com/", "")}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
              {defaultBranch && (
                <>
                  <span>•</span>
                  <span className="inline-flex items-center gap-1">
                    <GitBranch className="w-3 h-3 text-slate-500" />
                    {defaultBranch}
                  </span>
                </>
              )}
              {commitHash && (
                <>
                  <span>•</span>
                  <span>SHA: {commitHash.slice(0, 7)}</span>
                </>
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

      {/* Navigation Tabs Bar */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1 pt-1 border-t border-slate-800/80 scrollbar-thin">
        {TABS.map((tab) => {
          const isActive = tab.id === activeTab;
          const Icon = tab.Icon;
          return (
            <Link
              key={tab.id}
              href={`/projects/${projectId}${tab.hrefSuffix}`}
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all whitespace-nowrap ${
                isActive
                  ? "bg-slate-800 text-white border border-slate-700 shadow-sm font-semibold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? tab.accentColor : "text-slate-500"}`} />
              <span>{tab.label}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
