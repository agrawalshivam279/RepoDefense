import type { Announcement, PolitenessSetting } from "@/types/accessibility";

type AnnouncementListener = (announcement: Announcement) => void;

const listeners = new Set<AnnouncementListener>();

let announcementCounter = 0;

export function subscribeAnnouncements(listener: AnnouncementListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function announce(
  message: string,
  politeness: PolitenessSetting = "polite"
): void {
  const trimmed = message.trim();
  if (!trimmed) return;

  const announcement: Announcement = {
    id: `rd-a11y-${Date.now()}-${++announcementCounter}`,
    message: trimmed,
    politeness,
    timestamp: Date.now(),
  };

  listeners.forEach((listener) => {
    try {
      listener(announcement);
    } catch {
      // guard against faulty listener
    }
  });
}

// WCAG 2.1 Luminance & Contrast Calculation Helpers
function channelToLinear(c: number): number {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

export function getRelativeLuminance(r: number, g: number, b: number): number {
  const rLin = channelToLinear(r);
  const gLin = channelToLinear(g);
  const bLin = channelToLinear(b);
  return 0.2126 * rLin + 0.7152 * gLin + 0.0722 * bLin;
}

export function calculateContrastRatio(
  rgb1: [number, number, number],
  rgb2: [number, number, number]
): number {
  const lum1 = getRelativeLuminance(...rgb1);
  const lum2 = getRelativeLuminance(...rgb2);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

export function formatContrastRatio(ratio: number): string {
  return `${(Math.round(ratio * 100) / 100).toFixed(2)}:1`;
}

export function isWcagAACompliant(
  foregroundRgb: [number, number, number],
  backgroundRgb: [number, number, number],
  isLargeText = false
): boolean {
  const ratio = calculateContrastRatio(foregroundRgb, backgroundRgb);
  const threshold = isLargeText ? 3.0 : 4.5;
  return ratio >= threshold;
}
