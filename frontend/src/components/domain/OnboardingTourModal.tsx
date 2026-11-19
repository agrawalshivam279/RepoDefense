"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, Compass, Sparkles, X } from "lucide-react";
import { calculateCardPosition } from "@/lib/onboarding";
import type { TourRect, TourStep } from "@/types/onboarding";

interface OnboardingTourModalProps {
  isActive: boolean;
  currentStep: TourStep | null;
  currentStepIndex: number;
  totalSteps: number;
  targetRect: TourRect | null;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
  onFinish: () => void;
}

export function OnboardingTourModal({
  isActive,
  currentStep,
  currentStepIndex,
  totalSteps,
  targetRect,
  onNext,
  onPrev,
  onSkip,
  onFinish,
}: OnboardingTourModalProps) {
  const [mounted, setMounted] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Focus management & trap
  useEffect(() => {
    if (isActive) {
      previousActiveElementRef.current = document.activeElement as HTMLElement | null;
      const timer = setTimeout(() => {
        const focusable = modalRef.current?.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable && focusable.length > 0) {
          focusable[0].focus();
        }
      }, 50);
      return () => clearTimeout(timer);
    } else if (previousActiveElementRef.current) {
      previousActiveElementRef.current.focus();
    }
  }, [isActive, currentStepIndex]);

  if (!mounted || !isActive || !currentStep) return null;

  const isLastStep = currentStepIndex === totalSteps - 1;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Tab") {
      const focusable = modalRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  };

  const vpW = typeof window !== "undefined" ? window.innerWidth : 1024;
  const vpH = typeof window !== "undefined" ? window.innerHeight : 768;
  const pos = calculateCardPosition(targetRect, currentStep.placement, vpW, vpH, 360, 240);

  const cardStyle: React.CSSProperties = pos.isCentered
    ? {
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        maxWidth: "420px",
        width: "90vw",
        zIndex: 60,
      }
    : {
        position: "fixed",
        top: `${pos.top}px`,
        left: `${pos.left}px`,
        width: `${pos.width}px`,
        zIndex: 60,
      };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-step-title"
      onKeyDown={handleKeyDown}
      className="fixed inset-0 z-50 pointer-events-auto"
    >
      {/* 1. Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={onSkip}
      />

      {/* 2. Target Spotlight Halo Ring */}
      {targetRect && (
        <div
          className="fixed pointer-events-none rounded-xl ring-4 ring-emerald-400/50 ring-offset-2 ring-offset-slate-950 transition-all duration-300"
          style={{
            top: `${Math.max(0, targetRect.top - 4)}px`,
            left: `${Math.max(0, targetRect.left - 4)}px`,
            width: `${targetRect.width + 8}px`,
            height: `${targetRect.height + 8}px`,
            zIndex: 55,
          }}
        />
      )}

      {/* 3. Floating Step Card */}
      <div
        ref={modalRef}
        style={cardStyle}
        className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 text-slate-100 shadow-2xl shadow-black/80 space-y-3.5 animate-in fade-in-0 zoom-in-95"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Compass className="w-3.5 h-3.5" />
            </span>
            <span className="text-[11px] font-mono font-semibold text-emerald-400 uppercase tracking-wider">
              Step {currentStepIndex + 1} of {totalSteps}
            </span>
            {currentStep.badge && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-medium">
                {currentStep.badge}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onSkip}
            aria-label="Skip onboarding tour"
            className="text-slate-400 hover:text-white p-1 rounded-md transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div>
          <h3 id="tour-step-title" className="text-sm font-bold text-white mb-1 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
            <span>{currentStep.title}</span>
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            {currentStep.description}
          </p>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
          <button
            type="button"
            onClick={onSkip}
            className="text-[11px] font-medium text-slate-400 hover:text-slate-200 transition-colors"
          >
            Skip tour
          </button>

          <div className="flex items-center gap-2">
            {currentStepIndex > 0 && (
              <button
                type="button"
                onClick={onPrev}
                className="px-2.5 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-950 text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1 transition-colors"
              >
                <ArrowLeft className="w-3 h-3" />
                <span>Back</span>
              </button>
            )}
            <button
              type="button"
              onClick={isLastStep ? onFinish : onNext}
              className="px-3 py-1.5 rounded-lg bg-emerald-400 hover:bg-emerald-300 text-slate-950 text-xs font-semibold flex items-center gap-1 transition-colors shadow-sm"
            >
              <span>{isLastStep ? "Finish" : "Next"}</span>
              {isLastStep ? (
                <Check className="w-3 h-3" />
              ) : (
                <ArrowRight className="w-3 h-3" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
