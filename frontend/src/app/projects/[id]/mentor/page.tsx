"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  Database,
  Flame,
  Gauge,
  GraduationCap,
  Layers,
  Loader2,
  Lock,
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react";
import { MentorExplanationCard } from "@/components/domain/MentorExplanationCard";
import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { explainWeaknessOrTopic } from "@/lib/mentorApi";
import { getProjectOverview } from "@/lib/projectApi";
import { supabase } from "@/lib/supabase";
import {
  type MentorExplanationResponse,
  QUICK_MENTOR_TOPICS,
  type QuickTopicOption,
} from "@/types/mentor";
import type { ProjectOverviewResponse } from "@/types/project";

export default function MentorModePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const projectId = typeof params?.id === "string" ? params.id : "";

  const [overview, setOverview] = useState<ProjectOverviewResponse | null>(null);
  const [topicInput, setTopicInput] = useState<string>("connection_pooling");
  const [categoryInput, setCategoryInput] = useState<string>("scalability");
  const [explanation, setExplanation] = useState<MentorExplanationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
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

  const loadProjectMeta = useCallback(async () => {
    if (!projectId) return;
    try {
      const token = await getAuthToken();
      if (!token || !isMountedRef.current) return;
      const res = await getProjectOverview(projectId, token);
      if (isMountedRef.current) setOverview(res);
    } catch {
      // Non-blocking project header failure
    }
  }, [projectId, getAuthToken]);

  const handleSynthesize = useCallback(
    async (targetTopic: string, targetCategory: string) => {
      if (!targetTopic.trim()) return;
      setLoading(true);
      setError(null);

      try {
        const token = await getAuthToken();
        if (!token || !isMountedRef.current) return;

        const res = await explainWeaknessOrTopic(token, {
          topic: targetTopic.trim(),
          category: targetCategory || "architecture",
          language: "python",
        });

        if (isMountedRef.current) {
          setExplanation(res);
          setTopicInput(targetTopic);
          setCategoryInput(targetCategory);
        }
      } catch (err: unknown) {
        if (!isMountedRef.current) return;
        const msg = err instanceof Error ? err.message : "Failed to synthesize mentor content.";
        setError(msg);
      } finally {
        if (isMountedRef.current) setLoading(false);
      }
    },
    [getAuthToken]
  );

  useEffect(() => {
    loadProjectMeta();
    handleSynthesize("connection_pooling", "scalability");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const renderTopicIcon = (iconName: QuickTopicOption["iconName"]) => {
    switch (iconName) {
      case "database": return <Database className="h-4 w-4 text-emerald-400" />;
      case "lock": return <Lock className="h-4 w-4 text-rose-400" />;
      case "flame": return <Flame className="h-4 w-4 text-amber-400" />;
      case "gauge": return <Gauge className="h-4 w-4 text-sky-400" />;
      default: return <Layers className="h-4 w-4 text-purple-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <ProjectNavHeader
        projectId={projectId}
        projectName={overview?.name || overview?.summary?.title || "Repository"}
        githubUrl={overview?.github_url}
        defaultBranch={overview?.default_branch}
        commitHash={overview?.commit_hash}
        activeTab="mentor"
        subtitle="Principal Engineer Mentor Mode — Architectural Teaching & Drop-in Remediation"
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="relative overflow-hidden rounded-2xl border border-indigo-900/40 bg-gradient-to-r from-indigo-950/40 via-slate-900/60 to-purple-950/40 p-6 md:p-8 shadow-xl">
          <div className="relative z-10 max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-400 border border-indigo-500/20">
              <GraduationCap className="h-3.5 w-3.5" />
              Socratic Mentor Mode
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              Architectural Mastery & Code Remediation
            </h1>
            <p className="text-sm text-slate-300 leading-relaxed">
              Step away from high-pressure oral cross-examinations. Mentor Mode analyzes root-cause
              failure modes, teaches production software design principles, and delivers drop-in
              Before/After remediations.
            </p>
          </div>
        </div>

        {/* Quick Launch Chips */}
        <div className="space-y-3">
          <h2 className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
            Canonical Failure Modes & Topics
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {QUICK_MENTOR_TOPICS.map((t) => {
              const isSelected = topicInput === t.topic;
              return (
                <button
                  key={t.topic}
                  type="button"
                  onClick={() => handleSynthesize(t.topic, t.category)}
                  className={`text-left rounded-xl p-3.5 border transition-all flex flex-col justify-between space-y-2 ${
                    isSelected
                      ? "border-indigo-500/70 bg-indigo-950/30 shadow-md ring-1 ring-indigo-500/30"
                      : "border-slate-800 bg-slate-900/50 hover:bg-slate-900 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs text-white">{t.title}</span>
                    {renderTopicIcon(t.iconName)}
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2">{t.description}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Custom Topic Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSynthesize(topicInput, categoryInput);
          }}
          className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-3"
        >
          <div className="flex-1 min-w-[200px] flex items-center gap-2 bg-slate-950 rounded-lg px-3 py-2 border border-slate-800">
            <Search className="h-4 w-4 text-slate-400 shrink-0" />
            <input
              type="text"
              value={topicInput}
              onChange={(e) => setTopicInput(e.target.value)}
              placeholder="Enter architectural topic or mechanism (e.g. distributed_locking)"
              className="bg-transparent text-xs text-slate-100 placeholder-slate-500 w-full focus:outline-none"
            />
          </div>

          <select
            value={categoryInput}
            onChange={(e) => setCategoryInput(e.target.value)}
            className="rounded-lg bg-slate-950 border border-slate-800 px-3 py-2 text-xs font-mono text-slate-300 focus:outline-none"
          >
            <option value="scalability">Scalability</option>
            <option value="concurrency">Concurrency</option>
            <option value="security">Security</option>
            <option value="reliability">Reliability</option>
            <option value="architecture">Architecture</option>
          </select>

          <button
            type="submit"
            disabled={loading || !topicInput.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs px-4 py-2 transition-colors shadow-sm"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            <span>Synthesize Guidance</span>
          </button>
        </form>

        {/* Content Display Area */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 space-y-3 rounded-2xl border border-slate-800/80 bg-slate-900/30 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
            <p className="text-sm font-semibold text-slate-200">
              Generating Principal Mentor Teaching Content...
            </p>
            <p className="text-xs text-slate-400">
              Synthesizing root cause analysis and drop-in code remediation
            </p>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 p-5 flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-rose-300 uppercase tracking-wide">
                  Synthesis Error
                </h4>
                <p className="text-xs text-rose-200/90 mt-0.5">{error}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => handleSynthesize(topicInput, categoryInput)}
              className="inline-flex items-center gap-1.5 rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:text-white"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        )}

        {!loading && explanation && (
          <MentorExplanationCard
            explanation={explanation}
            onRetestRequest={() => router.push(`/projects/${projectId}`)}
          />
        )}
      </main>
    </div>
  );
}
