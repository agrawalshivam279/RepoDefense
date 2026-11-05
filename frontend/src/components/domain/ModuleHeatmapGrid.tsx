"use client";

import React from "react";
import { Folder, Layers, CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import type { ModuleCoverageItem } from "@/types/coverage";

interface ModuleHeatmapGridProps {
  modules: ModuleCoverageItem[];
  selectedModule: string | null;
  onSelectModule: (modulePath: string | null) => void;
}

export function ModuleHeatmapGrid({
  modules,
  selectedModule,
  onSelectModule,
}: ModuleHeatmapGridProps) {
  if (modules.length === 0) {
    return (
      <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 text-center text-slate-400 font-mono text-xs">
        No directory modules cataloged yet.
      </div>
    );
  }

  const getStatusBadge = (percentage: number) => {
    if (percentage === 100) {
      return {
        icon: CheckCircle2,
        label: "Fully Defended",
        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        barColor: "bg-emerald-500",
      };
    }
    if (percentage > 0) {
      return {
        icon: AlertCircle,
        label: "Partial",
        color: "text-sky-400 bg-sky-500/10 border-sky-500/20",
        barColor: "bg-sky-500",
      };
    }
    return {
      icon: XCircle,
      label: "Untested",
      color: "text-rose-400 bg-rose-500/10 border-rose-500/20",
      barColor: "bg-rose-500/60",
    };
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
            Repository Module Heatmap
          </h3>
          <span className="text-xs text-slate-400 font-mono">
            ({modules.length} modules)
          </span>
        </div>
        {selectedModule && (
          <button
            type="button"
            onClick={() => onSelectModule(null)}
            className="text-xs font-mono text-emerald-400 hover:text-emerald-300 underline underline-offset-4"
          >
            Clear Filter ({selectedModule})
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {modules.map((mod) => {
          const isSelected = selectedModule === mod.module_path;
          const statusInfo = getStatusBadge(mod.coverage_percentage);
          const Icon = statusInfo.icon;

          return (
            <button
              key={mod.module_path}
              type="button"
              onClick={() =>
                onSelectModule(isSelected ? null : mod.module_path)
              }
              className={`p-4 rounded-xl border text-left transition-all duration-200 relative overflow-hidden flex flex-col justify-between gap-3 ${
                isSelected
                  ? "bg-slate-800/90 border-emerald-500 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/50"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40"
              }`}
            >
              <div className="flex items-start justify-between gap-2 w-full">
                <div className="flex items-center gap-2 min-w-0">
                  <Folder
                    className={`w-4 h-4 flex-shrink-0 ${
                      mod.coverage_percentage === 100
                        ? "text-emerald-400"
                        : mod.coverage_percentage > 0
                        ? "text-sky-400"
                        : "text-slate-500"
                    }`}
                  />
                  <span
                    className="font-mono text-xs font-medium text-slate-200 truncate"
                    title={mod.module_path}
                  >
                    {mod.module_path}
                  </span>
                </div>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium border flex-shrink-0 ${statusInfo.color}`}
                >
                  <Icon className="w-3 h-3" />
                  {mod.coverage_percentage}%
                </span>
              </div>

              <div className="space-y-1.5 w-full">
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>
                    {mod.tested_files} / {mod.total_files} files defended
                  </span>
                  <span>{statusInfo.label}</span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${statusInfo.barColor}`}
                    style={{ width: `${Math.max(mod.coverage_percentage, 4)}%` }}
                  />
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
