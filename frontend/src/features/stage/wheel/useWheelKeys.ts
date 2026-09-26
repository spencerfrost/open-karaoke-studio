/**
 * useWheelKeys - arrow keys, Enter and Back for the song wheel.
 *
 * Bound on the window, like useStageKeyboard, so nothing has to hold focus: a
 * singer who clicked a button with the mic-stand mouse can still arrow away.
 * Only live while song select is showing, and it backs off from the same
 * things useStageKeyboard does (text fields, dialogs, sliders).
 *
 * Held ▲▼ ignore the OS key repeat, whose rate is the OS's choice and far too
 * slow for 600 artists. The wheel runs its own: one row, a pause, then a
 * climb to top speed over about a second (rates in wheelModel).
 */

import { useEffect, useRef } from "react";
import { WHEEL_TUNING, holdRate } from "./wheelModel";

interface WheelKeyHandlers {
  move: (dir: -1 | 1) => void;
  turn: (dir: -1 | 1) => void;
  enter: () => void;
  back: () => void;
}

interface UseWheelKeysOptions extends WheelKeyHandlers {
  enabled: boolean;
  /**
   * The row animation length while a key is held, or null when released. A
   * row that takes 160ms to slide cannot keep up with 36 rows a second.
   */
  onScrollMs: (ms: number | null) => void;
}

const isTextEntry = (el: HTMLElement): boolean =>
  ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable;

export function useWheelKeys({
  enabled,
  onScrollMs,
  ...handlers
}: UseWheelKeysOptions) {
  // The listener is bound once; these refs give it the latest of everything.
  const handlersRef = useRef<WheelKeyHandlers>(handlers);
  handlersRef.current = handlers;
  const onScrollMsRef = useRef(onScrollMs);
  onScrollMsRef.current = onScrollMs;

  useEffect(() => {
    if (!enabled) return;

    let hold: { key: string; timer: number } | null = null;

    const stopHold = () => {
      if (!hold) return;
      window.clearTimeout(hold.timer);
      hold = null;
      onScrollMsRef.current(null);
    };

    const startHold = (key: string, dir: -1 | 1) => {
      stopHold();
      handlersRef.current.move(dir);
      const startedAt = performance.now();
      const tick = () => {
        if (!hold) return;
        const rate = holdRate(
          performance.now() - startedAt - WHEEL_TUNING.holdDelayMs,
        );
        const interval = 1000 / rate;
        onScrollMsRef.current(
          Math.min(WHEEL_TUNING.scrollMs, Math.round(interval * 0.9)),
        );
        handlersRef.current.move(dir);
        hold.timer = window.setTimeout(tick, interval);
      };
      hold = {
        key,
        timer: window.setTimeout(tick, WHEEL_TUNING.holdDelayMs),
      };
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target instanceof HTMLElement ? e.target : null;
      if (t && isTextEntry(t)) return;
      if (t?.closest("[role='dialog'], [role='slider']")) return;

      switch (e.key) {
        case "ArrowUp":
        case "ArrowDown":
          e.preventDefault();
          // Our own repeat runs instead; see the header.
          if (e.repeat) return;
          startHold(e.key, e.key === "ArrowUp" ? -1 : 1);
          return;
        case "ArrowLeft":
        case "ArrowRight":
          e.preventDefault();
          if (e.repeat) return;
          handlersRef.current.turn(e.key === "ArrowLeft" ? -1 : 1);
          return;
        case "Enter":
          // A focused button owns Enter - the mouse may have just clicked it.
          if (t?.closest("button, a, [role='button']")) return;
          e.preventDefault();
          if (e.repeat) return;
          handlersRef.current.enter();
          return;
        case "Backspace":
        case "Escape":
          e.preventDefault();
          if (e.repeat) return;
          handlersRef.current.back();
          return;
        default:
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (hold && e.key === hold.key) stopHold();
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    // A key released while the window is not focused never sends keyup.
    window.addEventListener("blur", stopHold);
    return () => {
      stopHold();
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("blur", stopHold);
    };
  }, [enabled]);
}
