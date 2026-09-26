import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";

const logger = createLogger("store:auth");

interface AuthUser {
  id: string;
  displayName: string | null;
  isAdmin: boolean;
  isHost: boolean;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;

  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  /**
   * Log out because the server rejected the token (401), telling the user why.
   * A no-op when already logged out, so a burst of 401s toasts once.
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

        const data = await response.json();

        set({
          token: data.token,
          user: {
            id: data.id,
            displayName: data.display_name,
            isAdmin: data.is_admin,
            isHost: data.is_host ?? false,
          },
          isAuthenticated: true,
        });

        logger.info("Logged in as", username);
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
        get().logout();
        toast.error("Session expired. Please log in again.");
      },
    }),
    {
      name: "karaoke-auth",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
