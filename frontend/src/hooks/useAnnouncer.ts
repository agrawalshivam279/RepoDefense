"use client";

import { useCallback } from "react";
import { announce } from "@/lib/accessibility";
import type { PolitenessSetting } from "@/types/accessibility";

export function useAnnouncer() {
  const triggerAnnouncement = useCallback(
    (message: string, politeness: PolitenessSetting = "polite") => {
      announce(message, politeness);
    },
    []
  );

  return {
    announce: triggerAnnouncement,
  };
}
