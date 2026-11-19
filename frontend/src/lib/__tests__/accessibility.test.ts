import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  announce,
  calculateContrastRatio,
  getRelativeLuminance,
  isWcagAACompliant,
  subscribeAnnouncements,
} from "../accessibility";
import type { Announcement } from "@/types/accessibility";

describe("accessibility - Assistive Telemetry & WCAG 2.1 Contrast Helpers", () => {
  it("dispatches announcements to subscribers and ignores blank messages", () => {
    const received: Announcement[] = [];
    const unsubscribe = subscribeAnnouncements((a) => received.push(a));

    announce("  ");
    assert.strictEqual(received.length, 0);

    announce("Repository cloned successfully", "polite");
    assert.strictEqual(received.length, 1);
    assert.strictEqual(received[0].message, "Repository cloned successfully");
    assert.strictEqual(received[0].politeness, "polite");
    assert.ok(received[0].id.startsWith("rd-a11y-"));

    announce("Simulation timeout warning", "assertive");
    assert.strictEqual(received.length, 2);
    assert.strictEqual(received[1].politeness, "assertive");

    unsubscribe();
    announce("Another message", "polite");
    assert.strictEqual(received.length, 2);
  });

  it("calculates relative luminance according to sRGB formula", () => {
    const lumBlack = getRelativeLuminance(0, 0, 0);
    assert.strictEqual(lumBlack, 0);

    const lumWhite = getRelativeLuminance(255, 255, 255);
    assert.ok(Math.abs(lumWhite - 1) < 0.001);
  });

  it("computes contrast ratio between color pairs", () => {
    const black: [number, number, number] = [0, 0, 0];
    const white: [number, number, number] = [255, 255, 255];

    const ratioMax = calculateContrastRatio(black, white);
    assert.strictEqual(ratioMax, 21);

    const ratioSame = calculateContrastRatio(white, white);
    assert.strictEqual(ratioSame, 1);
  });

  it("evaluates WCAG 2.1 AA compliance for text sizes", () => {
    const darkBg: [number, number, number] = [11, 15, 25]; // #0b0f19
    const emeraldText: [number, number, number] = [52, 211, 153]; // #34d399
    const lowContrastGray: [number, number, number] = [30, 41, 59]; // #1e293b

    assert.strictEqual(isWcagAACompliant(emeraldText, darkBg, false), true);
    assert.strictEqual(isWcagAACompliant(lowContrastGray, darkBg, false), false);
    assert.strictEqual(isWcagAACompliant(lowContrastGray, darkBg, true), false);

    // Boundary check: [119, 119, 115] against white produces ~4.496:1.
    // WCAG prohibits rounding before threshold checks, so it must not pass 4.5:1.
    const white: [number, number, number] = [255, 255, 255];
    const boundaryGray: [number, number, number] = [119, 119, 115];
    const boundaryRatio = calculateContrastRatio(boundaryGray, white);
    assert.ok(boundaryRatio < 4.5);
    assert.strictEqual(isWcagAACompliant(boundaryGray, white, false), false);
    // But it passes large text threshold (3.0:1)
    assert.strictEqual(isWcagAACompliant(boundaryGray, white, true), true);
  });
});
