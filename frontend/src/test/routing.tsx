import { ReactElement } from "react";
import { cleanup } from "@testing-library/react";
import { useAuthStore } from "@/stores/authStore";
import { useSessionStore } from "@/stores/sessionStore";
import { updateStore } from "./zustand";
import { render } from "./utils";

type AuthOverrides = Partial<ReturnType<(typeof useAuthStore)["getState"]>>;
type SessionOverrides = Partial<
  ReturnType<(typeof useSessionStore)["getState"]>
>;

/**
 * Renders a route tree with the auth/session stores seeded for one persona,
 * for gate-matrix tests. Both stores are `persist`-wrapped, so localStorage
 * is cleared first to stop one test's session bleeding into the next.
 *
 * Cleans up any prior render first: matrix tests call this several times
 * per `it()` block (one persona against several routes), and vitest's
 * afterEach cleanup only runs between tests, not between calls within one.
 */
export function renderRoute(
  ui: ReactElement,
  path: string,
  overrides: { auth?: AuthOverrides; session?: SessionOverrides } = {},
) {
  cleanup();
  localStorage.clear();

  if (overrides.auth) {
    updateStore(useAuthStore, overrides.auth);
  }
  if (overrides.session) {
    updateStore(useSessionStore, overrides.session);
  }

  return render(ui, { initialEntries: [path], withRouter: true });
}
