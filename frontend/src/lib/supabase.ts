import { createClient } from "@supabase/supabase-js";

const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder-project.supabase.co";
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key";

/**
 * Global singleton Supabase client for browser authentication and data operations.
 * Configured with safe build-time fallbacks to prevent SSG failures.
 */
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
