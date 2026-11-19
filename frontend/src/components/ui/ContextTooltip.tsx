"use client";

import React, { useId, useState } from "react";

interface ContextTooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  placement?: "top" | "bottom" | "left" | "right";
  className?: string;
}

export function ContextTooltip({
  content,
  children,
  placement = "top",
  className = "",
}: ContextTooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipId = useId();

  const getPositionClasses = () => {
    switch (placement) {
      case "bottom":
        return "top-full left-1/2 -translate-x-1/2 mt-2";
      case "left":
        return "right-full top-1/2 -translate-y-1/2 mr-2";
      case "right":
        return "left-full top-1/2 -translate-y-1/2 ml-2";
      case "top":
      default:
        return "bottom-full left-1/2 -translate-x-1/2 mb-2";
    }
  };

  const getArrowClasses = () => {
    switch (placement) {
      case "bottom":
        return "bottom-full left-1/2 -translate-x-1/2 border-b-slate-800 border-x-transparent border-t-transparent border-4";
      case "left":
        return "left-full top-1/2 -translate-y-1/2 border-l-slate-800 border-y-transparent border-r-transparent border-4";
      case "right":
        return "right-full top-1/2 -translate-y-1/2 border-r-slate-800 border-y-transparent border-l-transparent border-4";
      case "top":
      default:
        return "top-full left-1/2 -translate-x-1/2 border-t-slate-800 border-x-transparent border-b-transparent border-4";
    }
  };

  // Merge aria-describedby onto focused child control directly
  let triggerChild = children;
  if (React.isValidElement<Record<string, unknown>>(children)) {
    const existingDescribedBy = children.props["aria-describedby"] as string | undefined;
    const mergedDescribedBy = isVisible
      ? [existingDescribedBy, tooltipId].filter(Boolean).join(" ")
      : existingDescribedBy;
    triggerChild = React.cloneElement(children, {
      "aria-describedby": mergedDescribedBy,
    });
  }

  return (
    <div
      className={`relative inline-flex items-center ${className}`}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
      onKeyDown={(e) => {
        if (e.key === "Escape") setIsVisible(false);
      }}
    >
      {triggerChild}
      {isVisible && (
        <div
          id={tooltipId}
          role="tooltip"
          className={`absolute z-50 pointer-events-none transition-all duration-150 animate-in fade-in-0 zoom-in-95 ${getPositionClasses()}`}
        >
          <div className="relative bg-slate-900 border border-slate-700/80 text-slate-200 text-[11px] font-medium px-2.5 py-1.5 rounded-lg shadow-xl whitespace-nowrap max-w-xs break-words">
            {content}
            <div className={`absolute w-0 h-0 pointer-events-none ${getArrowClasses()}`} />
          </div>
        </div>
      )}
    </div>
  );
}
