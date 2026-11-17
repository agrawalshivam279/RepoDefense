"use client";

import React, { useRef, useState } from "react";
import {
  AlertCircle, Database, Flame, Gauge, Layers,
  Loader2, Lock, RefreshCw, Search, Sparkles
} from "lucide-react";
import { ChallengeEditor } from "@/components/domain/ChallengeEditor";
import { MiniChallengeCard } from "@/components/domain/MiniChallengeCard";
import { SolutionEvaluationViewer } from "@/components/domain/SolutionEvaluationViewer";
import { generateMiniChallenge, submitChallengeSolution } from "@/lib/challengeApi";
import type {
  ChallengeEvaluationResponse, MiniChallengeDifficulty, MiniChallengeResponse,
} from "@/types/challenge";
import { QUICK_MENTOR_TOPICS, type QuickTopicOption } from "@/types/mentor";

interface MentorChallengeSandboxProps {
  token: string;
  defaultTopic?: string;
  defaultCategory?: string;
  className?: string;
}

const TOPIC_ICONS: Record<QuickTopicOption["iconName"], React.ReactNode> = {
  database: <Database className="h-4 w-4 text-emerald-400" />,
  lock: <Lock className="h-4 w-4 text-rose-400" />,
  flame: <Flame className="h-4 w-4 text-amber-400" />,
  gauge: <Gauge className="h-4 w-4 text-sky-400" />,
  layers: <Layers className="h-4 w-4 text-purple-400" />,
};

