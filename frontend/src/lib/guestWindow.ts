/**
 * Guest windows: a browser window that is somebody's phone rather than the
 * host's screen.
 *
 * The auth and session stores normally persist to localStorage, which every
 * window on the origin shares. That is right for the host - the stage, the
 * library and settings tabs should all be the same signed-in person - but a
 * guest joined from the same browser would overwrite the host's records, and
 * would start out signed in as the host. So a guest window keeps its identity
 * in sessionStorage, which belongs to that one window: it survives a reload of
 * the window and disappears when the window closes.
 *
 * A window becomes a guest window in one of two ways:
 *
 * - It was opened with `?guest-window` in the URL, as the stage's "Open a phone
 *   view" does. This is read at startup, before any store hydrates, then
 *   remembered in sessionStorage so a reload stays a guest window after the
 *   parameter has been taken out of the address bar.
 * - It joined a session as a guest while this browser holds the stage's
 *   record (see `sessionStore.joinSession`), e.g. a second tab on the stage
 *   computer typing the code in.
 *
 * Every other window behaves exactly as before.
 */

import { createLogger } from "@/lib/logger";

const logger = createLogger("lib:guest-window");

/** URL flag that opens a window as a guest window. */
export const GUEST_WINDOW_PARAM = "guest-window";

/** Remembers, in the window's own sessionStorage, that it is a guest window. */
export const GUEST_WINDOW_MARKER_KEY = "karaoke-guest-window";

/** The stage's phone view reuses one window rather than stacking new ones. */
export const PHONE_VIEW_WINDOW_NAME = "karaoke-phone-view";

/** The parts of the Storage API the stores use. */
export type IdentityStorage = Pick<
  Storage,
  "getItem" | "setItem" | "removeItem"
>;

interface GuestWindowEnv {
  /** `location.search` at startup. */
  search: string;
  /** This window's sessionStorage, or null where the browser refuses it. */
  sessionArea: Storage | null;
  /** The shared localStorage, or null where the browser refuses it. */
  sharedArea: Storage | null;
}

export interface GuestWindow {
  /** True when this window keeps its identity to itself. */
  isGuestWindow: () => boolean;
  /** Turn this window into a guest window from now on. */
  markGuestWindow: () => void;
  /**
   * Where the auth and session stores read and write. Resolved on every call,
   * so a window that becomes a guest window mid-life switches over at once.
   */
  identityStorage: IdentityStorage;
  /**
   * The shared localStorage, regardless of mode - for asking whether some
   * other window of this browser holds the host's records.
   */
  sharedStorage: IdentityStorage;
}

/** A Storage stand-in for browsers that refuse sessionStorage outright. */
function createMemoryStorage(): Storage {
  const items = new Map<string, string>();
  return {
    get length() {
      return items.size;
    },
    clear: () => items.clear(),
    getItem: (key) => items.get(key) ?? null,
    key: (index) => Array.from(items.keys())[index] ?? null,
    removeItem: (key) => {
      items.delete(key);
    },
    setItem: (key, value) => {
      items.set(key, String(value));
    },
  };
}

/**
 * Build the guest-window state for one window. Exported for tests; the app
 * uses the `guestWindow` singleton below.
 */
