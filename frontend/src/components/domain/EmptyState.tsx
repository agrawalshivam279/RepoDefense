"use client";

import type { LucideIcon } from "lucide-react";
import { FolderGit2, HelpCircle, Lightbulb } from "lucide-react";

interface ActionConfig {
  label: string;
  onClick: () => void;
  icon?: LucideIcon;
  disabled?: boolean;
}

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  primaryAction?: ActionConfig;
  secondaryAction?: ActionConfig;
  tips?: string[];
  className?: string;
}

export function EmptyState({
  icon: Icon = FolderGit2,
  title,
  description,
  primaryAction,
  secondaryAction,
  tips,
  className = "",
}: EmptyStateProps) {
  const PrimaryIcon = primaryAction?.icon;
  const SecondaryIcon = secondaryAction?.icon || HelpCircle;

  return (
    <div
      className={`rounded-xl border border-slate-800/90 bg-slate-900/40 p-8 sm:p-12 text-center max-w-2xl mx-auto shadow-inner ${className}`}
    >
      <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shadow-sm shadow-emerald-500/5">
        <Icon className="w-7 h-7" />
      </div>

      <h3 className="text-base sm:text-lg font-bold text-white mb-2">
        {title}
      </h3>

      <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto leading-relaxed mb-6">
        {description}
      </p>

      {/* Action Buttons */}
      {(primaryAction || secondaryAction) && (
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-6">
          {primaryAction && (
            <button
              type="button"
              onClick={primaryAction.onClick}
              disabled={primaryAction.disabled}
              className="w-full sm:w-auto px-4 py-2.5 rounded-lg bg-emerald-400 hover:bg-emerald-300 disabled:opacity-50 text-slate-950 text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-sm shadow-emerald-400/10 cursor-pointer"
            >
              {PrimaryIcon && <PrimaryIcon className="w-4 h-4" />}
              <span>{primaryAction.label}</span>
            </button>
          )}

          {secondaryAction && (
            <button
              type="button"
              onClick={secondaryAction.onClick}
              className="w-full sm:w-auto px-3.5 py-2.5 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-950/60 hover:bg-slate-900 text-xs font-medium text-slate-300 hover:text-white flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <SecondaryIcon className="w-3.5 h-3.5 text-slate-400" />
              <span>{secondaryAction.label}</span>
            </button>
          )}
        </div>
      )}

      {/* Optional Pro Tips */}
      {tips && tips.length > 0 && (
        <div className="pt-6 border-t border-slate-800/60 text-left">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400 mb-2">
            <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
            <span>Onboarding Tips</span>
          </div>
          <ul className="space-y-1.5">
            {tips.map((tip, idx) => (
              <li
                key={idx}
                className="text-[11px] text-slate-400 flex items-start gap-2 leading-relaxed"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400/60 mt-1.5 flex-shrink-0" />
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
