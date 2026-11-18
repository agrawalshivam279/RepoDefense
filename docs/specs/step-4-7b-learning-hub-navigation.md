# Technical Specification: Step 4.7b — Frontend Learning Hub Navigation, Breadcrumbs & Phase 4 UX Polish

**Milestone:** 4.7 (Phase 4 Polish & Deploy)  
**Step:** 4.7b  
**Status:** In Progress  
**Layer:** Frontend (Next.js 15 App Router, TypeScript, Tailwind CSS, shadcn/ui)  
**Parent PR:** Step 4.7a (`#85`)  

---

## 1. Executive Summary & Objective

Phase 4 of RepoDefense introduced comprehensive candidate-facing learning and remediation capabilities:
1. **Weakness Tracking & Skills DB** (Milestone 4.1): Real-time tracking of architectural deficits across evaluations.
2. **Mentor Mode** (Milestone 4.2): AI principal engineer teaching mode synthesizing targeted explanations, architectural tradeoffs, and code remediation snippets.
3. **Skill Progress Dashboard** (Milestone 4.4): Proficiency trajectories, mastery distribution, velocity, and streaks.
4. **Targeted Re-Testing** (Milestone 4.5): Isolated, contextual re-tests on identified weaknesses with automated database resolution upon passing.
5. **Senior Benchmark & Skill Gap Visualizer** (Milestone 4.6): Mathematical dual-polygon SVG radar charts, benchmark comparison matrices, and prioritized remediation actions.
6. **Learning Loop Telemetry Probe** (Milestone 4.7a): Backend diagnostic health inspection endpoint (`GET /api/v1/health/learning-loop`).

**Step 4.7b** delivers the unified frontend interface and navigation fabric that unifies these individual tools into a seamless, cohesive **Learning Hub**:
- Provides accessible, semantic breadcrumbs (`LearningHubBreadcrumbs`) across all Phase 4 learning routes.
- Introduces `LearningNavGroup` for rapid switching between Skill Progress, Benchmark & Skill Gap, Mentor Mode, and Targeted Re-Testing.
- Creates the dedicated `/dashboard/learning` page showcasing the complete 7-stage architectural improvement loop, feature cards, and real-time system diagnostic health telemetry.
- Enhances global navigation across `/dashboard`, `/dashboard/progress`, `/dashboard/skill-gap`, and `/projects/[id]` with cohesive Phase 4 UX polish.

---

## 2. Architecture & File Structure

```text
frontend/src/
├── types/
│   └── learning.ts                 # Contracts for Learning Health & Hub Navigation
├── lib/
│   ├── learningApi.ts              # Typed REST client for /api/v1/health/learning-loop
│   └── __tests__/
│       └── learningApi.test.ts     # Hermetic tests for learningApi
├── components/domain/
│   ├── LearningHubBreadcrumbs.tsx  # Accessible semantic navigation breadcrumbs
│   ├── LearningNavGroup.tsx        # Segmented switch & health badge between learning modules
│   └── LearningHealthStatusCard.tsx# Live visualizer for learning-loop health probe
└── app/
    └── dashboard/
        ├── learning/
        │   └── page.tsx            # Unified Learning Hub portal page
        ├── page.tsx                # Cross-linked to Learning Hub
        ├── progress/
        │   └── page.tsx            # Integrated with Breadcrumbs & LearningNavGroup
        └── skill-gap/
            └── page.tsx            # Integrated with Breadcrumbs & LearningNavGroup
```

---

## 3. Data Contracts & Interfaces (`types/learning.ts`)

