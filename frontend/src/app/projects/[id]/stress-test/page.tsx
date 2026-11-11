"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertCircle, Code2, Gauge, Loader2, RotateCcw, Zap } from "lucide-react";

import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { StressTestSession } from "@/components/domain/StressTestSession";
import {
  CONSTRAINT_LABELS,
  StressSeverityBadge,
} from "@/components/domain/StressTurnTranscript";
import { getProjectOverview } from "@/lib/projectApi";
import { fetchStressScenarios, startStressSession } from "@/lib/stressTestApi";
import { supabase } from "@/lib/supabase";
import type { ProjectOverviewResponse } from "@/types/project";
import type {
  StressConstraintType,
  StressDefenseSessionState,
  StressTestScenario,
} from "@/types/stressTest";

const CONSTRAINT_FILTERS: { label: string; value: StressConstraintType | "" }[] = [
  { label: "All Constraints", value: "" },
  { label: "Concurrency Spike", value: "CONCURRENCY_SPIKE" },
  { label: "100x Data Volume", value: "DATA_VOLUME_100X" },
  { label: "Memory Pressure", value: "MEMORY_PRESSURE" },
  { label: "Network Latency Jitter", value: "NETWORK_LATENCY_JITTER" },
  { label: "DB Pool Starvation", value: "DB_CONNECTION_STARVATION" },
];

