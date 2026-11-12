/**
 * SongCountdown - the 3-2-1 in the lyrics column before a new song starts.
 *
 * Silent: the old song has faded out and the new one hasn't started. While
 * the old song is still fading there is no number yet, only the line above
 * it. On 1 it holds, still, until the song is ready: no spinner, and the song
 * never starts early.
 */

import React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { SongCountdown as SongCountdownState } from "@/stores/useSongCountdownStore";

interface SongCountdownProps {
  countdown: Exclude<SongCountdownState, { phase: "idle" }>;
  singer?: string;
}

const SongCountdown: React.FC<SongCountdownProps> = ({ countdown, singer }) => {
  const reducedMotion = useReducedMotion() ?? false;
  const count = countdown.phase === "counting" ? countdown.count : null;

  return (
    <div
      data-tour="countdown"
      className="flex h-full w-full flex-col items-center justify-center gap-2 text-center"
    >
      <p className="text-2xl uppercase tracking-[0.2em] text-foreground-dim">
        {singer ? `${singer}, get ready` : "Get ready"}
      </p>
      {/* Fixed height, so the line above doesn't move when the number
          arrives. The numbers swap in place rather than queue up. */}
      <div
        className="relative flex h-[11rem] w-full items-center justify-center"
        role="timer"
        aria-live="assertive"
        aria-atomic="true"
      >
        <AnimatePresence initial={!reducedMotion}>
          {count !== null && (
            <motion.span
              key={count}
              className="text-shadow absolute font-display text-[10rem] font-extrabold leading-none text-primary"
              initial={
                reducedMotion ? { opacity: 1 } : { opacity: 0, scale: 1.4 }
              }
              animate={{ opacity: 1, scale: 1 }}
              exit={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.8 }}
              transition={{
                duration: reducedMotion ? 0 : 0.35,
                ease: [0.2, 0.8, 0.25, 1],
              }}
            >
              {count}
            </motion.span>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default SongCountdown;