export function MentorChallengeSandbox({
  token,
  defaultTopic = "connection_pooling",
  defaultCategory = "scalability",
  className = "",
}: MentorChallengeSandboxProps) {
  const [topic, setTopic] = useState<string>(defaultTopic);
  const [category, setCategory] = useState<string>(defaultCategory);
  const [difficulty, setDifficulty] = useState<MiniChallengeDifficulty>("intermediate");
  const [challenge, setChallenge] = useState<MiniChallengeResponse | null>(null);
  const [evaluation, setEvaluation] = useState<ChallengeEvaluationResponse | null>(null);

  const [generating, setGenerating] = useState<boolean>(false);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [failedOp, setFailedOp] = useState<"generate" | "evaluate" | null>(null);

  const activeEvalReqId = useRef(0);
  const lastSolutionRef = useRef<string>("");
  const lastGenParamsRef = useRef<{
    topic: string;
    category: string;
    difficulty: MiniChallengeDifficulty;
  }>({ topic: defaultTopic, category: defaultCategory, difficulty: "intermediate" });

  const handleGenerate = async (
    tgtTopic = topic,
    tgtCategory = category,
    tgtDifficulty = difficulty
  ) => {
    const trimmed = tgtTopic.trim();
    if (!trimmed) return;
    if (Array.from(trimmed).length > 128) {
      setError("Topic must be 128 characters or fewer.");
      return;
    }

    lastGenParamsRef.current = {
      topic: trimmed,
      category: tgtCategory || "architecture",
      difficulty: tgtDifficulty,
    };
    setGenerating(true);
    setError(null);
    setEvaluation(null);
    setFailedOp(null);
    activeEvalReqId.current++;
    setEvaluating(false);

    try {
      const res = await generateMiniChallenge(token, {
        topic: trimmed,
        category: tgtCategory || "architecture",
        difficulty: tgtDifficulty,
        language: "python",
      });
      setChallenge(res);
      setTopic(trimmed);
      setCategory(tgtCategory);
      setDifficulty(tgtDifficulty);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate challenge.");
      setFailedOp("generate");
    } finally {
      setGenerating(false);
    }
  };

  const handleSubmitSolution = async (solutionCode: string) => {
    if (!challenge || generating || evaluating) return;

    const currentChallengeId = challenge.challenge_id;
    const reqId = ++activeEvalReqId.current;
    lastSolutionRef.current = solutionCode;

    setEvaluating(true);
    setError(null);
    setFailedOp(null);

    try {
      const res = await submitChallengeSolution(token, {
        challenge_id: challenge.challenge_id,
        category: challenge.category,
        topic: challenge.topic,
        scenario: challenge.scenario,
        requirements: challenge.requirements,
        candidate_solution: solutionCode,
        language: challenge.language,
      });

      if (reqId === activeEvalReqId.current && challenge?.challenge_id === currentChallengeId) {
        setEvaluation(res);
      }
    } catch (err: unknown) {
      if (reqId !== activeEvalReqId.current) return;
      setError(err instanceof Error ? err.message : "Failed to evaluate solution.");
      setFailedOp("evaluate");
    } finally {
      if (reqId === activeEvalReqId.current) setEvaluating(false);
    }
  };

  const handleRetry = () => {
    if (failedOp === "evaluate" && lastSolutionRef.current) {
      handleSubmitSolution(lastSolutionRef.current);
    } else {
      const { topic: t, category: c, difficulty: d } = lastGenParamsRef.current;
      handleGenerate(t, c, d);
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Recommended Topics */}
      <section className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          <span>Recommended Architectural Challenge Topics</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {QUICK_MENTOR_TOPICS.map((item) => {
            const isSelected = topic === item.topic && category === item.category;
            return (
              <button
                key={item.topic}
                type="button"
                disabled={generating || evaluating}
                onClick={() => handleGenerate(item.topic, item.category)}
                className={`text-left p-3.5 rounded-xl border transition-all text-xs space-y-1 ${
                  isSelected
                    ? "border-indigo-500/80 bg-indigo-950/40 shadow-lg shadow-indigo-950/50"
                    : "border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900/90"
                } ${generating || evaluating ? "opacity-60 cursor-not-allowed" : ""}`}
              >
                <div className="flex items-center gap-2">
                  {TOPIC_ICONS[item.iconName]}
                  <span className="font-semibold text-slate-200">{item.title}</span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                  {item.description}
                </p>
              </button>
            );
          })}
        </div>
      </section>

      {/* Generation Bar */}
      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleGenerate();
          }}
          className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3"
        >
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              aria-label="Custom challenge topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter architecture topic (e.g. rate_limiting, connection_pooling)..."
              className="w-full rounded-lg border border-slate-800 bg-slate-950/80 pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <select
            aria-label="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="scalability">Scalability</option>
            <option value="concurrency">Concurrency</option>
            <option value="caching">Caching</option>
            <option value="architecture">Architecture</option>
            <option value="security">Security</option>
          </select>

          <select
            aria-label="Difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as MiniChallengeDifficulty)}
            className="rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="foundational">Foundational</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>

          <button
            type="submit"
            disabled={generating || evaluating || !topic.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors shrink-0"
          >
            {generating ? (
              <><Loader2 className="h-3.5 w-3.5 animate-spin" /><span>Synthesizing...</span></>
            ) : (
              <><Sparkles className="h-3.5 w-3.5" /><span>Synthesize Challenge</span></>
            )}
          </button>
        </form>
      </section>

      {/* Error Banner with Precision Retry */}
      {error && (
        <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 p-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
            <span className="text-xs text-rose-200">{error}</span>
          </div>
          <button
            type="button"
            onClick={handleRetry}
            className="inline-flex items-center gap-1 rounded bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:text-white"
          >
            <RefreshCw className="h-3 w-3" />
            <span>{failedOp === "evaluate" ? "Retry Evaluation" : "Retry Generation"}</span>
          </button>
        </div>
      )}

      {/* Challenge Display & Editor */}
      {challenge && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <MiniChallengeCard key={challenge.challenge_id} challenge={challenge} />
          <div className="space-y-6">
            <ChallengeEditor
              key={challenge.challenge_id}
              challengeId={challenge.challenge_id}
              starterCode={challenge.starter_code}
              language={challenge.language}
              isSubmitting={evaluating}
              onSubmit={handleSubmitSolution}
            />
            {evaluation && (
              <SolutionEvaluationViewer
                evaluation={evaluation}
                onRetry={() => setEvaluation(null)}
                onNextChallenge={() => handleGenerate()}
              />
            )}
          </div>
        </div>
      )}

      {!challenge && !generating && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-12 text-center space-y-3">
          <Sparkles className="h-8 w-8 text-indigo-400 mx-auto" />
          <h4 className="text-sm font-semibold text-white">No Active Mini-Challenge</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Select a recommended topic or enter a custom architectural concept above to generate a hands-on refactoring challenge.
          </p>
        </div>
      )}
    </div>
  );
}
