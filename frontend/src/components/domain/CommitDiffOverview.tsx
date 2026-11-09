"use client";

import { ExternalLink, FileCode, Loader2, Play } from "lucide-react";
import type { CommitAnalysisResponse } from "@/types/commitDefense";

interface CommitDiffOverviewProps {
  analysis: CommitAnalysisResponse;
  onStartDefense: () => void;
  startingDefense: boolean;
  numQuestions: number;
  setNumQuestions: (n: number) => void;
}

export function CommitDiffOverview({
  analysis,
  onStartDefense,
  startingDefense,
  numQuestions,
  setNumQuestions,
}: CommitDiffOverviewProps) {
  const meta = analysis.metadata;
  const activeFiles = analysis.files || [];
  const netImpact = analysis.total_additions - analysis.total_deletions;

  return (
    <div className="space-y-4">
      {/* Commit Metadata & CTA Banner */}
      <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/10 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs rounded bg-zinc-800 px-2 py-0.5 text-emerald-400 border border-zinc-700">
                {meta.commit_hash.slice(0, 7)}
              </span>
              <h3 className="text-base font-semibold text-zinc-100">{meta.message}</h3>
              {meta.html_url && (
                <a
                  href={meta.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-zinc-500 hover:text-zinc-300"
                  title="View on GitHub"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>
            <p className="text-xs text-zinc-400 mt-1">
              Committed by <span className="text-zinc-200 font-medium">{meta.author_name}</span> ·{" "}
              {new Date(meta.committed_at).toLocaleString()}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
              className="rounded-lg border border-zinc-700 bg-zinc-900 px-2.5 py-2 text-xs text-zinc-200 focus:outline-none"
            >
              <option value={1}>1 Question</option>
              <option value={2}>2 Questions</option>
              <option value={3}>3 Questions</option>
              <option value={5}>5 Questions</option>
            </select>
            <button
              type="button"
              onClick={onStartDefense}
              disabled={startingDefense}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-xs font-semibold text-white transition-colors disabled:opacity-50"
            >
              {startingDefense ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5 fill-current" />
              )}
              <span>Launch Commit Defense</span>
            </button>
          </div>
        </div>

        {/* Scorecard KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
            <p className="text-xs text-zinc-400">Files Changed</p>
            <p className="text-lg font-semibold text-zinc-100">{analysis.total_files_changed}</p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
            <p className="text-xs text-zinc-400">Additions</p>
            <p className="text-lg font-semibold text-emerald-400">+{analysis.total_additions}</p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
            <p className="text-xs text-zinc-400">Deletions</p>
            <p className="text-lg font-semibold text-rose-400">-{analysis.total_deletions}</p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
            <p className="text-xs text-zinc-400">Net Impact</p>
            <p className="text-lg font-semibold text-zinc-200">
              {netImpact > 0 ? `+${netImpact}` : netImpact}
            </p>
          </div>
        </div>

        {analysis.summary_narrative && (
          <p className="text-xs text-zinc-300 bg-zinc-900/40 p-3 rounded-lg border border-zinc-800/80 font-mono">
            {analysis.summary_narrative}
          </p>
        )}
      </div>

      {/* Changed Files Breakdown */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Modified Files in this Commit ({activeFiles.length})
        </h4>
        <div className="space-y-1.5">
          {activeFiles.map((file, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-lg border border-zinc-800/80 bg-zinc-900/50 px-3 py-2 text-xs"
            >
              <div className="flex items-center gap-2">
                <FileCode className="h-3.5 w-3.5 text-zinc-400" />
                <span className="font-mono text-zinc-200">{file.new_path || file.old_path}</span>
                <span className="text-[10px] rounded bg-zinc-800 px-1.5 py-0.5 text-zinc-400 capitalize">
                  {file.status}
                </span>
              </div>
              <div className="flex items-center gap-2 font-mono text-[11px]">
                <span className="text-emerald-400">+{file.total_additions}</span>
                <span className="text-rose-400">-{file.total_deletions}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
