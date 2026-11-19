"use client";

import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { Mic, MicOff, AlertCircle } from "lucide-react";

interface VoiceInputButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  className?: string;
}

export function VoiceInputButton({
  onTranscript,
  disabled = false,
  className = "",
}: VoiceInputButtonProps) {
  const {
    isListening,
    isSupported,
    interimTranscript,
    errorMessage,
    startListening,
    stopListening,
    clearError,
  } = useSpeechRecognition({
    disabled,
    onFinalTranscript: (sentence) => {
      onTranscript(sentence);
    },
  });

  if (!isSupported) {
    return null; // Gracefully degrade on unsupported browsers
  }

  const toggleListening = () => {
    if (errorMessage) {
      clearError();
    }
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={toggleListening}
        disabled={disabled}
        aria-label={
          isListening
            ? "Stop voice recording"
            : errorMessage
            ? `Voice error: ${errorMessage}`
            : "Dictate answer with voice"
        }
        aria-pressed={isListening}
        className={`relative inline-flex items-center justify-center p-2 rounded-lg text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:ring-offset-2 focus:ring-offset-slate-900 ${
          isListening
            ? "bg-rose-500/20 text-rose-400 border border-rose-500/50 shadow-lg shadow-rose-500/20"
            : errorMessage
            ? "bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20"
            : "bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-emerald-400 border border-slate-700/60"
        } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"} ${className}`}
      >
        {isListening ? (
          <>
            <span
              className="absolute -inset-1 rounded-lg bg-rose-500/30 animate-ping opacity-75 motion-reduce:hidden"
              aria-hidden="true"
            />
            <MicOff className="h-4 w-4 relative z-10" />
            <span className="ml-1.5 text-xs font-semibold relative z-10 hidden sm:inline">
              Listening...
            </span>
          </>
        ) : errorMessage ? (
          <>
            <AlertCircle className="h-4 w-4" />
            <span className="sr-only">Voice error: {errorMessage}</span>
          </>
        ) : (
          <Mic className="h-4 w-4" />
        )}
      </button>

      {/* Floating Interim Transcript Preview */}
      {isListening && interimTranscript && (
        <div
          role="status"
          aria-live="polite"
          className="absolute bottom-full left-0 mb-2 w-64 max-w-xs p-2 bg-slate-900/95 border border-rose-500/40 rounded-lg shadow-xl text-xs text-slate-200 italic truncate z-50 backdrop-blur-sm pointer-events-none"
        >
          <span className="text-rose-400 font-semibold mr-1 not-italic">
            ●
          </span>
          {interimTranscript}
        </div>
      )}

      {/* Error Tooltip */}
      {errorMessage && !isListening && (
        <div
          role="alert"
          className="absolute bottom-full left-0 mb-2 w-56 p-2 bg-slate-900/95 border border-amber-500/40 rounded-lg shadow-xl text-xs text-amber-300 z-50 backdrop-blur-sm"
        >
          {errorMessage}
        </div>
      )}
    </div>
  );
}
