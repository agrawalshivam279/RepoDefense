"use client";

import { useEffect, useState } from "react";
import { AlertCircle, FolderGit2, Loader2, Lock, X } from "lucide-react";
import { GitHubAppRepoSelector } from "@/components/domain/GitHubAppRepoSelector";
import { supabase } from "@/lib/supabase";
import type { Project } from "@/types/project";

interface AddProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (project: Project) => void;
  initialTab?: "public" | "private";
  initialInstallationId?: number | null;
}

const GITHUB_URL_REGEX =
  /^https?:\/\/(?:www\.)?github\.com\/([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:\.git)?\/?$/;

export function AddProjectModal({
  isOpen,
  onClose,
  onProjectCreated,
  initialTab = "public",
  initialInstallationId = null,
}: AddProjectModalProps) {
  const [activeTab, setActiveTab] = useState<"public" | "private">(
    initialInstallationId ? "private" : initialTab
  );
  const [githubUrl, setGithubUrl] = useState("");
  const [name, setName] = useState("");
  const [branch, setBranch] = useState("main");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialInstallationId) {
      setActiveTab("private");
    }
  }, [initialInstallationId]);

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
      setError("Please provide a valid GitHub repository URL.");
      return;
    }

    setLoading(true);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setError("Your session has expired. Please sign in again.");
        setLoading(false);
        return;
      }

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
      setError(err instanceof Error ? err.message : "Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 text-slate-100 shadow-2xl relative">
        <button
          onClick={onClose}
          disabled={loading}
          aria-label="Close dialog"
          className="absolute top-4 right-4 text-slate-500 hover:text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed p-1 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-5">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <FolderGit2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Add Repository</h2>
            <p className="text-xs text-slate-400">
              Register a public or private codebase for architectural defense
            </p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-slate-800 mb-5">
          <button
            type="button"
            disabled={loading}
            onClick={() => setActiveTab("public")}
            className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              activeTab === "public"
                ? "border-emerald-400 text-emerald-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Public Repository URL
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => setActiveTab("private")}
            className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed ${
              activeTab === "private"
                ? "border-emerald-400 text-emerald-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Lock className="w-3 h-3" />
            <span>Private GitHub App</span>
          </button>
        </div>

        {activeTab === "private" ? (
          <GitHubAppRepoSelector
            initialInstallationId={initialInstallationId}
            onProjectCreated={(proj) => {
              onProjectCreated(proj);
              onClose();
            }}
            onClose={onClose}
          />
        ) : (
          <>
            {error && (
              <div className="mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 flex items-start space-x-2.5 text-rose-300 text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400 mt-0.5" />
                <div className="leading-relaxed">{error}</div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="modal-github-url"
                  className="block text-xs font-medium text-slate-300 mb-1"
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
                  className="block w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs placeholder-slate-500 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="modal-name" className="block text-xs font-medium text-slate-300 mb-1">
                    Project Name
                  </label>
                  <input
                    id="modal-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Derived from repo"
                    className="block w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label htmlFor="modal-branch" className="block text-xs font-medium text-slate-300 mb-1">
                    Default Branch
                  </label>
                  <input
                    id="modal-branch"
                    type="text"
                    required
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="main"
                    className="block w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={loading}
                  className="px-3.5 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white border border-slate-800 hover:border-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-950 bg-emerald-400 hover:bg-emerald-300 disabled:opacity-50 transition-all flex items-center gap-1.5 shadow-sm"
                >
                  {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Register Repository</span>
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
