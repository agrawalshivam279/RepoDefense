"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Loader2,
  RefreshCw,
  RotateCcw,
} from "lucide-react";
import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { RetestCompletionCard } from "@/components/domain/RetestCompletionCard";
import { RetestDefenseEditor } from "@/components/domain/RetestDefenseEditor";
import { RetestEvaluationModal } from "@/components/domain/RetestEvaluationModal";
import { RetestSessionCard } from "@/components/domain/RetestSessionCard";
import { RetestWeaknessSelector } from "@/components/domain/RetestWeaknessSelector";
import { getProjectOverview } from "@/lib/projectApi";
import {
  createRetestSession,
  fetchEligibleWeaknesses,
  submitRetestAnswer,
} from "@/lib/retestApi";
import { supabase } from "@/lib/supabase";
import type { ProjectOverviewResponse } from "@/types/project";
import type {
  EligibleWeaknessItem,
  RetestEvaluationResponse,
  TargetedRetestSessionResponse,
} from "@/types/retest";

type RetestPhase = "selection" | "session" | "evaluation" | "completed";

export default function TargetedRetestPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const projectId = typeof params?.id === "string" ? params.id : "";

  const [authLoading, setAuthLoading] = useState<boolean>(true);
  const [overview, setOverview] = useState<ProjectOverviewResponse | null>(null);

  const [phase, setPhase] = useState<RetestPhase>("selection");
  const [weaknesses, setWeaknesses] = useState<EligibleWeaknessItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [maxQuestions, setMaxQuestions] = useState<number>(3);
  const [loadingWeaknesses, setLoadingWeaknesses] = useState<boolean>(false);
  const [loadFailed, setLoadFailed] = useState<boolean>(false);
  const [generatingSession, setGeneratingSession] = useState<boolean>(false);

  const [activeSession, setActiveSession] = useState<TargetedRetestSessionResponse | null>(null);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [defenseText, setDefenseText] = useState<string>("");
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [currentEvaluation, setCurrentEvaluation] = useState<RetestEvaluationResponse | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const getFreshToken = useCallback(async (): Promise<string | null> => {
    const { data } = await supabase.auth.getSession();
    const tok = data.session?.access_token || null;
    if (!tok) {
      router.replace("/login");
      return null;
    }
    return tok;
  }, [router]);

  useEffect(() => {
    let cancelled = false;
    getFreshToken().then((t) => {
      if (!cancelled && t) setAuthLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [getFreshToken]);

  const loadData = useCallback(
    async (pId: string, isCancelled?: () => boolean) => {
      setLoadingWeaknesses(true);
      setSessionError(null);
      setLoadFailed(false);
      try {
        const tok = await getFreshToken();
        if (!tok || isCancelled?.()) return;

        const [ov, weakRes] = await Promise.all([
          getProjectOverview(pId, tok).catch(() => null),
          fetchEligibleWeaknesses(tok, pId),
        ]);
        if (isCancelled?.()) return;

        setOverview(ov);
        setWeaknesses(weakRes.weaknesses);
        setSelectedIds(weakRes.weaknesses.slice(0, 50).map((w) => w.id));
      } catch (err) {
        if (!isCancelled?.()) {
          setLoadFailed(true);
          setSessionError(err instanceof Error ? err.message : "Failed to load weaknesses");
        }
      } finally {
        if (!isCancelled?.()) setLoadingWeaknesses(false);
      }
    },
    [getFreshToken]
  );

  useEffect(() => {
    let cancelled = false;
    if (projectId) {
      loadData(projectId, () => cancelled);
    }
    return () => {
      cancelled = true;
    };
  }, [projectId, loadData]);

  const handleToggleWeakness = (id: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((item) => item !== id);
      if (prev.length >= 50) return prev;
      return [...prev, id];
    });
  };

  const handleStartSession = async () => {
    if (selectedIds.length === 0) return;
    setGeneratingSession(true);
    setSessionError(null);
    try {
      const tok = await getFreshToken();
      if (!tok) return;

      const session = await createRetestSession(tok, {
        project_id: projectId || null,
        weakness_ids: selectedIds.slice(0, 50),
        max_questions: maxQuestions,
      });
      if (session.questions.length === 0) {
        throw new Error("No re-test questions could be generated for selected weaknesses.");
      }
      setActiveSession(session);
      setCurrentIndex(0);
      setDefenseText("");
      setCurrentEvaluation(null);
      setPhase("session");
    } catch (err) {
      setSessionError(err instanceof Error ? err.message : "Failed to start re-test session");
    } finally {
      setGeneratingSession(false);
    }
  };

  const handleSubmitDefense = async () => {
    if (!activeSession) return;
    const currentQ = activeSession.questions[currentIndex];
    if (!currentQ) return;

    setEvaluating(true);
    setSessionError(null);
    try {
      const tok = await getFreshToken();
      if (!tok) return;

      const evalResp = await submitRetestAnswer(tok, {
        session_id: activeSession.session_id,
        question_id: currentQ.question_id,
        weakness_id: currentQ.weakness_id,
        candidate_response: defenseText.trim(),
      });
      setCurrentEvaluation(evalResp);
      setPhase("evaluation");
    } catch (err) {
      setSessionError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setEvaluating(false);
    }
  };

  const handleNextQuestion = () => {
    if (!activeSession) return;
    if (currentIndex + 1 < activeSession.questions.length) {
      setCurrentIndex((prev) => prev + 1);
      setDefenseText("");
      setCurrentEvaluation(null);
      setPhase("session");
    } else {
      setPhase("completed");
    }
  };

  const handleRestart = () => {
    setPhase("selection");
    setActiveSession(null);
    setCurrentEvaluation(null);
    setDefenseText("");
    if (projectId) loadData(projectId);
  };

  if (authLoading || (loadingWeaknesses && !overview)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-zinc-400">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const currentQuestion = activeSession?.questions[currentIndex];

  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <ProjectNavHeader
        projectId={projectId}
        projectName={overview?.name || "Repository"}
        githubUrl={overview?.github_url}
        defaultBranch={overview?.default_branch}
        commitHash={overview?.commit_hash}
        activeTab="retest"
        subtitle="Targeted Re-Testing & Weakness Remediation"
      />

      <main className="mx-auto max-w-5xl px-4 py-8 space-y-8">
        {sessionError && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <span>{sessionError}</span>
            <div className="flex items-center gap-2 shrink-0">
              {loadFailed && (
                <button
                  type="button"
                  onClick={() => loadData(projectId)}
                  className="inline-flex items-center gap-1 rounded bg-red-500/20 px-2.5 py-1 text-xs font-semibold text-red-200 hover:bg-red-500/30"
                >
                  <RefreshCw className="h-3 w-3" /> Retry Loading
                </button>
              )}
              {phase === "session" && (
                <button
                  type="button"
                  onClick={handleRestart}
                  className="inline-flex items-center gap-1 rounded bg-zinc-800 px-2.5 py-1 text-xs font-semibold text-zinc-200 hover:bg-zinc-700"
                >
                  <RotateCcw className="h-3 w-3" /> Recover Session
                </button>
              )}
            </div>
          </div>
        )}

        {phase === "selection" && (
          <RetestWeaknessSelector
            weaknesses={weaknesses}
            selectedIds={selectedIds}
            onToggleWeakness={handleToggleWeakness}
            onSelectAll={() => setSelectedIds(weaknesses.slice(0, 50).map((w) => w.id))}
            onDeselectAll={() => setSelectedIds([])}
            maxQuestions={maxQuestions}
            onChangeMaxQuestions={setMaxQuestions}
            onStartSession={handleStartSession}
            isLoading={generatingSession || loadingWeaknesses}
          />
        )}

        {phase === "session" && currentQuestion && (
          <div className="space-y-6">
            <RetestSessionCard
              question={currentQuestion}
              currentIndex={currentIndex}
              totalQuestions={activeSession?.questions.length || 1}
            />
            <RetestDefenseEditor
              defenseText={defenseText}
              onChangeDefense={setDefenseText}
              onSubmit={handleSubmitDefense}
              isSubmitting={evaluating}
            />
          </div>
        )}

        {phase === "evaluation" && currentEvaluation && (
          <RetestEvaluationModal
            evaluation={currentEvaluation}
            currentIndex={currentIndex}
            totalQuestions={activeSession?.questions.length || 1}
            onNextQuestion={handleNextQuestion}
            onFinishSession={() => setPhase("completed")}
          />
        )}

        {phase === "completed" && (
          <RetestCompletionCard onRestart={handleRestart} />
        )}
      </main>
    </div>
  );
}