export function createGuestWindow(env: GuestWindowEnv): GuestWindow {
  // A guest window must never fall back to the shared area, so without
  // sessionStorage it keeps its identity in memory: lost on reload, but
  // still its own.
  const sessionArea = env.sessionArea ?? createMemoryStorage();
  const sharedArea = env.sharedArea ?? createMemoryStorage();

  const openedAsGuest = new URLSearchParams(env.search).has(GUEST_WINDOW_PARAM);

  let guest = false;
  try {
    if (openedAsGuest) {
      // A window opened from another inherits a copy of its opener's
      // sessionStorage. Whatever that copy holds belongs to the opener, so
      // a freshly opened guest window starts with nothing but the marker.
      sessionArea.clear();
      sessionArea.setItem(GUEST_WINDOW_MARKER_KEY, "1");
    }
    guest =
      openedAsGuest || sessionArea.getItem(GUEST_WINDOW_MARKER_KEY) === "1";
  } catch (error) {
    logger.warn("sessionStorage unavailable:", error);
    guest = openedAsGuest;
  }

  const current = (): IdentityStorage => (guest ? sessionArea : sharedArea);

  return {
    isGuestWindow: () => guest,
    markGuestWindow: () => {
      if (guest) return;
      guest = true;
      try {
        sessionArea.setItem(GUEST_WINDOW_MARKER_KEY, "1");
      } catch (error) {
        logger.warn("Could not remember the guest window:", error);
      }
      logger.info("This window is now a guest window");
    },
    identityStorage: {
      getItem: (key) => current().getItem(key),
      setItem: (key, value) => current().setItem(key, value),
      removeItem: (key) => current().removeItem(key),
    },
    sharedStorage: sharedArea,
  };
}

function readArea(name: "sessionStorage" | "localStorage"): Storage | null {
  try {
    return typeof window === "undefined" ? null : window[name];
  } catch {
    return null;
  }
}

/** Take the flag out of the address bar once it has been read. */
function stripGuestWindowParam(): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (!url.searchParams.has(GUEST_WINDOW_PARAM)) return;
  url.searchParams.delete(GUEST_WINDOW_PARAM);
  window.history.replaceState(window.history.state, "", url);
}

/**
 * This window's guest-window state, settled when the module first loads -
 * which is before the stores that import it hydrate.
 */
export const guestWindow: GuestWindow = createGuestWindow({
  search: typeof window === "undefined" ? "" : window.location.search,
  sessionArea: readArea("sessionStorage"),
  sharedArea: readArea("localStorage"),
});
stripGuestWindowParam();

/** The address a phone view opens at: the ordinary join link, as a guest window. */
export function phoneViewUrl(origin: string, displayCode: string): string {
  return `${origin}/join/${encodeURIComponent(displayCode)}?${GUEST_WINDOW_PARAM}`;
}

const PHONE_VIEW_WIDTH = 400;
const PHONE_VIEW_HEIGHT = 820;

/**
 * Open (or bring back) a phone-sized guest window joined to this session.
 * Resolves false when the browser blocked the window.
 *
 * Opening by name returns the phone view that is already open, if there is
 * one, without reloading it - so a second press brings the same guest back
 * rather than signing a new one in. It is only pointed at the join link when
 * it is new or still sitting on the join page (not joined yet, or its session
 * ended and sent it back there).
 */
export function openPhoneView(displayCode: string): boolean {
  const screenInfo = window.screen as Screen & { availLeft?: number };
  const height = Math.min(
    PHONE_VIEW_HEIGHT,
    screenInfo.availHeight || PHONE_VIEW_HEIGHT,
  );
  // Against the right edge of the screen, where it covers the least of the
  // stage's lyrics.
  const left = Math.max(
    0,
    (screenInfo.availLeft ?? 0) +
      (screenInfo.availWidth || PHONE_VIEW_WIDTH) -
      PHONE_VIEW_WIDTH -
      24,
  );
  const features = `popup,width=${PHONE_VIEW_WIDTH},height=${height},left=${left},top=48`;

  const phone = window.open("", PHONE_VIEW_WINDOW_NAME, features);
  if (!phone) return false;

  let path: string | null = null;
  try {
    path =
      phone.location.href === "about:blank" ? null : phone.location.pathname;
  } catch {
    // Not readable: somewhere off this origin. Start it over.
    path = null;
  }
  if (path === null || path === "/join" || path.startsWith("/join/")) {
    phone.location.href = phoneViewUrl(window.location.origin, displayCode);
  }
  phone.focus();
  return true;
}
