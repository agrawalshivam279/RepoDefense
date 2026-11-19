import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
  mapSpeechErrorToMessage,
  normalizeTranscript,
  selectPersonaVoice,
} from "../voice";

describe("voice - Web Speech API Integration & Helpers", () => {
  it("normalizes and appends transcripts with proper punctuation and spacing", () => {
    // Empty base
    assert.strictEqual(
      normalizeTranscript("", "i used connection pooling"),
      "I used connection pooling"
    );

    // After period
    assert.strictEqual(
      normalizeTranscript(
        "We used Redis for caching.",
        "it mitigated database load"
      ),
      "We used Redis for caching. It mitigated database load"
    );

    // After unpunctuated clause
    assert.strictEqual(
      normalizeTranscript("We designed this", "with high concurrency"),
      "We designed this with high concurrency"
    );

    // Empty incoming
    assert.strictEqual(
      normalizeTranscript("Existing text", "   "),
      "Existing text"
    );
  });

  it("maps Web Speech API error codes to informative guidance", () => {
    const denied = mapSpeechErrorToMessage("not-allowed");
    assert.strictEqual(denied.recoverable, false);
    assert.ok(denied.message.toLowerCase().includes("denied"));

    const noSpeech = mapSpeechErrorToMessage("no-speech");
    assert.strictEqual(noSpeech.recoverable, true);
    assert.ok(noSpeech.message.toLowerCase().includes("no speech"));

    const unknown = mapSpeechErrorToMessage("other-code");
    assert.strictEqual(unknown.recoverable, true);
    assert.ok(unknown.message.includes("other-code"));
  });

  it("selects appropriate persona voices from candidate pool", () => {
    const mockVoices = [
      { name: "French Voice", lang: "fr-FR", default: false, localService: true, voiceURI: "fr-1" },
      { name: "Microsoft Daniel - English (UK)", lang: "en-GB", default: true, localService: true, voiceURI: "uk-1" },
      { name: "Samantha", lang: "en-US", default: false, localService: true, voiceURI: "us-1" },
    ] as unknown as SpeechSynthesisVoice[];

    const principalVoice = selectPersonaVoice(mockVoices, "principal");
    assert.ok(principalVoice);
    assert.strictEqual(principalVoice.name, "Microsoft Daniel - English (UK)");

    const mentorVoice = selectPersonaVoice(mockVoices, "mentor");
    assert.ok(mentorVoice);
    assert.strictEqual(mentorVoice.name, "Samantha");

    // Empty list handling
    assert.strictEqual(selectPersonaVoice([], "principal"), null);
  });

  it("safely evaluates feature detection in Node / SSR environment", () => {
    // In Node.js, window is undefined, so helpers should return false safely
    assert.strictEqual(isSpeechRecognitionSupported(), false);
    assert.strictEqual(isSpeechSynthesisSupported(), false);
  });
});
