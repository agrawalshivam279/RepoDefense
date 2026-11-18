/**
 * Data contracts and badge helpers for Targeted Re-Testing in Next.js 15.
 * Matches backend schemas in backend/app/schemas/retest.py.
 */

export interface EligibleWeaknessItem {
  id: string;
  project_id?: string | null;
  category: string;
  topic: string;
  severity: "critical" | "major" | "minor" | string;
  original_prompt: string;
  feedback: string;
  created_at: string;
}

export interface EligibleWeaknessesResponse {
  total_eligible: number;
  weaknesses: EligibleWeaknessItem[];
}

export interface TargetedRetestSessionCreate {
  project_id?: string | null;
  weakness_ids?: string[] | null;
  category?: string | null;
  max_questions?: number;
}

export interface RetestQuestion {
  question_id: string;
  weakness_id: string;
  category: string;
  topic: string;
  severity: string;
  original_prompt: string;
  question_text: string;
  architectural_constraint: string;
  evaluation_rubric: string;
}

export interface TargetedRetestSessionResponse {
  session_id: string;
  user_id: string;
  project_id?: string | null;
  total_questions: number;
  questions: RetestQuestion[];
  created_at: string;
}

export interface SubmitRetestAnswerRequest {
  session_id: string;
  question_id: string;
  weakness_id: string;
  candidate_response: string;
}

export interface RetestEvaluationResponse {
  question_id: string;
  weakness_id: string;
  passed: boolean;
  score: number;
  feedback: string;
  key_improvements: string[];
  remaining_gaps: string[];
  weakness_resolved: boolean;
  updated_proficiency?: number | null;
}

export function getSeverityBadge(severity?: string): { label: string; className: string } {
  switch ((severity || "").toLowerCase()) {
    case "critical":
      return {
        label: "Critical",
        className: "bg-red-500/10 text-red-400 border border-red-500/30",
      };
    case "major":
      return {
        label: "Major",
        className: "bg-amber-500/10 text-amber-400 border border-amber-500/30",
      };
    case "minor":
      return {
        label: "Minor",
        className: "bg-blue-500/10 text-blue-400 border border-blue-500/30",
      };
    default:
      return {
        label: severity || "Unknown",
        className: "bg-zinc-800 text-zinc-400 border border-zinc-700",
      };
  }
}

export function getCategoryBadge(category?: string): { label: string; className: string } {
  switch ((category || "").toLowerCase()) {
    case "concurrency":
      return { label: "Concurrency", className: "bg-purple-500/10 text-purple-400 border border-purple-500/30" };
    case "caching":
      return { label: "Caching", className: "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30" };
    case "database":
      return { label: "Database", className: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" };
    case "security":
      return { label: "Security", className: "bg-rose-500/10 text-rose-400 border border-rose-500/30" };
    case "scalability":
      return { label: "Scalability", className: "bg-amber-500/10 text-amber-400 border border-amber-500/30" };
    default:
      return { label: category || "General", className: "bg-zinc-800 text-zinc-300 border border-zinc-700" };
  }
}
