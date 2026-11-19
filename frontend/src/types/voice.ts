export type VoiceRecognitionStatus =
  | "idle"
  | "listening"
  | "processing"
  | "unsupported"
  | "error";

export type VoiceSynthesisStatus =
  | "idle"
  | "speaking"
  | "paused"
  | "unsupported";

export interface VoiceSettings {
  autoReadQuestions: boolean;
  speechRate: number; // 0.5 to 2.0 (default: 1.0)
  speechPitch: number; // 0.5 to 1.5 (default: 1.0)
  selectedVoiceURI: string | null;
}

export interface SpeechRecognitionErrorDetail {
  error: string;
  message: string;
  recoverable: boolean;
}

export interface VoicePersonaPreset {
  persona: "principal" | "mentor";
  pitch: number;
  rate: number;
  preferredVoices: string[];
}
