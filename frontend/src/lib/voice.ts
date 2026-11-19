// Web Speech API type shims for non-browser or older typing environments
type SpeechRecognitionConstructor = new () => any;

export function isSpeechRecognitionSupported(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  );
}

export function isSpeechSynthesisSupported(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(typeof window.speechSynthesis !== "undefined");
}

export function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  return (
    (window as any).SpeechRecognition ||
    (window as any).webkitSpeechRecognition ||
    null
  );
}

export function normalizeTranscript(base: string, incoming: string): string {
  const trimmedIncoming = incoming.trim();
  if (!trimmedIncoming) return base;

  const trimmedBase = base.trim();
  if (!trimmedBase) {
    // Capitalize first character
    return trimmedIncoming.charAt(0).toUpperCase() + trimmedIncoming.slice(1);
  }

  const lastChar = trimmedBase.slice(-1);
  const isPunctuation = [".", "!", "?", "\n"].includes(lastChar);

  // Capitalize if following terminal punctuation
  const formattedIncoming = isPunctuation
    ? trimmedIncoming.charAt(0).toUpperCase() + trimmedIncoming.slice(1)
    : trimmedIncoming;

  const separator = isPunctuation ? " " : " ";
  return `${trimmedBase}${separator}${formattedIncoming}`;
}

export function mapSpeechErrorToMessage(error: string): {
  message: string;
  recoverable: boolean;
} {
  switch (error) {
    case "not-allowed":
    case "service-not-allowed":
      return {
        message: "Microphone access was denied. Enable microphone permissions in browser settings.",
        recoverable: false,
      };
    case "no-speech":
      return {
        message: "No speech detected. Please check your mic and speak clearly.",
        recoverable: true,
      };
    case "audio-capture":
      return {
        message: "Microphone capture failed. Verify your audio input device.",
        recoverable: true,
      };
    case "network":
      return {
        message: "Network error during speech recognition. Check your connection.",
        recoverable: true,
      };
    case "aborted":
      return {
        message: "Voice input was stopped.",
        recoverable: true,
      };
    default:
      return {
        message: `Voice error (${error}). Please try again or type your answer.`,
        recoverable: true,
      };
  }
}

export function selectPersonaVoice(
  voices: SpeechSynthesisVoice[],
  persona: "principal" | "mentor" = "principal"
): SpeechSynthesisVoice | null {
  if (!voices || voices.length === 0) return null;

  // Filter for English voices first
  const englishVoices = voices.filter((v) =>
    v.lang ? v.lang.toLowerCase().startsWith("en") : false
  );

  const candidatePool = englishVoices.length > 0 ? englishVoices : voices;

  if (persona === "principal") {
    // Look for authoritative, natural sounding voices (e.g. Google UK English Male, Daniel, Natural)
    const preferred = candidatePool.find(
      (v) =>
        /daniel|george|arthur|guy|natural|male/i.test(v.name) &&
        !/female|zira|samantha/i.test(v.name)
    );
    return preferred || candidatePool[0] || null;
  }

  // Mentor persona: Look for warm, articulate voices
  const preferredMentor = candidatePool.find((v) =>
    /samantha|karen|victoria|natural|female/i.test(v.name)
  );
  return preferredMentor || candidatePool[0] || null;
}
