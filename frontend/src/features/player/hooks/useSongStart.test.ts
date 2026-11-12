import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import {
  COUNTDOWN_STEP_MS,
  IDLE,
  useSongCountdownStore,
} from "@/stores/useSongCountdownStore";
import { useSongStart } from "./useSongStart";

type Props = Parameters<typeof useSongStart>[0];

const countdown = () => useSongCountdownStore.getState().countdown;

function setup(initial: Partial<Props> = {}) {
  const play = vi.fn();
  let props: Props = {
    enabled: true,
    visible: true,
    songId: "a",
    loadedSongId: null,
    isReady: false,
    isPlaying: false,
    failed: false,
    play,
    ...initial,
  };
  const hook = renderHook((p: Props) => useSongStart(p), {
    initialProps: props,
  });
  const update = (next: Partial<Props>) => {
    props = { ...props, ...next };
    hook.rerender(props);
  };
  // One step at a time: each tick schedules the next from an effect, which
  // only runs once React has rendered the last one.
  const steps = (n: number) => {
    for (let i = 0; i < n; i++) {
      act(() => {
        vi.advanceTimersByTime(COUNTDOWN_STEP_MS);
      });
    }
  };
  return { play, update, steps, hook };
}

describe("useSongStart", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    act(() => useSongCountdownStore.setState({ countdown: IDLE }));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("waits while the old song fades, then counts 3-2-1 and plays", () => {
    // The old song "z" is still loaded (fading) when "a" is asked for.
    const { play, update, steps } = setup({
      loadedSongId: "z",
      isPlaying: true,
    });
    update({ songId: "a" });
    expect(countdown()).toEqual({ phase: "waiting", songId: "a" });

    // The fade ends: the store switches to "a" and loads it.
    update({ loadedSongId: "a", isPlaying: false });
    expect(countdown()).toMatchObject({ phase: "counting", count: 3 });

    update({ isReady: true });
    steps(1);
    expect(countdown()).toMatchObject({ count: 2 });
    steps(1);
    expect(countdown()).toMatchObject({ count: 1 });
    expect(play).not.toHaveBeenCalled();
    steps(1);
    expect(play).toHaveBeenCalledTimes(1);
    expect(countdown()).toEqual(IDLE);
  });

  it("holds on 1 until the audio is ready", () => {
    const { play, update, steps } = setup({ songId: "z", loadedSongId: "z" });
    update({ songId: "a", loadedSongId: "a" });
    steps(3);
    expect(countdown()).toMatchObject({ count: 1, holding: true });
    steps(10);
    expect(countdown()).toMatchObject({ count: 1, holding: true });
    expect(play).not.toHaveBeenCalled();

    update({ isReady: true });
    expect(play).toHaveBeenCalledTimes(1);
    expect(countdown()).toEqual(IDLE);
  });

  it("never counts for the song it already started", () => {
    // Restarting a song seeks it back to 0:00; the song id doesn't change.
    const { play, update, steps } = setup({
      songId: "a",
      loadedSongId: "a",
      isReady: true,
      isPlaying: true,
    });
    expect(countdown()).toEqual(IDLE);
    update({ isPlaying: false });
    update({ isPlaying: true });
    steps(5);
    expect(countdown()).toEqual(IDLE);
    expect(play).not.toHaveBeenCalled();
  });

  it("doesn't count again for a song it counted into", () => {
    const { play, update, steps } = setup({ songId: "z", loadedSongId: "z" });
    update({ songId: "a", loadedSongId: "a", isReady: true });
    steps(3);
    expect(play).toHaveBeenCalledTimes(1);
    update({ isPlaying: true });
    update({ isPlaying: false });
    steps(5);
    expect(countdown()).toEqual(IDLE);
    expect(play).toHaveBeenCalledTimes(1);
  });

  it("waits while the player is covered, and restarts the count when shown", () => {
    const { play, update, steps } = setup({
      songId: "z",
      loadedSongId: "z",
      visible: false,
    });
    update({ songId: "a", loadedSongId: "a", isReady: true });
    steps(5);
    expect(countdown()).toEqual({ phase: "waiting", songId: "a" });

    update({ visible: true });
    steps(1);
    expect(countdown()).toMatchObject({ count: 2 });
    update({ visible: false });
    expect(countdown()).toEqual({ phase: "waiting", songId: "a" });
    update({ visible: true });
    expect(countdown()).toMatchObject({ count: 3 });
    expect(play).not.toHaveBeenCalled();
  });

  it("ends the count without playing again when someone presses play", () => {
    const { play, update } = setup({ songId: "z", loadedSongId: "z" });
    update({ songId: "a", loadedSongId: "a", isReady: true });
    update({ isPlaying: true });
    expect(countdown()).toEqual(IDLE);
    expect(play).not.toHaveBeenCalled();
  });

  it("drops the count when loading fails", () => {
    const { update } = setup({ songId: "z", loadedSongId: "z" });
    update({ songId: "a", loadedSongId: "a" });
    expect(countdown().phase).toBe("counting");
    update({ failed: true });
    expect(countdown()).toEqual(IDLE);
  });

  it("does nothing when autoplay is off", () => {
    const { update, steps } = setup({
      enabled: false,
      songId: "z",
      loadedSongId: "z",
    });
    update({ songId: "a", loadedSongId: "a", isReady: true });
    steps(5);
    expect(countdown()).toEqual(IDLE);
  });
});
