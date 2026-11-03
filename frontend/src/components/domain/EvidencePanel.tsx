"use client";

import { useMemo, useState } from "react";
import {
  Code,
  Database,
  ExternalLink,
  FileCode,
  Filter,
  Key,
  Layers,
  Loader2,
  Server,
  Sparkles,
  X,
} from "lucide-react";
import type { EvidenceItem, EvidenceType } from "@/types/evidence";

interface EvidencePanelProps {
  isOpen: boolean;
  onClose: () => void;
  evidenceList: EvidenceItem[];
  activeEvidenceIds: string[];
  loading?: boolean;
}

const TYPE_CONFIG: Record<
  EvidenceType,
  { label: string; badge: string; icon: typeof Code }
> = {
  framework: {
    label: "Framework",
    badge: "bg-sky-500/10 text-sky-400 border-sky-500/30",
    icon: Code,
  },
  database: {
    label: "Database",
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    icon: Database,
  },
  auth: {
    label: "Auth Guard",
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    icon: Key,
  },
  api_endpoint: {
    label: "API Endpoint",
    badge: "bg-violet-500/10 text-violet-400 border-violet-500/30",
    icon: Server,
  },
  queue: {
    label: "Worker Queue",
    badge: "bg-orange-500/10 text-orange-400 border-orange-500/30",
    icon: Layers,
  },
  infrastructure: {
    label: "Infrastructure",
    badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
    icon: Server,
  },
  architecture: {
    label: "Architecture",
    badge: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
    icon: Sparkles,
  },
};

export function EvidencePanel({
  isOpen,
  onClose,
  evidenceList,
  activeEvidenceIds,
  loading = false,
}: EvidencePanelProps) {
  const [filterMode, setFilterMode] = useState<"cited" | "all">("all");
  const [selectedType, setSelectedType] = useState<string>("all");

  const citedIdsSet = useMemo(() => new Set(activeEvidenceIds), [activeEvidenceIds]);

  const filteredItems = useMemo(() => {
    return evidenceList.filter((item) => {
      const matchesCited = filterMode === "all" || citedIdsSet.has(item.id);
      const matchesType = selectedType === "all" || item.evidence_type === selectedType;
      return matchesCited && matchesType;
    });
  }, [evidenceList, filterMode, selectedType, citedIdsSet]);

  const citedCount = useMemo(
    () => evidenceList.filter((item) => citedIdsSet.has(item.id)).length,
    [evidenceList, citedIdsSet]
  );

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full sm:max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <FileCode className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-bold text-white">Code Evidence</h3>
              <p className="text-xs font-mono text-slate-400">
                AST-grounded architectural anchors
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Close Drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filters */}
        <div className="p-4 border-b border-slate-800/80 space-y-3 bg-slate-950/40">
          {/* Mode Switcher */}
          <div className="grid grid-cols-2 gap-2 bg-slate-900 p-1 rounded-lg border border-slate-800">
            <button
              onClick={() => setFilterMode("all")}
              className={`py-1.5 px-3 rounded-md text-xs font-mono font-medium transition-all ${
                filterMode === "all"
                  ? "bg-slate-800 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Evidence ({evidenceList.length})
            </button>
            <button
              onClick={() => setFilterMode("cited")}
              className={`py-1.5 px-3 rounded-md text-xs font-mono font-medium transition-all ${
                filterMode === "cited"
                  ? "bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Active Question ({citedCount})
            </button>
          </div>

          {/* Type Selector */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <button
              onClick={() => setSelectedType("all")}
              className={`px-2.5 py-1 rounded-full font-mono text-[11px] whitespace-nowrap transition-colors ${
                selectedType === "all"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                  : "bg-slate-800/80 text-slate-400 hover:text-slate-200"
              }`}
            >
              All Types
            </button>
            {Object.keys(TYPE_CONFIG).map((type) => {
              const cfg = TYPE_CONFIG[type as EvidenceType];
              const count = evidenceList.filter((e) => e.evidence_type === type).length;
              if (count === 0) return null;
              return (
                <button
                  key={type}
                  onClick={() => setSelectedType(type)}
                  className={`px-2.5 py-1 rounded-full font-mono text-[11px] whitespace-nowrap transition-colors ${
                    selectedType === type
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "bg-slate-800/80 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {cfg.label} ({count})
                </button>
              );
            })}
          </div>
        </div>

        {/* Evidence List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400 space-y-2">
              <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
              <p className="text-xs font-mono">Loading code evidence...</p>
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center text-slate-400 space-y-2">
              <Filter className="w-8 h-8 text-slate-600 stroke-1" />
              <p className="text-sm font-semibold text-slate-300">No Evidence Matches</p>
              <p className="text-xs font-mono text-slate-500 max-w-xs">
                No code evidence was found matching the active filters.
              </p>
            </div>
          ) : (
            filteredItems.map((item) => {
              const isCited = citedIdsSet.has(item.id);
              const cfg = TYPE_CONFIG[item.evidence_type] || TYPE_CONFIG.architecture;
              const Icon = cfg.icon;

              return (
                <div
                  key={item.id}
                  className={`p-3.5 rounded-xl border transition-all ${
                    isCited
                      ? "bg-slate-900/90 border-emerald-500/50 shadow-md shadow-emerald-950/20 ring-1 ring-emerald-500/30"
                      : "bg-slate-950/60 border-slate-800/80 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium border ${cfg.badge}`}
                    >
                      <Icon className="w-3 h-3" />
                      {cfg.label}
                    </span>
                    {isCited && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                        <Sparkles className="w-2.5 h-2.5" />
                        Cited Anchor
                      </span>
                    )}
                  </div>

                  <h4 className="text-sm font-semibold text-slate-100 mb-1 leading-snug">
                    {item.title}
                  </h4>
                  <p className="text-xs text-slate-300 font-sans leading-relaxed mb-2.5">
                    {item.description}
                  </p>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/70 text-[11px] font-mono text-slate-400">
                    <span
                      className="truncate max-w-[260px] text-slate-300 hover:text-emerald-400 transition-colors"
                      title={item.file_path}
                    >
                      {item.file_path}
                    </span>
                    <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-mono text-[10px] flex-shrink-0">
                      L{item.start_line}-L{item.end_line}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-950/80 border-t border-slate-800 text-center">
          <p className="text-[11px] font-mono text-slate-500 flex items-center justify-center gap-1.5">
            <ExternalLink className="w-3 h-3 text-emerald-400" />
            Grounding claims against Tree-sitter AST nodes
          </p>
        </div>
      </div>
    </>
  );
}
