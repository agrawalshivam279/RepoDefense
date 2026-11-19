"use client";

import { useEffect, useRef, useState } from "react";
import { subscribeAnnouncements } from "@/lib/accessibility";
import type { Announcement } from "@/types/accessibility";

const CLEAR_DELAY_MS = 8000;

export function LiveAnnouncer() {
  const [politeQueue, setPoliteQueue] = useState<Announcement[]>([]);
  const [assertiveQueue, setAssertiveQueue] = useState<Announcement[]>([]);
  const timeoutsRef = useRef<Set<NodeJS.Timeout>>(new Set());

  useEffect(() => {
    const timeouts = timeoutsRef.current;

    const unsubscribe = subscribeAnnouncements((announcement: Announcement) => {
      if (announcement.politeness === "assertive") {
        setAssertiveQueue((prev) => [...prev, announcement]);
        const timer = setTimeout(() => {
          setAssertiveQueue((prev) =>
            prev.filter((a) => a.id !== announcement.id)
          );
          timeouts.delete(timer);
        }, CLEAR_DELAY_MS);
        timeouts.add(timer);
      } else {
        setPoliteQueue((prev) => [...prev, announcement]);
        const timer = setTimeout(() => {
          setPoliteQueue((prev) =>
            prev.filter((a) => a.id !== announcement.id)
          );
          timeouts.delete(timer);
        }, CLEAR_DELAY_MS);
        timeouts.add(timer);
      }
    });

    return () => {
      unsubscribe();
      timeouts.forEach((timer) => clearTimeout(timer));
      timeouts.clear();
    };
  }, []);

  return (
    <div className="sr-only" aria-hidden="false">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="false"
        className="sr-only"
      >
        {politeQueue.map((item) => (
          <p key={item.id}>{item.message}</p>
        ))}
      </div>
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="false"
        className="sr-only"
      >
        {assertiveQueue.map((item) => (
          <p key={item.id}>{item.message}</p>
        ))}
      </div>
    </div>
  );
}
