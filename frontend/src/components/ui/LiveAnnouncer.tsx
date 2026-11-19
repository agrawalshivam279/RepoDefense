"use client";

import { useEffect, useRef, useState } from "react";
import { subscribeAnnouncements } from "@/lib/accessibility";
import type { Announcement } from "@/types/accessibility";

const CLEAR_DELAY_MS = 8000;

export function LiveAnnouncer() {
  const [politeMessage, setPoliteMessage] = useState("");
  const [assertiveMessage, setAssertiveMessage] = useState("");
  const politeTimerRef = useRef<NodeJS.Timeout | null>(null);
  const assertiveTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const unsubscribe = subscribeAnnouncements((announcement: Announcement) => {
      if (announcement.politeness === "assertive") {
        setAssertiveMessage(announcement.message);
        if (assertiveTimerRef.current) clearTimeout(assertiveTimerRef.current);
        assertiveTimerRef.current = setTimeout(() => {
          setAssertiveMessage("");
        }, CLEAR_DELAY_MS);
      } else {
        setPoliteMessage(announcement.message);
        if (politeTimerRef.current) clearTimeout(politeTimerRef.current);
        politeTimerRef.current = setTimeout(() => {
          setPoliteMessage("");
        }, CLEAR_DELAY_MS);
      }
    });

    return () => {
      unsubscribe();
      if (politeTimerRef.current) clearTimeout(politeTimerRef.current);
      if (assertiveTimerRef.current) clearTimeout(assertiveTimerRef.current);
    };
  }, []);

  return (
    <div className="sr-only" aria-hidden="false">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {politeMessage}
      </div>
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      >
        {assertiveMessage}
      </div>
    </div>
  );
}
