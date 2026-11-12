import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useAuthStore } from "@/stores/authStore";
import { useSessionStore } from "@/stores/sessionStore";
import { updateStore } from "@/test/zustand";
import { render } from "@/test/utils";
import AccountMenu from "./AccountMenu";

const ACCOUNT = {
  isAuthenticated: true,
  token: "t",
  user: {
    id: "u1",
    isAdmin: false,
    isHost: true,
    displayName: "Spencer",
  },
};

const NO_SESSION = {
  sessionId: null,
  isStageDevice: false,
  displayName: null,
};

const GUEST_SESSION = {
  sessionId: "s1",
  isStageDevice: false,
  displayName: "Alex",
};

const openMenu = async (name: string) => {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: new RegExp(name) }));
  return user;
};

describe("AccountMenu", () => {
  let leaveSession: Mock<() => Promise<void>>;
  let logout: Mock<() => void>;

  beforeEach(() => {
    localStorage.clear();
    leaveSession = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    logout = vi.fn<() => void>();
    updateStore(useAuthStore, {
      isAuthenticated: false,
      token: null,
      user: null,
      logout,
    });
    updateStore(useSessionStore, { ...NO_SESSION, leaveSession });
  });

  it("renders nothing without access", () => {
    const { container } = render(<AccountMenu />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows on the stage device too", () => {
    updateStore(useAuthStore, ACCOUNT);
    updateStore(useSessionStore, { sessionId: "s1", isStageDevice: true });
    render(<AccountMenu />);
    expect(screen.getByRole("button", { name: /Spencer/ })).toBeInTheDocument();
  });

  it("lets a guest leave the session, with no log out", async () => {
    updateStore(useSessionStore, GUEST_SESSION);
    render(<AccountMenu />);

    const user = await openMenu("Alex");
    expect(screen.queryByText("Log out")).not.toBeInTheDocument();
    await user.click(screen.getByText("Leave session"));

    expect(leaveSession).toHaveBeenCalledOnce();
    expect(logout).not.toHaveBeenCalled();
  });

  it("logs an account out without a session to leave", async () => {
    updateStore(useAuthStore, ACCOUNT);
    render(<AccountMenu />);

    const user = await openMenu("Spencer");
    expect(screen.queryByText("Leave session")).not.toBeInTheDocument();
    await user.click(screen.getByText("Log out"));

    expect(leaveSession).not.toHaveBeenCalled();
    expect(logout).toHaveBeenCalledOnce();
  });

  it("leaves the session before logging out of an account", async () => {
    updateStore(useAuthStore, ACCOUNT);
    updateStore(useSessionStore, GUEST_SESSION);
    render(<AccountMenu />);

    const user = await openMenu("Alex");
    await user.click(screen.getByText("Log out"));

    expect(leaveSession).toHaveBeenCalledOnce();
    expect(logout).toHaveBeenCalledOnce();
    expect(leaveSession.mock.invocationCallOrder[0]).toBeLessThan(
      logout.mock.invocationCallOrder[0],
    );
  });
});
