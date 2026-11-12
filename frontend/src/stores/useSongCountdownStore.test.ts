import { describe, expect, it } from "vitest";
import {
  COUNTDOWN_FROM,
  IDLE,
  beginCountdown,
  isReadyToStart,
  requestCountdown,
  suspendCountdown,
  tickCountdown,
  type SongCountdown,
} from "./useSongCountdownStore";

const counting = (count: number, holding = false): SongCountdown => ({
  phase: "counting",
  songId: "a",
  count,
  holding,
});

describe("song countdown transitions", () => {
  it("waits when a song is asked for, then counts from the top", () => {
    const waiting = requestCountdown(IDLE, "a");
    expect(waiting).toEqual({ phase: "waiting", songId: "a" });
    expect(beginCountdown(waiting, "a")).toEqual(counting(COUNTDOWN_FROM));
  });

  it("ignores a repeat request for the song already counting", () => {
    const state = counting(2);
    expect(requestCountdown(state, "a")).toBe(state);
  });

  it("lets a later song replace one mid-count", () => {
    expect(requestCountdown(counting(2), "b")).toEqual({
      phase: "waiting",
      songId: "b",
    });
  });

  it("only begins for the song it is waiting on", () => {
    const waiting = requestCountdown(IDLE, "a");
    expect(beginCountdown(waiting, "b")).toBe(waiting);
    expect(beginCountdown(IDLE, "a")).toBe(IDLE);
  });

  it("steps 3, 2, 1 and then holds on 1", () => {
    let state = counting(3);
    state = tickCountdown(state);
    expect(state).toEqual(counting(2));
    state = tickCountdown(state);
    expect(state).toEqual(counting(1));
    state = tickCountdown(state);
    expect(state).toEqual(counting(1, true));
    // Holding: further ticks change nothing.
    expect(tickCountdown(state)).toBe(state);
  });

  it("is ready to start only once holding and the audio is ready", () => {
    expect(isReadyToStart(counting(1), "a", true)).toBe(false);
    expect(isReadyToStart(counting(1, true), "a", false)).toBe(false);
    expect(isReadyToStart(counting(1, true), "b", true)).toBe(false);
    expect(isReadyToStart(counting(1, true), "a", true)).toBe(true);
  });

  it("goes back to waiting when the player is covered mid-count", () => {
    expect(suspendCountdown(counting(2))).toEqual({
      phase: "waiting",
      songId: "a",
    });
    expect(suspendCountdown(IDLE)).toBe(IDLE);
  });
});
