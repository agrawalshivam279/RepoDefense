/**
 * TypeScript contracts and types for Skill Gap Analysis.
 * Aligned with backend Pydantic schemas in app/schemas/skill_gap.py.
 */

export type TargetRoleBenchmark = "mid_level" | "senior_engineer" | "staff_principal";

export type GapStatus = "surpassed" | "met" | "moderate_gap" | "critical_gap";

export type RemediationPriority = "critical" | "high" | "medium" | "low";

export interface CategoryGapMetric {
  category: string;
  current_score: number;
  benchmark_score: number;
  gap_deficit: number;
  status: GapStatus;
  weight: number;
  percentile_estimate: number;
}

export interface RemediationRecommendation {
  topic: string;
  category: string;
  priority: RemediationPriority;
  rationale: string;
  unresolved_weakness_count: number;
  suggested_action: string;
}

export interface SkillGapAnalysisResponse {
  target_role: TargetRoleBenchmark;
  overall_candidate_score: number;
  overall_benchmark_score: number;
  overall_readiness_pct: number;
  categories: CategoryGapMetric[];
  recommendations: RemediationRecommendation[];
  strengths: string[];
  critical_gaps: string[];
  analyzed_at: string;
}

export function getRoleDisplayName(role: TargetRoleBenchmark): string {
  switch (role) {
    case "staff_principal":
      return "Staff / Principal Engineer";
    case "senior_engineer":
      return "Senior Software Engineer";
    case "mid_level":
      return "Mid-Level Engineer";
    default:
      return "Engineering Benchmark";
  }
}

export function getGapStatusBadge(status: GapStatus): {
  label: string;
  className: string;
  borderClass: string;
} {
  switch (status) {
    case "surpassed":
      return {
        label: "Surpassed (+5)",
        className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        borderClass: "border-emerald-500/50",
      };
    case "met":
      return {
        label: "Benchmark Met",
        className: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
        borderClass: "border-indigo-500/50",
      };
    case "moderate_gap":
      return {
        label: "Moderate Gap",
        className: "bg-amber-500/10 text-amber-400 border-amber-500/30",
        borderClass: "border-amber-500/50",
      };
    case "critical_gap":
      return {
        label: "Critical Deficit",
        className: "bg-rose-500/10 text-rose-400 border-rose-500/30",
        borderClass: "border-rose-500/50",
      };
    default:
      return {
        label: "Evaluated",
        className: "bg-zinc-800 text-zinc-300 border-zinc-700",
        borderClass: "border-zinc-700",
      };
  }
}

export function getPriorityBadge(priority: RemediationPriority): {
  label: string;
  className: string;
} {
  switch (priority) {
    case "critical":
      return {
        label: "P0 · Critical",
        className: "bg-rose-500/10 text-rose-400 border border-rose-500/30",
      };
    case "high":
      return {
        label: "P1 · High",
        className: "bg-amber-500/10 text-amber-400 border border-amber-500/30",
      };
    case "medium":
      return {
        label: "P2 · Medium",
        className: "bg-blue-500/10 text-blue-400 border border-blue-500/30",
      };
    case "low":
      return {
        label: "P3 · Low",
        className: "bg-zinc-800 text-zinc-400 border border-zinc-700",
      };
    default:
      return {
        label: "Remediation",
        className: "bg-zinc-800 text-zinc-300 border border-zinc-700",
      };
  }
}
