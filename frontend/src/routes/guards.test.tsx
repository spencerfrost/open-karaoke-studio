import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderRoute } from "@/test/routing";
import AppRoutes from "./AppRoutes";

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
vi.mock("../pages/Entry", () => ({
  default: () => <div>join-page</div>,
}));
vi.mock("../pages/AdminPanel", () => ({
  default: () => <div>admin-page</div>,
}));
vi.mock("../pages/AdminThreeTrackComparePage", () => ({
  default: () => <div>admin-compare-page</div>,
}));

interface Persona {
  auth: {
    isAuthenticated: boolean;
    user: { id: string; isAdmin: boolean; isHost: boolean; displayName: string | null } | null;
  };
  session: {
    sessionId: string | null;
    isStageDevice: boolean;
    isSessionOwner: boolean;
    isRecovering: boolean;
    displayName: string | null;
  };
}

const ANON: Persona = {
  auth: { isAuthenticated: false, user: null },
  session: {
    sessionId: null,
    isStageDevice: false,
    isSessionOwner: false,
    isRecovering: false,
    displayName: null,
  },
};

const GUEST: Persona = {
  auth: { isAuthenticated: false, user: null },
  session: {
    sessionId: "ABCD",
    isStageDevice: false,
    isSessionOwner: false,
    isRecovering: false,
    displayName: "Guest",
  },
};

const ACCOUNT_NOT_HOST: Persona = {
  auth: {
    isAuthenticated: true,
    user: { id: "1", isAdmin: false, isHost: false, displayName: "Fan" },
  },
  session: {
    sessionId: null,
    isStageDevice: false,
    isSessionOwner: false,
    isRecovering: false,
    displayName: null,
  },
};

const HOST_NO_SESSION: Persona = {
  auth: {
    isAuthenticated: true,
    user: { id: "2", isAdmin: false, isHost: true, displayName: "Host" },
  },
  session: {
    sessionId: null,
    isStageDevice: false,
    isSessionOwner: false,
    isRecovering: false,
    displayName: null,
  },
};

const HOST_STAGE_DEVICE: Persona = {
  auth: {
    isAuthenticated: true,
    user: { id: "2", isAdmin: false, isHost: true, displayName: "Host" },
  },
  session: {
    sessionId: "WXYZ",
    isStageDevice: true,
    isSessionOwner: true,
    isRecovering: false,
    displayName: null,
  },
};

const ADMIN_NO_SESSION: Persona = {
  auth: {
    isAuthenticated: true,
    user: { id: "3", isAdmin: true, isHost: false, displayName: "Admin" },
  },
  session: {
    sessionId: null,
    isStageDevice: false,
    isSessionOwner: false,
    isRecovering: false,
    displayName: null,
  },
};

const RECOVERING: Persona = {
  auth: { isAuthenticated: false, user: null },
  session: {
    sessionId: null,
    isStageDevice: false,
    isSessionOwner: false,
    isRecovering: true,
    displayName: null,
  },
};

function expectFinalPage(path: string, persona: Persona, text: string) {
  renderRoute(<AppRoutes />, path, persona);
  expect(screen.getByText(text)).toBeInTheDocument();
}

describe("gate matrix", () => {
  const routes = {
    "/": "library-page",
    "/add": "add-page",
  };

  it("anon is redirected to the entry screen from every gated route", () => {
    for (const path of ["/", "/add", "/settings", "/stage", "/controls", "/admin"]) {
      expectFinalPage(path, ANON, "join-page");
    }
  });

  it("a session guest reaches Library, Add and Controls", () => {
    expectFinalPage("/", GUEST, "library-page");
    expectFinalPage("/add", GUEST, "add-page");
    expectFinalPage("/controls", GUEST, "controls-page");
  });

  it("a session guest is bounced off Settings, Stage and Admin", () => {
    expectFinalPage("/settings", GUEST, "library-page");
    expectFinalPage("/stage", GUEST, "library-page");
    expectFinalPage("/admin", GUEST, "library-page");
  });

  it("a signed-in non-host account reaches Library, Add and Settings", () => {
    expectFinalPage("/", ACCOUNT_NOT_HOST, "library-page");
    expectFinalPage("/add", ACCOUNT_NOT_HOST, "add-page");
    expectFinalPage("/settings", ACCOUNT_NOT_HOST, "settings-page");
  });

  it("a signed-in non-host account is bounced off Stage, Controls and Admin", () => {
    expectFinalPage("/stage", ACCOUNT_NOT_HOST, "library-page");
    expectFinalPage("/controls", ACCOUNT_NOT_HOST, "library-page");
    expectFinalPage("/admin", ACCOUNT_NOT_HOST, "library-page");
  });

  it("a host with no session reaches Stage but not Controls or Admin", () => {
    expectFinalPage("/stage", HOST_NO_SESSION, "stage-page");
    expectFinalPage("/controls", HOST_NO_SESSION, "library-page");
    expectFinalPage("/admin", HOST_NO_SESSION, "library-page");
  });

  it("a host on their own stage device is bounced from Controls back to Stage", () => {
    expectFinalPage("/controls", HOST_STAGE_DEVICE, "stage-page");
  });

  it("an admin with no session reaches Stage and Admin but not Controls", () => {
    expectFinalPage("/stage", ADMIN_NO_SESSION, "stage-page");
    expectFinalPage("/admin", ADMIN_NO_SESSION, "admin-page");
    expectFinalPage("/controls", ADMIN_NO_SESSION, "library-page");
  });

  it("shows the recovery spinner instead of redirecting while a session is being recovered", () => {
    renderRoute(<AppRoutes />, "/", RECOVERING);
    expect(screen.getByText("Recovering session...")).toBeInTheDocument();
    expect(screen.queryByText("join-page")).not.toBeInTheDocument();
    expect(screen.queryByText("library-page")).not.toBeInTheDocument();
  });

  it("sanity: route table covers Library and Add with no persona", () => {
    for (const [path, text] of Object.entries(routes)) {
      expectFinalPage(path, HOST_NO_SESSION, text);
    }
  });
});
