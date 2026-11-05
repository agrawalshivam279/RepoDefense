"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Search,
  CheckCircle2,
  Cpu,
  Layers,
  ArrowRight,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { ResumeUploadCard } from "@/components/domain/ResumeUploadCard";
import type {
  ClaimCategory,
  ClaimExtractionResponse,
  TechnicalClaim,
} from "@/types/claim";

const CATEGORY_COLORS: Record<ClaimCategory, string> = {
  architecture: "border-blue-500/30 text-blue-400 bg-blue-500/10",
  scalability: "border-amber-500/30 text-amber-400 bg-amber-500/10",
  security: "border-purple-500/30 text-purple-400 bg-purple-500/10",
  database: "border-cyan-500/30 text-cyan-400 bg-cyan-500/10",
  performance: "border-rose-500/30 text-rose-400 bg-rose-500/10",
  framework: "border-emerald-500/30 text-emerald-400 bg-emerald-500/10",
  infrastructure: "border-indigo-500/30 text-indigo-400 bg-indigo-500/10",
};

export default function ClaimsPage() {
  const [data, setData] = useState<ClaimExtractionResponse | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const filteredClaims: TechnicalClaim[] = (data?.claims || []).filter((claim) => {
    const matchesCat =
      selectedCategory === "all" || claim.category === selectedCategory;
    const query = searchQuery.toLowerCase().trim();
    const matchesSearch =
      !query ||
      claim.statement.toLowerCase().includes(query) ||
      claim.technologies.some((t) => t.toLowerCase().includes(query));
    return matchesCat && matchesSearch;
  });

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16 space-y-10">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-[11px] font-semibold text-emerald-400">
            <Sparkles className="w-3 h-3" />
            <span>Phase 2: Differentiation</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Resume Claim Extraction
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm">
            Extract and catalog technical claims from your resume to verify against codebase truth.
          </p>
        </div>

        {data && (
          <button
            onClick={() => setData(null)}
            className="self-start sm:self-auto px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-900 text-xs text-slate-300 font-medium transition-colors flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Upload Another
          </button>
        )}
      </div>

      {!data ? (
        <div className="max-w-3xl mx-auto space-y-8">
          <ResumeUploadCard onClaimsExtracted={(res) => setData(res)} />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-2">
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold font-mono">
                <FileText className="w-4 h-4" />
                <span>1. Parse & Categorize</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Extracts architectural, scalability, security, and database claims from PDF or text.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-2">
              <div className="flex items-center gap-2 text-blue-400 text-xs font-bold font-mono">
                <Cpu className="w-4 h-4" />
                <span>2. Match Evidence</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Correlates claims with Tree-sitter AST symbols and pgvector codebase embeddings.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-2">
              <div className="flex items-center gap-2 text-purple-400 text-xs font-bold font-mono">
                <Layers className="w-4 h-4" />
                <span>3. Defend Decisions</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Defend claims in a structured oral interview against the AI Principal Engineer.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Summary Scorecard Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 space-y-1">
              <span className="text-[11px] font-mono uppercase text-slate-400">Total Claims</span>
              <p className="text-2xl font-black text-white">{data.total_claims}</p>
            </div>
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 space-y-1">
              <span className="text-[11px] font-mono uppercase text-slate-400">Technologies</span>
              <p className="text-2xl font-black text-emerald-400">
                {data.technologies_detected.length}
              </p>
            </div>
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 space-y-1">
              <span className="text-[11px] font-mono uppercase text-slate-400">Source Characters</span>
              <p className="text-2xl font-black text-blue-400">{data.source_char_count}</p>
            </div>
            <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 space-y-1 flex flex-col justify-between">
              <span className="text-[11px] font-mono uppercase text-emerald-400">Next Action</span>
              <Link
                href="/dashboard"
                className="text-xs font-semibold text-emerald-300 hover:text-emerald-200 flex items-center gap-1"
              >
                Match with Project <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Detected Technologies Cloud */}
          {data.technologies_detected.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
              <span className="text-xs font-mono uppercase text-slate-400 font-semibold">
                Detected Tools & Frameworks
              </span>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {data.technologies_detected.map((tech) => (
                  <span
                    key={tech}
                    className="px-2.5 py-0.5 rounded-md bg-slate-800 border border-slate-700/60 text-xs font-mono text-slate-300"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto">
              {["all", "architecture", "scalability", "security", "database", "performance", "infrastructure"].map(
                (cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-all ${
                      selectedCategory === cat
                        ? "bg-slate-700 text-white font-semibold"
                        : "text-slate-400 hover:text-white hover:bg-slate-800"
                    }`}
                  >
                    {cat}
                  </button>
                )
              )}
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search claims or tools..."
                className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>
          </div>

          {/* Claims List */}
          <div className="space-y-3">
            {filteredClaims.length === 0 ? (
              <div className="rounded-xl border border-slate-800 p-8 text-center text-slate-500 text-xs">
                No technical claims found matching the current filters.
              </div>
            ) : (
              filteredClaims.map((claim) => (
                <div
                  key={claim.id}
                  className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 sm:p-5 space-y-3 hover:border-slate-700 transition-colors"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span
                      className={`px-2 py-0.5 rounded-md text-[11px] font-mono uppercase font-semibold border ${
                        CATEGORY_COLORS[claim.category] || "border-slate-700 text-slate-300"
                      }`}
                    >
                      {claim.category}
                    </span>

                    {claim.verifiable && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
                        <CheckCircle2 className="w-3 h-3" />
                        Verifiable Claim
                      </span>
                    )}
                  </div>

                  <p className="text-sm font-semibold text-white leading-relaxed">
                    {claim.statement}
                  </p>

                  {claim.technologies.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1 pt-1">
                      {claim.technologies.map((t) => (
                        <span
                          key={t}
                          className="px-2 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-slate-300 border border-slate-700/50"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}

                  {claim.source_context && claim.source_context !== claim.statement && (
                    <p className="text-[11px] text-slate-400 italic pt-1 border-t border-slate-800/60">
                      Context: &quot;{claim.source_context}&quot;
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
