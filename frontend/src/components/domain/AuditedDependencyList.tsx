"use client";

import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Filter,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import type {
  AuditCategory,
  AuditedDependencyItem,
  AuditSeverity,
} from "@/types/techAudit";

interface AuditedDependencyListProps {
  items: AuditedDependencyItem[];
}

export function AuditedDependencyList({ items }: AuditedDependencyListProps) {
  const [search, setSearch] = useState("");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const matchSearch =
        search.trim() === "" ||
        item.name.toLowerCase().includes(search.toLowerCase()) ||
        item.issue_description.toLowerCase().includes(search.toLowerCase());

      const matchSeverity =
        selectedSeverity === "all" || item.severity === selectedSeverity;

      const matchCategory =
        selectedCategory === "all" || item.category === selectedCategory;

      return matchSearch && matchSeverity && matchCategory;
    });
  }, [items, search, selectedSeverity, selectedCategory]);

  const getSeverityBadge = (severity: AuditSeverity) => {
    switch (severity) {
      case "critical":
        return "bg-rose-500/15 text-rose-400 border-rose-500/30";
      case "high":
        return "bg-orange-500/15 text-orange-400 border-orange-500/30";
      case "medium":
        return "bg-amber-500/15 text-amber-400 border-amber-500/30";
      case "low":
        return "bg-slate-700/50 text-slate-300 border-slate-600";
    }
  };

  const getCategoryBadge = (category: AuditCategory) => {
    switch (category) {
      case "security_risk":
        return "bg-red-950/40 text-red-300 border-red-800/40";
      case "deprecated":
        return "bg-purple-950/40 text-purple-300 border-purple-800/40";
      case "outdated":
        return "bg-sky-950/40 text-sky-300 border-sky-800/40";
      case "unmaintained":
        return "bg-zinc-800/60 text-zinc-300 border-zinc-700";
    }
  };

  if (items.length === 0) {
    return (
      <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800 text-center space-y-3">
        <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
          <CheckCircle className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-white font-mono">
          Clean Bill of Health
        </h3>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          No obsolete, deprecated, or vulnerable dependencies detected in this
          repository. All inspected packages conform to current baselines.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Filter by package or issue..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-slate-700 font-mono"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <span>Severity:</span>
          </div>
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 font-mono focus:outline-none"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 font-mono focus:outline-none"
          >
            <option value="all">All Categories</option>
            <option value="security_risk">Security Risk</option>
            <option value="deprecated">Deprecated</option>
            <option value="outdated">Outdated</option>
            <option value="unmaintained">Unmaintained</option>
          </select>
        </div>
      </div>

      {/* Flagged Items List */}
      {filteredItems.length === 0 ? (
        <div className="p-8 rounded-xl bg-slate-900/30 border border-slate-800 text-center text-xs font-mono text-slate-500">
          No dependencies match the current search or filter query.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredItems.map((item, idx) => (
            <div
              key={`${item.name}-${idx}`}
              className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-colors space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white font-mono">
                    {item.name}
                  </span>
                  {item.version && (
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                      v{item.version}
                    </span>
                  )}
                  {item.is_dev && (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono uppercase bg-slate-800/80 text-slate-400 border border-slate-700">
                      dev
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold uppercase border ${getSeverityBadge(
                      item.severity
                    )}`}
                  >
                    {item.severity}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-mono capitalize border ${getCategoryBadge(
                      item.category
                    )}`}
                  >
                    {item.category.replace("_", " ")}
                  </span>
                </div>
              </div>

              {/* Issue Description */}
              <div className="flex items-start gap-2 text-xs text-slate-300 leading-relaxed font-sans">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <span>{item.issue_description}</span>
              </div>

              {/* Suggested Remediation */}
              <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-800/30 flex items-start gap-2.5 text-xs">
                <ArrowRight className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <span className="font-mono text-emerald-400 font-semibold">
                    Remediation:
                  </span>{" "}
                  <span className="text-emerald-200/90 font-sans">
                    {item.suggested_alternative}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
