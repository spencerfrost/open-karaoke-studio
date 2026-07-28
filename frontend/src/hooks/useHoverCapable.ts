import { useSyncExternalStore } from "react";

const QUERY = "(hover: hover) and (pointer: fine)";

let mediaQuery: MediaQueryList | null = null;

const getMediaQuery = (): MediaQueryList | null => {
  if (typeof window === "undefined" || !window.matchMedia) return null;
  if (!mediaQuery) mediaQuery = window.matchMedia(QUERY);
  return mediaQuery;
};

const subscribe = (onChange: () => void) => {
  const mq = getMediaQuery();
  if (!mq) return () => {};
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
};

const getSnapshot = () => getMediaQuery()?.matches ?? false;

/**
 * True when the device has a real hovering pointer (a mouse or trackpad).
 *
 * Used to gate hover-triggered behaviour that costs something — a timer, a
 * network request — which a CSS media query cannot do. Stays correct when a
 * mouse is attached to a tablet mid-session.
 */
export function useHoverCapable(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
