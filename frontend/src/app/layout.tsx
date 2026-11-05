import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { AuthStatus } from "@/components/domain/AuthStatus";
import { SystemHealthBadge } from "@/components/domain/SystemHealthBadge";

export const metadata: Metadata = {
  title: "RepoDefense | Architectural Stress-Testing for Codebases",
  description:
    "Prove that you understand — and can defend — the software you built. Automated evidence-based technical defense simulation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-[#0b0f19] text-slate-100 min-h-screen flex flex-col font-sans selection:bg-emerald-500/20 selection:text-emerald-300">
        <header className="border-b border-slate-800/80 bg-[#0b0f19]/90 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 group">
              <span className="h-8 w-8 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center font-black text-emerald-400 text-sm shadow-lg shadow-emerald-500/10 group-hover:border-emerald-500/50 transition-colors">
                RD
              </span>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                RepoDefense
              </span>
            </Link>

            <nav className="flex items-center gap-4 sm:gap-6 text-xs sm:text-sm text-slate-300">
              <Link
                href="/#showcase"
                className="hover:text-white transition-colors hidden md:inline-block"
              >
                Showcase
              </Link>
              <Link
                href="/#core-loop"
                className="hover:text-white transition-colors hidden sm:inline-block"
              >
                Core Loop
              </Link>
              <Link
                href="/#differentiators"
                className="hover:text-white transition-colors hidden lg:inline-block"
              >
                Why RepoDefense
              </Link>
              <a
                href="https://github.com/agrawalshivam279/RepoDefense"
                target="_blank"
                rel="noreferrer"
                className="hover:text-white transition-colors hidden sm:inline-block"
              >
                GitHub
              </a>

              <div className="hidden sm:flex items-center">
                <SystemHealthBadge variant="compact" />
              </div>

              <AuthStatus />
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-slate-800/80 bg-slate-950/60 py-10 text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="space-y-1.5 text-center sm:text-left">
              <div className="flex items-center justify-center sm:justify-start gap-2">
                <span className="font-bold text-slate-300 text-sm">RepoDefense</span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-[10px] font-mono text-emerald-400 font-semibold">
                  MVP Live
                </span>
              </div>
              <p className="text-slate-400 max-w-sm">
                Prove that you understand — and can defend — the software you built.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-2 font-mono text-[11px] text-slate-400">
              <span className="px-2 py-1 rounded-md bg-slate-900 border border-slate-800">Next.js 15</span>
              <span className="px-2 py-1 rounded-md bg-slate-900 border border-slate-800">FastAPI</span>
              <span className="px-2 py-1 rounded-md bg-slate-900 border border-slate-800">PostgreSQL 17 + pgvector</span>
              <span className="px-2 py-1 rounded-md bg-slate-900 border border-slate-800">Tree-sitter</span>
              <span className="px-2 py-1 rounded-md bg-slate-900 border border-slate-800">LiteLLM</span>
            </div>

            <div className="text-center sm:text-right space-y-1">
              <p>© 2026 RepoDefense. Evidence-grounded technical assessment.</p>
              <div className="flex items-center justify-center sm:justify-end gap-3 text-slate-400">
                <a
                  href="https://github.com/agrawalshivam279/RepoDefense"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-emerald-400 transition-colors"
                >
                  GitHub Repository
                </a>
                <span>•</span>
                <a
                  href="/#core-loop"
                  className="hover:text-emerald-400 transition-colors"
                >
                  7-Stage Core Loop
                </a>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
