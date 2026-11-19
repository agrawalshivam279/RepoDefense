"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getSpeechRecognitionConstructor,
  isSpeechRecognitionSupported,
  mapSpeechErrorToMessage,
} from "@/lib/voice";
import { announce } from "@/lib/accessibility";
import type { VoiceRecognitionStatus } from "@/types/voice";

interface UseSpeechRecognitionOptions {
  lang?: string;
  disabled?: boolean;
  onFinalTranscript?: (text: string) => void;
}

export function useSpeechRecognition({
  lang = "en-US",
  disabled = false,
  onFinalTranscript,
}: UseSpeechRecognitionOptions = {}) {
  const [status, setStatus] = useState<VoiceRecognitionStatus>("idle");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const isManuallyStoppedRef = useRef(false);
  const onFinalRef = useRef(onFinalTranscript);
  onFinalRef.current = onFinalTranscript;

  const isSupported =
    typeof window !== "undefined" && isSpeechRecognitionSupported();

  const stopListening = useCallback(() => {
    isManuallyStoppedRef.current = true;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore already stopped error
      }
      recognitionRef.current = null;
    }
    setStatus("idle");
    setInterimTranscript("");
    announce("Voice input stopped", "polite");
  }, []);

  // When disabled changes to true (e.g. form submission starts), end recording immediately
  useEffect(() => {
    if (disabled && (status === "listening" || status === "processing")) {
      stopListening();
    }
  }, [disabled, status, stopListening]);

  const startListening = useCallback(() => {
    if (disabled) return;

    if (!isSupported) {
      setStatus("unsupported");
      setErrorMessage("Speech recognition is not supported in this browser.");
      return;
    }

    const SpeechConstructor = getSpeechRecognitionConstructor();
    if (!SpeechConstructor) {
      setStatus("unsupported");
      return;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore abort error
      }
      recognitionRef.current = null;
    }

    setErrorMessage(null);
    setInterimTranscript("");
    isManuallyStoppedRef.current = false;

    try {
      const recognition = new SpeechConstructor();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onstart = () => {
        if (isManuallyStoppedRef.current) {
          try {
            recognition.abort();
          } catch {
            // ignore
          }
          return;
        }
        setStatus("listening");
        announce("Microphone active. Listening...", "polite");
      };

      recognition.onresult = (event: any) => {
        if (isManuallyStoppedRef.current) {
          return; // Ignore any late results after stopping
        }

        let interim = "";
        let finalSentence = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcriptChunk = event.results[i][0]?.transcript || "";
          if (event.results[i].isFinal) {
            finalSentence += transcriptChunk;
          } else {
            interim += transcriptChunk;
          }
        }

        setInterimTranscript(interim);

        if (finalSentence && onFinalRef.current && !isManuallyStoppedRef.current) {
          onFinalRef.current(finalSentence);
        }
      };

      recognition.onerror = (event: any) => {
        const errorType = event.error || "unknown";
        if (errorType === "aborted" || isManuallyStoppedRef.current) {
          return;
        }
        const errorInfo = mapSpeechErrorToMessage(errorType);
        setErrorMessage(errorInfo.message);
        setStatus("error");
        announce(`Voice error: ${errorInfo.message}`, "assertive");
      };

      recognition.onend = () => {
        setInterimTranscript("");
        if (!isManuallyStoppedRef.current && status === "listening") {
          setStatus("idle");
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch {
      setStatus("error");
      setErrorMessage("Could not start microphone. Please check permissions.");
    }
  }, [disabled, isSupported, lang, status]);

  useEffect(() => {
    return () => {
      isManuallyStoppedRef.current = true;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore cleanup error
        }
        recognitionRef.current = null;
      }
    };
  }, []);

  return {
    status,
    isListening: status === "listening",
    isSupported,
    interimTranscript,
    errorMessage,
    startListening,
    stopListening,
    clearError: () => setErrorMessage(null),
  };
}
