"use client";

import { useEffect, useRef } from "react";
import { useSpeechSynthesis } from "@/hooks/useSpeechSynthesis";
import { Volume2, Square } from "lucide-react";

interface AudioReadAloudButtonProps {
  text: string;
  persona?: "principal" | "mentor";
  className?: string;
  label?: string;
}

export function AudioReadAloudButton({
  text,
  persona = "principal",
  className = "",
  label,
}: AudioReadAloudButtonProps) {
  const { isSpeaking, isSupported, speak, stop } = useSpeechSynthesis();
  const prevTextRef = useRef(text);

  useEffect(() => {
    if (prevTextRef.current !== text) {
      prevTextRef.current = text;
      if (isSpeaking) {
        stop();
      }
    }
  }, [text, isSpeaking, stop]);

  if (!isSupported || !text.trim()) {
    return null;
  }

  const togglePlayback = () => {
    if (isSpeaking) {
      stop();
    } else {
      speak(text, { persona });
    }
  };

  const buttonLabel =
    label ||
    (isSpeaking
      ? "Stop reading aloud"
      : `Read aloud (${persona === "principal" ? "Principal Engineer" : "Mentor"} voice)`);

  return (
    <button
      type="button"
      onClick={togglePlayback}
      aria-label={buttonLabel}
      aria-pressed={isSpeaking}
      title={buttonLabel}
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:ring-offset-1 focus:ring-offset-slate-900 ${
        isSpeaking
          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
          : "bg-slate-800/60 hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 border border-slate-700/50"
      } ${className}`}
    >
      {isSpeaking ? (
        <>
          <Square className="h-3 w-3 fill-current animate-pulse motion-reduce:animate-none" />
          <span>Stop</span>
        </>
      ) : (
        <>
          <Volume2 className="h-3.5 w-3.5" />
          <span>Read Aloud</span>
        </>
      )}
    </button>
  );
}
