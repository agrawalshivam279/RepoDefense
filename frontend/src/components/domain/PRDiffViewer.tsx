"use client";

import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  FileCode,
  FileDiff,
  Filter,
  Minimize2,
  Maximize2,
  Search,
} from "lucide-react";
import type {
  DiffLineType,
  FileChangeStatus,
  ParsedDiffHunk,
  ParsedFileDiff,
} from "@/types/prAnalysis";

interface PRDiffViewerProps {
  files: ParsedFileDiff[];
  className?: string;
}

const STATUS_CONFIG: Record<
  FileChangeStatus,
  { label: string; badgeClass: string }
> = {
  added: {
    label: "Added",
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  },
  modified: {
    label: "Modified",
    badgeClass: "bg-sky-500/10 text-sky-400 border-sky-500/30",
  },
  deleted: {
    label: "Deleted",
    badgeClass: "bg-rose-500/10 text-rose-400 border-rose-500/30",
  },
  renamed: {
    label: "Renamed",
    badgeClass: "bg-purple-500/10 text-purple-400 border-purple-500/30",
  },
  binary: {
    label: "Binary",
    badgeClass: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
  },
};

const LINE_STYLES: Record<DiffLineType, { row: string; prefix: string }> = {
  addition: {
    row: "bg-emerald-950/35 text-emerald-200 border-l-2 border-emerald-500",
    prefix: "+",
  },
  deletion: {
    row: "bg-rose-950/35 text-rose-200 border-l-2 border-rose-500",
    prefix: "-",
  },
  context: {
    row: "text-zinc-300 hover:bg-zinc-900/50",
    prefix: " ",
  },
};

function renderContentWithRedactions(text: string): React.ReactNode {
  if (!text.includes("[REDACTED_SECRET]")) {
    return text;
  }
  const parts = text.split("[REDACTED_SECRET]");
  return (
    <>
      {parts.map((part, idx) => (
        <React.Fragment key={idx}>
          {part}
          {idx < parts.length - 1 && (
            <span className="inline-flex items-center gap-1 rounded bg-amber-500/20 px-1 py-0.5 text-xs font-semibold text-amber-300 border border-amber-500/30">
              <AlertTriangle className="h-3 w-3 inline" />
              [REDACTED_SECRET]
            </span>
          )}
        </React.Fragment>
      ))}
    </>
  );
}

function DiffHunkView({ hunk }: { hunk: ParsedDiffHunk }) {
  return (
    <div className="border-t border-zinc-800">
      <div className="bg-zinc-900/80 px-3 py-1 font-mono text-xs text-zinc-400 border-b border-zinc-800/80">
        @@ -{hunk.old_start},{hunk.old_lines} +{hunk.new_start},{hunk.new_lines} @@
        {hunk.header ? ` ${hunk.header}` : ""}
      </div>
      <div className="font-mono text-xs leading-5 overflow-x-auto">
        {hunk.lines.map((line, idx) => {
          const style = LINE_STYLES[line.line_type];
          return (
            <div
              key={idx}
              className={`flex items-start px-2 py-0.5 select-text ${style.row}`}
            >
              <span className="w-10 shrink-0 text-right pr-2 text-zinc-500 select-none">
                {line.old_line_number ?? ""}
              </span>
              <span className="w-10 shrink-0 text-right pr-2 text-zinc-500 select-none border-r border-zinc-800/80">
                {line.new_line_number ?? ""}
              </span>
              <span className="w-5 shrink-0 text-center select-none font-bold">
                {style.prefix}
              </span>
              <span className="whitespace-pre flex-1 pl-1">
                {renderContentWithRedactions(line.content)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function PRDiffViewer({ files, className = "" }: PRDiffViewerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [collapsedFiles, setCollapsedFiles] = useState<Record<string, boolean>>(
    {}
  );

  const filteredFiles = useMemo(() => {
    return files.filter((f) => {
      const matchesSearch =
        searchQuery === "" ||
        f.new_path.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (f.old_path &&
          f.old_path.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesStatus =
        statusFilter === "all" || f.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [files, searchQuery, statusFilter]);

  const toggleFile = (path: string) => {
    setCollapsedFiles((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const expandAll = () => setCollapsedFiles({});
  const collapseAll = () => {
    const all: Record<string, boolean> = {};
    files.forEach((f) => {
      all[f.new_path] = true;
    });
    setCollapsedFiles(all);
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400" />
          <input
            type="text"
            placeholder="Filter files by path..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-zinc-700 bg-zinc-950 pl-9 pr-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-zinc-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto">
          <Filter className="h-4 w-4 text-zinc-400 shrink-0" />
          {(["all", "modified", "added", "deleted", "renamed"] as const).map(
            (st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition-colors ${
                  statusFilter === st
                    ? "bg-zinc-800 text-zinc-100 border border-zinc-600"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40"
                }`}
              >
                {st}
              </button>
            )
          )}
          <div className="h-4 w-px bg-zinc-800 mx-1" />
          <button
            onClick={expandAll}
            title="Expand All"
            className="rounded p-1 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
          <button
            onClick={collapseAll}
            title="Collapse All"
            className="rounded p-1 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60"
          >
            <Minimize2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Files List */}
      <div className="space-y-3">
        {filteredFiles.length === 0 ? (
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-8 text-center text-sm text-zinc-400">
            <FileDiff className="mx-auto h-8 w-8 text-zinc-600 mb-2" />
            No files match the selected filter criteria.
          </div>
        ) : (
          filteredFiles.map((file) => {
            const isCollapsed = collapsedFiles[file.new_path];
            const cfg = STATUS_CONFIG[file.status] || STATUS_CONFIG.modified;
            return (
              <div
                key={file.new_path}
                className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950 transition-colors"
              >
                {/* File Header Bar */}
                <button
                  type="button"
                  onClick={() => toggleFile(file.new_path)}
                  className="w-full flex items-center justify-between px-3 py-2.5 bg-zinc-900/80 hover:bg-zinc-900 text-left transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {isCollapsed ? (
                      <ChevronRight className="h-4 w-4 text-zinc-400 shrink-0" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-zinc-400 shrink-0" />
                    )}
                    <FileCode className="h-4 w-4 text-zinc-400 shrink-0" />
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase border ${cfg.badgeClass}`}
                    >
                      {cfg.label}
                    </span>
                    <span className="font-mono text-xs text-zinc-200 truncate">
                      {file.status === "renamed" && file.old_path
                        ? `${file.old_path} → ${file.new_path}`
                        : file.new_path}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 text-xs font-mono">
                    {file.total_additions > 0 && (
                      <span className="text-emerald-400 font-semibold">
                        +{file.total_additions}
                      </span>
                    )}
                    {file.total_deletions > 0 && (
                      <span className="text-rose-400 font-semibold">
                        -{file.total_deletions}
                      </span>
                    )}
                  </div>
                </button>

                {/* File Body */}
                {!isCollapsed && (
                  <div>
                    {file.is_binary ? (
                      <div className="p-4 text-center text-xs text-zinc-500 font-mono">
                        Binary file differences are not displayed.
                      </div>
                    ) : file.hunks.length === 0 ? (
                      <div className="p-4 text-center text-xs text-zinc-500 font-mono">
                        File mode or path changed with zero content modifications.
                      </div>
                    ) : (
                      file.hunks.map((hunk, hIdx) => (
                        <DiffHunkView key={hIdx} hunk={hunk} />
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
