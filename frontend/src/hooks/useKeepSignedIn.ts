import { useEffect } from "react";
import { useAuthStore } from "@/stores/authStore";

/** How often a page left open (the TV, the stage) checks its sign-in. */
const CHECK_EVERY_MS = 60 * 60 * 1000;

/**
 * Keeps this device signed in while it's being used: renews the token when
 * the app opens, when the tab comes back into view, and hourly while it stays
 * open. The store only calls the server once the token is a day old.
 */
export function useKeepSignedIn(): void {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) return;

    const check = () => void useAuthStore.getState().renewIfDue();
    const onVisible = () => {
      if (document.visibilityState === "visible") check();
    };

    check();
    const timer = window.setInterval(check, CHECK_EVERY_MS);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [isAuthenticated]);
}
