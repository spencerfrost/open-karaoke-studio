import { afterEach, describe, expect, it, vi } from "vitest";
import {
  LOCAL_UPDATE_DEBOUNCE_MS,
  shouldIgnoreWebSocketUpdate,
  trackLocalUpdate,
} from "./websocketSync";
import type { LocalUpdateTracker } from "./types";

describe("shouldIgnoreWebSocketUpdate", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("ignores the echo of a local change", () => {
    const tracker: LocalUpdateTracker = {};
    trackLocalUpdate(tracker, "vocal_volume", 0.8);
    expect(shouldIgnoreWebSocketUpdate(tracker, "vocal_volume", 0.8)).toBe(
      true,
    );
  });

  it("ignores a stale broadcast that still carries the old value", () => {
    const tracker: LocalUpdateTracker = {};
    trackLocalUpdate(tracker, "vocal_volume", 0.8);
    expect(shouldIgnoreWebSocketUpdate(tracker, "vocal_volume", 0.4)).toBe(
      true,
    );
  });

  it("accepts any value once the window has passed", () => {
    vi.useFakeTimers();
    const tracker: LocalUpdateTracker = {};
    trackLocalUpdate(tracker, "vocal_volume", 0.8);
    vi.advanceTimersByTime(LOCAL_UPDATE_DEBOUNCE_MS + 1);
    expect(shouldIgnoreWebSocketUpdate(tracker, "vocal_volume", 0.4)).toBe(
      false,
    );
  });

  it("accepts controls with no local change", () => {
    expect(shouldIgnoreWebSocketUpdate({}, "vocal_volume", 0.4)).toBe(false);
  });

  it("still applies a different playback position", () => {
    const tracker: LocalUpdateTracker = {};
    trackLocalUpdate(tracker, "current_time", 10);
    expect(shouldIgnoreWebSocketUpdate(tracker, "current_time", 10.2)).toBe(
      true,
    );
    expect(shouldIgnoreWebSocketUpdate(tracker, "current_time", 42)).toBe(
      false,
    );
  });
});
