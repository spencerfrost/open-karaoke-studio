import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { screen, userEvent } from "@/test/utils";
import { renderRoute } from "@/test/routing";
import { useDesktopLayout } from "@/hooks/useDesktopLayout";
import Entry from "./Entry";

vi.mock("@/hooks/useDesktopLayout", () => ({
  useDesktopLayout: vi.fn(() => false),
}));

const ANON = {
  auth: { isAuthenticated: false, user: null },
  session: { sessionId: null, isConnecting: false, connectionError: null },
};

const renderEntry = (path: string) =>
  renderRoute(
    <Routes>
      <Route path="/join" element={<Entry />} />
      <Route path="/join/:code" element={<Entry />} />
    </Routes>,
    path,
    ANON,
  );

describe("Entry - which way in comes first", () => {
  beforeEach(() => {
    vi.mocked(useDesktopLayout).mockReturnValue(false);
  });

  it("opens on joining with a code on a phone", () => {
    renderEntry("/join");

    expect(
      screen.getByRole("heading", { name: "Join the karaoke" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Hosting tonight?")).toBeInTheDocument();
  });

  it("opens on sign-in on a computer or TV, the code row underneath", () => {
    vi.mocked(useDesktopLayout).mockReturnValue(true);
    renderEntry("/join");

    expect(
      screen.getByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Here to sing? Type the code from the TV."),
    ).toBeInTheDocument();
  });

  it("swaps between joining and signing in", async () => {
    renderEntry("/join");

    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      screen.getByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Enter a code" }));
    expect(
      screen.getByRole("heading", { name: "Join the karaoke" }),
    ).toBeInTheDocument();
  });

  it("asks only for a name after a QR scan, with a way to retype the code", async () => {
    renderEntry("/join/WXYZ");

    expect(screen.getByText("WXYZ")).toBeInTheDocument();
    expect(screen.getByLabelText("What should we call you?")).toHaveFocus();
    expect(screen.queryByText("Hosting tonight?")).not.toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "Type the code instead" }),
    );
    expect(screen.getByLabelText("Code from the TV")).toHaveValue("WXYZ");
  });
});
