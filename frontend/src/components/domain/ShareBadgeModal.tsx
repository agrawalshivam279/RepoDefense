"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  Check,
  Code2,
  Copy,
  ExternalLink,
  Globe,
  Loader2,
  Share2,
  Shield,
  Trash2,
  X,
} from "lucide-react";

import {
  createPublicShareToken,
  getPublicShareInfo,
  revokePublicShare,
} from "@/lib/publicReportApi";
import type { PublicShareTokenResponse } from "@/types/publicReport";

interface ShareBadgeModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  sessionId: string;
  token: string;
}

export function ShareBadgeModal({
  isOpen,
  onClose,
  projectId,
  sessionId,
  token,
}: ShareBadgeModalProps) {
  const [shareData, setShareData] = useState<PublicShareTokenResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [expiresInDays, setExpiresInDays] = useState<number | null>(30);

  useEffect(() => {
    if (!isOpen || !projectId || !sessionId || !token) return;

    let mounted = true;
    async function loadShareInfo() {
      setLoading(true);
      setError(null);
      try {
        const info = await getPublicShareInfo(projectId, sessionId, token);
        if (mounted) setShareData(info);
      } catch {
        // Not yet generated, keep null
        if (mounted) setShareData(null);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadShareInfo();
    return () => {
      mounted = false;
    };
  }, [isOpen, projectId, sessionId, token]);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await createPublicShareToken(projectId, sessionId, token, {
        is_active: true,
        expires_in_days: expiresInDays,
      });
      setShareData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate share credentials.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevoke = async () => {
    if (!window.confirm("Are you sure you want to revoke this public link and badge?")) return;
    setActionLoading(true);
    setError(null);
    try {
      await revokePublicShare(projectId, sessionId, token);
      setShareData(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke share link.");
    } finally {
      setActionLoading(false);
    }
  };

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      setError("Unable to copy to clipboard.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 sm:p-7 space-y-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Share2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white tracking-tight">Public Defense Report & Badge</h3>
              <p className="text-xs font-mono text-slate-400">Share verifiable proof on GitHub & your resume</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-500/30 flex items-start gap-2.5 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
            <p className="text-xs font-mono">Loading share configuration...</p>
          </div>
        ) : !shareData ? (
          <div className="space-y-5 text-center py-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-300">
              <Globe className="w-6 h-6 text-emerald-400" />
            </div>
            <div className="space-y-1.5 max-w-md mx-auto">
              <h4 className="text-sm font-semibold text-white">Public Sharing Not Activated</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Generate an unguessable cryptographic token to share your verified defense report and dynamic SVG badge without revealing internal emails or files.
              </p>
            </div>
            <div className="flex items-center justify-center gap-3 pt-2">
              <label htmlFor="duration-select" className="text-xs font-mono text-slate-400">Valid for:</label>
              <select
                id="duration-select"
                value={expiresInDays ?? "never"}
                onChange={(e) => setExpiresInDays(e.target.value === "never" ? null : Number(e.target.value))}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 font-mono focus:outline-none focus:border-emerald-500"
              >
                <option value={30}>30 Days</option>
                <option value={90}>90 Days</option>
                <option value={365}>1 Year</option>
                <option value="never">Never Expires</option>
              </select>
            </div>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={actionLoading}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-950/50 transition-colors disabled:opacity-50"
            >
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
              Generate Public Verification Link & Badge
            </button>
          </div>
        ) : (
          <div className="space-y-5">
            {/* Live SVG Badge Preview */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-emerald-400" /> Dynamic SVG Badge Preview
                </span>
                <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  Active
                </span>
              </div>
              <div className="flex items-center justify-center py-3 bg-slate-900/50 rounded-lg border border-slate-800/60 overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={shareData.badge_url} alt="RepoDefense Verification Badge" className="h-6" />
              </div>
            </div>

            {/* Shareable Verification Link */}
            <div className="space-y-1.5">
              <label htmlFor="share-link-input" className="text-xs font-mono text-slate-400 flex items-center justify-between">
                <span>Public Verification URL</span>
                <a
                  href={shareData.share_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 hover:text-emerald-300 inline-flex items-center gap-1 text-[11px]"
                >
                  Visit Portal <ExternalLink className="w-3 h-3" />
                </a>
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="share-link-input"
                  type="text"
                  readOnly
                  value={shareData.share_url}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-300 select-all"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(shareData.share_url, "url")}
                  className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono inline-flex items-center gap-1.5 shrink-0 border border-slate-700 transition-colors"
                >
                  {copiedField === "url" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedField === "url" ? "Copied" : "Copy"}
                </button>
              </div>
            </div>

            {/* Markdown Badge Snippet */}
            <div className="space-y-1.5">
              <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5 text-sky-400" /> Markdown (GitHub README)
              </span>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={shareData.markdown_badge}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-300 select-all"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(shareData.markdown_badge, "md")}
                  className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono inline-flex items-center gap-1.5 shrink-0 border border-slate-700 transition-colors"
                >
                  {copiedField === "md" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedField === "md" ? "Copied" : "Copy"}
                </button>
              </div>
            </div>

            {/* HTML Badge Snippet */}
            <div className="space-y-1.5">
              <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5 text-amber-400" /> HTML (Portfolio / Resume)
              </span>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={shareData.html_badge}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-300 select-all"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(shareData.html_badge, "html")}
                  className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono inline-flex items-center gap-1.5 shrink-0 border border-slate-700 transition-colors"
                >
                  {copiedField === "html" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedField === "html" ? "Copied" : "Copy"}
                </button>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-slate-800 text-xs font-mono text-slate-400">
              <span>{shareData.expires_at ? `Expires: ${new Date(shareData.expires_at).toLocaleDateString()}` : "Never Expires"}</span>
              <button
                type="button"
                onClick={handleRevoke}
                disabled={actionLoading}
                className="inline-flex items-center gap-1.5 text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" /> Revoke Access
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
