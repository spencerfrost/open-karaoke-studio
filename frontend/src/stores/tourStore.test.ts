import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "./sessionStore";
import { tourKeyFor, tourStepFor, useTourStore } from "./tourStore";

describe("tourStore", () => {
  beforeEach(() => {
    useSessionStore.setState({ sessionId: null });
    useTourStore.getState().clear();
  });

  it("keys a session by its code and creation time", () => {
    const first = tourKeyFor("ABCD", "2026-10-25T10:00:00");
    const reused = tourKeyFor("ABCD", "2026-10-25T11:00:00");
    useTourStore.getState().setStep(first, "done");

    const { steps } = useTourStore.getState();
    expect(tourStepFor(steps, first)).toBe("done");
    // The same code handed to a later session starts the tour afresh.
    expect(tourStepFor(steps, reused)).toBe("sound");
  });

  it("keeps only the current session", () => {
    useTourStore.getState().setStep("A@1", "wheel");
    useTourStore.getState().setStep("B@2", "scan");
    expect(Object.keys(useTourStore.getState().steps)).toEqual(["B@2"]);
  });

  it("drops the tour when the session ends in this page", () => {
    useSessionStore.setState({ sessionId: "ABCD" });
    useTourStore.getState().setStep("ABCD@1", "mix");

    useSessionStore.setState({ sessionId: null });

    expect(useTourStore.getState().steps).toEqual({});
  });

  it("leaves the tour alone while a session is being recovered", () => {
    useTourStore.getState().setStep("ABCD@1", "mix");

    useSessionStore.setState({ sessionId: "ABCD" });

    expect(tourStepFor(useTourStore.getState().steps, "ABCD@1")).toBe("mix");
  });
});
