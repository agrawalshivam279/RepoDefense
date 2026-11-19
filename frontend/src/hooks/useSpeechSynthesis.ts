"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  isSpeechSynthesisSupported,
  selectPersonaVoice,
} from "@/lib/voice";
import { announce } from "@/lib/accessibility";
import type { VoiceSynthesisStatus } from "@/types/voice";

interface SpeakOptions {
  persona?: "principal" | "mentor";
  rate?: number;
  pitch?: number;
}

export function useSpeechSynthesis() {
  const [status, setStatus] = useState<VoiceSynthesisStatus>("idle");
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const currentUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const isSupported =
    typeof window !== "undefined" && isSpeechSynthesisSupported();

  useEffect(() => {
    if (!isSupported) {
      setStatus("unsupported");
      return;
    }

    const loadVoices = () => {
      try {
        const available = window.speechSynthesis.getVoices();
        if (available && available.length > 0) {
          setVoices(available);
        }
      } catch {
        // ignore voice loading error
      }
    };

    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);

    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoices);
      if (currentUtteranceRef.current) {
        try {
          window.speechSynthesis.cancel();
        } catch {
          // ignore
        }
        currentUtteranceRef.current = null;
      }
    };
  }, [isSupported]);

  const stop = useCallback(() => {
    if (!isSupported) return;
    if (currentUtteranceRef.current) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // ignore
      }
      currentUtteranceRef.current = null;
    }
    setStatus("idle");
    announce("Audio playback stopped", "polite");
  }, [isSupported]);

  const speak = useCallback(
    (text: string, options: SpeakOptions = {}) => {
      if (!isSupported) return;

      const trimmed = text.trim();
      if (!trimmed) return;

      try {
        // Resume synthesis engine before cancelling/starting fresh so paused state is not retained
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
        }
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(trimmed);
        currentUtteranceRef.current = utterance;

        const persona = options.persona || "principal";
        const selectedVoice = selectPersonaVoice(voices, persona);

        if (selectedVoice) {
          utterance.voice = selectedVoice;
        }

        const defaultRate = persona === "principal" ? 0.95 : 1.0;
        const defaultPitch = persona === "principal" ? 0.95 : 1.05;

        utterance.rate = options.rate ?? defaultRate;
        utterance.pitch = options.pitch ?? defaultPitch;

        utterance.onstart = () => {
          if (currentUtteranceRef.current === utterance) {
            setStatus("speaking");
            announce("Audio playback started", "polite");
          }
        };

        utterance.onend = () => {
          if (currentUtteranceRef.current === utterance) {
            currentUtteranceRef.current = null;
            setStatus("idle");
          }
        };

        utterance.onerror = () => {
          if (currentUtteranceRef.current === utterance) {
            currentUtteranceRef.current = null;
            setStatus("idle");
          }
        };

        window.speechSynthesis.speak(utterance);
      } catch {
        currentUtteranceRef.current = null;
        setStatus("idle");
      }
    },
    [isSupported, voices]
  );

  const pause = useCallback(() => {
    if (!isSupported) return;
    try {
      window.speechSynthesis.pause();
      setStatus("paused");
    } catch {
      // ignore
    }
  }, [isSupported]);

  const resume = useCallback(() => {
    if (!isSupported) return;
    try {
      window.speechSynthesis.resume();
      setStatus("speaking");
    } catch {
      // ignore
    }
  }, [isSupported]);

  return {
    status,
    isSpeaking: status === "speaking",
    isPaused: status === "paused",
    isSupported,
    voices,
    speak,
    stop,
    pause,
    resume,
  };
}