```typescript
export type ComponentHealthStatus = "healthy" | "degraded" | "unhealthy";

export interface DatabaseModelsHealth {
  status: ComponentHealthStatus;
  user_skills_accessible: boolean;
  candidate_weaknesses_accessible: boolean;
  total_user_skills: number;
  total_candidate_weaknesses: number;
  detail: string | null;
}

export interface BenchmarkProfilesHealth {
  status: ComponentHealthStatus;
  configured_tiers: string[];
  total_categories: number;
  tier_integrity_verified: boolean;
  detail: string | null;
}

export interface MentorServiceHealth {
  status: ComponentHealthStatus;
  fallbacks_ready: boolean;
  supported_fallback_topics: string[];
  detail: string | null;
}

export interface RetestServiceHealth {
  status: ComponentHealthStatus;
  cache_active: boolean;
  cached_question_count: number;
  max_cache_capacity: number;
  detail: string | null;
}

export interface LearningLoopHealthResponse {
  status: ComponentHealthStatus;
  app: string;
  version: string;
  database_models: DatabaseModelsHealth;
  benchmark_profiles: BenchmarkProfilesHealth;
  mentor_service: MentorServiceHealth;
  retest_service: RetestServiceHealth;
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ComponentType<{ className?: string }>;
  isCurrent?: boolean;
}

export type LearningModuleId = "progress" | "skill-gap" | "mentor" | "retest";

export interface LearningModuleItem {
  id: LearningModuleId;
  title: string;
  shortLabel: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  category: "telemetry" | "benchmarking" | "remediation" | "evaluation";
}
```

---

## 4. REST API Client (`lib/learningApi.ts`)

- Method: `fetchLearningLoopHealth(token: string): Promise<LearningLoopHealthResponse>`
- Endpoint: `GET /api/v1/health/learning-loop`
- Headers: `Authorization: Bearer <token>`, `Accept: application/json`
- Response parsing:
  - Supports HTTP 200 (healthy or degraded).
  - Supports HTTP 503 (database outage diagnostic report). Parses body into `LearningLoopHealthResponse`.
  - Throws informative errors for HTTP 401 or non-diagnostic server failures.
  - Runtime validation guarantees valid enum fields and numbers.

---

## 5. UI Components

### 5.1 `LearningHubBreadcrumbs.tsx`
- Structured `<nav aria-label="Breadcrumb">` containing `<ol className="flex items-center ...">`.
- Renders clickable antecedent links and a high-contrast active terminal item with `aria-current="page"`.
- Uses accessible icons and separator glyphs (`ChevronRight`).

### 5.2 `LearningNavGroup.tsx`
- Clean segmented horizontal pill bar for switching between:
  - 📈 Skill Progress (`/dashboard/progress`)
  - 🎯 Senior Benchmarks (`/dashboard/skill-gap`)
  - 🎓 Learning Hub (`/dashboard/learning`)
- Embeds a live operational health indicator (pulsing green dot for `healthy`, amber for `degraded`, red for `unhealthy`).

### 5.3 `LearningHealthStatusCard.tsx`
- Interactive diagnostic health panel showing:
  - Database status (`UserSkill` & `CandidateWeakness` record counters)
  - Benchmark Catalog (3 tiers & 6 domain categories)
  - Offline Mentor Fallbacks (Zero-downtime offline resiliency status)
  - Retest Bounded Question Cache (Cache entries vs capacity)

### 5.4 `app/dashboard/learning/page.tsx`
- Comprehensive Learning Loop Overview:
  - **7-Stage Architectural Improvement Journey**: Diagram visualizer showing Evidence ➔ Deficit ➔ Mentor ➔ Re-Test ➔ Benchmark Mastery.
  - **Active Tools Grid**: Four launcher cards for Progression, Benchmark & Gap, Mentor Mode, and Targeted Re-Testing.
  - **Diagnostic Health Section**: Subsystem telemetry for transparency and operational confidence.

---

## 6. Testing & Quality Acceptance Criteria

1. **Strict LOC Invariant**: All new files strictly $\le 300$ LOC.
2. **TypeScript Integrity**: `npx tsc --noEmit` completes with zero errors.
3. **Hermetic Test Suite**: `src/lib/__tests__/learningApi.test.ts` passes 100% via `npx tsx --test`.
4. **Production Build**: `npm run build` succeeds cleanly across all 25+ Next.js 15 App Router pages.
5. **Accessibility**: ARIA labels on all breadcrumbs, tabs, and status badges.
