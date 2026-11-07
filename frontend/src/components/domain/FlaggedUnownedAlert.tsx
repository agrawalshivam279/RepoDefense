"use client";

import React from "react";
import { ShieldAlert } from "lucide-react";
import { SymbolOwnershipCard } from "@/components/domain/SymbolOwnershipCard";
import type { SymbolOwnership } from "@/types/ownership";

interface FlaggedUnownedAlertProps {
  flaggedSymbols: SymbolOwnership[];
}

export function FlaggedUnownedAlert({ flaggedSymbols }: FlaggedUnownedAlertProps) {
  if (flaggedSymbols.length === 0) {
    return null;
  }

  return (
    <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-950/20 space-y-3">
      <div className="flex items-center gap-2 text-rose-400">
        <ShieldAlert className="w-5 h-5 flex-shrink-0" />
        <h3 className="text-sm font-bold font-mono uppercase tracking-wider">
          Flagged Unowned Load-Bearing Code ({flaggedSymbols.length})
        </h3>
      </div>
      <p className="text-xs text-slate-300 font-mono">
        The candidate authored 0% or &lt;20% of these critical architectural components. RepoDefense
        will probe deep implementation tradeoffs to verify genuine comprehension.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        {flaggedSymbols.slice(0, 4).map((sym) => (
          <SymbolOwnershipCard key={sym.symbol_id} symbol={sym} />
        ))}
      </div>
    </div>
  );
}
