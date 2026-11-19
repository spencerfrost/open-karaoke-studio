import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import { guestWindow } from "@/lib/guestWindow";

const logger = createLogger("store:auth");

interface AuthUser {
  id: string;
  displayName: string | null;
  isAdmin: boolean;
  isHost: boolean;
  /** A demo pool account: this browser is running the public live demo.
   * Absent on a store persisted before the flag existed. */
  isDemo?: boolean;
}

/** What /api/users/login and /api/demo/start both return. */
interface LoginResponse {
  id: string;
  display_name: string | null;
  token: string;
  is_admin: boolean;
  is_host?: boolean;
  is_demo?: boolean;
}

/** A failed demo start, keeping the status so the page can explain it
 * (503: every demo seat is taken, 429: too many starts from this network). */
export class DemoStartError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "DemoStartError";
  }
}

/** Shown when a demo visitor is sent back to the start page. */
export const DEMO_ENDED_MESSAGE =
  "Your demo has ended. Press Try it live to start another.";

const signedIn = (data: LoginResponse) => ({
  token: data.token,
  user: {
    id: data.id,
    displayName: data.display_name,
    isAdmin: data.is_admin,
    isHost: data.is_host ?? false,
    isDemo: data.is_demo ?? false,
  },
  isAuthenticated: true,
});

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;

  login: (username: string, password: string) => Promise<void>;
  /** Sign in to a free demo pool account, its session already started. */
  startDemo: () => Promise<void>;
  logout: () => void;
  /**
   * Log out because the server rejected the token (401), or a demo session is
   * over, telling the user why. A no-op when already logged out, so a burst of
   * 401s toasts once.
   */
  expireSession: () => void;
  /**
   * Trade the token for a fresh one once it is a day old, so a device that is
   * in use never reaches the end of its sign-in. Demo tokens are left alone:
   * they end with their demo session.
   */
  renewIfDue: () => Promise<void>;
}

/** Renew once the token has been in use this long. */
const RENEW_AFTER_MS = 24 * 60 * 60 * 1000;

/**
 * A JWT's expiry in milliseconds, read from its payload. Null when the token
 * can't be read; the server is still the judge of whether it's valid.
 */
export function tokenExpiryMs(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    const exp = (JSON.parse(json) as { exp?: unknown }).exp;
    return typeof exp === "number" ? exp * 1000 : null;
  } catch {
    return null;
  }
}

/** Server tokens last this long; mirrors ACCESS_TOKEN_EXPIRE_MINUTES in auth_service. */
const TOKEN_LIFETIME_MS = 7 * 24 * 60 * 60 * 1000;

/** True when the token has been in use long enough to renew. */
export function isRenewalDue(token: string, now = Date.now()): boolean {
  const expiry = tokenExpiryMs(token);
  if (expiry === null) return false;
  return expiry - now < TOKEN_LIFETIME_MS - RENEW_AFTER_MS;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      login: async (username: string, password: string) => {
        const response = await fetch("/api/users/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
          const data = await response.json().catch(() => null);
          throw new Error(data?.detail || "Invalid username or password");
        }

        set(signedIn(await response.json()));

        logger.info("Logged in as", username);
      },

      startDemo: async () => {
        const response = await fetch("/api/demo/start", { method: "POST" });

        if (!response.ok) {
          const data = await response.json().catch(() => null);
          throw new DemoStartError(
            data?.detail || "Couldn't start the demo",
            response.status,
          );
        }

        const data: LoginResponse = await response.json();
        set(signedIn(data));

        logger.info("Started a demo session on account", data.id);
      },

      logout: () => {
        set({
          token: null,
          user: null,
          isAuthenticated: false,
        });
        logger.info("Logged out");
      },

      expireSession: () => {
        if (!get().isAuthenticated) return;
        // A demo token ends with its demo session, so for a demo visitor this
        // is the demo running out, not a sign-in to redo.
        const wasDemo = Boolean(get().user?.isDemo);
        get().logout();
        if (wasDemo) {
          toast(DEMO_ENDED_MESSAGE);
        } else {
          toast.error("Session expired. Please log in again.");
        }
      },

      renewIfDue: async () => {
        const { token, isAuthenticated, user } = get();
        if (!token || !isAuthenticated || user?.isDemo) return;
        if (!isRenewalDue(token)) return;

        let response: Response;
        try {
          response = await fetch("/api/users/refresh", {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
          });
        } catch (error) {
          // Offline or the server is restarting: the token is still good for
          // days, so try again on the next check.
          logger.warn("Couldn't renew sign-in:", error);
          return;
        }

        // Signed out or signed in as someone else while the request was out.
        if (get().token !== token) return;

        if (response.status === 401) {
          get().expireSession();
          return;
        }
        if (!response.ok) {
          logger.warn("Couldn't renew sign-in: status", response.status);
          return;
        }

        set(signedIn(await response.json()));
        logger.info("Renewed sign-in");
      },
    }),
    {
      name: "karaoke-auth",
      // localStorage, except in a guest window - see lib/guestWindow.ts.
      storage: createJSONStorage(() => guestWindow.identityStorage),
    },
  ),
);
