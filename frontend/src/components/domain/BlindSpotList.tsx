"use client";

import React from "react";
import Link from "next/link";
import { AlertTriangle, ShieldAlert, FileCode, ArrowRight, ShieldCheck } from "lucide-react";
import type { BlindSpotItem } from "@/types/coverage";

interface BlindSpotListProps {
  blindSpots: BlindSpotItem[];
  projectId: string;
}

export function BlindSpotList({ blindSpots, projectId }: BlindSpotListProps) {
  if (blindSpots.length === 0) {
    return (
      <div className="p-8 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-center space-y-3">
        <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto text-emerald-400">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <h4 className="text-sm font-semibold text-white font-mono">
          Zero Untested Blind Spots
        </h4>
        <p className="text-xs text-slate-400 font-mono max-w-md mx-auto">
          All cataloged load-bearing architectural components (databases, auth, queues) have been defended in interview sessions.
        </p>
      </div>
    );
  }

  const getPriorityBadge = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "critical":
        return "text-rose-400 bg-rose-500/10 border-rose-500/30";
      case "high":
        return "text-amber-400 bg-amber-500/10 border-amber-500/30";
      default:
        return "text-sky-400 bg-sky-500/10 border-sky-500/30";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
            High-Risk Untested Blind Spots
          </h3>
          <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            {blindSpots.length} Critical Components
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {blindSpots.map((item) => (
          <div
            key={item.evidence_id}
            className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
          >
            <div className="space-y-1.5 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase border ${getPriorityBadge(
                    item.priority
                  )}`}
                >
                  {item.priority}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono text-slate-300 bg-slate-800 border border-slate-700">
                  {item.evidence_type}
                </span>
                <h4 className="text-sm font-bold text-white font-mono truncate">
                  {item.title}
                </h4>
              </div>

              <p className="text-xs text-slate-400 font-mono line-clamp-2">
                {item.description}
              </p>

              <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-500 pt-1">
                <FileCode className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-slate-300">{item.file_path}</span>
                <span>:</span>
                <span className="text-amber-400">
                  L{item.start_line}-L{item.end_line}
                </span>
              </div>
            </div>

            <div className="flex-shrink-0">
              <Link
                href={`/interview/${projectId}`}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 text-white font-mono text-xs font-semibold transition-colors shadow-sm"
              >
                <span>Defend Component</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
