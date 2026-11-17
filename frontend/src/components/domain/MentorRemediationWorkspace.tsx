"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Database,
  Flame,
  Gauge,
  Layers,
  Loader2,
  Lock,
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react";
import { MentorExplanationCard } from "@/components/domain/MentorExplanationCard";
import { explainWeaknessOrTopic } from "@/lib/mentorApi";
import {
  type MentorExplanationResponse,
  QUICK_MENTOR_TOPICS,
  type QuickTopicOption,
} from "@/types/mentor";

interface MentorRemediationWorkspaceProps {
  token: string;
  projectId: string;
  defaultTopic?: string;
  defaultCategory?: string;
  className?: string;
}

export function MentorRemediationWorkspace({
  token,
  projectId,
  defaultTopic = "connection_pooling",
  defaultCategory = "scalability",
  className = "",
}: MentorRemediationWorkspaceProps) {
  const [topicInput, setTopicInput] = useState<string>(defaultTopic);
  const [categoryInput, setCategoryInput] = useState<string>(defaultCategory);
  const [explanation, setExplanation] = useState<MentorExplanationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const activeRequestIdRef = useRef(0);
  const tokenRef = useRef(token);
  tokenRef.current = token;

  const lastAttemptedRef = useRef<{ topic: string; category: string }>({
    topic: defaultTopic,
    category: defaultCategory,
  });

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
        const res = await explainWeaknessOrTopic(tokenRef.current, {
          topic: trimmedTopic,
          category: targetCategory || "architecture",
          language: "python",
        });

        if (reqId === activeRequestIdRef.current) {
          setExplanation(res);
          setTopicInput(trimmedTopic);
          setCategoryInput(targetCategory);
        }
      } catch (err: unknown) {
        if (reqId !== activeRequestIdRef.current) return;
        const msg = err instanceof Error ? err.message : "Failed to synthesize mentor content.";
        setError(msg);
      } finally {
        if (reqId === activeRequestIdRef.current) {
          setLoading(false);
        }
      }
    },
    []
  );

  useEffect(() => {
    handleSynthesize(defaultTopic, defaultCategory);
    return () => {
      // Invalidate active request on cleanup or parameter change
      activeRequestIdRef.current++;
    };
  }, [projectId, defaultTopic, defaultCategory, handleSynthesize]);

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
    <div className={`space-y-6 ${className}`}>
      {/* Recommended Topics */}
      <section className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          <span>Core Architectural Remediation Topics</span>
        </h3>
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

      {/* Search Input Bar */}
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

      {/* Loading */}
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

      {/* Error */}
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

      {/* Mentor Content Card */}
      {!loading && explanation && (
        <MentorExplanationCard
          explanation={explanation}
          onRetestRequest={() => window.location.assign(`/projects/${projectId}`)}
        />
      )}
    </div>
  );
}
