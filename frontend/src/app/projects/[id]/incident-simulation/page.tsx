"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertCircle, Flame, Loader2 } from "lucide-react";

import { IncidentWarRoom } from "@/components/domain/IncidentWarRoom";
import { ProjectNavHeader } from "@/components/domain/ProjectNavHeader";
import { getProjectOverview } from "@/lib/projectApi";
import { supabase } from "@/lib/supabase";
import type { ProjectOverviewResponse } from "@/types/project";

export default function IncidentSimulationPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [project, setProject] = useState<ProjectOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getSessionToken = async () => {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      router.push("/login");
      return null;
    }
    return session.access_token;
  };

  const fetchProjectInfo = useCallback(async () => {
    if (!projectId) return;
    try {
      const token = await getSessionToken();
      if (token) {
        const data = await getProjectOverview(projectId, token);
        setProject(data);
      }
    } catch {
      // Graceful fallback if project overview endpoint fails
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchProjectInfo();
  }, [fetchProjectInfo]);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-rose-500" />
        <p className="text-sm font-mono text-zinc-400">Loading Incident War Room...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 p-8 max-w-5xl mx-auto">
        <div className="rounded-xl border border-rose-900/60 bg-rose-950/20 p-6 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-rose-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-1">
            <h3 className="font-semibold text-rose-200">Unable to load project</h3>
            <p className="text-sm text-rose-300/80">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <ProjectNavHeader
          projectId={projectId}
          projectName={project?.name || "Repository"}
          githubUrl={project?.github_url}
          defaultBranch={project?.default_branch}
          commitHash={project?.commit_hash}
          activeTab="incident-simulation"
          subtitle="Simulate and defend high-impact production outages grounded in codebase architecture"
        />

        <IncidentWarRoom projectId={projectId} />
      </div>
    </div>
  );
}
