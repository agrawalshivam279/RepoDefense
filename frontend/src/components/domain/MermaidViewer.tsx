"use client";

import { useEffect, useId, useRef, useState } from "react";
import {
  Check,
  Code2,
  Copy,
  Maximize2,
  Minimize2,
  Sparkles,
  Workflow,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from "lucide-react";
import mermaid from "mermaid";
import type { DiagramResponse } from "@/types/diagram";

interface MermaidViewerProps {
  diagram: DiagramResponse;
}

export function MermaidViewer({ diagram }: MermaidViewerProps) {
  const uniqueId = useId().replace(/:/g, "_");
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgHtml, setSvgHtml] = useState<string>("");
  const [renderError, setRenderError] = useState<string | null>(null);
  const [zoomScale, setZoomScale] = useState<number>(1);
  const [copied, setCopied] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showRawCode, setShowRawCode] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      securityLevel: "strict",
      fontFamily: "ui-sans-serif, system-ui, sans-serif",
      themeVariables: {
        darkMode: true,
        background: "#090d16",
        primaryColor: "#1e293b",
        primaryTextColor: "#f8fafc",
        primaryBorderColor: "#334155",
        lineColor: "#38bdf8",
        secondaryColor: "#0f172a",
        tertiaryColor: "#1e1b4b",
      },
      flowchart: {
        htmlLabels: true,
        curve: "basis",
        padding: 16,
      },
    });

    async function renderChart() {
      try {
        setRenderError(null);
        const renderId = `mermaid_${uniqueId}_${Date.now()}`;
        const { svg } = await mermaid.render(renderId, diagram.mermaid_code);
        if (isMounted) {
          setSvgHtml(svg);
        }
      } catch (err: unknown) {
        if (isMounted) {
          setRenderError(err instanceof Error ? err.message : "Mermaid render failed");
        }
      }
    }

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [diagram.mermaid_code, uniqueId]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(diagram.mermaid_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignore clipboard write failures
    }
  };

  const handleZoom = (delta: number) => {
    setZoomScale((prev) => Math.min(2.5, Math.max(0.5, +(prev + delta).toFixed(1))));
  };

  const resetZoom = () => setZoomScale(1);

  return (
    <div
      className={`rounded-xl bg-slate-900/90 border border-slate-800 shadow-xl transition-all ${
        isFullscreen
          ? "fixed inset-4 z-50 flex flex-col bg-slate-950 p-6 overflow-hidden"
          : "p-6 space-y-4"
      }`}
    >
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Workflow className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-bold text-white tracking-tight">
              Architecture Topology Diagram
            </h3>
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-mono border ${
                diagram.is_fallback
                  ? "bg-slate-800 text-slate-300 border-slate-700"
                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              }`}
            >
              {diagram.is_fallback ? "Deterministic Fallback" : "AI Principal Synthesis"}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Component relations, data flows, and structural tier boundaries
          </p>
        </div>

        {/* Action Toolbar */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto font-mono text-xs">
          <button
            type="button"
            onClick={() => handleZoom(-0.15)}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={resetZoom}
            className="px-2 py-1 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 text-[11px] transition-colors"
            title="Reset Zoom"
          >
            {Math.round(zoomScale * 100)}%
          </button>
          <button
            type="button"
            onClick={() => handleZoom(0.15)}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setShowRawCode((prev) => !prev)}
            className={`p-1.5 rounded-lg border transition-colors ${
              showRawCode
                ? "bg-indigo-600 text-white border-indigo-500"
                : "bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border-slate-700"
            }`}
            title="Toggle Raw Mermaid Code"
          >
            <Code2 className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 transition-colors"
            title="Copy Mermaid Code"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>
          <button
            type="button"
            onClick={() => setIsFullscreen((prev) => !prev)}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 transition-colors"
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen View"}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Main View Area */}
      {showRawCode ? (
        <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-sky-300 overflow-x-auto whitespace-pre max-h-[500px]">
          {diagram.mermaid_code}
        </div>
      ) : renderError ? (
        <div className="p-6 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-mono space-y-2">
          <p className="font-semibold text-rose-200">Unable to render Mermaid diagram:</p>
          <p>{renderError}</p>
          <div className="p-3 rounded bg-slate-950 text-slate-400 overflow-x-auto whitespace-pre">
            {diagram.mermaid_code}
          </div>
        </div>
      ) : (
        <div
          ref={containerRef}
          className={`w-full overflow-auto rounded-lg bg-slate-950/70 border border-slate-800/80 p-6 flex items-center justify-center min-h-[320px] transition-transform ${
            isFullscreen ? "flex-1" : ""
          }`}
        >
          <div
            style={{ transform: `scale(${zoomScale})`, transformOrigin: "center top" }}
            className="transition-transform duration-150 flex items-center justify-center w-full"
            dangerouslySetInnerHTML={{ __html: svgHtml }}
          />
        </div>
      )}

      {/* Summary Narrative */}
      <div className="p-3.5 rounded-lg bg-slate-950/50 border border-slate-800/60 flex items-start gap-2.5 text-xs text-slate-300 font-sans">
        <Sparkles className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
        <p className="leading-relaxed">{diagram.summary}</p>
      </div>
    </div>
  );
}
