"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ExternalLink,
  FileDiff,
  GitPullRequest,
  Loader2,
  Play,
  ShieldAlert,
} from "lucide-react";

import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { PRDiffViewer } from "@/components/domain/PRDiffViewer";
import { PRDefenseSession } from "@/components/domain/PRDefenseSession";
import { getProjectOverview } from "@/lib/projectApi";
import { analyzeProjectPR, parseRawDiff } from "@/lib/prAnalysisApi";
import { startPRDefenseSession } from "@/lib/prDefenseApi";
import { supabase } from "@/lib/supabase";
import type { PRAnalysisResponse, ParsedFileDiff } from "@/types/prAnalysis";
import type { PRDefenseSessionState } from "@/types/prDefense";
import type { ProjectOverviewResponse } from "@/types/project";

export default function PRDefensePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [project, setProject] = useState<ProjectOverviewResponse | null>(null);
  const [prUrl, setPrUrl] = useState("");
  const [rawDiff, setRawDiff] = useState("");
  const [activeMode, setActiveMode] = useState<"url" | "raw">("url");
  const [analysis, setAnalysis] = useState<PRAnalysisResponse | null>(null);
  const [rawFiles, setRawFiles] = useState<ParsedFileDiff[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<PRDefenseSessionState | null>(null);
  const [startingDefense, setStartingDefense] = useState(false);
  const [activeView, setActiveView] = useState<"diff" | "session">("diff");

  const getSessionToken = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) { router.push("/login"); return null; }
    return session.access_token;
  };

  const fetchProjectInfo = useCallback(async () => {
    if (!projectId) return;
    try {
      const token = await getSessionToken();
      if (token) setProject(await getProjectOverview(projectId, token));
    } catch {
      // Continue without header metadata if overview fails
    } finally {
      setPageLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchProjectInfo(); }, [fetchProjectInfo]);

  const handleAnalyzeUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prUrl.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getSessionToken();
      if (token) {
        setAnalysis(await analyzeProjectPR(projectId, prUrl.trim(), token));
        setRawFiles(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to analyze PR");
    } finally {
      setLoading(false);
    }
  };

  const handleParseRaw = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawDiff.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setRawFiles(await parseRawDiff(rawDiff.trim()));
      setAnalysis(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to parse patch");
    } finally {
      setLoading(false);
    }
  };

  const handleStartPRDefense = async () => {
    const targetUrl = analysis?.metadata?.html_url || (activeMode === "url" ? prUrl.trim() : null);
    if (!targetUrl) return setError("Please analyze a public GitHub Pull Request URL first.");
    setStartingDefense(true);
    setError(null);
    try {
      const token = await getSessionToken();
      if (!token) return;
      const session = await startPRDefenseSession(projectId, targetUrl, token, 3);
      setActiveSession(session);
      setActiveView("session");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start PR defense session");
    } finally {
      setStartingDefense(false);
    }
  };

  const activeFiles = analysis?.files || rawFiles || [];
  const totalAdds = analysis?.total_additions ?? rawFiles?.reduce((a, f) => a + f.total_additions, 0) ?? 0;
  const totalDels = analysis?.total_deletions ?? rawFiles?.reduce((a, f) => a + f.total_deletions, 0) ?? 0;
  const netImpact = totalAdds - totalDels;

  const statItems = [
    { label: "Files Changed", val: activeFiles.length, color: "text-zinc-100" },
    { label: "Additions", val: `+${totalAdds}`, color: "text-emerald-400" },
    { label: "Deletions", val: `-${totalDels}`, color: "text-rose-400" },
    { label: "Net Impact", val: netImpact > 0 ? `+${netImpact}` : netImpact, color: "text-zinc-200" },
  ];

  if (pageLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-6xl space-y-6">
      <ProjectNavHeader
        projectId={projectId}
        projectName={project?.name}
        githubUrl={project?.github_url}
        defaultBranch={project?.default_branch}
        commitHash={project?.commit_hash}
        activeTab="pr-defense"
      />

      {/* Ingestion Configuration Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <div className="flex items-center gap-2">
            <GitPullRequest className="h-5 w-5 text-rose-400" />
            <h2 className="text-base font-semibold text-zinc-100">Ingest Pull Request for Defense</h2>
          </div>
          <div className="flex rounded-lg bg-zinc-900 p-0.5 border border-zinc-800 text-xs">
            {(["url", "raw"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setActiveMode(mode)}
                className={`rounded-md px-3 py-1 font-medium transition-colors ${
                  activeMode === mode ? "bg-zinc-800 text-zinc-100 shadow-sm" : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {mode === "url" ? "GitHub PR URL" : "Raw Patch / Diff"}
              </button>
            ))}
          </div>
        </div>

        {activeMode === "url" ? (
          <form onSubmit={handleAnalyzeUrl} className="flex gap-2">
            <input
              type="url"
              placeholder="https://github.com/owner/repository/pull/123"
              value={prUrl}
              onChange={(e) => setPrUrl(e.target.value)}
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900/80 px-3.5 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-rose-500 focus:outline-none"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-500 px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitPullRequest className="h-4 w-4" />}
              Analyze PR
            </button>
          </form>
        ) : (
          <form onSubmit={handleParseRaw} className="space-y-3">
            <textarea
              rows={4}
              placeholder="Paste raw unified diff patch (diff --git a/... b/...)..."
              value={rawDiff}
              onChange={(e) => setRawDiff(e.target.value)}
              className="w-full font-mono text-xs rounded-lg border border-zinc-700 bg-zinc-900/80 p-3 text-zinc-200 placeholder-zinc-500 focus:border-rose-500 focus:outline-none"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-500 px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDiff className="h-4 w-4" />}
              Parse Raw Diff
            </button>
          </form>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-lg bg-rose-500/10 border border-rose-500/20 px-3 py-2 text-xs text-rose-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Mode Switcher when Active Session Exists */}
      {activeSession && (
        <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-rose-400" />
            <span className="text-xs font-semibold text-zinc-200">
              PR Defense Session #{activeSession.pr_number} Active
            </span>
          </div>
          <div className="flex rounded-lg bg-zinc-900 p-0.5 border border-zinc-800 text-xs">
            <button
              type="button"
              onClick={() => setActiveView("session")}
              className={`rounded-md px-3 py-1 font-medium transition-colors ${activeView === "session" ? "bg-rose-600 text-white shadow-sm" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              Active Interview
            </button>
            <button
              type="button"
              onClick={() => setActiveView("diff")}
              className={`rounded-md px-3 py-1 font-medium transition-colors ${activeView === "diff" ? "bg-zinc-800 text-zinc-100 shadow-sm" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              Diff Viewer ({activeFiles.length})
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area: Session or Diff Viewer */}
      {activeSession && activeView === "session" ? (
        <PRDefenseSession
          session={activeSession}
          onSessionUpdate={setActiveSession}
          onExitSession={() => setActiveView("diff")}
        />
      ) : activeFiles.length > 0 ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {statItems.map((item) => (
              <div key={item.label} className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
                <span className="text-xs text-zinc-400">{item.label}</span>
                <p className={`text-2xl font-bold mt-1 ${item.color}`}>{item.val}</p>
              </div>
            ))}
          </div>

          {analysis && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 px-2 py-0.5 text-xs font-semibold">
                    PR #{analysis.metadata.pr_number}
                  </span>
                  <h3 className="text-sm font-semibold text-zinc-100">{analysis.metadata.title}</h3>
                  <a href={analysis.metadata.html_url} target="_blank" rel="noopener noreferrer" className="text-zinc-400 hover:text-zinc-200">
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
                <p className="text-xs text-zinc-400">{analysis.summary_narrative}</p>
              </div>

              <button
                type="button"
                onClick={activeSession ? () => setActiveView("session") : handleStartPRDefense}
                disabled={startingDefense}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-xs font-semibold text-white transition-colors shrink-0 shadow-lg shadow-emerald-950/40 disabled:opacity-50"
              >
                {startingDefense ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5 fill-current" />}
                {startingDefense ? "Generating Questions..." : activeSession ? "Resume PR Defense" : "Start PR Defense"}
              </button>
            </div>
          )}

          <PRDiffViewer files={activeFiles} />
        </div>
      ) : null}
    </div>
  );
}
