"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle2, AlertCircle } from "lucide-react";

interface HealthData {
  status: string;
  app: string;
  version: string;
}

interface SystemHealthBadgeProps {
  className?: string;
  variant?: "compact" | "detailed";
}

export function SystemHealthBadge({
  className = "",
  variant = "compact",
}: SystemHealthBadgeProps) {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/api/health`)
      .then((res) => {
        if (!res.ok) throw new Error("API unreachable");
        return res.json();
      })
      .then((data: HealthData) => {
        if (isMounted) {
          setHealth(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setHealth(null);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  if (variant === "compact") {
    return (
      <div
        className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900/90 border border-slate-800 text-[11px] font-mono transition-colors ${className}`}
        title={
          health?.status === "ok"
            ? `${health.app} v${health.version} is healthy`
            : loading
            ? "Probing backend API..."
            : "Backend offline (run docker-compose up)"
        }
      >
        <span
          className={`h-2 w-2 rounded-full ${
            health?.status === "ok"
              ? "bg-emerald-500 animate-pulse"
              : loading
              ? "bg-amber-400 animate-ping"
              : "bg-slate-500"
          }`}
        />
        {health?.status === "ok" ? (
          <span className="text-slate-300">
            API <span className="text-emerald-400 font-semibold">Online</span>
          </span>
        ) : loading ? (
          <span className="text-amber-400/90">Connecting...</span>
        ) : (
          <span className="text-slate-400">API Offline</span>
        )}
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center gap-3 px-4 py-2 rounded-xl bg-slate-900/90 border border-slate-800/80 text-xs font-mono shadow-sm ${className}`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`h-2.5 w-2.5 rounded-full ${
            health?.status === "ok"
              ? "bg-emerald-500 animate-pulse"
              : loading
              ? "bg-amber-400 animate-ping"
              : "bg-rose-500"
          }`}
        />
        {health?.status === "ok" ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        ) : loading ? (
          <Activity className="w-3.5 h-3.5 text-amber-400 animate-spin" />
        ) : (
          <AlertCircle className="w-3.5 h-3.5 text-slate-500" />
        )}
      </div>

      <div className="text-slate-300">
        {health?.status === "ok" ? (
          <span>
            Backend API Online •{" "}
            <span className="text-emerald-400 font-semibold">{health.app}</span>{" "}
            v{health.version}
          </span>
        ) : loading ? (
          <span className="text-slate-400">Probing FastAPI Backend (/api/health)...</span>
        ) : (
          <span className="text-slate-400">
            Backend Offline (Start via docker-compose up)
          </span>
        )}
      </div>
    </div>
  );
}
