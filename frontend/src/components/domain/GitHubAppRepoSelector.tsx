"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  GitBranch,
  Globe,
  Loader2,
  Lock,
  Search,
  ShieldAlert,
} from "lucide-react";
import {
  createPrivateRepoProject,
  fetchGitHubAppStatus,
  fetchInstallationRepositories,
} from "@/lib/githubAppApi";
import type {
  GitHubAppRepoItem,
  GitHubAppStatusResponse,
} from "@/types/githubApp";
import type { Project } from "@/types/project";

interface GitHubAppRepoSelectorProps {
  initialInstallationId?: number | null;
  onProjectCreated: (project: Project) => void;
  onClose?: () => void;
}

export function GitHubAppRepoSelector({
  initialInstallationId,
  onProjectCreated,
  onClose,
}: GitHubAppRepoSelectorProps) {
  const [appStatus, setAppStatus] = useState<GitHubAppStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [installationIdInput, setInstallationIdInput] = useState<string>(
    initialInstallationId ? String(initialInstallationId) : ""
  );
  const [loadedInstallationId, setLoadedInstallationId] = useState<number | null>(
    initialInstallationId ?? null
  );
  const [repositories, setRepositories] = useState<GitHubAppRepoItem[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [importingId, setImportingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Load GitHub App configuration status
  useEffect(() => {
    let mounted = true;
    fetchGitHubAppStatus()
      .then((status) => {
        if (mounted) setAppStatus(status);
      })
      .catch((err: unknown) => {
        if (mounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to retrieve GitHub App status"
          );
        }
      })
      .finally(() => {
        if (mounted) setStatusLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Auto-fetch repositories if initialInstallationId was passed
  useEffect(() => {
    if (initialInstallationId) {
      loadRepositories(initialInstallationId);
    }
  }, [initialInstallationId]);

  const loadRepositories = async (id: number) => {
    setError(null);
    setLoadingRepos(true);
    try {
      const data = await fetchInstallationRepositories(id);
      setRepositories(data.repositories);
      setLoadedInstallationId(id);
    } catch (err: unknown) {
      setRepositories([]);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load repositories for this installation"
      );
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleFetchClick = (e: React.FormEvent) => {
    e.preventDefault();
    const id = parseInt(installationIdInput.trim(), 10);
    if (isNaN(id) || id <= 0) {
      setError("Please enter a valid numeric GitHub installation ID.");
      return;
    }
    loadRepositories(id);
  };

  const handleImport = async (repo: GitHubAppRepoItem) => {
    if (!loadedInstallationId) return;
    setError(null);
    setSuccessMsg(null);
    setImportingId(repo.id);

    try {
      const project = await createPrivateRepoProject({
        full_name: repo.full_name,
        installation_id: loadedInstallationId,
        default_branch: repo.default_branch || "main",
      });
      setSuccessMsg(`Imported ${repo.name} successfully! Cloner worker initiated.`);
      onProjectCreated(project);
      if (onClose) {
        setTimeout(onClose, 1200);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to import repository");
    } finally {
      setImportingId(null);
    }
  };

  const filteredRepos = repositories.filter(
    (r) =>
      r.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.description && r.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-4 text-slate-200">
      {/* 1. App Deployment Status / Install Button */}
      {statusLoading ? (
        <div className="flex items-center space-x-2 p-3 bg-slate-950/60 rounded-lg border border-slate-800 text-xs text-slate-400">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Verifying GitHub App deployment...</span>
        </div>
      ) : appStatus?.configured ? (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg flex items-center justify-between">
          <div className="space-y-0.5">
            <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>GitHub App Ready: {appStatus.app_slug || "RepoDefense"}</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Grant RepoDefense read-only access to select private repositories.
            </p>
          </div>
          {appStatus.install_url && (
            <a
              href={appStatus.install_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-emerald-400 hover:bg-emerald-300 text-slate-950 text-xs font-semibold transition-colors"
            >
              <span>Install App</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      ) : (
        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex items-start gap-2.5 text-amber-300 text-xs">
          <ShieldAlert className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-400" />
          <div>
            <span className="font-semibold">GitHub App Not Configured</span>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Private repository ingestion requires GITHUB_APP_ID & Private Key.
            </p>
          </div>
        </div>
      )}

      {/* 2. Error & Success Notifications */}
      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2.5 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
          <div className="leading-relaxed">{error}</div>
        </div>
      )}
      {successMsg && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center space-x-2 text-emerald-300 text-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* 3. Installation ID Query Bar */}
      <form onSubmit={handleFetchClick} className="flex gap-2">
        <input
          type="number"
          value={installationIdInput}
          onChange={(e) => setInstallationIdInput(e.target.value)}
          placeholder="Installation ID (e.g. 12345678)"
          className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
        <button
          type="submit"
          disabled={loadingRepos}
          className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          {loadingRepos && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          <span>Load Repos</span>
        </button>
      </form>

      {/* 4. Search Filter (when repos are loaded) */}
      {repositories.length > 0 && (
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`Filter ${repositories.length} accessible repositories...`}
            className="w-full pl-8 pr-3 py-2 bg-slate-950/70 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>
      )}

      {/* 5. Repository Results List */}
      {loadedInstallationId && (
        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
          {filteredRepos.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-lg">
              {loadingRepos
                ? "Loading repositories from GitHub API..."
                : repositories.length === 0
                ? "No repositories found for this installation ID."
                : "No matching repositories."}
            </div>
          ) : (
            filteredRepos.map((repo) => (
              <div
                key={repo.id}
                className="p-3 bg-slate-950/80 border border-slate-800/80 rounded-lg flex items-center justify-between hover:border-slate-700 transition-all gap-3"
              >
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-semibold text-xs text-white truncate">
                      {repo.full_name}
                    </span>
                    {repo.private ? (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        <Lock className="w-2.5 h-2.5" />
                        <span>Private</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300">
                        <Globe className="w-2.5 h-2.5" />
                        <span>Public</span>
                      </span>
                    )}
                    <span className="inline-flex items-center gap-0.5 text-[10px] font-mono text-slate-400">
                      <GitBranch className="w-2.5 h-2.5" />
                      <span>{repo.default_branch}</span>
                    </span>
                  </div>
                  {repo.description && (
                    <p className="text-[11px] text-slate-400 truncate">
                      {repo.description}
                    </p>
                  )}
                </div>

                <button
                  onClick={() => handleImport(repo)}
                  disabled={importingId === repo.id}
                  className="px-2.5 py-1.5 rounded-md bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-medium transition-colors flex items-center gap-1 disabled:opacity-50 flex-shrink-0"
                >
                  {importingId === repo.id && (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  )}
                  <span>Import</span>
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
