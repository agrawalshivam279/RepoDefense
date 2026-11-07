"use client";

import React from "react";
import { AlertTriangle, Code2, FileCode, ShieldAlert } from "lucide-react";
import type { OwnershipStatus, SymbolOwnership } from "@/types/ownership";

interface SymbolOwnershipCardProps {
  symbol: SymbolOwnership;
}

export function SymbolOwnershipCard({ symbol }: SymbolOwnershipCardProps) {
  const getStatusBadge = (status: OwnershipStatus) => {
    switch (status) {
      case "primary":
        return {
          label: "Primary Author",
          color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
        };
      case "collaborator":
        return {
          label: "Collaborator",
          color: "text-sky-400 bg-sky-500/10 border-sky-500/30",
        };
      case "minor":
        return {
          label: "Minor Share",
          color: "text-amber-400 bg-amber-500/10 border-amber-500/30",
        };
      case "unowned":
      default:
        return {
          label: "Unowned",
          color: "text-rose-400 bg-rose-500/10 border-rose-500/30",
        };
    }
  };

  const statusInfo = getStatusBadge(symbol.candidate_status);

  return (
    <div
      className={`p-4 rounded-xl border transition-colors flex flex-col justify-between gap-3 ${
        symbol.is_architectural_evidence &&
        (symbol.candidate_status === "unowned" || symbol.candidate_status === "minor")
          ? "bg-rose-950/20 border-rose-500/30 shadow-sm"
          : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
      }`}
    >
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Code2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <h4
              className="text-sm font-bold text-white font-mono truncate"
              title={symbol.symbol_name}
            >
              {symbol.symbol_name}
            </h4>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-slate-400 bg-slate-800 border border-slate-700">
              {symbol.symbol_type}
            </span>
          </div>

          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium border flex-shrink-0 ${statusInfo.color}`}
          >
            {statusInfo.label} ({symbol.candidate_ownership_percentage}%)
          </span>
        </div>

        {symbol.is_architectural_evidence && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-[11px] font-mono text-amber-300">
            {symbol.candidate_status === "unowned" ? (
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
            )}
            <span>
              Architectural Evidence ({symbol.evidence_type ?? "load-bearing"})
            </span>
          </div>
        )}

        <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
          <FileCode className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-300 truncate" title={symbol.file_path}>
            {symbol.file_path}
          </span>
          <span>:</span>
          <span className="text-amber-400">
            L{symbol.start_line}-L{symbol.end_line}
          </span>
          <span className="text-slate-500">({symbol.total_lines} lines)</span>
        </div>
      </div>

      {/* Authorship Progress Bar */}
      <div className="space-y-1.5 pt-1">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Primary: {symbol.primary_author}</span>
          <span>Candidate: {symbol.candidate_ownership_percentage}%</span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden flex">
          <div
            className={`h-full transition-all duration-300 ${
              symbol.candidate_ownership_percentage >= 80
                ? "bg-emerald-500"
                : symbol.candidate_ownership_percentage >= 20
                ? "bg-sky-500"
                : "bg-rose-500"
            }`}
            style={{ width: `${Math.max(symbol.candidate_ownership_percentage, 0)}%` }}
            title={`Candidate: ${symbol.candidate_ownership_percentage}%`}
          />
          <div
            className="h-full bg-slate-700 transition-all duration-300"
            style={{ width: `${100 - symbol.candidate_ownership_percentage}%` }}
            title="Teammates / Upstream"
          />
        </div>
      </div>
    </div>
  );
}
