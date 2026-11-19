"use client";

import { useCallback, useEffect, useState } from "react";
import type { TourConfig, TourRect, TourStep } from "@/types/onboarding";

const STORAGE_PREFIX = "repodefense_tour_";

export function useOnboardingTour({
  tourId,
  steps,
  autoStart = false,
  onComplete,
  onSkip,
}: TourConfig) {
  const [isActive, setIsActive] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<TourRect | null>(null);
  const [hasCompletedTour, setHasCompletedTour] = useState(true);

  const storageKey = `${STORAGE_PREFIX}${tourId}_completed`;

  // SSR-safe check on initial mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      const completed = stored === "true";
      setHasCompletedTour(completed);
      if (autoStart && !completed && steps.length > 0) {
        setIsActive(true);
      }
    } catch {
      // LocalStorage unavailable in SSR or sandboxed iframes
      setHasCompletedTour(false);
    }
  }, [storageKey, autoStart, steps.length]);

  const updateTargetRect = useCallback(() => {
    if (!isActive || currentStepIndex >= steps.length) {
      setTargetRect(null);
      return;
    }

    const currentStep = steps[currentStepIndex];
    if (!currentStep.targetSelector) {
      setTargetRect(null);
      return;
    }

    try {
      const el = document.querySelector(currentStep.targetSelector);
      if (el) {
        const rect = el.getBoundingClientRect();
        setTargetRect({
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
          bottom: rect.bottom,
          right: rect.right,
        });
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } else {
        setTargetRect(null);
      }
    } catch {
      setTargetRect(null);
    }
  }, [isActive, currentStepIndex, steps]);

  // Recalculate target position on step change, resize, or scroll
  useEffect(() => {
    if (!isActive) return;
    updateTargetRect();

    const handleWindowEvents = () => {
      updateTargetRect();
    };

    window.addEventListener("resize", handleWindowEvents, { passive: true });
    window.addEventListener("scroll", handleWindowEvents, { passive: true });

    return () => {
      window.removeEventListener("resize", handleWindowEvents);
      window.removeEventListener("scroll", handleWindowEvents);
    };
  }, [isActive, updateTargetRect]);

  const markCompleted = useCallback(() => {
    try {
      localStorage.setItem(storageKey, "true");
    } catch {
      // ignore storage write errors
    }
    setHasCompletedTour(true);
  }, [storageKey]);

  const startTour = useCallback(
    (initialIndex = 0) => {
      if (steps.length === 0) return;
      setCurrentStepIndex(Math.min(Math.max(0, initialIndex), steps.length - 1));
      setIsActive(true);
    },
    [steps.length]
  );

  const finishTour = useCallback(() => {
    setIsActive(false);
    markCompleted();
    onComplete?.();
  }, [markCompleted, onComplete]);

  const skipTour = useCallback(() => {
    setIsActive(false);
    markCompleted();
    onSkip?.();
  }, [markCompleted, onSkip]);

  const nextStep = useCallback(() => {
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex((prev) => prev + 1);
    } else {
      finishTour();
    }
  }, [currentStepIndex, steps.length, finishTour]);

  const prevStep = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex((prev) => prev - 1);
    }
  }, [currentStepIndex]);

  const resetTour = useCallback(() => {
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
    setHasCompletedTour(false);
    startTour(0);
  }, [storageKey, startTour]);

  // Keyboard navigation
  useEffect(() => {
    if (!isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        skipTour();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        nextStep();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        prevStep();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isActive, nextStep, prevStep, skipTour]);

  const currentStep: TourStep | null =
    isActive && currentStepIndex < steps.length ? steps[currentStepIndex] : null;

  return {
    isActive,
    currentStep,
    currentStepIndex,
    totalSteps: steps.length,
    targetRect,
    hasCompletedTour,
    startTour,
    nextStep,
    prevStep,
    skipTour,
    finishTour,
    resetTour,
  };
}
