"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  BookOpen,
  Code2,
  GraduationCap,
  Loader2,
} from "lucide-react";
import { MentorChallengeSandbox } from "@/components/domain/MentorChallengeSandbox";
import { MentorRemediationWorkspace } from "@/components/domain/MentorRemediationWorkspace";
import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { getProjectOverview } from "@/lib/projectApi";
import { supabase } from "@/lib/supabase";
import type { ProjectOverviewResponse } from "@/types/project";

type MentorActiveTab = "remediation" | "challenges";

export default function MentorModePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const projectId = typeof params?.id === "string" ? params.id : "";

  const [activeTab, setActiveTab] = useState<MentorActiveTab>("remediation");
  const [token, setToken] = useState<string | null>(null);
  const [overview, setOverview] = useState<ProjectOverviewResponse | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(true);

  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const loadAuthAndProject = useCallback(async () => {
    const { data } = await supabase.auth.getSession();
    const sessionToken = data.session?.access_token;
    if (!sessionToken) {
      router.replace("/login");
      return;
    }
    if (!isMountedRef.current) return;
    setToken(sessionToken);
    setAuthLoading(false);

    if (projectId) {
      try {
        const meta = await getProjectOverview(projectId, sessionToken);
        if (isMountedRef.current) setOverview(meta);
      } catch {
        // Non-blocking project header metadata failure
      }
    }
  }, [projectId, router]);

  useEffect(() => {
    loadAuthAndProject();
  }, [loadAuthAndProject]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <ProjectNavHeader
        projectId={projectId}
        projectName={overview?.name || overview?.summary?.title || "Repository"}
        activeTab="mentor"
      />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Page Header */}
        <header className="rounded-2xl border border-indigo-900/40 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-900/60 p-6 md:p-8 backdrop-blur-sm flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-indigo-500/10 p-2.5 border border-indigo-500/20 text-indigo-400">
              <GraduationCap className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                  Learning Loop &bull; Milestones 4.2 & 4.3
                </span>
                <span className="rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-[10px] font-medium text-indigo-300 border border-indigo-500/20">
                  Constructive Principal
                </span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white mt-0.5">
                Mentor Mode: Architectural Remediation & Mini-Challenges
              </h1>
              <p className="text-sm text-slate-400 mt-1 max-w-3xl">
                Close architectural blind spots discovered during defense simulations. Learn from Principal Engineer root cause walkthroughs, then solve interactive code challenges to reinforce proficiency.
              </p>
            </div>
          </div>
        </header>

        {/* Sub-Tabs Switcher */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <button
            type="button"
            onClick={() => setActiveTab("remediation")}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === "remediation"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-950/50"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <BookOpen className="h-4 w-4" />
            <span>Remediation Guides & Diffs</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("challenges")}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === "challenges"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-950/50"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <Code2 className="h-4 w-4" />
            <span>Interactive Mini-Challenges</span>
          </button>
        </div>

        {/* Active Content */}
        {authLoading || !token ? (
          <div className="flex flex-col items-center justify-center py-24 space-y-3 rounded-2xl border border-slate-800 bg-slate-900/20 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
            <p className="text-xs text-slate-400">Authenticating session...</p>
          </div>
        ) : activeTab === "remediation" ? (
          <MentorRemediationWorkspace
            token={token}
            projectId={projectId}
          />
        ) : (
          <MentorChallengeSandbox
            token={token}
          />
        )}
      </main>
    </div>
  );
}
