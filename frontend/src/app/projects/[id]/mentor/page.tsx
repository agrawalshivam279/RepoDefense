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
  const activeRequestIdRef = useRef(0);
  const lastAttemptedRef = useRef<{ topic: string; category: string }>({
    topic: "connection_pooling",
    category: "scalability",
  });

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
      const trimmedTopic = targetTopic.trim();
      if (!trimmedTopic) return;

      if (Array.from(trimmedTopic).length > 128) {
        setError("Topic must be 128 characters or fewer.");
        return;
      }

      lastAttemptedRef.current = { topic: trimmedTopic, category: targetCategory };
      const reqId = ++activeRequestIdRef.current;
      setLoading(true);
      setError(null);

      try {
        const token = await getAuthToken();
        if (!token || !isMountedRef.current || reqId !== activeRequestIdRef.current) return;

        const res = await explainWeaknessOrTopic(token, {
          topic: trimmedTopic,
          category: targetCategory || "architecture",
          language: "python",
        });

        if (isMountedRef.current && reqId === activeRequestIdRef.current) {
          setExplanation(res);
          setTopicInput(trimmedTopic);
          setCategoryInput(targetCategory);
        }
      } catch (err: unknown) {
        if (!isMountedRef.current || reqId !== activeRequestIdRef.current) return;
        const msg = err instanceof Error ? err.message : "Failed to synthesize mentor content.";
        setError(msg);
      } finally {
        if (isMountedRef.current && reqId === activeRequestIdRef.current) {
          setLoading(false);
        }
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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <ProjectNavHeader
        projectId={projectId}
        projectName={overview?.name || overview?.summary?.title || "Repository"}
        activeTab="mentor"
      />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <header className="rounded-2xl border border-indigo-900/40 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-900/60 p-6 md:p-8 backdrop-blur-sm flex items-center gap-3">
          <div className="rounded-xl bg-indigo-500/10 p-2.5 border border-indigo-500/20 text-indigo-400">
            <GraduationCap className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                Learning Loop &bull; Milestone 4.2
              </span>
              <span className="rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-[10px] font-medium text-indigo-300 border border-indigo-500/20">
                Constructive Principal
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white mt-0.5">
              Mentor Mode: Architectural Remediation
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">
              Bridge identified technical blind spots. Instead of scoring, our Principal Engineer persona walks through root cause failure modes, production principles, and drop-in code fixes.
            </p>
          </div>
        </header>

        <section className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-400" />
            <span>Core Architectural Remediation Topics</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {QUICK_MENTOR_TOPICS.map((topic) => {
              const isSelected = topicInput === topic.topic && categoryInput === topic.category;
              return (
                <button
                  key={topic.topic}
                  type="button"
                  disabled={loading}
                  onClick={() => handleSynthesize(topic.topic, topic.category)}
                  className={`text-left p-3.5 rounded-xl border transition-all text-xs space-y-1.5 ${
                    isSelected
                      ? "border-indigo-500/80 bg-indigo-950/40 shadow-lg shadow-indigo-950/50"
                      : "border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900/90"
                  } ${loading ? "opacity-60 cursor-not-allowed" : ""}`}
                >
                  <div className="flex items-center gap-2">
                    {renderTopicIcon(topic.iconName)}
                    <span className="font-semibold text-slate-200">{topic.title}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                    {topic.description}
                  </p>
                </button>
              );
            })}
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSynthesize(topicInput, categoryInput);
            }}
            className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3"
          >
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
              <input
                type="text"
                aria-label="Topic"
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                placeholder="Request guidance on any architecture topic or weakness..."
                className="w-full rounded-lg border border-slate-800 bg-slate-950/80 pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <select
              aria-label="Category"
              value={categoryInput}
              onChange={(e) => setCategoryInput(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="scalability">Scalability</option>
              <option value="concurrency">Concurrency</option>
              <option value="caching">Caching</option>
              <option value="architecture">Architecture</option>
              <option value="security">Security</option>
              <option value="data_modeling">Data Modeling</option>
            </select>
            <button
              type="submit"
              disabled={loading || !topicInput.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors shrink-0"
            >
              {loading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Synthesizing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Ask Mentor</span>
                </>
              )}
            </button>
          </form>
        </section>

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
              onClick={() => handleSynthesize(lastAttemptedRef.current.topic, lastAttemptedRef.current.category)}
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
