"use client";

import { useEffect, useState } from "react";
import {
  ShieldCheck,
  Cpu,
  Layers,
  Terminal,
  Activity,
  Award,
  BookOpen,
  ArrowRight,
  Sparkles,
} from "lucide-react";

interface HealthData {
  status: string;
  app: string;
  version: string;
}

const CORE_LOOP_STEPS = [
  {
    step: "01",
    title: "Evidence",
    desc: "Deterministic Tree-sitter AST extraction & pgvector semantic chunking index load-bearing components.",
    icon: Layers,
    color: "from-blue-500/20 to-cyan-500/10 border-blue-500/30",
  },
  {
    step: "02",
    title: "Claim",
    desc: "Architectural decisions and design patterns claimed by code symbols are surfaced.",
    icon: Terminal,
    color: "from-indigo-500/20 to-blue-500/10 border-indigo-500/30",
  },
  {
    step: "03",
    title: "Defense",
    desc: "Defend your design choices, trade-offs, and boundary isolation in a structured interview dialogue.",
    icon: ShieldCheck,
    color: "from-purple-500/20 to-indigo-500/10 border-purple-500/30",
  },
  {
    step: "04",
    title: "Stress Test",
    desc: "AI Principal Engineer persona injects 10k req/sec spikes, dropped connections, and scale bottlenecks.",
    icon: Activity,
    color: "from-amber-500/20 to-rose-500/10 border-amber-500/30",
  },
  {
    step: "05",
    title: "Evaluation",
    desc: "Objective rubric scoring grounded strictly in repository facts — no buzzwords or hand-waving.",
    icon: Award,
    color: "from-emerald-500/20 to-teal-500/10 border-emerald-500/30",
  },
  {
    step: "06",
    title: "Mentor",
    desc: "Targeted architectural critiques highlighting concurrency traps, memory leaks, and anti-patterns.",
    icon: BookOpen,
    color: "from-blue-500/20 to-violet-500/10 border-blue-500/30",
  },
  {
    step: "07",
    title: "Re-test",
    desc: "Adaptive follow-up challenges to verify that architectural blind spots are fully mastered.",
    icon: Cpu,
    color: "from-teal-500/20 to-emerald-500/10 border-teal-500/30",
  },
];

export default function Home() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiUrl}/api/health`)
      .then((res) => {
        if (!res.ok) throw new Error("API unreachable");
        return res.json();
      })
      .then((data: HealthData) => {
        setHealth(data);
        setLoading(false);
      })
      .catch(() => {
        setHealth(null);
        setLoading(false);
      });
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24 space-y-24">
      {/* Hero Section */}
      <section className="text-center space-y-8 max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/30 bg-blue-500/10 text-xs font-semibold text-blue-400">
          <Sparkles className="w-3.5 h-3.5" />
          Evidence-Grounded Architectural Stress-Testing
        </div>

        <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-white leading-tight">
          Prove that you understand — and can defend — the software you built.
        </h1>

        <p className="text-lg sm:text-xl text-slate-400 leading-relaxed">
          RepoDefense indexes your repository with deterministic Tree-sitter AST parsing,
          grounds claims in vector evidence, and conducts a rigorous oral-style architectural
          defense against an AI Principal Engineer.
        </p>

        {/* Backend Connectivity Status Badge */}
        <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-lg bg-slate-900/90 border border-slate-800 text-xs font-mono text-slate-300">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              health?.status === "ok"
                ? "bg-emerald-500 animate-pulse"
                : loading
                ? "bg-amber-400 animate-ping"
                : "bg-slate-500"
            }`}
          />
          {health?.status === "ok" ? (
            <span>
              Backend API Online • <span className="text-emerald-400">{health.app}</span> v{health.version}
            </span>
          ) : loading ? (
            <span>Probing FastAPI Backend (/api/health)...</span>
          ) : (
            <span className="text-slate-400">
              Backend Offline (Start via docker-compose up)
            </span>
          )}
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <button
            type="button"
            className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-500 font-semibold text-white shadow-lg shadow-blue-600/25 transition-all flex items-center justify-center gap-2"
          >
            Start Defense <ArrowRight className="w-4 h-4" />
          </button>
          <a
            href="#core-loop"
            className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 font-semibold text-slate-200 transition-all text-center"
          >
            Explore 7-Stage Core Loop
          </a>
        </div>
      </section>

      {/* Core Loop Section */}
      <section id="core-loop" className="space-y-12">
        <div className="text-center space-y-3">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            The RepoDefense Interaction Engine
          </h2>
          <p className="text-slate-400 text-sm max-w-xl mx-auto">
            A state-machine governed loop moving from codebase AST evidence to production
            stress tests, rubric evaluation, and targeted re-testing.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {CORE_LOOP_STEPS.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.step}
                className={`p-6 rounded-2xl border bg-gradient-to-b ${item.color} backdrop-blur-sm space-y-4 flex flex-col justify-between hover:scale-[1.02] transition-transform`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-400 tracking-wider">
                    STAGE {item.step}
                  </span>
                  <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-blue-400">
                    <Icon className="w-4 h-4" />
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="text-lg font-bold text-white">{item.title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{item.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
