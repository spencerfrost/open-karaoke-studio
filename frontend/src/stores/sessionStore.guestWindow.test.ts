/**
 * Joining as a guest from a browser that runs the stage. Its own file because
 * it turns the module-level guest window on, which can't be undone in-process.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { guestWindow } from "@/lib/guestWindow";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { useAuthStore } from "./authStore";
import { useSessionStore } from "./sessionStore";

const HOST_RECORD = JSON.stringify({ sessionId: "ABCD", deviceId: "stage-1" });

function mockJoin(isHost: boolean) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        session_id: "ABCD",
        display_code: "ABCD",
        device_id: "phone-1",
        is_host: isHost,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );
}

describe("joinSession in a browser that runs the stage", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.spyOn(sessionWebSocketService, "connectToSession").mockImplementation(
      () => {},
    );
    vi.spyOn(sessionWebSocketService, "on").mockReturnValue(() => {});
    vi.spyOn(sessionWebSocketService, "disconnect").mockImplementation(
      () => {},
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("leaves an ordinary browser's join exactly as it was", async () => {
    mockJoin(false);

    await useSessionStore.getState().joinSession("ABCD", "performer", "Sam");

    expect(guestWindow.isGuestWindow()).toBe(false);
    expect(localStorage.getItem("karaoke-performer-session")).toContain(
      "phone-1",
    );
  });

  it("turns the window into a guest window and leaves the host's records alone", async () => {
    localStorage.setItem("karaoke-host-session", HOST_RECORD);
    useAuthStore.setState({
      token: "host-token",
      user: { id: "1", displayName: "Host", isAdmin: false, isHost: true },
      isAuthenticated: true,
    });
    const hostAuth = localStorage.getItem("karaoke-auth");
    expect(hostAuth).toContain("host-token");
    mockJoin(false);

    await useSessionStore.getState().joinSession("ABCD", "performer", "Sam");

    expect(guestWindow.isGuestWindow()).toBe(true);
    // The guest is not signed in as the host...
    expect(useAuthStore.getState().token).toBeNull();
    // ...but the host still is, for every other window.
    expect(localStorage.getItem("karaoke-auth")).toBe(hostAuth);
    expect(localStorage.getItem("karaoke-host-session")).toBe(HOST_RECORD);
    // The guest's own record is kept to this window.
    expect(sessionStorage.getItem("karaoke-performer-session")).toContain(
      "phone-1",
    );
    expect(localStorage.getItem("karaoke-performer-session")).toBeNull();

    // Leaving clears only the guest's records.
    useSessionStore.getState().clearSession();
    expect(sessionStorage.getItem("karaoke-performer-session")).toBeNull();
    expect(localStorage.getItem("karaoke-host-session")).toBe(HOST_RECORD);
    expect(localStorage.getItem("karaoke-auth")).toBe(hostAuth);
  });
});
