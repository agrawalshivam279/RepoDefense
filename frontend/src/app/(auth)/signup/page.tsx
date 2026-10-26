"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2, Lock, Mail, ShieldAlert } from "lucide-react";
import { supabase } from "@/lib/supabase";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const { data, error: authError } = await supabase.auth.signUp({
        email,
        password,
      });

      if (authError) {
        setError(authError.message);
        setLoading(false);
      } else if (data.session) {
        // Immediate session created (auto-confirm enabled)
        window.location.href = "/";
      } else {
        // Email confirmation required
        setSuccess(true);
        setLoading(false);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-slate-100">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link
          href="/"
          className="inline-flex items-center text-xs font-mono text-slate-400 hover:text-emerald-400 mb-6 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to RepoDefense
        </Link>

        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">RepoDefense</h1>
            <p className="text-xs text-slate-400">Architectural Defense Simulation</p>
          </div>
        </div>

        <h2 className="mt-6 text-2xl font-bold tracking-tight text-white">
          Create your account
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-900/80 backdrop-blur-sm py-8 px-4 shadow-xl border border-slate-800 sm:rounded-xl sm:px-10">
          {success ? (
            <div className="text-center py-4 space-y-4">
              <div className="w-12 h-12 bg-emerald-500/10 border border-emerald-500/30 rounded-full flex items-center justify-center mx-auto text-emerald-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-semibold text-white">Account Created</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Your account for <span className="text-slate-200 font-mono">{email}</span> has been created.
                If email confirmation is enabled, please verify your email before logging in.
              </p>
              <Link
                href="/login"
                className="inline-block w-full py-2.5 px-4 rounded-lg bg-emerald-400 text-slate-950 font-semibold text-sm hover:bg-emerald-300 transition-colors"
              >
                Proceed to Sign In
              </Link>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-6 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3.5 flex items-start space-x-3 text-rose-300">
                  <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400 mt-0.5" />
                  <div className="text-xs font-medium leading-relaxed">{error}</div>
                </div>
              )}

              <form onSubmit={handleSignup} className="space-y-4">
                <div>
                  <label
                    htmlFor="email"
                    className="block text-xs font-medium text-slate-300 mb-1.5"
                  >
                    Email address
                  </label>
                  <div className="relative rounded-md shadow-sm">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Mail className="h-4 w-4 text-slate-500" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="architect@company.com"
                      className="block w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm placeholder-slate-500 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="password"
                    className="block text-xs font-medium text-slate-300 mb-1.5"
                  >
                    Password (min. 8 characters)
                  </label>
                  <div className="relative rounded-md shadow-sm">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-4 w-4 text-slate-500" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type="password"
                      autoComplete="new-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="block w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm placeholder-slate-500 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="confirmPassword"
                    className="block text-xs font-medium text-slate-300 mb-1.5"
                  >
                    Confirm password
                  </label>
                  <div className="relative rounded-md shadow-sm">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-4 w-4 text-slate-500" />
                    </div>
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type="password"
                      autoComplete="new-password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="block w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm placeholder-slate-500 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-slate-950 bg-emerald-400 hover:bg-emerald-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 transition-all mt-2"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                  ) : (
                    "Create Account"
                  )}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
