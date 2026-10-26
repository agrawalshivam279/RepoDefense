"use client";

import { useEffect, useState } from "react";
import { AlertCircle, FolderGit2, Loader2, X } from "lucide-react";
import { supabase } from "@/lib/supabase";
import type { Project } from "@/types/project";

interface AddProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (project: Project) => void;
}

const GITHUB_URL_REGEX =
  /^https?:\/\/(?:www\.)?github\.com\/([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:\.git)?\/?$/;

export function AddProjectModal({
  isOpen,
  onClose,
  onProjectCreated,
}: AddProjectModalProps) {
  const [githubUrl, setGithubUrl] = useState("");
  const [name, setName] = useState("");
  const [branch, setBranch] = useState("main");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-derive project name from repo slug if custom name has not been manually touched
  useEffect(() => {
    const match = githubUrl.trim().match(GITHUB_URL_REGEX);
    if (match && !name) {
      const repo = match[2].endsWith(".git") ? match[2].slice(0, -4) : match[2];
      setName(repo);
    }
  }, [githubUrl, name]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedUrl = githubUrl.trim();
    if (!GITHUB_URL_REGEX.test(trimmedUrl)) {
      setError("Please provide a valid GitHub repository URL (e.g., https://github.com/owner/repo).");
      return;
    }

    setLoading(true);

    try {
      // 1. Get Supabase JWT session token
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setError("Your session has expired. Please sign in again.");
        setLoading(false);
        return;
      }

      // 2. Send creation request to FastAPI backend
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/v1/projects`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          github_url: trimmedUrl,
          name: name.trim() || undefined,
          default_branch: branch.trim() || "main",
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        if (response.status === 409) {
          setError("This repository is already registered under your account.");
        } else if (errorData?.detail) {
          setError(
            typeof errorData.detail === "string"
              ? errorData.detail
              : JSON.stringify(errorData.detail)
          );
        } else {
          setError(`Request failed with status ${response.status}`);
        }
        setLoading(false);
        return;
      }

      const createdProject: Project = await response.json();
      onProjectCreated(createdProject);
      setGithubUrl("");
      setName("");
      setBranch("main");
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to connect to backend service");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 text-slate-100 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-500 hover:text-slate-300 p-1 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <FolderGit2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Add GitHub Repository</h2>
            <p className="text-xs text-slate-400">
              Register a codebase for architectural stress-testing
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-5 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3.5 flex items-start space-x-3 text-rose-300">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400 mt-0.5" />
            <div className="text-xs font-medium leading-relaxed">{error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="modal-github-url"
              className="block text-xs font-medium text-slate-300 mb-1.5"
            >
              GitHub Repository URL <span className="text-rose-400">*</span>
            </label>
            <input
              id="modal-github-url"
              type="url"
              required
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/fastapi/fastapi"
              className="block w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm placeholder-slate-500 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all font-mono text-xs"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="modal-name"
                className="block text-xs font-medium text-slate-300 mb-1.5"
              >
                Project Name
              </label>
              <input
                id="modal-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Derived from repo"
                className="block w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm placeholder-slate-500 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
              />
            </div>
            <div>
              <label
                htmlFor="modal-branch"
                className="block text-xs font-medium text-slate-300 mb-1.5"
              >
                Default Branch
              </label>
              <input
                id="modal-branch"
                type="text"
                required
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="main"
                className="block w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm placeholder-slate-500 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all font-mono text-xs"
              />
            </div>
          </div>

          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white border border-slate-800 hover:border-slate-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-950 bg-emerald-400 hover:bg-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50 transition-all flex items-center gap-1.5 shadow-sm"
            >
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>Register Repository</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
