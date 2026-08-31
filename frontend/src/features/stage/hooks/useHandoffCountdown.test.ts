import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useHandoffCountdown } from "./useHandoffCountdown";

describe("useHandoffCountdown", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("counts down and fires once at zero", () => {
    const onExpire = vi.fn();
    const { result } = renderHook(() =>
      useHandoffCountdown({ seconds: 3, onExpire, resetKey: 1 }),
    );

    expect(result.current.remaining).toBe(3);
    act(() => void vi.advanceTimersByTime(3000));
    expect(result.current.remaining).toBe(0);
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("does not run at all when seconds is null", () => {
    const onExpire = vi.fn();
    const { result } = renderHook(() =>
      useHandoffCountdown({ seconds: null, onExpire, resetKey: 1 }),
    );

    act(() => void vi.advanceTimersByTime(60000));
    expect(result.current.remaining).toBeNull();
    expect(onExpire).not.toHaveBeenCalled();
  });

  it("stops for good once cancelled", () => {
    const onExpire = vi.fn();
    const { result } = renderHook(() =>
      useHandoffCountdown({ seconds: 5, onExpire, resetKey: 1 }),
    );

    act(() => void vi.advanceTimersByTime(1000));
    act(() => result.current.cancel());
    expect(result.current.cancelled).toBe(true);

    act(() => void vi.advanceTimersByTime(60000));
    expect(onExpire).not.toHaveBeenCalled();
  });

  it("stays cancelled across re-renders from queue broadcasts", () => {
    // The regression this hook exists for: the handoff screen re-renders on
    // every queue_updated, and the version it replaces reset its guard on any
    // dependency change - so an unrelated broadcast restarted a countdown
    // somebody had already stopped.
    const onExpire = vi.fn();
    const { result, rerender } = renderHook(
      ({ onExpire: fn }) =>
        useHandoffCountdown({ seconds: 5, onExpire: fn, resetKey: 1 }),
      { initialProps: { onExpire } },
    );

    act(() => result.current.cancel());
    rerender({ onExpire: vi.fn() });
    rerender({ onExpire: vi.fn() });

    act(() => void vi.advanceTimersByTime(60000));
    expect(result.current.cancelled).toBe(true);
    expect(onExpire).not.toHaveBeenCalled();
  });

  it("starts fresh when the next handoff begins", () => {
    const onExpire = vi.fn();
    const { result, rerender } = renderHook(
      ({ resetKey }) => useHandoffCountdown({ seconds: 3, onExpire, resetKey }),
      { initialProps: { resetKey: 1 } },
    );

    act(() => result.current.cancel());
    expect(result.current.cancelled).toBe(true);

    // A different person is up now - that is a new handoff, not the old one.
    rerender({ resetKey: 2 });
    expect(result.current.cancelled).toBe(false);
    expect(result.current.remaining).toBe(3);

    act(() => void vi.advanceTimersByTime(3000));
    expect(onExpire).toHaveBeenCalledTimes(1);
  });
});
