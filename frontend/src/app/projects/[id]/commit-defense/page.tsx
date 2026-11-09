"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertCircle, GitCommit, Loader2 } from "lucide-react";

import { CommitDefenseSession } from "@/components/domain/CommitDefenseSession";
import { CommitDiffOverview } from "@/components/domain/CommitDiffOverview";
import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { analyzeCommitDiff, startCommitDefenseSession } from "@/lib/commitDefenseApi";
import { getProjectOverview } from "@/lib/projectApi";
import { supabase } from "@/lib/supabase";
import type { CommitAnalysisResponse, CommitDefenseSessionState } from "@/types/commitDefense";
import type { ProjectOverviewResponse } from "@/types/project";

export default function CommitDefensePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [project, setProject] = useState<ProjectOverviewResponse | null>(null);
  const [commitInput, setCommitInput] = useState("");
  const [analysis, setAnalysis] = useState<CommitAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<CommitDefenseSessionState | null>(null);
  const [startingDefense, setStartingDefense] = useState(false);
  const [activeView, setActiveView] = useState<"diff" | "session">("diff");
  const [numQuestions, setNumQuestions] = useState<number>(3);

  const getSessionToken = async () => {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      router.push("/login");
      return null;
    }
    return session.access_token;
  };

  const fetchProjectInfo = useCallback(async () => {
    if (!projectId) return;
    try {
      const token = await getSessionToken();
      if (token) setProject(await getProjectOverview(projectId, token));
    } catch {
      // Graceful fallback if overview endpoint fails
    } finally {
      setPageLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchProjectInfo();
  }, [fetchProjectInfo]);

  const handleAnalyzeCommit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commitInput.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getSessionToken();
      if (token) {
        setAnalysis(await analyzeCommitDiff(projectId, commitInput.trim(), token));
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to analyze commit diff");
    } finally {
      setLoading(false);
    }
  };

  const handleStartCommitDefense = async () => {
    const targetRef = analysis?.metadata?.commit_hash || commitInput.trim();
    if (!targetRef) return setError("Please analyze a commit first.");
    setStartingDefense(true);
    setError(null);
    try {
      const token = await getSessionToken();
      if (!token) return;
      const session = await startCommitDefenseSession(
        projectId,
        targetRef,
        token,
        numQuestions
      );
      setActiveSession(session);
      setActiveView("session");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start commit defense session");
    } finally {
      setStartingDefense(false);
    }
  };

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
        activeTab="commit-defense"
      />

      {/* Commit Input & Analysis Form */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <div className="flex items-center gap-2">
            <GitCommit className="h-5 w-5 text-emerald-400" />
            <h2 className="text-base font-semibold text-zinc-100">
              Ingest Git Commit for Architectural Defense
            </h2>
          </div>
          <span className="text-xs text-zinc-400 font-mono">
            Full SHA, 7-char hash, or GitHub commit URL
          </span>
        </div>

        <form onSubmit={handleAnalyzeCommit} className="flex gap-2">
          <input
            type="text"
            placeholder="e.g. 7f18c60 or https://github.com/owner/repo/commit/7f18c60"
            value={commitInput}
            onChange={(e) => setCommitInput(e.target.value)}
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900/80 px-3.5 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-emerald-500 focus:outline-none"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitCommit className="h-4 w-4" />}
            Analyze Commit
          </button>
        </form>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-rose-500/20 bg-rose-950/30 p-3 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Mode Switcher when Active Session Exists */}
      {activeSession && (
        <div className="flex justify-between items-center rounded-xl border border-zinc-800 bg-zinc-900/50 p-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-zinc-300 font-mono">
              Active Defense Session: {activeSession.commit_hash.slice(0, 7)}
            </span>
          </div>
          <div className="flex rounded-lg bg-zinc-950 border border-zinc-800 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setActiveView("diff")}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                activeView === "diff"
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Commit Overview
            </button>
            <button
              type="button"
              onClick={() => setActiveView("session")}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                activeView === "session"
                  ? "bg-emerald-600 text-white"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Active Interview
            </button>
          </div>
        </div>
      )}

      {/* View Switch: Active Interview vs Commit Diff Overview */}
      {activeView === "session" && activeSession ? (
        <CommitDefenseSession
          session={activeSession}
          onSessionUpdate={setActiveSession}
          onExitSession={() => setActiveView("diff")}
        />
      ) : analysis ? (
        <CommitDiffOverview
          analysis={analysis}
          onStartDefense={handleStartCommitDefense}
          startingDefense={startingDefense}
          numQuestions={numQuestions}
          setNumQuestions={setNumQuestions}
        />
      ) : (
        /* Empty State */
        <div className="rounded-xl border border-dashed border-zinc-800 p-12 text-center space-y-3">
          <GitCommit className="mx-auto h-8 w-8 text-zinc-600" />
          <h3 className="text-sm font-semibold text-zinc-300">No Commit Analyzed Yet</h3>
          <p className="text-xs text-zinc-500 max-w-sm mx-auto">
            Paste a commit hash or GitHub commit URL above to inspect the unified diff and initiate
            a targeted technical defense session.
          </p>
        </div>
      )}
    </div>
  );
}
