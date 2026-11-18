"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  Award,
  CheckCircle2,
  Compass,
  Flame,
  Loader2,
  RefreshCw,
  Target,
  TrendingUp,
} from "lucide-react";
import { LearningHubBreadcrumbs } from "@/components/domain/LearningHubBreadcrumbs";
import { LearningNavGroup } from "@/components/domain/LearningNavGroup";
import { CategoryMasteryGrid } from "@/components/domain/CategoryMasteryGrid";
import { FocusTopicsPanel } from "@/components/domain/FocusTopicsPanel";
import { LearningTimelineChart } from "@/components/domain/LearningTimelineChart";
import { WeaknessVelocityCard } from "@/components/domain/WeaknessVelocityCard";
import { fetchProgressOverview, fetchProgressTimeline } from "@/lib/progressApi";
import { supabase } from "@/lib/supabase";
import type {
  ProficiencyTrendPoint,
  UserProgressOverviewResponse,
} from "@/types/progress";

export default function ProgressDashboardPage() {
  const [overview, setOverview] = useState<UserProgressOverviewResponse | null>(null);
  const [timeline, setTimeline] = useState<ProficiencyTrendPoint[]>([]);
  const [selectedDays, setSelectedDays] = useState<number>(30);
  const [loading, setLoading] = useState(true);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timelineError, setTimelineError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const timelineAbortRef = useRef<AbortController | null>(null);
  const selectedDaysRef = useRef(selectedDays);
  selectedDaysRef.current = selectedDays;

  const loadData = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);
    setTimelineError(null);

    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        window.location.href = "/login";
        return;
      }

      const [ovData, tlData] = await Promise.all([
        fetchProgressOverview(session.access_token, controller.signal),
        fetchProgressTimeline(session.access_token, selectedDaysRef.current, controller.signal),
      ]);

      if (!controller.signal.aborted) {
        setOverview(ovData);
        setTimeline(tlData);
      }
    } catch (err: unknown) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Failed to load progress telemetry");
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, []);

  const handleDaysChange = async (days: number) => {
    if (timelineAbortRef.current) {
      timelineAbortRef.current.abort();
    }
    const controller = new AbortController();
    timelineAbortRef.current = controller;

    setSelectedDays(days);
    setTimelineLoading(true);
    setTimelineError(null);

    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;

      const tlData = await fetchProgressTimeline(session.access_token, days, controller.signal);
      if (!controller.signal.aborted) {
        setTimeline(tlData);
      }
    } catch (err: unknown) {
      if (!controller.signal.aborted) {
        setTimelineError(err instanceof Error ? err.message : "Failed to load timeline data");
      }
    } finally {
      if (timelineAbortRef.current === controller) {
        setTimelineLoading(false);
      }
    }
  };

  useEffect(() => {
    loadData();
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
      if (timelineAbortRef.current) timelineAbortRef.current.abort();
    };
  }, [loadData]);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-8">
        {/* Header Breadcrumbs & Segmented Nav */}
        <div className="space-y-4 border-b border-border/60 pb-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <LearningHubBreadcrumbs
              items={[
                { label: "Learning Hub", href: "/dashboard/learning", icon: Compass },
                { label: "Skill Progression", isCurrent: true },
              ]}
            />
            {overview && overview.learning_streak_days > 0 && (
              <div className="flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-500">
                <Flame className="h-3.5 w-3.5 fill-amber-500" />
                <span>{overview.learning_streak_days} Day Streak</span>
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                Skill & Improvement Telemetry
              </h1>
              <p className="text-sm text-muted-foreground">
                Track architectural proficiency growth, remediation velocity, and mastery trajectory
              </p>
            </div>

            <div className="flex items-center gap-3">
              <LearningNavGroup activeModule="progress" />
              <button
                onClick={loadData}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-500">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}

        {overview && (
          <>
            {/* Quick Metrics */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="rounded-xl border border-border/50 bg-card p-5 shadow-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium uppercase tracking-wider">Proficiency</span>
                  <TrendingUp className="h-4 w-4 text-primary" />
                </div>
                <div className="mt-2 text-2xl font-bold text-foreground">
                  {overview.overall_proficiency.toFixed(1)}%
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Mean across technical skills</p>
              </div>

              <div className="rounded-xl border border-border/50 bg-card p-5 shadow-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium uppercase tracking-wider">Mastered Skills</span>
                  <Award className="h-4 w-4 text-emerald-500" />
                </div>
                <div className="mt-2 text-2xl font-bold text-foreground">
                  {overview.mastered_skills_count}
                  <span className="text-sm font-normal text-muted-foreground">/{overview.active_skills_count}</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Skills rated &ge; 80%</p>
              </div>

              <div className="rounded-xl border border-border/50 bg-card p-5 shadow-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium uppercase tracking-wider">Pass Rate</span>
                  <CheckCircle2 className="h-4 w-4 text-blue-500" />
                </div>
                <div className="mt-2 text-2xl font-bold text-foreground">
                  {overview.overall_pass_rate_pct.toFixed(0)}%
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {overview.total_passed} of {overview.total_evaluations} evaluations
                </p>
              </div>

              <div className="rounded-xl border border-border/50 bg-card p-5 shadow-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium uppercase tracking-wider">Remediated</span>
                  <Flame className="h-4 w-4 text-amber-500" />
                </div>
                <div className="mt-2 text-2xl font-bold text-foreground">
                  {overview.weakness_velocity.total_resolved}
                  <span className="text-sm font-normal text-muted-foreground">
                    /{overview.weakness_velocity.total_identified}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {overview.weakness_velocity.resolution_rate_pct.toFixed(0)}% resolved
                </p>
              </div>
            </div>

            {/* Interactive Timeline & Remediation Velocity */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <LearningTimelineChart
                  timeline={timeline}
                  selectedDays={selectedDays}
                  onDaysChange={handleDaysChange}
                  isLoading={timelineLoading}
                  errorMessage={timelineError}
                  onRetry={() => handleDaysChange(selectedDays)}
                />
              </div>
              <div>
                <WeaknessVelocityCard velocity={overview.weakness_velocity} />
              </div>
            </div>

            {/* Category Mastery Breakdown */}
            <CategoryMasteryGrid categories={overview.category_deltas} />

            {/* Focus & Recommendations */}
            <FocusTopicsPanel
              topImproved={overview.top_improved_topics}
              needsFocus={overview.needs_focus_topics}
            />
          </>
        )}
      </div>
    </div>
  );
}
