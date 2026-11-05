"use client";

import { useState } from "react";
import {
  ShieldAlert,
  Terminal,
  FileCode2,
  Award,
  ChevronRight,
  Flame,
  CheckCircle2,
  Bot,
  User,
} from "lucide-react";

interface ShowcaseStage {
  id: string;
  stageName: string;
  badge: string;
  badgeColor: string;
  speaker: "interviewer" | "candidate" | "system";
  title: string;
  codeSnippet?: {
    file: string;
    lines: string;
    code: string;
  };
  content: string;
  detail?: string;
  score?: string;
}

const SHOWCASE_STAGES: ShowcaseStage[] = [
  {
    id: "evidence",
    stageName: "Stage 01: Evidence",
    badge: "AST Symbol",
    badgeColor: "border-blue-500/30 text-blue-400 bg-blue-500/10",
    speaker: "system",
    title: "Deterministic AST Extraction & Indexing",
    codeSnippet: {
      file: "backend/app/ai/fsm.py",
      lines: "L120-136",
      code: `class DefenseSessionStateMachine:\n    """Deterministic FSM controlling interview progression."""\n    def __init__(self, session_id: str, redis_client: Redis):\n        self.session_id = session_id\n        self.redis = redis_client\n        self.state = DefenseStage.QUESTION_ACTIVE`,
    },
    content:
      "Tree-sitter deterministic parser indexes the AST symbol `DefenseSessionStateMachine` in `backend/app/ai/fsm.py`, identifying it as a load-bearing architectural component.",
    detail: "Indexed via all-MiniLM-L6-v2 (384-dim) & pgvector cosine retrieval.",
  },
  {
    id: "question",
    stageName: "Stage 02 & 03: Claim & Interrogation",
    badge: "Interviewer Question",
    badgeColor: "border-indigo-500/30 text-indigo-400 bg-indigo-500/10",
    speaker: "interviewer",
    title: "Principal Engineer Architectural Inquiry",
    content:
      '"Looking at your `fsm.py`, you opted for a rigid Python state machine instead of an autonomous multi-agent framework like AutoGPT or CrewAI. Why avoid autonomous agents here, and what happens to turn predictability?"',
    detail: "Question mathematically grounded in AST class hierarchy and file imports.",
  },
  {
    id: "defense",
    stageName: "Stage 04: Candidate Defense",
    badge: "Candidate Argument",
    badgeColor: "border-purple-500/30 text-purple-400 bg-purple-500/10",
    speaker: "candidate",
    title: "Evidence-Backed Architectural Reasoning",
    content:
      '"Autonomous agent loops suffer from non-deterministic branching, context drift, and unbounded token costs during timed interviews. A deterministic FSM guarantees our 7-stage loop and isolates LLM calls to pure, testable functions."',
    detail: "Candidate addresses system determinism and API failure surface.",
  },
  {
    id: "stress_test",
    stageName: "Stage 05: Stress Test Injection",
    badge: "Hypothetical Constraint",
    badgeColor: "border-amber-500/30 text-amber-400 bg-amber-500/10",
    speaker: "interviewer",
    title: "Production Failure Scenario Injected",
    content:
      '"Fair architectural justification. But under a 10,000 req/sec surge, what happens if your Redis broker drops connection mid-transition between EVALUATION and MENTOR? How do you prevent orphaned session states?"',
    detail: "Principal Engineer injects hypothetical distributed system failure constraint.",
  },
  {
    id: "evaluation",
    stageName: "Stage 06 & 07: Evaluation & Mentorship",
    badge: "Rubric Scorecard",
    badgeColor: "border-emerald-500/30 text-emerald-400 bg-emerald-500/10",
    speaker: "system",
    title: "Objective Architectural Score & Feedback",
    score: "9.4 / 10.0",
    content:
      "Verdict: Certified Principal Defense. Demonstrated exceptional grasp of state determinism, bounded execution contexts, and transactional failure modes.",
    detail:
      "Actionable Takeaway: Introduce Redis MULTI/EXEC or atomic Lua scripts to prevent distributed state bifurcation.",
  },
];

