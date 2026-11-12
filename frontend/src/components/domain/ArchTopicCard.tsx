"use client";

import React from "react";
import { GitBranch, Layers, Loader2, Play } from "lucide-react";
import { ARCH_FOCUS_META } from "@/components/domain/ArchTopologyPanel";
import type { ArchDefenseTopic } from "@/types/archDefense";

export interface ArchTopicCardProps {
  topic: ArchDefenseTopic;
  isStarting: boolean;
  disabled: boolean;
  onLaunch: (topicId: string) => void;
}

export function ArchTopicCard({ topic, isStarting, disabled, onLaunch }: ArchTopicCardProps) {
  const focusMeta = ARCH_FOCUS_META[topic.focus_area];
  return (
    <article className="flex flex-col justify-between rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 transition hover:border-zinc-700">
      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${focusMeta.badgeClass}`}>
            {focusMeta.label}
          </span>
          <span className="rounded border border-zinc-700 bg-zinc-950 px-2 py-0.5 text-[11px] font-medium text-zinc-300">
            {topic.severity_or_confidence}
          </span>
        </div>
        <h2 className="text-base font-semibold text-zinc-100">{topic.title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-zinc-400">{topic.design_claim}</p>

        {topic.target_nodes.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {topic.target_nodes.slice(0, 4).map((node) => (
              <span
                key={node.node_id}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[11px] text-zinc-300"
              >
                <Layers className="h-3 w-3 text-cyan-400" />
                <span>{node.label}</span>
                {node.connected_edges.length > 0 && (
                  <span className="inline-flex items-center gap-0.5 text-zinc-500">
                    <GitBranch className="h-2.5 w-2.5" />
                    {node.connected_edges.length}
                  </span>
                )}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="mt-5 border-t border-zinc-800 pt-4">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onLaunch(topic.id)}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isStarting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          <span>{isStarting ? "Preparing Defense..." : "Start Architecture Defense"}</span>
        </button>
      </div>
    </article>
  );
}
