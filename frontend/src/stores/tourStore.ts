/**
 * Guided tour progress, keyed by session.
 *
 * Persisted, so reloading the stage mid-tour resumes the step it was on
 * instead of starting over. Keyed by the session id: a new demo session (a
 * second "Try it live") starts the tour from the top, and only the current
 * session's entry is kept.
 *
 * Only the stage reads or writes this. A phone-view window on the same browser
 * shares localStorage but never mounts the tour, so it never writes here.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { isTourStep, type TourStep } from "@/features/tour/tourSteps";

interface TourState {
  /** Step by session id. Holds the current session only. */
  steps: Record<string, TourStep>;
  setStep: (sessionId: string, step: TourStep) => void;
}

export const useTourStore = create<TourState>()(
  persist(
    (set) => ({
      steps: {},
      setStep: (sessionId, step) => set({ steps: { [sessionId]: step } }),
    }),
    {
      name: "karaoke-guided-tour",
      version: 1,
      partialize: (state) => ({ steps: state.steps }),
      // Drop anything that isn't a step this build knows.
      merge: (persisted, current) => {
        const raw = (persisted as Partial<TourState> | undefined)?.steps ?? {};
        const steps: Record<string, TourStep> = {};
        for (const [id, step] of Object.entries(raw)) {
          if (isTourStep(step)) steps[id] = step;
        }
        return { ...current, steps };
      },
    },
  ),
);

/** The session's step; a session the tour hasn't seen starts at the top. */
export function tourStepFor(
  steps: Record<string, TourStep>,
  sessionId: string | null,
): TourStep {
  if (!sessionId) return "sound";
  return steps[sessionId] ?? "sound";
}
