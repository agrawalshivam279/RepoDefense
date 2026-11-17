"use client";

import React, { useEffect, useState } from "react";
import { AlertCircle, Loader2, RefreshCw, X } from "lucide-react";
import type { MentorExplanationResponse } from "@/types/mentor";
import { explainWeaknessOrTopic, getExplanationForWeakness } from "@/lib/mentorApi";
import { MentorExplanationCard } from "./MentorExplanationCard";

interface MentorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  token?: string | null;
  weaknessId?: string | null;
  topic?: string | null;
  category?: string | null;
  questionPrompt?: string | null;
  candidateResponse?: string | null;
  feedback?: string | null;
  onRetestLaunch?: () => void;
}

export function MentorDrawer({
  isOpen,
  onClose,
  token,
  weaknessId,
  topic,
  category,
  questionPrompt,
  candidateResponse,
  feedback,
  onRetestLaunch,
}: MentorDrawerProps) {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MentorExplanationResponse | null>(null);

  const loadExplanation = async () => {
    if (!token || (!weaknessId && !topic)) return;

    setLoading(true);
    setError(null);

    try {
      if (weaknessId) {
        const res = await getExplanationForWeakness(token, weaknessId);
        setData(res);
      } else if (topic) {
        const res = await explainWeaknessOrTopic(token, {
          category: category || "architecture",
          topic,
          question_prompt: questionPrompt || undefined,
          candidate_response: candidateResponse || undefined,
          feedback: feedback || undefined,
        });
        setData(res);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load mentor content.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadExplanation();
    } else {
      setData(null);
      setError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, weaknessId, topic]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/80 backdrop-blur-sm transition-opacity">
      <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
        <div className="w-screen max-w-4xl bg-slate-900 border-l border-slate-800 p-6 flex flex-col shadow-2xl overflow-y-auto">
          {/* Header Action Bar */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Principal Engineer Mentor Guidance</span>
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              aria-label="Close drawer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1">
            {loading && (
              <div className="flex flex-col items-center justify-center py-24 space-y-4 text-center">
                <Loader2 className="h-10 w-10 animate-spin text-indigo-500" />
                <p className="text-sm font-medium text-slate-300">
                  Synthesizing architectural guidance and drop-in code remediation...
                </p>
                <p className="text-xs text-slate-500">
                  Grounding failure modes in production software design patterns
                </p>
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 p-6 text-center space-y-4">
                <div className="flex items-center justify-center gap-2 text-rose-400 font-semibold text-sm">
                  <AlertCircle className="h-5 w-5 shrink-0" />
                  <span>Unable to Generate Mentor Explanation</span>
                </div>
                <p className="text-xs text-rose-200/90">{error}</p>
                <button
                  type="button"
                  onClick={loadExplanation}
                  className="inline-flex items-center gap-2 rounded-lg bg-slate-800 hover:bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Retry Generation
                </button>
              </div>
            )}

            {!loading && !error && data && (
              <MentorExplanationCard
                explanation={data}
                onRetestRequest={() => {
                  onClose();
                  if (onRetestLaunch) onRetestLaunch();
                }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
