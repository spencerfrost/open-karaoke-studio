import { afterEach, describe, expect, it, vi } from "vitest";
import {
  GUEST_WINDOW_MARKER_KEY,
  PHONE_VIEW_WINDOW_NAME,
  createGuestWindow,
  openPhoneView,
  phoneViewUrl,
} from "./guestWindow";

/** A fresh Storage per test, so nothing leaks between windows. */
function makeStorage(seed: Record<string, string> = {}): Storage {
  const items = new Map(Object.entries(seed));
  return {
    get length() {
      return items.size;
    },
    clear: () => items.clear(),
    getItem: (key) => items.get(key) ?? null,
    key: (index) => Array.from(items.keys())[index] ?? null,
    removeItem: (key) => {
      items.delete(key);
    },
    setItem: (key, value) => {
      items.set(key, String(value));
    },
  };
}

describe("createGuestWindow", () => {
  it("keeps an ordinary window's identity in the shared storage", () => {
    const sessionArea = makeStorage();
    const sharedArea = makeStorage();
    const win = createGuestWindow({ search: "", sessionArea, sharedArea });

    win.identityStorage.setItem("karaoke-auth", "host");

    expect(win.isGuestWindow()).toBe(false);
    expect(sharedArea.getItem("karaoke-auth")).toBe("host");
    expect(sessionArea.getItem("karaoke-auth")).toBeNull();
  });

  it("treats a window opened with the flag as a guest window", () => {
    const sessionArea = makeStorage();
    const sharedArea = makeStorage({ "karaoke-auth": "host" });
    const win = createGuestWindow({
      search: "?guest-window",
      sessionArea,
      sharedArea,
    });

    expect(win.isGuestWindow()).toBe(true);
    // The host's sign-in is not visible to the guest...
    expect(win.identityStorage.getItem("karaoke-auth")).toBeNull();
    // ...and the guest's records never reach the shared area.
    win.identityStorage.setItem("karaoke-performer-session", "guest");
    expect(sessionArea.getItem("karaoke-performer-session")).toBe("guest");
    expect(sharedArea.getItem("karaoke-performer-session")).toBeNull();
    expect(sharedArea.getItem("karaoke-auth")).toBe("host");
  });

  it("accepts the flag alongside other parameters", () => {
    const win = createGuestWindow({
      search: "?code=ABCD&guest-window=1",
      sessionArea: makeStorage(),
      sharedArea: makeStorage(),
    });
    expect(win.isGuestWindow()).toBe(true);
  });

  it("drops whatever sessionStorage it inherited from its opener", () => {
    // window.open copies the opener's sessionStorage into the new window.
    const sessionArea = makeStorage({ "karaoke-auth": "opener's" });
    const win = createGuestWindow({
      search: "?guest-window",
      sessionArea,
      sharedArea: makeStorage(),
    });

    expect(win.identityStorage.getItem("karaoke-auth")).toBeNull();
    expect(sessionArea.getItem(GUEST_WINDOW_MARKER_KEY)).toBe("1");
  });

  it("stays a guest window after a reload without the flag", () => {
    const sessionArea = makeStorage();
    createGuestWindow({
      search: "?guest-window",
      sessionArea,
      sharedArea: makeStorage(),
    });
    sessionArea.setItem("karaoke-performer-session", "guest");

    const reloaded = createGuestWindow({
      search: "",
      sessionArea,
      sharedArea: makeStorage(),
    });

    expect(reloaded.isGuestWindow()).toBe(true);
    // A reload keeps the guest it already is.
    expect(reloaded.identityStorage.getItem("karaoke-performer-session")).toBe(
      "guest",
    );
  });

  it("switches storage at once when marked mid-life", () => {
    const sessionArea = makeStorage();
    const sharedArea = makeStorage({ "karaoke-auth": "host" });
    const win = createGuestWindow({ search: "", sessionArea, sharedArea });

    win.markGuestWindow();
    win.identityStorage.removeItem("karaoke-auth");
    win.identityStorage.setItem("karaoke-auth", "signed out");

    expect(win.isGuestWindow()).toBe(true);
    expect(sessionArea.getItem(GUEST_WINDOW_MARKER_KEY)).toBe("1");
    expect(sessionArea.getItem("karaoke-auth")).toBe("signed out");
    expect(sharedArea.getItem("karaoke-auth")).toBe("host");
    // sharedStorage still reads the shared area in guest mode.
    expect(win.sharedStorage.getItem("karaoke-auth")).toBe("host");
  });

  it("keeps a guest in memory when sessionStorage is refused", () => {
    const sharedArea = makeStorage();
    const win = createGuestWindow({
      search: "?guest-window",
      sessionArea: null,
      sharedArea,
    });

    win.identityStorage.setItem("karaoke-auth", "guest");

    expect(win.isGuestWindow()).toBe(true);
    expect(win.identityStorage.getItem("karaoke-auth")).toBe("guest");
    expect(sharedArea.getItem("karaoke-auth")).toBeNull();
  });
});

describe("phoneViewUrl", () => {
  it("is the ordinary join link with the guest-window flag", () => {
    expect(phoneViewUrl("http://localhost:5173", "ABCD")).toBe(
      "http://localhost:5173/join/ABCD?guest-window",
    );
  });
});

describe("openPhoneView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function fakeWindow(href: string, pathname: string) {
    return {
      location: { href, pathname },
      focus: vi.fn(),
    };
  }

  it("opens a narrow named window and points it at the join link", () => {
    const phone = fakeWindow("about:blank", "blank");
    const open = vi
      .spyOn(window, "open")
      .mockReturnValue(phone as unknown as Window);

    expect(openPhoneView("ABCD")).toBe(true);

    const [url, name, features] = open.mock.calls[0];
    expect(url).toBe("");
    expect(name).toBe(PHONE_VIEW_WINDOW_NAME);
    expect(features).toContain("width=400");
    expect(phone.location.href).toBe(
      `${window.location.origin}/join/ABCD?guest-window`,
    );
    expect(phone.focus).toHaveBeenCalled();
  });

  it("brings back a phone view that has already joined, without reloading it", () => {
    const phone = fakeWindow("http://localhost:3000/", "/");
    vi.spyOn(window, "open").mockReturnValue(phone as unknown as Window);

    openPhoneView("ABCD");

    expect(phone.location.href).toBe("http://localhost:3000/");
    expect(phone.focus).toHaveBeenCalled();
  });

  it("re-points a phone view still on the join page", () => {
    const phone = fakeWindow("http://localhost:3000/join", "/join");
    vi.spyOn(window, "open").mockReturnValue(phone as unknown as Window);

    openPhoneView("WXYZ");

    expect(phone.location.href).toBe(
      `${window.location.origin}/join/WXYZ?guest-window`,
    );
  });

  it("reports a blocked window", () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    expect(openPhoneView("ABCD")).toBe(false);
  });
});
