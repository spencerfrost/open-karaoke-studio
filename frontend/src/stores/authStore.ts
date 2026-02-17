import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { createLogger } from "@/lib/logger";

const logger = createLogger("store:auth");

interface AuthUser {
  id: string;
  displayName: string | null;
  isAdmin: boolean;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;

  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
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
    }),
    {
      name: "karaoke-auth",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
