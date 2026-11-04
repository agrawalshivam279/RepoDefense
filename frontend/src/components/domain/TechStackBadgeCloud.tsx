"use client";

import { useMemo, useState } from "react";
import { Box, Code2, Layers, Package, Search } from "lucide-react";
import type { DependencyOverviewItem } from "@/types/project";

interface TechStackBadgeCloudProps {
  detectedFrameworks: string[];
  primaryLanguage: string;
  architecturalStyle: string;
  dependencies: DependencyOverviewItem[];
}

export function TechStackBadgeCloud({
  detectedFrameworks,
  primaryLanguage,
  architecturalStyle,
  dependencies,
}: TechStackBadgeCloudProps) {
  const [filter, setFilter] = useState<"all" | "runtime" | "dev">("all");
  const [search, setSearch] = useState("");

  const filteredDependencies = useMemo(() => {
    return dependencies.filter((dep) => {
      const matchesFilter =
        filter === "all" ? true : filter === "dev" ? dep.is_dev : !dep.is_dev;
      const matchesSearch = dep.name.toLowerCase().includes(search.toLowerCase());
      return matchesFilter && matchesSearch;
    });
  }, [dependencies, filter, search]);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-sm">
      {/* Top Section: Architectural Style & Frameworks */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-emerald-400 border-b border-slate-800 pb-3">
          <Layers className="w-5 h-5" />
          <h3 className="text-sm font-bold uppercase tracking-wider font-mono">
            Core Technology Stack & Frameworks
          </h3>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <Code2 className="w-3.5 h-3.5" /> Primary: {primaryLanguage}
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/30">
            <Box className="w-3.5 h-3.5" /> Style: {architecturalStyle}
          </span>
          {detectedFrameworks.map((fw) => (
            <span
              key={fw}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30"
            >
              ● {fw}
            </span>
          ))}
        </div>
      </div>

      {/* Bottom Section: Dependencies Catalog */}
      <div className="space-y-4 pt-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 text-slate-300">
            <Package className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider font-mono">
              Third-Party Dependencies ({dependencies.length})
            </h4>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter packages..."
                className="pl-8 pr-3 py-1 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 font-mono w-36 sm:w-44"
              />
            </div>
            <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-[11px] font-mono">
              <button
                type="button"
                onClick={() => setFilter("all")}
                className={`px-2 py-0.5 rounded ${
                  filter === "all" ? "bg-slate-800 text-white font-semibold" : "text-slate-400"
                }`}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setFilter("runtime")}
                className={`px-2 py-0.5 rounded ${
                  filter === "runtime" ? "bg-slate-800 text-white font-semibold" : "text-slate-400"
                }`}
              >
                Runtime
              </button>
              <button
                type="button"
                onClick={() => setFilter("dev")}
                className={`px-2 py-0.5 rounded ${
                  filter === "dev" ? "bg-slate-800 text-white font-semibold" : "text-slate-400"
                }`}
              >
                Dev
              </button>
            </div>
          </div>
        </div>

        {filteredDependencies.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-72 overflow-y-auto pr-1">
            {filteredDependencies.map((dep, idx) => (
              <div
                key={`${dep.name}-${idx}`}
                className="flex items-center justify-between p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-xl text-xs font-mono"
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="font-semibold text-slate-200 truncate">{dep.name}</span>
                  {dep.version && (
                    <span className="text-[10px] text-slate-500 shrink-0">{dep.version}</span>
                  )}
                </div>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold shrink-0 ${
                    dep.is_dev
                      ? "bg-slate-800 text-slate-400 border border-slate-700"
                      : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  }`}
                >
                  {dep.is_dev ? "dev" : "prod"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 font-mono italic">
            No dependencies matching &quot;{search}&quot;.
          </p>
        )}
      </div>
    </div>
  );
}
