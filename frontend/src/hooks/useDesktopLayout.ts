import { useSyncExternalStore } from "react";

/**
 * Room for two columns and not a touchscreen: a computer, or a TV driven by a
 * remote, keyboard or mouse. Width alone can't tell - the Shield's WebView is
 * 960px wide, a landscape phone nearly as much - but a phone's pointer is
 * "coarse" while a remote-only TV's is "none". Keep in step with the
 * `desktop` variant in index.css.
 */
const QUERY =
  "(min-width: 48rem) and (pointer: fine), (min-width: 48rem) and (pointer: none)";

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

/** True on a computer or TV - the screens the `desktop:` variant styles. */
export function useDesktopLayout(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
