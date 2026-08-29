/**
 * useStageRails - decides when the stage rails collapse to icon strips.
 *
 * They collapse the moment playback starts, and re-open on real pointer or
 * keyboard activity (then stay open until it goes quiet again). Nothing
 * unmounts when they collapse — the strip is only hidden — so open dialogs,
 * drag state and focus all survive.
 */

import { useEffect, useRef, useState } from "react";

const POINTER_IDLE_MS = 4000;

/**
 * How long to ignore pointer/key activity after playback starts. The click (or
 * spacebar) that started the song would otherwise re-open the rails a frame
 * after they collapse.
 */
const PLAY_GRACE_MS = 600;

export const useStageRails = (isPlaying: boolean) => {
  const [pointerActive, setPointerActive] = useState(true);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ignoreActivityUntil = useRef(0);

  // Hitting play clears the stage immediately — no waiting out the idle timer.
  const wasPlaying = useRef(isPlaying);
  useEffect(() => {
    if (isPlaying && !wasPlaying.current) {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      ignoreActivityUntil.current = Date.now() + PLAY_GRACE_MS;
      setPointerActive(false);
    }
    wasPlaying.current = isPlaying;
  }, [isPlaying]);

  useEffect(() => {
    const markActive = () => {
      if (Date.now() < ignoreActivityUntil.current) return;
      setPointerActive(true);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(
        () => setPointerActive(false),
        POINTER_IDLE_MS,
      );
    };

    window.addEventListener("mousemove", markActive);
    window.addEventListener("pointerdown", markActive);
    window.addEventListener("keydown", markActive);

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      window.removeEventListener("mousemove", markActive);
      window.removeEventListener("pointerdown", markActive);
      window.removeEventListener("keydown", markActive);
    };
  }, []);

  return { collapsed: isPlaying && !pointerActive };
};
