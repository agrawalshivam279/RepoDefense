"use client";

import React, { useState } from "react";
import { Check, Columns2, Copy, FileCode, Rows2, ShieldAlert, ShieldCheck } from "lucide-react";
import type { CodeRemediationSnippet, RemediationViewMode } from "@/types/mentor";

interface CodeRemediationViewerProps {
  snippet: CodeRemediationSnippet;
  defaultViewMode?: RemediationViewMode;
}

export function CodeRemediationViewer({
  snippet,
  defaultViewMode = "split",
}: CodeRemediationViewerProps) {
  const [viewMode, setViewMode] = useState<RemediationViewMode>(defaultViewMode);
  const [activeTab, setActiveTab] = useState<"before" | "after">("after");
  const [copiedBefore, setCopiedBefore] = useState(false);
  const [copiedAfter, setCopiedAfter] = useState(false);

  const handleCopy = async (code: string, target: "before" | "after") => {
    try {
      await navigator.clipboard.writeText(code);
      if (target === "before") {
        setCopiedBefore(true);
        setTimeout(() => setCopiedBefore(false), 2000);
      } else {
        setCopiedAfter(true);
        setTimeout(() => setCopiedAfter(false), 2000);
      }
    } catch {
      // Ignore clipboard write failure
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 overflow-hidden shadow-lg transition-all">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-4 py-3 bg-slate-950/60">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode className="h-4 w-4 text-indigo-400 shrink-0" />
          <h4 className="font-semibold text-sm text-slate-100 truncate">{snippet.title}</h4>
          {snippet.file_context && (
            <span className="hidden sm:inline-flex items-center rounded-md bg-slate-800/80 px-2 py-0.5 text-[11px] font-mono text-slate-300 border border-slate-700/50">
              {snippet.file_context}
            </span>
          )}
        </div>

        {/* View Mode Toggle Controls */}
        <div className="flex items-center gap-1.5">
          <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5">
            <button
              type="button"
              onClick={() => setViewMode("split")}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                viewMode === "split"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="Side-by-side view"
            >
              <Columns2 className="h-3.5 w-3.5" />
              <span className="hidden md:inline">Split</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("unified")}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                viewMode === "unified"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="Tabbed view"
            >
              <Rows2 className="h-3.5 w-3.5" />
              <span className="hidden md:inline">Unified</span>
            </button>
          </div>
        </div>
      </div>

      {/* Unified Tab Switcher (Visible only in Unified viewMode) */}
      {viewMode === "unified" && (
        <div className="flex border-b border-slate-800/80 bg-slate-950/40 px-4 pt-2">
          <button
            type="button"
            onClick={() => setActiveTab("before")}
            className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === "before"
                ? "border-rose-500 text-rose-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
            Anti-Pattern (Before)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("after")}
            className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === "after"
                ? "border-emerald-500 text-emerald-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            Hardened Remediation (After)
          </button>
        </div>
      )}

      {/* Code Display Area */}
      <div
        className={
          viewMode === "split"
            ? "grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-800"
            : "block"
        }
      >
        {/* Before Pane */}
        {(viewMode === "split" || activeTab === "before") && (
          <div className="flex flex-col bg-slate-950/40">
            <div className="flex items-center justify-between border-b border-rose-950/40 bg-rose-950/20 px-3.5 py-1.5">
              <span className="flex items-center gap-1.5 text-xs font-semibold text-rose-300">
                <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
                Anti-Pattern / Vulnerable
              </span>
              <button
                type="button"
                onClick={() => handleCopy(snippet.before_code, "before")}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200"
                aria-label="Copy flawed code"
              >
                {copiedBefore ? (
                  <Check className="h-3 w-3 text-emerald-400" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
                <span>{copiedBefore ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <pre className="p-4 text-xs font-mono text-rose-200/90 overflow-x-auto leading-relaxed whitespace-pre font-normal selection:bg-rose-900/60 selection:text-white">
              <code>{snippet.before_code}</code>
            </pre>
          </div>
        )}

        {/* After Pane */}
        {(viewMode === "split" || activeTab === "after") && (
          <div className="flex flex-col bg-slate-950/40">
            <div className="flex items-center justify-between border-b border-emerald-950/40 bg-emerald-950/20 px-3.5 py-1.5">
              <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-300">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                Hardened Remediation
              </span>
              <button
                type="button"
                onClick={() => handleCopy(snippet.after_code, "after")}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200"
                aria-label="Copy remediated code"
              >
                {copiedAfter ? (
                  <Check className="h-3 w-3 text-emerald-400" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
                <span>{copiedAfter ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <pre className="p-4 text-xs font-mono text-emerald-200/95 overflow-x-auto leading-relaxed whitespace-pre font-normal selection:bg-emerald-900/60 selection:text-white">
              <code>{snippet.after_code}</code>
            </pre>
          </div>
        )}
      </div>

      {/* Rationale Callout Footer */}
      <div className="border-t border-slate-800/80 bg-slate-950/80 p-3.5 text-xs text-slate-300">
        <span className="font-semibold text-indigo-300 mr-1.5">Architectural Rationale:</span>
        <span className="text-slate-300 leading-normal">{snippet.explanation}</span>
      </div>
    </div>
  );
}
