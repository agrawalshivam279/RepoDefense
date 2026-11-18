"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  CheckCircle2,
  GraduationCap,
  Loader2,
  RotateCcw,
} from "lucide-react";
import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
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

  const [token, setToken] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(true);
  const [overview, setOverview] = useState<ProjectOverviewResponse | null>(null);

  // Re-Test State
  const [phase, setPhase] = useState<RetestPhase>("selection");
  const [weaknesses, setWeaknesses] = useState<EligibleWeaknessItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [maxQuestions, setMaxQuestions] = useState<number>(3);
  const [loadingWeaknesses, setLoadingWeaknesses] = useState<boolean>(false);
  const [generatingSession, setGeneratingSession] = useState<boolean>(false);

  // Active Session State
  const [activeSession, setActiveSession] = useState<TargetedRetestSessionResponse | null>(null);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [defenseText, setDefenseText] = useState<string>("");
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [currentEvaluation, setCurrentEvaluation] = useState<RetestEvaluationResponse | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  // Auth bootstrap
  useEffect(() => {
    let cancelled = false;
    async function init() {
      const { data } = await supabase.auth.getSession();
      const t = data.session?.access_token;
      if (!cancelled) {
        if (!t) {
          router.replace("/login");
          return;
        }
        setToken(t);
        setAuthLoading(false);
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [router]);

  // Load project overview and eligible weaknesses
  const loadData = useCallback(async (tok: string, pId: string) => {
    setLoadingWeaknesses(true);
    setSessionError(null);
    try {
      const [ov, weakRes] = await Promise.all([
        getProjectOverview(pId, tok).catch(() => null),
        fetchEligibleWeaknesses(tok, pId),
      ]);
      setOverview(ov);
      setWeaknesses(weakRes.weaknesses);
      setSelectedIds(weakRes.weaknesses.map((w) => w.id));
    } catch (err) {
      setSessionError(err instanceof Error ? err.message : "Failed to load weaknesses");
    } finally {
      setLoadingWeaknesses(false);
    }
  }, []);

  useEffect(() => {
    if (token && projectId) {
      loadData(token, projectId);
    }
  }, [token, projectId, loadData]);

  // Weakness selection toggles
  const handleToggleWeakness = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleStartSession = async () => {
    if (!token || selectedIds.length === 0) return;
    setGeneratingSession(true);
    setSessionError(null);
    try {
      const session = await createRetestSession(token, {
        project_id: projectId || null,
        weakness_ids: selectedIds,
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
    if (!token || !activeSession) return;
    const currentQ = activeSession.questions[currentIndex];
    if (!currentQ) return;

    setEvaluating(true);
    setSessionError(null);
    try {
      const evalResp = await submitRetestAnswer(token, {
        session_id: activeSession.session_id,
        question_id: currentQ.question_id,
        weakness_id: currentQ.weakness_id,
        candidate_response: defenseText,
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

  const handleFinishSession = () => {
    setPhase("completed");
  };

  const handleRestart = () => {
    setPhase("selection");
    setActiveSession(null);
    setCurrentEvaluation(null);
    setDefenseText("");
    if (token && projectId) {
      loadData(token, projectId);
    }
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
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300">
            {sessionError}
          </div>
        )}

        {/* Phase A: Weakness Selection */}
        {phase === "selection" && (
          <RetestWeaknessSelector
            weaknesses={weaknesses}
            selectedIds={selectedIds}
            onToggleWeakness={handleToggleWeakness}
            onSelectAll={() => setSelectedIds(weaknesses.map((w) => w.id))}
            onDeselectAll={() => setSelectedIds([])}
            maxQuestions={maxQuestions}
            onChangeMaxQuestions={setMaxQuestions}
            onStartSession={handleStartSession}
            isLoading={generatingSession}
          />
        )}

        {/* Phase B: Active Question Defense */}
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

        {/* Phase C: Turn Evaluation */}
        {phase === "evaluation" && currentEvaluation && (
          <RetestEvaluationModal
            evaluation={currentEvaluation}
            currentIndex={currentIndex}
            totalQuestions={activeSession?.questions.length || 1}
            onNextQuestion={handleNextQuestion}
            onFinishSession={handleFinishSession}
          />
        )}

        {/* Phase D: Session Completed */}
        {phase === "completed" && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-8 text-center space-y-6">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-zinc-100">
                Targeted Re-Test Completed
              </h2>
              <p className="text-sm text-zinc-400 max-w-md mx-auto">
                Passed weaknesses have been marked resolved in your profile and skill proficiency scores updated.
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={handleRestart}
                className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-xs font-semibold text-zinc-200 hover:bg-zinc-800"
              >
                <RotateCcw className="h-4 w-4" />
                Retest More Weaknesses
              </button>
              <Link
                href="/dashboard/progress"
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 shadow-md shadow-indigo-600/20"
              >
                <GraduationCap className="h-4 w-4" />
                View Skill Progress Dashboard
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
