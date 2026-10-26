"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ExternalLink,
  GitBranch,
  Loader2,
  Shield,
  Trash2,
} from "lucide-react";
import type { Project } from "@/types/project";

interface ProjectCardProps {
  project: Project;
  onDelete: (id: string) => Promise<void>;
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (confirm(`Are you sure you want to delete "${project.name}"? This action cannot be undone.`)) {
      setDeleting(true);
      try {
        await onDelete(project.id);
      } finally {
        setDeleting(false);
      }
    }
  };

  const getStatusBadge = (status: Project["status"]) => {
    switch (status) {
      case "analyzed":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            ● Analyzed
          </span>
        );
      case "analyzing":
      case "cloning":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Loader2 className="w-2.5 h-2.5 mr-1 animate-spin" />
            Processing
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Pending Ingestion
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900/60 backdrop-blur-sm border border-slate-800 hover:border-slate-700/80 rounded-xl p-5 flex flex-col justify-between transition-all group shadow-sm hover:shadow-md">
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <Shield className="w-4 h-4 text-emerald-400" />
            </div>
            <h3 className="text-base font-bold text-white tracking-tight truncate group-hover:text-emerald-400 transition-colors">
              {project.name}
            </h3>
          </div>
          {getStatusBadge(project.status)}
        </div>

        <a
          href={project.github_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors truncate max-w-full"
        >
          <span className="truncate">{project.github_url.replace("https://github.com/", "")}</span>
          <ExternalLink className="w-3 h-3 ml-1 flex-shrink-0 text-slate-500" />
        </a>

        <div className="flex items-center gap-3 pt-1 text-xs text-slate-400">
          <div className="flex items-center gap-1 font-mono">
            <GitBranch className="w-3.5 h-3.5 text-slate-500" />
            <span>{project.default_branch}</span>
          </div>
          <span>•</span>
          <span className="text-slate-500">
            Added {new Date(project.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 pt-5 mt-4 border-t border-slate-800/80">
        <Link
          href={`/interview/${project.id}`}
          className="flex-1 text-center py-2 px-3 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-semibold text-xs transition-colors"
        >
          Start Defense
        </Link>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all disabled:opacity-50"
          title="Delete repository"
        >
          {deleting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  );
}
