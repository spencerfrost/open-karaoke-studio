/**
 * useHandoffCountdown - the between-songs clock, and the one rule about it.
 *
 * **Any interaction cancels it permanently.** A clock ticking down while
 * someone is halfway through deciding who they are is hostile, so the first tap
 * kills it for the rest of this handoff - it does not pause and resume. But
 * removing it entirely recreates the exact stall the feature exists to prevent,
 * which is why the empty-seat case gets its own slower timer rather than none.
 *
 * The cancel flag lives in a ref keyed on `resetKey` because the handoff screen
 * re-renders on every queue broadcast. The version this replaces kept its guard
 * in a ref the effect reset on every dependency change, so an unrelated queue
 * update could restart a countdown someone had already stopped.
 */

import { useCallback, useEffect, useRef, useState } from "react";

interface UseHandoffCountdownOptions {
  /** Seconds to count down, or null for no timer at all. */
  seconds: number | null;
  onExpire: () => void;
  /**
   * Changes when a new handoff begins - normally the performer whose turn it
   * is. A new value starts a fresh countdown; anything else leaves a cancelled
   * one cancelled.
   */
  resetKey: string | number | null;
}

export interface HandoffCountdown {
  /** Seconds left, or null when there is no timer running. */
  remaining: number | null;
  cancelled: boolean;
  /** Stop the clock for the rest of this handoff. Safe to call repeatedly. */
  cancel: () => void;
}

export function useHandoffCountdown({
  seconds,
  onExpire,
  resetKey,
}: UseHandoffCountdownOptions): HandoffCountdown {
  const [remaining, setRemaining] = useState<number | null>(seconds);
  const [cancelled, setCancelled] = useState(false);

  // Which handoff the current cancel applies to. Compared rather than reset by
  // an effect, so a re-render cannot quietly un-cancel anything.
  const cancelledForKey = useRef<string | number | null>(null);
  // Kept in a ref so a caller passing an inline arrow does not restart the
  // interval on every render.
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;

  const cancel = useCallback(() => {
    cancelledForKey.current = resetKey;
    setCancelled(true);
    setRemaining(null);
  }, [resetKey]);

  useEffect(() => {
    if (cancelledForKey.current === resetKey) {
      setCancelled(true);
      setRemaining(null);
      return;
    }

    setCancelled(false);
    if (seconds === null) {
      setRemaining(null);
      return;
    }

    setRemaining(seconds);
    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev === null) return null;
        if (prev > 1) return prev - 1;
        clearInterval(interval);
        onExpireRef.current();
        return 0;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [seconds, resetKey]);

  return { remaining, cancelled, cancel };
}