export default function StressTestPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [project, setProject] = useState<ProjectOverviewResponse | null>(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);

  const [scenarios, setScenarios] = useState<StressTestScenario[]>([]);
  const [selectedConstraint, setSelectedConstraint] = useState<StressConstraintType | "">("");
  const [loadingScenarios, setLoadingScenarios] = useState(false);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<StressDefenseSessionState | null>(null);
  const [startingSession, setStartingSession] = useState(false);

  const latestRequestRef = useRef(0);

  const getAuthToken = useCallback(async (): Promise<string | null> => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      router.push("/login");
      return null;
    }
    return session.access_token;
  }, [router]);

  const fetchProjectInfo = useCallback(async () => {
    if (!projectId) {
      setPageError("Missing project identifier.");
      setPageLoading(false);
      return;
    }
    setPageLoading(true);
    setPageError(null);
    try {
      const token = await getAuthToken();
      if (!token) return;
      const overview = await getProjectOverview(projectId, token);
      setProject(overview);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Failed to load project");
    } finally {
      setPageLoading(false);
    }
  }, [projectId, getAuthToken]);

  const loadScenarios = useCallback(async () => {
    if (!projectId) return;
    const requestId = ++latestRequestRef.current;
    setLoadingScenarios(true);
    setScenarioError(null);
    try {
      const token = await getAuthToken();
      if (!token) return;
      const res = await fetchStressScenarios(
        projectId,
        token,
        selectedConstraint || undefined,
        5
      );
      if (requestId === latestRequestRef.current) setScenarios(res.scenarios);
    } catch (err) {
      if (requestId === latestRequestRef.current) {
        setScenarioError(err instanceof Error ? err.message : "Failed to load stress test scenarios");
      }
    } finally {
      if (requestId === latestRequestRef.current) {
        setLoadingScenarios(false);
      }
    }
  }, [projectId, selectedConstraint, getAuthToken]);

  useEffect(() => {
    void fetchProjectInfo();
  }, [fetchProjectInfo]);

  useEffect(() => {
    void loadScenarios();
    return () => {
      latestRequestRef.current += 1;
    };
  }, [loadScenarios]);

  const handleLaunchSession = async (scenarioId: string) => {
    setStartingSession(true);
    setScenarioError(null);
    try {
      const token = await getAuthToken();
      if (!token) return;
      const newSession = await startStressSession(projectId, scenarioId, token);
      setActiveSession(newSession);
    } catch (err) {
      setScenarioError(err instanceof Error ? err.message : "Failed to start stress defense session");
    } finally {
      setStartingSession(false);
    }
  };

  if (pageLoading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
        <p className="text-sm font-mono text-zinc-400">Loading Stress Test Arena...</p>
      </div>
    );
  }

  if (pageError) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 p-8 max-w-5xl mx-auto">
        <div role="alert" className="rounded-xl border border-rose-900/60 bg-rose-950/20 p-6 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-rose-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-1">
            <h3 className="font-semibold text-rose-200">Unable to load project</h3>
            <p className="text-sm text-rose-300/80">{pageError}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <ProjectNavHeader
          projectId={projectId}
          projectName={project?.name || "Repository"}
          githubUrl={project?.github_url}
          defaultBranch={project?.default_branch}
          commitHash={project?.commit_hash}
          activeTab="stress-test"
          subtitle="Defend architectural limits against 100x growth, traffic surges, and resource clamping"
          onRefresh={!activeSession ? loadScenarios : undefined}
          isRefreshing={loadingScenarios}
        />

        {activeSession ? (
          <StressTestSession
            session={activeSession}
            onSessionUpdate={setActiveSession}
            onExitSession={() => {
              setActiveSession(null);
              setScenarioError(null);
            }}
          />
        ) : (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-amber-900/40 bg-gradient-to-r from-amber-950/20 via-zinc-950 to-zinc-950 p-6">
              <div className="space-y-1">
                <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
                  <Gauge className="h-5 w-5 text-amber-400" /> What-If Scaling Stress Tests
                </h2>
                <p className="text-sm text-zinc-400">
                  Hypothetical production scaling constraints anchored to this repository&apos;s load-bearing symbols and dependencies.
                </p>
              </div>
              <select
                aria-label="Filter stress scenarios by constraint type"
                value={selectedConstraint}
                onChange={(e) => setSelectedConstraint(e.target.value as StressConstraintType | "")}
                className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-amber-500"
              >
                {CONSTRAINT_FILTERS.map((opt) => (
                  <option key={opt.label} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {scenarioError && (
              <div role="alert" className="rounded-lg border border-rose-800/40 bg-rose-950/30 p-4 text-xs text-rose-300">
                {scenarioError}
              </div>
            )}

            {loadingScenarios ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-400">
                <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
                <p className="text-sm font-mono">Synthesizing scaling constraints from repository evidence...</p>
              </div>
            ) : scenarios.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-8 text-center space-y-3">
                <p className="text-sm text-zinc-300">
                  No scaling scenarios available{selectedConstraint ? " for this constraint filter" : ""}.
                </p>
                <div className="flex justify-center gap-2">
                  {selectedConstraint && (
                    <button
                      type="button"
                      onClick={() => setSelectedConstraint("")}
                      className="rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-100 px-3 py-1.5 text-xs font-medium transition-colors"
                    >
                      Clear Filter
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={loadScenarios}
                    className="inline-flex items-center gap-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white px-3 py-1.5 text-xs font-medium transition-colors"
                  >
                    <RotateCcw className="h-3.5 w-3.5" /> Retry Synthesis
                  </button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {scenarios.map((sc) => (
                  <div
                    key={sc.id}
                    className="flex flex-col justify-between rounded-xl border border-zinc-800/80 bg-zinc-950/80 p-5 hover:border-amber-700/50 transition-all space-y-4"
                  >
                    <div className="space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <StressSeverityBadge severity={sc.severity} />
                        <span className="font-mono text-[10px] rounded bg-zinc-900 px-2 py-0.5 text-amber-300 border border-zinc-800">
                          {CONSTRAINT_LABELS[sc.constraint_type]}
                        </span>
                      </div>
                      <h3 className="font-semibold text-zinc-100 text-base leading-snug">{sc.title}</h3>
                      <p className="text-xs text-zinc-400 leading-relaxed">{sc.context_description}</p>
                      <div className="rounded-lg bg-zinc-900/60 p-3 space-y-1.5 border border-zinc-800/40 text-xs font-mono">
                        <div className="flex items-center gap-1.5 text-zinc-300">
                          <Code2 className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />
                          <span className="truncate">{sc.target.file_path}</span>
                        </div>
                        <div className="text-[11px] text-zinc-400 pl-5">
                          Symbol: <span className="text-amber-300">{sc.target.symbol_name}</span> (L{sc.target.line_range})
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={startingSession}
                      onClick={() => handleLaunchSession(sc.id)}
                      className="w-full flex items-center justify-center gap-2 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-medium py-2 text-xs transition-colors"
                    >
                      {startingSession ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
                      Launch Stress Defense
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
