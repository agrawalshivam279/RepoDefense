"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";
import type { BreadcrumbItem } from "@/types/learning";

export interface LearningHubBreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function LearningHubBreadcrumbs({ items, className = "" }: LearningHubBreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb" className={`flex items-center text-xs font-mono text-zinc-400 ${className}`}>
      <ol className="flex items-center flex-wrap gap-1.5 list-none m-0 p-0">
        <li className="flex items-center">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1 text-zinc-400 hover:text-emerald-400 transition-colors"
          >
            <Home className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Dashboard</span>
          </Link>
        </li>

        {items.map((item, index) => {
          const isLast = index === items.length - 1 || item.isCurrent;
          const Icon = item.icon;

          return (
            <li key={`${item.label}-${index}`} className="flex items-center gap-1.5">
              <ChevronRight className="h-3.5 w-3.5 text-zinc-600 shrink-0" aria-hidden="true" />
              {isLast || !item.href ? (
                <span
                  aria-current={isLast ? "page" : undefined}
                  className={`inline-flex items-center gap-1 truncate max-w-[240px] sm:max-w-xs ${
                    isLast ? "text-emerald-400 font-semibold" : "text-zinc-300"
                  }`}
                  title={item.label}
                >
                  {Icon && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
                  <span>{item.label}</span>
                </span>
              ) : (
                <Link
                  href={item.href}
                  className="inline-flex items-center gap-1 text-zinc-400 hover:text-zinc-200 transition-colors truncate max-w-[240px] sm:max-w-xs"
                  title={item.label}
                >
                  {Icon && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
                  <span>{item.label}</span>
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
