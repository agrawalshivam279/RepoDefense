"use client";

import React, { useMemo, useState } from "react";
import {
  CheckCircle2,
  Filter,
  Layers,
  Sparkles,
} from "lucide-react";
import type { EligibleWeaknessItem } from "@/types/retest";
import { getCategoryBadge, getSeverityBadge } from "@/types/retest";

interface RetestWeaknessSelectorProps {
  weaknesses: EligibleWeaknessItem[];
  selectedIds: string[];
  onToggleWeakness: (id: string) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  maxQuestions: number;
  onChangeMaxQuestions: (count: number) => void;
  onStartSession: () => void;
  isLoading?: boolean;
}

export const RetestWeaknessSelector: React.FC<RetestWeaknessSelectorProps> = ({
  weaknesses,
  selectedIds,
  onToggleWeakness,
  onSelectAll,
  onDeselectAll,
  maxQuestions,
  onChangeMaxQuestions,
  onStartSession,
  isLoading = false,
}) => {
  const [activeCategory, setActiveCategory] = useState<string>("all");

  const categories = useMemo(() => {
    const set = new Set<string>();
    weaknesses.forEach((w) => set.add(w.category.toLowerCase()));
    return ["all", ...Array.from(set)];
  }, [weaknesses]);

  const filteredWeaknesses = useMemo(() => {
    if (activeCategory === "all") return weaknesses;
    return weaknesses.filter((w) => w.category.toLowerCase() === activeCategory);
  }, [weaknesses, activeCategory]);

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-6 backdrop-blur-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
              <Layers className="h-5 w-5 text-indigo-400" />
              Active Architectural Weaknesses
            </h2>
            <p className="mt-1 text-sm text-zinc-400">
              Select up to 50 active gaps to target with Principal Engineer stress scenarios.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-400">
              {selectedIds.length} of {weaknesses.length} selected
            </span>
            <button
              type="button"
              onClick={selectedIds.length === weaknesses.length ? onDeselectAll : onSelectAll}
              className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              {selectedIds.length === weaknesses.length ? "Deselect All" : "Select All"}
            </button>
          </div>
        </div>

        {/* Category Filter Tabs */}
        {categories.length > 2 && (
          <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-zinc-800/80 pt-4">
            <span className="text-xs text-zinc-500 flex items-center gap-1 mr-1">
              <Filter className="h-3.5 w-3.5" /> Category:
            </span>
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setActiveCategory(cat)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium capitalize transition-all ${
                  activeCategory === cat
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "bg-zinc-900 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 border border-zinc-800"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Weakness List Cards */}
      {filteredWeaknesses.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-800 p-12 text-center">
          <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-500/60" />
          <h3 className="mt-4 text-base font-semibold text-zinc-200">No Active Weaknesses</h3>
          <p className="mt-1 text-sm text-zinc-400">
            All detected gaps in this filter category have been successfully resolved.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {filteredWeaknesses.map((item) => {
            const isSelected = selectedIds.includes(item.id);
            const sev = getSeverityBadge(item.severity);
            const cat = getCategoryBadge(item.category);

            return (
              <div
                key={item.id}
                onClick={() => onToggleWeakness(item.id)}
                className={`cursor-pointer rounded-xl border p-4 transition-all duration-200 ${
                  isSelected
                    ? "border-indigo-500/80 bg-indigo-950/20 shadow-sm shadow-indigo-900/10"
                    : "border-zinc-800/80 bg-zinc-950/40 hover:border-zinc-700 hover:bg-zinc-900/40"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={`cb-${item.id}`}
                      aria-labelledby={`weakness-title-${item.id}`}
                      checked={isSelected}
                      onChange={() => onToggleWeakness(item.id)}
                      className="h-4 w-4 rounded border-zinc-700 bg-zinc-900 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-zinc-950"
                    />
                    <label
                      id={`weakness-title-${item.id}`}
                      htmlFor={`cb-${item.id}`}
                      className="text-sm font-semibold text-zinc-200 capitalize cursor-pointer"
                    >
                      {item.topic.replace(/_/g, " ")}
                    </label>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${sev.className}`}>
                      {sev.label}
                    </span>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${cat.className}`}>
                      {cat.label}
                    </span>
                  </div>
                </div>

                <div className="mt-2.5 text-xs text-zinc-400 line-clamp-2">
                  <span className="font-medium text-zinc-500">Prompt: </span>
                  {item.original_prompt}
                </div>

                {item.feedback && (
                  <div className="mt-2 text-xs text-zinc-500 line-clamp-1 italic">
                    <span className="font-medium text-zinc-400">Mentor: </span>
                    {item.feedback}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Action Footer */}
      {weaknesses.length > 0 && (
        <div className="sticky bottom-4 rounded-xl border border-zinc-800 bg-zinc-900/90 p-4 shadow-xl backdrop-blur-md flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <label htmlFor="max-q" className="text-xs text-zinc-400 font-medium">
              Max Questions:
            </label>
            <select
              id="max-q"
              value={maxQuestions}
              onChange={(e) => onChangeMaxQuestions(Number(e.target.value))}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-2.5 py-1 text-xs font-semibold text-zinc-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {[1, 2, 3, 4, 5, 8, 10].map((num) => (
                <option key={num} value={num}>
                  {num} {num === 1 ? "question" : "questions"}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            disabled={selectedIds.length === 0 || isLoading}
            onClick={onStartSession}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/20 transition-all hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Sparkles className="h-4 w-4" />
            {isLoading
              ? "Synthesizing Re-Test Scenario..."
              : `Generate Re-Test (${selectedIds.length} Selected)`}
          </button>
        </div>
      )}
    </div>
  );
};
