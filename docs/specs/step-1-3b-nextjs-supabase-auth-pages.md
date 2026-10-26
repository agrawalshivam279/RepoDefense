# Technical Specification: Step 1.3b — Next.js 15 Supabase Auth Client, Auth Pages & Session State

> **Milestone**: 1.3 Authentication  
> **Feature Branch**: `feat/step-1-3b-nextjs-supabase-auth-pages`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.3b is to complete Milestone 1.3 by establishing the frontend authentication infrastructure in Next.js 15 (App Router). This includes:
1. Installing `@supabase/supabase-js` and configuring a resilient browser client in `frontend/src/lib/supabase.ts` with fallback handling for build-time static page generation.
2. Building an accessible, dark-themed Sign-In page (`frontend/src/app/(auth)/login/page.tsx`) supporting Email/Password and GitHub OAuth login.
3. Building an accessible, dark-themed Sign-Up page (`frontend/src/app/(auth)/signup/page.tsx`) with password confirmation and input validation.
4. Implementing a real-time reactive authentication state component (`frontend/src/components/domain/AuthStatus.tsx`) embedded in the global navigation bar, dynamically presenting user identity and Sign Out capabilities.

---

## 2. Invariants & Guardrails

1. **Static Rendering Safety (SSG)**: The Supabase client initialization must not throw or crash during `next build` if `NEXT_PUBLIC_SUPABASE_URL` is omitted or contains default placeholder values.
2. **Strict Client Components**: Forms and auth hooks utilize React 19 `"use client"` directives with controlled state, async submission handlers, and accessible error banners.
3. **No Hardcoded Secrets**: Secrets are never embedded in client bundles; only public variables (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`) are utilized on the frontend.
4. **Max 300 LOC Constraint**: Every page and component must strictly stay under 300 lines of code.
5. **Clean Type Checking**: Must pass `npm run build` (`next build`) and `npm run typecheck` (`tsc --noEmit`) with 0 errors.

---

## 3. Target Files & Component Specifications

### 1. `frontend/package.json`
- Add `@supabase/supabase-js: ^2.49.0` to dependencies.

### 2. `frontend/src/lib/supabase.ts` ($\le 40$ LOC)
- Creates browser Supabase client using `createClient`.
- Resolves `process.env.NEXT_PUBLIC_SUPABASE_URL` and `process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- Fallbacks to dummy URL during static analysis/build if variables are unset to prevent `supabaseUrl is required` build errors.

### 3. `frontend/src/app/(auth)/login/page.tsx` ($\le 180$ LOC)
- `"use client"` component.
- Form inputs: Email, Password.
- Actions:
  - Email/password sign-in (`supabase.auth.signInWithPassword`).
  - GitHub OAuth sign-in (`supabase.auth.signInWithOAuth({ provider: 'github' })`).
- Visual states: Loading spinners, error messages, disabled buttons during inflight requests.
- Navigation links to `/signup` and `/`.

### 4. `frontend/src/app/(auth)/signup/page.tsx` ($\le 180$ LOC)
- `"use client"` component.
- Form inputs: Email, Password, Confirm Password.
- Client validation: Password match, minimum 8 characters.
- Action: `supabase.auth.signUp({ email, password })`.
- Success state: Informational banner instructing user to check their email for confirmation.
- Navigation link to `/login`.

### 5. `frontend/src/components/domain/AuthStatus.tsx` ($\le 90$ LOC)
- `"use client"` navigation component.
- Tracks `User | null` via `supabase.auth.onAuthStateChange`.
- When authenticated: Displays user email and a "Sign Out" button (`supabase.auth.signOut()`).
- When unauthenticated: Displays "Sign In" and "Get Started" links.

### 6. `frontend/src/app/page.tsx` (Update)
- Embeds `AuthStatus` into the top header navigation bar.

---

## 4. Acceptance Criteria

1. `@supabase/supabase-js` installed and integrated without peer dependency conflicts.
2. Visiting `/login` renders clean, styled sign-in form with GitHub OAuth and credentials inputs.
3. Visiting `/signup` renders clean, styled registration form with client validation.
4. Landing page header dynamically reflects authentication state via `AuthStatus`.
5. `npm run build` and `npm run typecheck` succeed with zero errors.
