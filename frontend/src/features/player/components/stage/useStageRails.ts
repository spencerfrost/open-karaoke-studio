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

/**
 * Cumulative mouse travel (px) required to re-expand collapsed rails. Keeps a
 * mic stand bump or a twitchy touchpad from triggering the expand transition
 * — only deliberate movement should bring the rails back.
 */
const REVEAL_DISTANCE_PX = 120;

export const useStageRails = (isPlaying: boolean) => {
  const [pointerActive, setPointerActive] = useState(true);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ignoreActivityUntil = useRef(0);

  const collapsedRef = useRef(false);
  collapsedRef.current = isPlaying && !pointerActive;

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

    let lastMouseX: number | null = null;
    let lastMouseY: number | null = null;
    let traveled = 0;

    const handleMouseMove = (event: MouseEvent) => {
      if (!collapsedRef.current) {
        lastMouseX = null;
        lastMouseY = null;
        traveled = 0;
        markActive();
        return;
      }

      if (lastMouseX === null || lastMouseY === null) {
        lastMouseX = event.clientX;
        lastMouseY = event.clientY;
        return;
      }

      traveled += Math.hypot(
        event.clientX - lastMouseX,
        event.clientY - lastMouseY,
      );
      lastMouseX = event.clientX;
      lastMouseY = event.clientY;

      if (traveled >= REVEAL_DISTANCE_PX) {
        traveled = 0;
        markActive();
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("pointerdown", markActive);
    window.addEventListener("keydown", markActive);

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("pointerdown", markActive);
      window.removeEventListener("keydown", markActive);
    };
  }, []);

  return { collapsed: isPlaying && !pointerActive };
};
