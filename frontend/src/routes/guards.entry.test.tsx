import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderRoute } from "@/test/routing";
import { useAuthStore } from "@/stores/authStore";
import { updateStore } from "@/test/zustand";
import AppRoutes from "./AppRoutes";

// Entry is deliberately left unmocked here (unlike guards.test.tsx) so these
// two tests exercise the real return-to / QR-prefill behaviour end to end.
vi.mock("../pages/Library", () => ({
  default: () => <div>library-page</div>,
}));
vi.mock("../pages/AddSong", () => ({
  default: () => <div>add-page</div>,
}));
vi.mock("../pages/Settings", () => ({
  default: () => <div>settings-page</div>,
}));
vi.mock("../pages/Stage", () => ({
  default: () => <div>stage-page</div>,
}));
vi.mock("../pages/PerformanceControlsPage", () => ({
  default: () => <div>controls-page</div>,
}));
vi.mock("../pages/AdminPanel", () => ({
  default: () => <div>admin-page</div>,
}));
vi.mock("../pages/AdminThreeTrackComparePage", () => ({
  default: () => <div>admin-compare-page</div>,
}));

const ANON = {
  auth: { isAuthenticated: false, user: null },
  session: {
    sessionId: null,
    isStageDevice: false,
    isSessionOwner: false,
    isRecovering: false,
    displayName: null,
  },
};

describe("Entry - return to and QR prefill", () => {
  it("carries the originally requested route through sign-in", async () => {
    renderRoute(<AppRoutes />, "/settings", ANON);

    // Redirected to the entry screen, host sign-in section present.
    expect(await screen.findByText("Join Karaoke Session")).toBeInTheDocument();

    // Sign in (bypassing the form - authStore.login talks to a real API).
    updateStore(useAuthStore, {
      isAuthenticated: true,
      user: { id: "1", isAdmin: false, isHost: true, displayName: "Host" },
    });

    expect(await screen.findByText("settings-page")).toBeInTheDocument();
  });

  it("prefills the code from a scanned QR link", () => {
    renderRoute(<AppRoutes />, "/join/WXYZ", ANON);

    expect(screen.getByText("Joining session")).toBeInTheDocument();
    expect(screen.getByText("WXYZ")).toBeInTheDocument();
  });
});
