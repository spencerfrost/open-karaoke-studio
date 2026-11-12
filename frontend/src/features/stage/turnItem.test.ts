import { describe, expect, it } from "vitest";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";
import type { Song } from "@/types/Song";
import { findTurnItem } from "./turnItem";

const item = (id: string): KaraokeQueueItemWithSong => ({
  id,
  songId: `song-${id}`,
  singer: "Sarah",
  position: Number(id),
  addedAt: "2026-09-29T20:00:00Z",
  song: { id: `song-${id}` } as Song,
});

const upcoming = [item("4"), item("7")];

describe("findTurnItem", () => {
  it("finds the queued turn's item", () => {
    expect(findTurnItem({ kind: "queued", itemId: 7 }, upcoming)?.id).toBe("7");
  });

  it("is null for an empty seat or an open turn", () => {
    expect(findTurnItem({ kind: "empty_seat", itemId: null }, upcoming)).toBe(
      null,
    );
    expect(findTurnItem({ kind: "open", itemId: null }, upcoming)).toBe(null);
  });

  it("is null when the item hasn't reached the queue yet", () => {
    // The turn and the queue arrive in the same payload, but a stale cache
    // can still pair a new turn with the old list.
    expect(findTurnItem({ kind: "queued", itemId: 9 }, upcoming)).toBe(null);
  });
});
