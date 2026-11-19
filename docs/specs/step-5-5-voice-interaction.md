# Technical Specification: Milestone 5.5 — Voice Interaction (Web Speech API)

## 1. Overview & Goal
RepoDefense simulates rigorous, high-stakes architectural defense interviews. While text-based chat provides complete technical precision, oral communication is central to real engineering interviews. Milestone 5.5 introduces browser-native Voice Interaction via the W3C Web Speech API (`SpeechRecognition` & `SpeechSynthesis`). Candidates can dictate defense responses in real time, and listen to spoken questions and challenge escalations delivered by the AI Principal Engineer persona.

## 2. Architecture & Invariants
- **Zero Third-Party Audio Costs**: 100% native browser Web Speech API (`window.SpeechRecognition` / `window.webkitSpeechRecognition` and `window.speechSynthesis`). No external audio APIs (OpenAI Whisper / ElevenLabs) required.
- **Graceful Degradation**: If Web Speech API is unsupported (e.g. Firefox without STT flags enabled or insecure HTTP contexts), the interface gracefully hides or disables voice controls without degrading text-based defense.
- **Privacy & Security**: Microphone access is requested only on explicit user click. Transcripts are handled purely client-side and inserted into standard defense input fields before submission.
- **Reduced Motion & Accessibility**: Visual pulse animations on recording buttons adhere to `@media (prefers-reduced-motion: reduce)`. ARIA live announcements report microphone state transitions (`"Listening..."`, `"Voice input stopped"`).
- **Strict File Limit**: All `.ts` and `.tsx` files must strictly remain $\le 300$ LOC.

## 3. Data Contracts (`frontend/src/types/voice.ts`)
- `VoiceRecognitionStatus`: `'idle' | 'listening' | 'processing' | 'unsupported' | 'error'`
- `VoiceSynthesisStatus`: `'idle' | 'speaking' | 'paused' | 'unsupported'`
- `VoiceSettings`: `{ autoReadQuestions: boolean; speechRate: number; speechPitch: number; selectedVoiceURI: string | null }`
- `SpeechRecognitionErrorDetail`: `{ error: string; message: string }`

## 4. Components & Utilities
1. `frontend/src/lib/voice.ts`:
   - Feature detection (`isSpeechRecognitionSupported`, `isSpeechSynthesisSupported`).
   - Clean transcript normalization (capitalization, sentence boundary spacing).
   - Voice lookup and filtering (English voices, persona-specific pitch/rate presets).
2. `frontend/src/hooks/useSpeechRecognition.ts`:
   - Manages `SpeechRecognition` instance, cross-browser initialization (`webkitSpeechRecognition` fallback).
   - Emits interim transcripts for live preview and appends finalized sentences.
   - Cleans up event listeners on unmount.
3. `frontend/src/hooks/useSpeechSynthesis.ts`:
   - Manages `SpeechSynthesisUtterance` lifecycle.
   - Exposes `speak(text)`, `pause()`, `resume()`, `cancel()`.
   - Handles boundary events and voices changed events.
4. `frontend/src/components/ui/VoiceInputButton.tsx`:
   - Sleek recording button with microphone icon, pulsing ring when active, tooltip with keyboard shortcut, and error banner.
5. `frontend/src/components/ui/AudioReadAloudButton.tsx`:
   - Speaker button with volume animation to trigger read-aloud playback of questions/evaluations.

## 5. Acceptance Criteria
- [x] Full TypeScript strict mode compliance with zero type errors (`tsc --noEmit`).
- [x] Hermetic unit tests in `voice.test.ts` verifying transcript normalization, feature guards, and error translation.
- [x] Next.js 15 production build succeeds cleanly.
- [x] All touched files remain $\le 300$ LOC.
