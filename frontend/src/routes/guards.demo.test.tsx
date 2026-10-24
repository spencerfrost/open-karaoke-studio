import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { renderRoute } from "@/test/routing";
import { server } from "@/test/mocks/server";
import { useAuthStore } from "@/stores/authStore";
import AppRoutes from "./AppRoutes";

// Entry is left unmocked so "Try it live" runs end to end: the click, the
// auth store, and the entry page's redirect of demo accounts to the stage.
vi.mock("@/hooks/useDesktopLayout", () => ({ useDesktopLayout: () => true }));
vi.mock("../pages/Library", () => ({
  default: () => <div>library-page</div>,
}));
vi.mock("../pages/Stage", () => ({
  default: () => <div>stage-page</div>,
}));

const ANON = {
  auth: { isAuthenticated: false, user: null, token: null },
  session: {
    sessionId: null,
    isStageDevice: false,
    isSessionOwner: false,
    isRecovering: false,
    displayName: null,
  },
};

const demoEnabled = () =>
  server.use(http.get("/api/demo", () => HttpResponse.json({ enabled: true })));

describe("Entry - live demo", () => {
  it("hides Try it live when the server has no demo pool", async () => {
    renderRoute(<AppRoutes />, "/join", ANON);
    await screen.findByRole("heading", { name: "Sign in" });
    expect(
      screen.queryByRole("button", { name: "Try it live" }),
    ).not.toBeInTheDocument();
  });

  it("signs in to a demo account and opens the stage", async () => {
    demoEnabled();
    server.use(
      http.post("/api/demo/start", () =>
        HttpResponse.json({
          success: true,
          id: "7",
          display_name: "Demo Host",
          token: "demo-token",
          is_admin: false,
          is_host: true,
          is_demo: true,
        }),
      ),
    );
    renderRoute(<AppRoutes />, "/join", ANON);

    const button = await screen.findByRole("button", { name: "Try it live" });
    expect(button).toHaveAttribute("data-tour", "try-it-live");
    await userEvent.click(button);

    expect(await screen.findByText("stage-page")).toBeInTheDocument();
    expect(useAuthStore.getState().user?.isDemo).toBe(true);
  });

  it("explains a full pool", async () => {
    demoEnabled();
    server.use(
      http.post("/api/demo/start", () =>
        HttpResponse.json({ detail: "busy" }, { status: 503 }),
      ),
    );
    renderRoute(<AppRoutes />, "/join", ANON);

    await userEvent.click(
      await screen.findByRole("button", { name: "Try it live" }),
    );

    expect(
      await screen.findByText(/Every demo seat is taken right now/),
    ).toBeInTheDocument();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("explains the per-network limit", async () => {
    demoEnabled();
    server.use(
      http.post("/api/demo/start", () =>
        HttpResponse.json({ error: "Rate limit exceeded" }, { status: 429 }),
      ),
    );
    renderRoute(<AppRoutes />, "/join", ANON);

    await userEvent.click(
      await screen.findByRole("button", { name: "Try it live" }),
    );

    expect(
      await screen.findByText(/started a lot from your network/),
    ).toBeInTheDocument();
  });
});
