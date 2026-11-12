import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import { renderRoute } from "@/test/routing";
import { server } from "@/test/mocks/server";
import { useAuthStore } from "@/stores/authStore";
import AppRoutes from "@/routes/AppRoutes";

// Stage itself is real: the point is what it does with no session to resume.
vi.mock("@/hooks/useDesktopLayout", () => ({ useDesktopLayout: () => true }));
vi.mock("./Library", () => ({ default: () => <div>library-page</div> }));
vi.mock("./Entry", () => ({ default: () => <div>join-page</div> }));
const createScreen = vi.hoisted(() => vi.fn());
vi.mock("@/features/stage/screens/CreateSessionScreen", () => ({
  default: () => {
    createScreen();
    return <div>create-session-screen</div>;
  },
}));

const host = (isDemo: boolean) => ({
  auth: {
    isAuthenticated: true,
    token: "token",
    user: {
      id: "7",
      displayName: "Host",
      isAdmin: false,
      isHost: true,
      isDemo,
    },
  },
});

/** Answers "no live session"; resolves once Stage has asked. */
const noLiveSession = () => {
  let asked = false;
  server.use(
    http.get("/api/sessions/my", () => {
      asked = true;
      return HttpResponse.json(null);
    }),
  );
  return () => asked;
};

describe("Stage - demo account with no session left", () => {
  it("signs the visitor out and sends them to the start page", async () => {
    createScreen.mockClear();
    noLiveSession();
    renderRoute(<AppRoutes />, "/stage", host(true));

    expect(await screen.findByText("join-page")).toBeInTheDocument();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(createScreen).not.toHaveBeenCalled();
  });

  it("still offers a normal host the create screen", async () => {
    const asked = noLiveSession();
    renderRoute(<AppRoutes />, "/stage", host(false));

    await waitFor(() => {
      expect(asked()).toBe(true);
      expect(screen.getByText("create-session-screen")).toBeInTheDocument();
    });
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });
});
