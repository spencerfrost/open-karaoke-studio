import { beforeEach, describe, expect, it, vi } from "vitest";

// Capture the listeners the store registers at module scope, so tests can play
// server messages into it.
const handlers = vi.hoisted(
  () => new Map<string, (data: Record<string, unknown>) => void>(),
);
vi.mock("@/services/sessionWebSocketService", () => ({
  sessionWebSocketService: {
    on: (event: string, listener: (data: Record<string, unknown>) => void) => {
      handlers.set(event, listener);
      return () => handlers.delete(event);
    },
  },
}));

import {
  needsPhoneOpened,
  shouldOpenControls,
  usePresenceStore,
} from "./presenceStore";

const emit = (event: string, data: Record<string, unknown>) =>
  handlers.get(event)?.(data);

const sarah = {
  performerId: 3,
  connected: true,
  visible: true,
  onControls: false,
};

describe("shouldOpenControls", () => {
  const mine = { id: "12", performerId: 3 };

  it("opens for this device's song", () => {
    expect(
      shouldOpenControls({
        current: mine,
        myPerformerId: 3,
        autoOpenedItemId: null,
      }),
    ).toBe(true);
  });

  it("opens once per song, not on every later broadcast", () => {
    expect(
      shouldOpenControls({
        current: mine,
        myPerformerId: 3,
        autoOpenedItemId: "12",
      }),
    ).toBe(false);
  });

  it("opens again for this device's next song", () => {
    expect(
      shouldOpenControls({
        current: { id: 15, performerId: 3 },
        myPerformerId: 3,
        autoOpenedItemId: "12",
      }),
    ).toBe(true);
  });

  it("leaves someone else's song alone", () => {
    expect(
      shouldOpenControls({
        current: { id: "12", performerId: 4 },
        myPerformerId: 3,
        autoOpenedItemId: null,
      }),
    ).toBe(false);
  });

  it("waits until the server says which seat this device is", () => {
    expect(
      shouldOpenControls({
        current: mine,
        myPerformerId: null,
        autoOpenedItemId: null,
      }),
    ).toBe(false);
  });

  it("does nothing with no song playing, or a song with no seat", () => {
    expect(
      shouldOpenControls({
        current: null,
        myPerformerId: 3,
        autoOpenedItemId: null,
      }),
    ).toBe(false);
    expect(
      shouldOpenControls({
        current: { id: "12", performerId: null },
        myPerformerId: 3,
        autoOpenedItemId: null,
      }),
    ).toBe(false);
  });
});

describe("needsPhoneOpened", () => {
  it("prompts for a phone that is closed or in the background", () => {
    expect(needsPhoneOpened({ ...sarah, connected: false })).toBe(true);
    expect(needsPhoneOpened({ ...sarah, visible: false })).toBe(true);
  });

  it("stays quiet for an open phone, even off the controls page", () => {
    expect(needsPhoneOpened(sarah)).toBe(false);
  });

  it("stays quiet for a singer with no phone linked", () => {
    expect(needsPhoneOpened(undefined)).toBe(false);
  });
});

describe("usePresenceStore", () => {
  beforeEach(() => {
    usePresenceStore.getState().reset();
  });

  it("hydrates from the greeting and follows updates", () => {
    emit("session_connected", { session_id: "ABCD", presence: [sarah] });
    expect(usePresenceStore.getState().performers[3]).toEqual(sarah);

    emit("presence_updated", {
      performers: [{ ...sarah, visible: false }],
    });
    expect(usePresenceStore.getState().performers[3].visible).toBe(false);
  });

  it("learns this device's seat from the acknowledgement", () => {
    emit("presence_acknowledged", { performer_id: 3 });
    expect(usePresenceStore.getState().myPerformerId).toBe(3);
  });

  it("keeps the seat and the opened song across a reconnect", () => {
    emit("session_connected", { session_id: "ABCD", presence: [] });
    emit("presence_acknowledged", { performer_id: 3 });
    usePresenceStore.getState().markAutoOpened("12");

    emit("session_connected", { session_id: "ABCD", presence: [] });
    expect(usePresenceStore.getState().myPerformerId).toBe(3);
    expect(usePresenceStore.getState().autoOpenedItemId).toBe("12");
  });

  it("forgets everything for a different session or when it ends", () => {
    emit("session_connected", { session_id: "ABCD", presence: [sarah] });
    emit("presence_acknowledged", { performer_id: 3 });

    emit("session_connected", { session_id: "WXYZ", presence: [] });
    expect(usePresenceStore.getState().myPerformerId).toBe(null);
    expect(usePresenceStore.getState().performers).toEqual({});

    emit("presence_acknowledged", { performer_id: 5 });
    emit("session_ended", { reason: "Host disconnected" });
    expect(usePresenceStore.getState().myPerformerId).toBe(null);
    expect(usePresenceStore.getState().sessionId).toBe(null);
  });

  it("records when it opened the controls", () => {
    usePresenceStore.getState().markAutoOpened("12");
    const { autoOpenedItemId, autoOpenedAt } = usePresenceStore.getState();
    expect(autoOpenedItemId).toBe("12");
    expect(autoOpenedAt).toEqual(expect.any(Number));
  });
});
