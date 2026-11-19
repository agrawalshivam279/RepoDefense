import type { TourPlacement, TourRect, TourStep } from "@/types/onboarding";

export const DASHBOARD_TOUR_ID = "dashboard_overview";

export const DASHBOARD_TOUR_STEPS: TourStep[] = [
  {
    id: "welcome",
    title: "Welcome to RepoDefense",
    description:
      "Prove that you understand — and can defend — the software you built against a Principal Engineer AI persona grounded in your actual code.",
    placement: "center",
    badge: "Core Mission",
  },
  {
    id: "add-repo",
    targetSelector: "[data-tour='add-repo']",
    title: "Ingest Your Codebase",
    description:
      "Register a public GitHub repository URL or connect our dedicated GitHub App to defend private codebases with zero arbitrary code execution.",
    placement: "bottom",
    badge: "Ingestion",
  },
  {
    id: "project-list",
    targetSelector: "[data-tour='project-list']",
    title: "Project Analysis Hub",
    description:
      "Inspect Tree-sitter AST symbols, architectural patterns, dependency health scores, and verified resume claim evidence for each repository.",
    placement: "top",
    badge: "Static Analysis",
  },
  {
    id: "simulation-modes",
    targetSelector: "[data-tour='quick-actions']",
    title: "Simulation Arena",
    description:
      "Conduct live defenses across Incident War Room chaos, Scaling Stress Tests, PR & Commit reviews, and Architecture Topology diagrams.",
    placement: "bottom",
    badge: "Simulations",
  },
  {
    id: "learning-loop",
    targetSelector: "[data-tour='learning-hub']",
    title: "Mentorship & Verification",
    description:
      "Turn missed questions into architectural strengths with Mentor Mode, targeted re-testing, and shareable SVG resume badges for recruiters.",
    placement: "bottom",
    badge: "Verification",
  },
];

const STORAGE_PREFIX = "repodefense_tour_";

export function getTourStorageKey(tourId: string): string {
  return `${STORAGE_PREFIX}${tourId}_completed`;
}

export function isTourCompleted(tourId: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(getTourStorageKey(tourId)) === "true";
  } catch {
    return false;
  }
}

export function setTourCompleted(tourId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(getTourStorageKey(tourId), "true");
  } catch {
    // ignore storage quota / access errors
  }
}

export function resetTourStatus(tourId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(getTourStorageKey(tourId));
  } catch {
    // ignore
  }
}

export function calculateCardPosition(
  targetRect: TourRect | null,
  placement: TourPlacement = "bottom",
  viewportWidth = 1024,
  viewportHeight = 768
): { top: number; left: number; isCentered: boolean } {
  if (!targetRect || placement === "center") {
    return {
      top: Math.round(viewportHeight / 2),
      left: Math.round(viewportWidth / 2),
      isCentered: true,
    };
  }

  const margin = 14;
  const cardWidth = 360;
  const cardHeight = 220;

  let top = targetRect.bottom + margin;
  let left = targetRect.left;

  if (placement === "top") {
    top = Math.max(margin, targetRect.top - cardHeight - margin);
  } else if (placement === "left") {
    top = targetRect.top;
    left = Math.max(margin, targetRect.left - cardWidth - margin);
  } else if (placement === "right") {
    top = targetRect.top;
    left = Math.min(viewportWidth - cardWidth - margin, targetRect.right + margin);
  }

  left = Math.max(margin, Math.min(left, viewportWidth - cardWidth - margin));
  top = Math.max(margin, Math.min(top, viewportHeight - cardHeight - margin));

  return { top: Math.round(top), left: Math.round(left), isCentered: false };
}
