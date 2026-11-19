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
    if (typeof window.speechSynthesis.onvoiceschanged !== "undefined") {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }

    return () => {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // ignore cleanup error
      }
    };
  }, [isSupported]);

  const stop = useCallback(() => {
    if (!isSupported) return;
    try {
      window.speechSynthesis.cancel();
    } catch {
      // ignore
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
        // Cancel any active speech before starting new
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(trimmed);
        const persona = options.persona || "principal";
        const selectedVoice = selectPersonaVoice(voices, persona);

        if (selectedVoice) {
          utterance.voice = selectedVoice;
        }

        // Persona default presets:
        // Principal: slightly slower (0.95), neutral pitch (0.95) for authoritative tone
        // Mentor: standard rate (1.0), slightly higher pitch (1.05) for warm encouragement
        const defaultRate = persona === "principal" ? 0.95 : 1.0;
        const defaultPitch = persona === "principal" ? 0.95 : 1.05;

        utterance.rate = options.rate ?? defaultRate;
        utterance.pitch = options.pitch ?? defaultPitch;

        utterance.onstart = () => {
          setStatus("speaking");
          announce("Audio playback started", "polite");
        };

        utterance.onend = () => {
          setStatus("idle");
        };

        utterance.onerror = () => {
          setStatus("idle");
        };

        window.speechSynthesis.speak(utterance);
      } catch {
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
