"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
  CheckCircle2,
  XCircle,
  Code2,
  Database,
  Lock,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { DefenseShowcaseCard } from "@/components/domain/DefenseShowcaseCard";
import { SystemHealthBadge } from "@/components/domain/SystemHealthBadge";

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
    desc: "Architectural decisions, data contracts, and design patterns claimed by code symbols are surfaced.",
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

const DIFFERENTIATORS = [
  {
    feature: "Assessment Basis",
    traditional: "Generic LeetCode puzzles (reverse a linked list)",
    chatgpt: "Superficial chat prompts prone to sycophancy",
    repodefense: "Grounded strictly in your actual GitHub repository AST",
  },
  {
    feature: "Hallucination Defense",
    traditional: "Rigid unit test harnesses, zero system thinking",
    chatgpt: "Easily tricked by technical jargon and confidence",
    repodefense: "Demands line-level code citations; rejects hand-waving",
  },
  {
    feature: "Production Stress Testing",
    traditional: "None (only checks asymptotic O(N) runtime)",
    chatgpt: "Passive answers with no active architectural pushback",
    repodefense: "Injects 10k req/sec traffic spikes and network partition scenarios",
  },
  {
    feature: "Security & Execution",
    traditional: "Executes untrusted code in heavy sandboxes",
    chatgpt: "No code inspection or execution bounds",
    repodefense: "100% static analysis; zero arbitrary code execution risk",
  },
];

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsAuthenticated(!!session?.user);
    });
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24 space-y-28">
      {/* Hero Section */}
      <section className="text-center space-y-8 max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-xs font-semibold text-emerald-400 shadow-sm">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Evidence-Grounded Architectural Stress-Testing</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-white leading-tight">
          Prove that you understand — and can defend — the software you built.
        </h1>

        <p className="text-lg sm:text-xl text-slate-400 leading-relaxed max-w-3xl mx-auto">
          RepoDefense indexes your repository with deterministic Tree-sitter AST parsing,
          grounds claims in vector evidence, and conducts a rigorous oral-style architectural
          defense against an AI Principal Engineer.
        </p>

        <div className="flex justify-center">
          <SystemHealthBadge variant="detailed" />
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <Link
            href={isAuthenticated ? "/dashboard" : "/signup"}
            className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 font-semibold text-slate-950 shadow-lg shadow-emerald-500/25 transition-all flex items-center justify-center gap-2"
          >
            {isAuthenticated ? "Go to Dashboard" : "Start Defense"}
            <ArrowRight className="w-4 h-4" />
          </Link>
          <a
            href="#showcase"
            className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 font-semibold text-slate-200 transition-all text-center"
          >
            Explore Interactive Demo
          </a>
        </div>
      </section>

      {/* Interactive Showcase Section */}
      <section id="showcase" className="space-y-8 scroll-mt-24">
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">
            Live Preview
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            See the Defense Loop in Action
          </h2>
          <p className="text-slate-400 text-sm">
            Step through a simulated defense turn grounded in real RepoDefense state machine code.
          </p>
        </div>

        <div className="max-w-4xl mx-auto">
          <DefenseShowcaseCard />
        </div>
      </section>

      {/* Core Loop Section */}
      <section id="core-loop" className="space-y-12 scroll-mt-24">
        <div className="text-center space-y-3">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">
            State Machine Architecture
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            The 7-Stage Interaction Engine
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
                className={`p-6 rounded-2xl bg-gradient-to-b ${item.color} bg-slate-900/60 backdrop-blur-sm border flex flex-col justify-between space-y-4 hover:border-slate-700 transition-all`}
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-slate-500">
                      STAGE {item.step}
                    </span>
                    <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/50">
                      <Icon className="w-4 h-4 text-slate-300" />
                    </div>
                  </div>
                  <h3 className="text-base font-bold text-white tracking-tight">
                    {item.title}
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Differentiators Section */}
      <section id="differentiators" className="space-y-10 scroll-mt-24">
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">
            Comparison
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Why RepoDefense vs Generic Approaches
          </h2>
          <p className="text-slate-400 text-sm">
            Evaluating real engineering capability requires repository grounding, not memorized puzzles.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border border-slate-800 rounded-2xl overflow-hidden bg-slate-900/40">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-300 font-mono">
              <tr>
                <th className="p-4">Capability</th>
                <th className="p-4 text-slate-400">LeetCode / Coding Quizzes</th>
                <th className="p-4 text-slate-400">Generic AI Chat (ChatGPT)</th>
                <th className="p-4 text-emerald-400 bg-emerald-500/5">RepoDefense</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {DIFFERENTIATORS.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="p-4 font-semibold text-white whitespace-nowrap">{row.feature}</td>
                  <td className="p-4 text-slate-400">{row.traditional}</td>
                  <td className="p-4 text-slate-400">{row.chatgpt}</td>
                  <td className="p-4 font-medium text-emerald-300 bg-emerald-500/5">{row.repodefense}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Bottom CTA Banner */}
      <section className="rounded-3xl border border-emerald-500/20 bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-950 p-8 sm:p-12 text-center space-y-6 shadow-2xl">
        <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
          Ready to defend your architecture?
        </h2>
        <p className="text-slate-400 text-sm sm:text-base max-w-xl mx-auto leading-relaxed">
          Connect your GitHub repository and survive a 45-minute architectural defense
          against an AI Principal Engineer.
        </p>
        <div className="pt-2">
          <Link
            href={isAuthenticated ? "/dashboard" : "/signup"}
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 font-bold text-slate-950 shadow-lg shadow-emerald-500/25 transition-all text-sm"
          >
            {isAuthenticated ? "Open Dashboard" : "Start Your Free Defense"}
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
