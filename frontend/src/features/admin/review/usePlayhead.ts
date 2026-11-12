import { useCallback, useRef, useSyncExternalStore } from "react";

/**
 * The playing position, read by the parts that move with it (a timeline's
 * playhead, the moment being played) without re-rendering the whole panel
 * every frame.
 */
export function usePlayhead() {
  const time = useRef(0);
  const listeners = useRef(new Set<() => void>());
  const set = useCallback((seconds: number) => {
    time.current = seconds;
    listeners.current.forEach((listener) => listener());
  }, []);
  const subscribe = useCallback((listener: () => void) => {
    listeners.current.add(listener);
    return () => listeners.current.delete(listener);
  }, []);
  const get = useCallback(() => time.current, []);
  return { set, subscribe, get };
}

export type Playhead = ReturnType<typeof usePlayhead>;

/** The playing position; re-renders on every change. */
export function usePlayheadTime(playhead: Playhead): number {
  return useSyncExternalStore(playhead.subscribe, playhead.get);
}

/** Whether the playhead is in [start, end]; re-renders only when that flips. */
export function usePlayheadInside(
  playhead: Playhead,
  start: number,
  end: number,
): boolean {
  return useSyncExternalStore(playhead.subscribe, () => {
    const t = playhead.get();
    return t >= start && t <= end;
  });
}
