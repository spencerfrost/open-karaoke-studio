import { act } from "@testing-library/react";
import type { StoreApi, UseBoundStore } from "zustand";

/**
 * Resets a Zustand store to its initial state.
 * Use this in beforeEach to ensure clean state between tests.
 *
 * @example
 * beforeEach(() => {
 *   resetStore(useKaraokePlayerStore);
 * });
 */
export function resetStore<T extends object>(
  store: UseBoundStore<StoreApi<T>>,
  initialState?: Partial<T>,
): void {
  const state = store.getState();

  // Get initial values (non-function properties)
  const initialValues: Partial<T> = {};
  for (const key of Object.keys(state) as Array<keyof T>) {
    if (typeof state[key] !== "function") {
      initialValues[key] = undefined as T[keyof T];
    }
  }

  // Apply initial state override if provided
  act(() => {
    store.setState({ ...initialValues, ...initialState } as Partial<T>, true);
  });
}

/**
 * Gets the current state of a Zustand store (excluding functions).
 * Useful for assertions in tests.
 *
 * @example
 * const state = getStoreState(useKaraokePlayerStore);
 * expect(state.isPlaying).toBe(false);
 */
export function getStoreState<T extends object>(
  store: UseBoundStore<StoreApi<T>>,
): Partial<T> {
  const state = store.getState();
  const result: Partial<T> = {};

  for (const key of Object.keys(state) as Array<keyof T>) {
    if (typeof state[key] !== "function") {
      result[key] = state[key];
    }
  }

  return result;
}

/**
 * Updates a Zustand store state within an act() wrapper.
 * Use this when testing store actions in isolation.
 *
 * @example
 * updateStore(useKaraokePlayerStore, { isPlaying: true });
 */
export function updateStore<T extends object>(
  store: UseBoundStore<StoreApi<T>>,
  updates: Partial<T>,
): void {
  act(() => {
    store.setState(updates);
  });
}

/**
 * Calls a store action within an act() wrapper.
 * Use this when testing store actions that trigger state updates.
 *
 * @example
 * await callStoreAction(useKaraokePlayerStore, (state) => state.play());
 */
export async function callStoreAction<T extends object, R>(
  store: UseBoundStore<StoreApi<T>>,
  actionFn: (state: T) => R,
): Promise<R> {
  let result: R;
  await act(async () => {
    result = actionFn(store.getState());
    if (result instanceof Promise) {
      result = await result;
    }
  });
  return result!;
}

/**
 * Creates a mock initial state for the KaraokePlayerStore.
 * Useful for setting up specific test scenarios.
 */
export function createMockPlayerState(overrides: Record<string, unknown> = {}) {
  return {
    songId: null,
    instrumentalUrl: "",
    vocalUrl: "",
    isReady: false,
    isLoading: false,
    duration: 0,
    error: null,
    songTitle: null,
    songArtist: null,
    isPlaying: false,
    currentTime: 0,
    songEnded: false,
    vocalVolume: 0,
    instrumentalVolume: 1.0,
    lyricsSize: "medium" as const,
    lyricsOffset: 0,
    autoScrollEnabled: true,
    connected: false,
    miniPlayerEnabled: true,
    miniPlayerPosition: { x: 24, y: 24 },
    miniPlayerDismissed: false,
    ...overrides,
  };
}
