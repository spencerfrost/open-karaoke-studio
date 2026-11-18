import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { isRenewalDue, tokenExpiryMs, useAuthStore } from "./authStore";

const DAY = 24 * 60 * 60 * 1000;

/** An unsigned JWT-shaped token; the client only reads the payload. */
function tokenExpiringIn(ms: number, now = Date.now()): string {
  const payload = btoa(JSON.stringify({ sub: "1", exp: (now + ms) / 1000 }))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `header.${payload}.signature`;
}

function signIn(token: string, isDemo = false) {
  useAuthStore.setState({
    token,
    isAuthenticated: true,
    user: { id: "1", displayName: "Sam", isAdmin: false, isHost: true, isDemo },
  });
}

describe("token expiry", () => {
  it("reads the expiry from the payload", () => {
    const now = Date.now();
    expect(tokenExpiryMs(tokenExpiringIn(DAY, now))).toBeCloseTo(now + DAY, -3);
  });

  it("is null for a token it can't read", () => {
    expect(tokenExpiryMs("not-a-jwt")).toBeNull();
  });

  it("is due once the token is a day old", () => {
    expect(isRenewalDue(tokenExpiringIn(7 * DAY))).toBe(false);
    expect(isRenewalDue(tokenExpiringIn(5 * DAY))).toBe(true);
  });
});

describe("renewIfDue", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    useAuthStore.setState({ token: null, user: null, isAuthenticated: false });
  });

  it("leaves a fresh token alone", async () => {
    signIn(tokenExpiringIn(7 * DAY));
    await useAuthStore.getState().renewIfDue();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("never renews a demo token", async () => {
    signIn(tokenExpiringIn(DAY), true);
    await useAuthStore.getState().renewIfDue();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("stores the renewed token", async () => {
    signIn(tokenExpiringIn(DAY));
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "1",
          display_name: "Sam",
          token: "renewed",
          is_admin: false,
          is_host: true,
          is_demo: false,
        }),
        { status: 200 },
      ),
    );

    await useAuthStore.getState().renewIfDue();

    expect(useAuthStore.getState().token).toBe("renewed");
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it("logs out when the server rejects the token", async () => {
    signIn(tokenExpiringIn(DAY));
    fetchMock.mockResolvedValue(new Response("{}", { status: 401 }));

    await useAuthStore.getState().renewIfDue();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("keeps the token when the server can't be reached", async () => {
    const token = tokenExpiringIn(DAY);
    signIn(token);
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    await useAuthStore.getState().renewIfDue();

    expect(useAuthStore.getState().token).toBe(token);
  });
});
