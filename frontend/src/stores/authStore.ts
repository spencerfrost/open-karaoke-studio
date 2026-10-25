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
    }),
    {
      name: "karaoke-auth",
      // localStorage, except in a guest window - see lib/guestWindow.ts.
      storage: createJSONStorage(() => guestWindow.identityStorage),
    },
  ),
);
