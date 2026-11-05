"use client";

import { useState } from "react";
import {
  UploadCloud,
  FileText,
  AlertCircle,
  Loader2,
  Sparkles,
  FileCheck,
  X,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { extractClaimsFromText, uploadResumeFile } from "@/lib/claimApi";
import type { ClaimExtractionResponse } from "@/types/claim";

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

interface ResumeUploadCardProps {
  onClaimsExtracted: (data: ClaimExtractionResponse) => void;
  className?: string;
}

export function ResumeUploadCard({
  onClaimsExtracted,
  className = "",
}: ResumeUploadCardProps) {
  const [mode, setMode] = useState<"pdf" | "text">("pdf");
  const [file, setFile] = useState<File | null>(null);
  const [rawText, setRawText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateAndSetFile = (selected: File) => {
    setError(null);
    const isPdf =
      selected.name.toLowerCase().endsWith(".pdf") ||
      selected.type === "application/pdf";

    if (!isPdf) {
      setError("Only PDF files (.pdf) are supported.");
      return;
    }

    if (selected.size > MAX_FILE_SIZE_BYTES) {
      setError("File exceeds maximum allowed size of 10MB.");
      return;
    }

    setFile(selected);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;

      let result: ClaimExtractionResponse;
      if (mode === "pdf") {
        if (!file) {
          setError("Please select a PDF resume file to upload.");
          setIsLoading(false);
          return;
        }
        result = await uploadResumeFile(file, token);
      } else {
        if (!rawText.trim() || rawText.trim().length < 10) {
          setError("Please paste at least 10 characters of resume content.");
          setIsLoading(false);
          return;
        }
        result = await extractClaimsFromText(rawText.trim(), token);
      }

      onClaimsExtracted(result);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to extract technical claims."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-slate-900/90 p-6 sm:p-8 backdrop-blur-md shadow-2xl space-y-6 ${className}`}
    >
      {/* Mode Switcher Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            Upload Resume or Profile
          </h2>
          <p className="text-xs text-slate-400">
            Extract concrete, verifiable engineering claims to defend against your codebase.
          </p>
        </div>

        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            type="button"
            onClick={() => {
              setMode("pdf");
              setError(null);
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              mode === "pdf"
                ? "bg-emerald-500 text-slate-950 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5" />
            PDF Upload
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("text");
              setError(null);
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              mode === "text"
                ? "bg-emerald-500 text-slate-950 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Paste Text
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-5">
        {mode === "pdf" ? (
          <div>
            {!file ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                  isDragging
                    ? "border-emerald-500 bg-emerald-500/5"
                    : "border-slate-800 hover:border-slate-700 bg-slate-950/40"
                }`}
              >
                <input
                  type="file"
                  id="resume-pdf-input"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      validateAndSetFile(e.target.files[0]);
                    }
                  }}
                />
                <label
                  htmlFor="resume-pdf-input"
                  className="cursor-pointer space-y-3 block"
                >
                  <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/50 w-fit mx-auto text-slate-300">
                    <UploadCloud className="w-6 h-6 text-emerald-400" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-white">
                      Click to upload or drag and drop your PDF resume
                    </p>
                    <p className="text-xs text-slate-400">
                      Standard PDF documents up to 10MB
                    </p>
                  </div>
                </label>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                    <FileCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white truncate max-w-xs sm:max-w-md">
                      {file.name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to analyze
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200"
                  title="Remove file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Paste bullet points or work experience from your resume (e.g., 'Architected event-driven streaming pipeline using Kafka, handling 50k events/sec with zero loss')..."
              rows={6}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 p-4 text-xs font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
            />
            <div className="flex justify-between text-[11px] text-slate-500 font-mono">
              <span>Supports bullet points, job descriptions, and project writeups</span>
              <span>{rawText.length} / 50,000 chars</span>
            </div>
          </div>
        )}

        {/* Action Button */}
        <button
          type="submit"
          disabled={isLoading || (mode === "pdf" ? !file : rawText.trim().length < 10)}
          className="w-full py-3 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed font-semibold text-slate-950 text-sm shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Analyzing Technical Claims...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Extract Technical Claims</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
