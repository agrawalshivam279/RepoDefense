"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertCircle, ChevronDown, ChevronUp, Compass, Loader2 } from "lucide-react";
import { ArchDefenseSession } from "@/components/domain/ArchDefenseSession";
import { ArchTopicCard } from "@/components/domain/ArchTopicCard";
import { ARCH_FOCUS_META } from "@/components/domain/ArchTopologyPanel";
import { MermaidViewer } from "@/components/domain/MermaidViewer";
import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { fetchArchDefenseTopics, startArchDefenseSession } from "@/lib/archDefenseApi";
import { getProjectOverview } from "@/lib/projectApi";
import { supabase } from "@/lib/supabase";
import type { ArchDefenseSessionState, ArchFocusAreaType, ArchTopicListResponse } from "@/types/archDefense";
import type { DiagramResponse } from "@/types/diagram";
import type { ProjectOverviewResponse } from "@/types/project";

const FOCUS_FILTER_KEYS: ArchFocusAreaType[] = [
  "PATTERN_CHOICE",
  "COMPONENT_BOUNDARY",
  "DATA_FLOW_COUPLING",
  "ARCHITECTURAL_RISK",
];

export default function ArchDefensePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const projectId = typeof params?.id === "string" ? params.id : "";

  const [project, setProject] = useState<ProjectOverviewResponse | null>(null);
  const [topicData, setTopicData] = useState<ArchTopicListResponse | null>(null);
  const [selectedFocus, setSelectedFocus] = useState<ArchFocusAreaType | "">("");
  const [loading, setLoading] = useState(true);
  const [startingTopicId, setStartingTopicId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showTopologyPreview, setShowTopologyPreview] = useState(true);
  const [activeSession, setActiveSession] = useState<ArchDefenseSessionState | null>(null);

  const isMountedRef = useRef(true);
  const topicAbortRef = useRef<AbortController | null>(null);
  const latestRequestRef = useRef(0);
  const overviewRequestRef = useRef(0);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      topicAbortRef.current?.abort();
    };
  }, []);

  const getAuthToken = useCallback(async (): Promise<string | null> => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
      router.replace("/login");
      return null;
    }
    return token;
  }, [router]);

  const fetchOverview = useCallback(async () => {
    if (!projectId) return;
    const requestId = ++overviewRequestRef.current;
    try {
      const token = await getAuthToken();
      if (!token || !isMountedRef.current || requestId !== overviewRequestRef.current) return;
      const overview = await getProjectOverview(projectId, token);
      if (isMountedRef.current && requestId === overviewRequestRef.current) setProject(overview);
    } catch {
      // Non-fatal metadata fetch; topic loader handles primary surface errors.
    }
  }, [projectId, getAuthToken]);

  const loadTopics = useCallback(async () => {
    if (!projectId) return;
    topicAbortRef.current?.abort();
    const controller = new AbortController();
    topicAbortRef.current = controller;
    const requestId = ++latestRequestRef.current;

    setLoading(true);
    setError(null);
    try {
      const token = await getAuthToken();
      if (!token || controller.signal.aborted || !isMountedRef.current) return;
      const res = await fetchArchDefenseTopics(projectId, token, selectedFocus || undefined, 6, controller.signal);
      if (isMountedRef.current && requestId === latestRequestRef.current && !controller.signal.aborted) {
        setTopicData(res);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      if (isMountedRef.current && requestId === latestRequestRef.current) {
        setError(err instanceof Error ? err.message : "Failed to load architecture defense topics.");
      }
    } finally {
      if (isMountedRef.current && requestId === latestRequestRef.current) setLoading(false);
    }
  }, [projectId, selectedFocus, getAuthToken]);

  useEffect(() => {
    void fetchOverview();
    return () => {
      overviewRequestRef.current += 1;
    };
  }, [fetchOverview]);

  useEffect(() => {
    void loadTopics();
    return () => {
      latestRequestRef.current += 1;
      topicAbortRef.current?.abort();
    };
  }, [loadTopics]);

  const previewDiagram = useMemo<DiagramResponse | null>(() => {
    if (!topicData) return null;
    return {
      project_id: topicData.project_id,
      project_name: topicData.project_name,
      diagram_type: topicData.diagram_type,
      mermaid_code: topicData.mermaid_code,
      nodes: topicData.nodes,
      edges: topicData.edges,
      is_fallback: topicData.is_diagram_fallback,
      summary: `Primary pattern: ${topicData.primary_pattern.pattern_name} (${topicData.primary_pattern.tier})`,
    };
  }, [topicData]);

  async function handleLaunchDefense(topicId: string) {
    if (!projectId || startingTopicId !== null) return;
    setStartingTopicId(topicId);
    setError(null);
    try {
      const token = await getAuthToken();
      if (!token || !isMountedRef.current) return;
      const session = await startArchDefenseSession(projectId, topicId, token);
      if (isMountedRef.current) setActiveSession(session);
    } catch (err) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : "Failed to start architecture defense session.");
      }
    } finally {
      if (isMountedRef.current) setStartingTopicId(null);
    }
  }

  if (!projectId) {
    return (
      <div className="mx-auto min-h-screen max-w-5xl bg-zinc-950 p-8 text-zinc-100">
        <div role="alert" className="flex items-start gap-3 rounded-xl border border-rose-900/60 bg-rose-950/20 p-6">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
          <div>
            <h3 className="font-semibold text-rose-200">Unable to load project</h3>
            <p className="text-sm text-rose-300/80">Missing project identifier.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <ProjectNavHeader
        projectId={projectId}
        projectName={project?.name ?? topicData?.project_name}
        githubUrl={project?.github_url}
        defaultBranch={project?.default_branch}
        commitHash={project?.commit_hash}
        statusBadge={project?.status}
        activeTab="arch-defense"
        subtitle="Diagram-grounded architecture defense"
        onRefresh={activeSession ? undefined : () => void loadTopics()}
        isRefreshing={loading}
      />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {error && (
          <div role="alert" className="mb-6 flex items-center gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {activeSession ? (
          <ArchDefenseSession
            session={activeSession}
            projectName={project?.name ?? topicData?.project_name}
            diagramType={topicData?.diagram_type}
            diagramNodes={topicData?.nodes}
            diagramEdges={topicData?.edges}
            isDiagramFallback={topicData?.is_diagram_fallback}
            onSessionUpdate={setActiveSession}
            onExitSession={() => setActiveSession(null)}
          />
        ) : (
          <div className="space-y-6">
            <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5">
              <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-300">
                    <Compass className="h-4 w-4" />
                    <span>Architecture Defense Arena</span>
                  </div>
                  <h1 className="mt-1 text-xl font-bold text-zinc-100">
                    {topicData ? topicData.primary_pattern.pattern_name : "Analyzing Repository Architecture..."}
                  </h1>
                  {topicData && (
                    <p className="mt-1 text-sm text-zinc-400">
                      Confidence: {Math.round(topicData.primary_pattern.confidence_score * 100)}% ({topicData.primary_pattern.tier}) &bull; {topicData.nodes.length} nodes &bull; {topicData.edges.length} edges
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <label className="flex items-center gap-2 text-xs text-zinc-400">
                    <span>Focus:</span>
                    <select
                      value={selectedFocus}
                      onChange={(e) => setSelectedFocus(e.target.value as ArchFocusAreaType | "")}
                      className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-xs font-medium text-zinc-100 focus:border-cyan-500 focus:outline-none"
                    >
                      <option value="">All Focus Axes</option>
                      {FOCUS_FILTER_KEYS.map((key) => (
                        <option key={key} value={key}>
                          {ARCH_FOCUS_META[key].label}
                        </option>
                      ))}
                    </select>
                  </label>

                  {previewDiagram && (
                    <button
                      type="button"
                      aria-expanded={showTopologyPreview}
                      onClick={() => setShowTopologyPreview((prev) => !prev)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-xs font-medium text-zinc-200 transition hover:border-zinc-600"
                    >
                      <span>{showTopologyPreview ? "Hide Diagram" : "Show Diagram"}</span>
                      {showTopologyPreview ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                    </button>
                  )}
                </div>
              </div>

              {showTopologyPreview && previewDiagram && (
                <div className="mt-4 border-t border-zinc-800 pt-4">
                  <MermaidViewer diagram={previewDiagram} />
                </div>
              )}
            </section>

            {loading ? (
              <div className="flex items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/50 py-16 text-sm text-zinc-400">
                <Loader2 className="mr-2.5 h-5 w-5 animate-spin text-cyan-400" />
                Extracting diagram-linked architecture topics...
              </div>
            ) : !topicData || topicData.topics.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 text-center text-sm text-zinc-400">
                No architectural defense topics matched the selected filter.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {topicData.topics.map((topic) => (
                  <ArchTopicCard
                    key={topic.id}
                    topic={topic}
                    isStarting={startingTopicId === topic.id}
                    disabled={startingTopicId !== null}
                    onLaunch={(id) => void handleLaunchDefense(id)}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
