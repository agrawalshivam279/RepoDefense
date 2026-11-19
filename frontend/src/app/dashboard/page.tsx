"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle, ArrowLeft, Compass, FolderGit2, HelpCircle,
  Loader2, Plus, RefreshCw, Target, TrendingUp
} from "lucide-react";
import { AddProjectModal } from "@/components/domain/AddProjectModal";
import { EmptyState } from "@/components/domain/EmptyState";
import { OnboardingTourModal } from "@/components/domain/OnboardingTourModal";
import { ProjectCard } from "@/components/domain/ProjectCard";
import { ContextTooltip } from "@/components/ui/ContextTooltip";
import { useOnboardingTour } from "@/hooks/useOnboardingTour";
import { DASHBOARD_TOUR_ID, DASHBOARD_TOUR_STEPS } from "@/lib/onboarding";
import { supabase } from "@/lib/supabase";
import type { Project } from "@/types/project";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [initialInstallationId, setInitialInstallationId] = useState<number | null>(null);

  const tour = useOnboardingTour({
    tourId: DASHBOARD_TOUR_ID,
    steps: DASHBOARD_TOUR_STEPS,
  });

  // Auto-detect GitHub App post-installation callback parameters
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const rawInstId = params.get("installation_id")?.trim();
      if (rawInstId && /^\d{1,18}$/.test(rawInstId)) {
        const parsed = Number(rawInstId);
        if (Number.isSafeInteger(parsed) && parsed > 0) {
          setInitialInstallationId(parsed);
          setIsModalOpen(true);
        }
      }
    }
  }, []);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        window.location.href = "/login";
        return;
      }
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/v1/projects`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!response.ok) throw new Error(`Failed to fetch projects (status ${response.status})`);
      const data: Project[] = await response.json();
      setProjects(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleDeleteProject = async (id: string) => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      window.location.href = "/login";
      return;
    }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(`${apiUrl}/api/v1/projects/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${session.access_token}` },
    });
    if (!response.ok) {
      alert("Failed to delete repository. Please try again.");
      return;
    }
    setProjects((prev) => prev.filter((p) => p.id !== id));
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8 text-slate-100">
      {/* Header Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div className="space-y-1">
          <Link
            href="/"
            className="inline-flex items-center text-xs font-mono text-slate-400 hover:text-emerald-400 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1" />
            Back to Overview
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <span>Codebase Repositories</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
              {projects.length}
            </span>
          </h1>
          <p className="text-xs text-slate-400">
            Registered codebases prepared for static AST parsing and architectural defense
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap" data-tour="quick-actions">
          <ContextTooltip content="Explore personalized mentorship and weakness remediations" placement="bottom">
            <Link
              href="/dashboard/learning"
              data-tour="learning-hub"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 font-semibold text-xs transition-colors shadow-sm"
            >
              <Compass className="w-4 h-4" />
              <span>Learning Hub</span>
            </Link>
          </ContextTooltip>

          <ContextTooltip content="Track moving average mastery and velocity across topics" placement="bottom">
            <Link
              href="/dashboard/progress"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-emerald-400 font-semibold text-xs transition-colors shadow-sm"
            >
              <TrendingUp className="w-4 h-4" />
              <span>Skill Progress</span>
            </Link>
          </ContextTooltip>

          <ContextTooltip content="Benchmark skills against Senior / Staff Engineer standards" placement="bottom">
            <Link
              href="/dashboard/skill-gap"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-indigo-400 font-semibold text-xs transition-colors shadow-sm"
            >
              <Target className="w-4 h-4" />
              <span>Skill Gaps</span>
            </Link>
          </ContextTooltip>

          <ContextTooltip content="Take interactive feature walkthrough tour" placement="bottom">
            <button
              type="button"
              onClick={() => tour.startTour(0)}
              className="p-2 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-900/40 text-amber-400 hover:text-amber-300 transition-colors"
              aria-label="Start onboarding tour"
            >
              <HelpCircle className="w-4 h-4" />
            </button>
          </ContextTooltip>

          <ContextTooltip content="Refresh registered repository list" placement="bottom">
            <button
              onClick={fetchProjects}
              disabled={loading}
              className="p-2 rounded-lg border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-50"
              aria-label="Refresh repository list"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </ContextTooltip>

          <button
            onClick={() => setIsModalOpen(true)}
            data-tour="add-repo"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-400 hover:bg-emerald-300 text-slate-950 font-semibold text-xs transition-colors shadow-sm cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add Repository</span>
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-lg bg-rose-500/10 border border-rose-500/30 p-4 flex items-center justify-between text-rose-300">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span className="text-xs font-medium">{error}</span>
          </div>
          <button onClick={fetchProjects} className="text-xs font-semibold underline hover:text-rose-200">
            Retry
          </button>
        </div>
      )}

      {/* Content Area */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 rounded-xl bg-slate-900/40 border border-slate-800 animate-pulse p-6" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          icon={FolderGit2}
          title="No repositories registered"
          description="Add your public or private GitHub repository to begin deterministic AST indexing and architectural defense."
          primaryAction={{
            label: "Register First Repository",
            icon: Plus,
            onClick: () => setIsModalOpen(true),
          }}
          secondaryAction={{
            label: "Take Feature Tour",
            icon: Compass,
            onClick: () => tour.startTour(0),
          }}
          tips={[
            "Public repositories need only a valid GitHub URL (e.g., https://github.com/fastapi/fastapi).",
            "Private repositories require 1-click installation of our dedicated GitHub App.",
            "We rely 100% on static analysis — your code is never executed or evaluated in a container.",
          ]}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-tour="project-list">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onDelete={handleDeleteProject}
            />
          ))}
        </div>
      )}

      {/* Add Project Modal */}
      <AddProjectModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setInitialInstallationId(null);
        }}
        onProjectCreated={(newProject) => setProjects((prev) => [newProject, ...prev])}
        initialInstallationId={initialInstallationId}
      />

      {/* Onboarding Tour Modal */}
      <OnboardingTourModal
        isActive={tour.isActive}
        currentStep={tour.currentStep}
        currentStepIndex={tour.currentStepIndex}
        totalSteps={tour.totalSteps}
        targetRect={tour.targetRect}
        onNext={tour.nextStep}
        onPrev={tour.prevStep}
        onSkip={tour.skipTour}
        onFinish={tour.finishTour}
      />
    </div>
  );
}