export function DefenseShowcaseCard() {
  const [activeIdx, setActiveIdx] = useState<number>(0);
  const current = SHOWCASE_STAGES[activeIdx];

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl overflow-hidden backdrop-blur-md">
      {/* Top Interactive Stage Strip */}
      <div className="border-b border-slate-800 bg-slate-950/60 p-2 sm:p-3 overflow-x-auto flex items-center gap-1.5 sm:gap-2">
        {SHOWCASE_STAGES.map((stage, idx) => (
          <button
            key={stage.id}
            onClick={() => setActiveIdx(idx)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all flex items-center gap-1.5 ${
              activeIdx === idx
                ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                activeIdx === idx ? "bg-emerald-400" : "bg-slate-600"
              }`}
            />
            {stage.stageName.split(":")[0]}
          </button>
        ))}
      </div>

      {/* Main Showcase Body */}
      <div className="p-6 sm:p-8 space-y-6">
        {/* Stage Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <span
              className={`inline-block px-2.5 py-0.5 rounded-md text-[11px] font-mono border font-semibold ${current.badgeColor}`}
            >
              {current.badge}
            </span>
            <h3 className="text-lg font-bold text-white tracking-tight">
              {current.title}
            </h3>
          </div>

          {current.score && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono font-bold text-sm">
              <Award className="w-4 h-4" />
              <span>Score: {current.score}</span>
            </div>
          )}
        </div>

        {/* Code Snippet Box (if present) */}
        {current.codeSnippet && (
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs space-y-2">
            <div className="flex items-center justify-between text-slate-400 text-[11px] pb-2 border-b border-slate-800/80">
              <div className="flex items-center gap-1.5">
                <FileCode2 className="w-3.5 h-3.5 text-blue-400" />
                <span>{current.codeSnippet.file}</span>
              </div>
              <span className="text-slate-500">{current.codeSnippet.lines}</span>
            </div>
            <pre className="text-slate-300 overflow-x-auto leading-relaxed pt-1">
              <code>{current.codeSnippet.code}</code>
            </pre>
          </div>
        )}

        {/* Dialogue Card */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-5 space-y-3">
          <div className="flex items-center gap-2.5">
            <div
              className={`p-1.5 rounded-lg border ${
                current.speaker === "interviewer"
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                  : current.speaker === "candidate"
                  ? "bg-purple-500/10 border-purple-500/30 text-purple-400"
                  : "bg-blue-500/10 border-blue-500/30 text-blue-400"
              }`}
            >
              {current.speaker === "interviewer" ? (
                <Bot className="w-4 h-4" />
              ) : current.speaker === "candidate" ? (
                <User className="w-4 h-4" />
              ) : (
                <Terminal className="w-4 h-4" />
              )}
            </div>
            <span className="text-xs font-semibold text-slate-300 capitalize">
              {current.speaker === "interviewer"
                ? "AI Principal Engineer"
                : current.speaker === "candidate"
                ? "Candidate Defense"
                : "RepoDefense Engine"}
            </span>
          </div>

          <p className="text-sm text-slate-200 leading-relaxed font-sans">
            {current.content}
          </p>

          {current.detail && (
            <div className="flex items-center gap-2 text-xs text-slate-400 pt-2 border-t border-slate-800/60 font-mono">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>{current.detail}</span>
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-1.5">
            {SHOWCASE_STAGES.map((_, i) => (
              <span
                key={i}
                className={`h-1.5 rounded-full transition-all ${
                  i === activeIdx ? "w-6 bg-emerald-400" : "w-1.5 bg-slate-700"
                }`}
              />
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() =>
                setActiveIdx((prev) => (prev > 0 ? prev - 1 : SHOWCASE_STAGES.length - 1))
              }
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() =>
                setActiveIdx((prev) => (prev + 1) % SHOWCASE_STAGES.length)
              }
              className="px-3.5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-xs text-slate-950 font-semibold transition-colors flex items-center gap-1 shadow-sm"
            >
              Next Stage <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
