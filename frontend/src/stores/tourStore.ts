/**
 * Guided tour progress, keyed by session.
 *
 * Persisted, so reloading the stage mid-tour resumes the step it was on
 * instead of starting over. Only the current session's entry is kept.
 *
 * The key is the session code plus the session's creation time, not the code
 * alone: join codes are four letters and get reused once an old session is
 * purged, so a later visitor handed the same code must not pick up a finished
 * visitor's tour. The entry is also dropped as soon as the session ends in
 * this page (the demo's time runs out, or the session is left).
 *
 * Only the stage reads or writes this. A phone-view window on the same browser
 * shares localStorage but never mounts the tour, so it never writes here.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { isTourStep, type TourStep } from "@/features/tour/tourSteps";
import { useSessionStore } from "./sessionStore";

interface TourState {
  /** Step by tour key (see tourKeyFor). Holds the current session only. */
  steps: Record<string, TourStep>;
  setStep: (tourKey: string, step: TourStep) => void;
  clear: () => void;
}

export const useTourStore = create<TourState>()(
  persist(
    (set) => ({
      steps: {},
      setStep: (tourKey, step) => set({ steps: { [tourKey]: step } }),
      clear: () => set({ steps: {} }),
    }),
    {
      name: "karaoke-guided-tour",
      version: 2,
      partialize: (state) => ({ steps: state.steps }),
      // Version 1 keyed by the bare code, which a reused code would resume.
      migrate: () => ({ steps: {} }),
      // Drop anything that isn't a step this build knows.
      merge: (persisted, current) => {
        const raw = (persisted as Partial<TourState> | undefined)?.steps ?? {};
        const steps: Record<string, TourStep> = {};
        for (const [key, step] of Object.entries(raw)) {
          if (isTourStep(step)) steps[key] = step;
        }
        return { ...current, steps };
      },
    },
  ),
);

/** One session's key: its code and when it was created. */
export function tourKeyFor(sessionId: string, createdAt: string): string {
  return `${sessionId}@${createdAt}`;
}

/** The session's step; a session the tour hasn't seen starts at the top. */
export function tourStepFor(
  steps: Record<string, TourStep>,
  tourKey: string | null,
): TourStep {
  if (!tourKey) return "sound";
  return steps[tourKey] ?? "sound";
}

// A session that ends while the page is up (the demo timer, session_ended,
// leaving) takes its tour with it. A fresh page starts with no session and
// recovers one, which never looks like an end.
useSessionStore.subscribe((state, prev) => {
  if (prev.sessionId && !state.sessionId) useTourStore.getState().clear();
});
