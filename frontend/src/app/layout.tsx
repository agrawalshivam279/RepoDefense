import type { Metadata } from "next";
import "./globals.css";

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
      <body className="antialiased bg-[#0b0f19] text-slate-100 min-h-screen flex flex-col">
        <header className="border-b border-slate-800/80 bg-[#0b0f19]/80 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center font-black text-white text-lg shadow-lg shadow-blue-500/20">
                RD
              </span>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                RepoDefense
              </span>
            </div>
            <nav className="flex items-center gap-6 text-sm text-slate-300">
              <a
                href="#core-loop"
                className="hover:text-white transition-colors"
              >
                Core Loop
              </a>
              <a
                href="https://github.com/agrawalshivam279/RepoDefense"
                target="_blank"
                rel="noreferrer"
                className="hover:text-white transition-colors"
              >
                GitHub
              </a>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-slate-800/80 py-8 text-center text-xs text-slate-500">
          <p>© 2026 RepoDefense. Evidence-based technical defense simulation.</p>
        </footer>
      </body>
    </html>
  );
}
