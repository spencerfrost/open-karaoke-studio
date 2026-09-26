import { describe, expect, it } from "vitest";
import { evaluateAccess } from "./useAccess";

const noAuth = { isAuthenticated: false, user: null };
const noSession = {
  sessionId: null,
  displayName: null,
  isStageDevice: false,
  isSessionOwner: false,
  isRecovering: false,
};

describe("evaluateAccess", () => {
  it("denies entry with no account and no session", () => {
    const access = evaluateAccess(noAuth, noSession);
    expect(access.canEnter).toBe(false);
    expect(access.isAuthenticated).toBe(false);
    expect(access.inSession).toBe(false);
  });

  it("grants entry to a session guest with no account", () => {
    const access = evaluateAccess(noAuth, { ...noSession, sessionId: "ABCD" });
    expect(access.canEnter).toBe(true);
    expect(access.isHost).toBe(false);
    expect(access.isAdmin).toBe(false);
  });

  it("grants entry to any authenticated account, not just host/admin", () => {
    const access = evaluateAccess(
      {
        isAuthenticated: true,
        user: { isAdmin: false, isHost: false, displayName: "Performer" },
      },
      noSession,
    );
    expect(access.canEnter).toBe(true);
    expect(access.isHost).toBe(false);
  });

  it("does not derive canEnter from isHost or isAdmin", () => {
    // A guest with a session but definitely no host/admin flag must still
    // clear the gate. This pins the requirement down against the backend's
    // require_host_or_session_member (any account, not host-only).
    const access = evaluateAccess(noAuth, { ...noSession, sessionId: "ABCD" });
    expect(access.canEnter).toBe(access.isAuthenticated || access.inSession);
    expect(access.canEnter).not.toBe(access.isHost || access.isAdmin);
  });

  it("treats admin as host", () => {
    const access = evaluateAccess(
      {
        isAuthenticated: true,
        user: { isAdmin: true, isHost: false, displayName: "Admin" },
      },
      noSession,
    );
    expect(access.isHost).toBe(true);
    expect(access.isAdmin).toBe(true);
  });

  it("prefers the session display name over the account display name", () => {
    const access = evaluateAccess(
      {
        isAuthenticated: true,
        user: { isAdmin: false, isHost: true, displayName: "Host Account" },
      },
      { ...noSession, sessionId: "ABCD", displayName: "Tonight's Name" },
    );
    expect(access.singerName).toBe("Tonight's Name");
  });

  it("falls back to the account display name when the session has none", () => {
    const access = evaluateAccess(
      {
        isAuthenticated: true,
        user: { isAdmin: false, isHost: true, displayName: "Host Account" },
      },
      { ...noSession, sessionId: "ABCD", displayName: null },
    );
    expect(access.singerName).toBe("Host Account");
  });

  it("surfaces isRecovering from the session slice", () => {
    const access = evaluateAccess(noAuth, { ...noSession, isRecovering: true });
    expect(access.isRecovering).toBe(true);
  });
});
