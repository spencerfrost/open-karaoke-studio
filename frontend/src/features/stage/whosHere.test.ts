import { describe, expect, it } from "vitest";
import type {
  KaraokeQueueItemWithSong,
  SessionTurn,
} from "@/types/KaraokeQueue";
import type { SessionPerformer } from "@/types/SessionPerformer";
import { statusLabel, whosHere } from "./whosHere";

const performer = (
  id: number,
  name: string,
  seat: number,
  is_active = true,
): SessionPerformer => ({ id, name, seat, is_active });

const item = (
  id: string,
  performerId: number | null,
): KaraokeQueueItemWithSong =>
  ({
    id,
    performerId,
    singer: "",
    songId: "s",
    position: 0,
    addedAt: "",
  }) as KaraokeQueueItemWithSong;

const turn = (overrides: Partial<SessionTurn> = {}): SessionTurn => ({
  kind: "open",
  performerId: null,
  performerName: null,
  itemId: null,
  circle: [],
  ...overrides,
});

const roster = [
  performer(1, "Ana", 0),
  performer(2, "Ben", 1),
  performer(3, "Cy", 2),
];

describe("whosHere", () => {
  it("orders by the circle, which starts with whoever is up", () => {
    const rows = whosHere({
      roster,
      current: item("10", 1),
      upcoming: [item("11", 2)],
      turn: turn({
        kind: "queued",
        performerId: 2,
        itemId: 11,
        circle: [
          { id: 2, name: "Ben" },
          { id: 3, name: "Cy" },
          { id: 1, name: "Ana" },
        ],
      }),
      presence: {},
    });
    expect(rows.map((r) => [r.name, r.status])).toEqual([
      ["Ben", "up_next"],
      ["Cy", "no_song"],
      ["Ana", "singing"],
    ]);
  });

  it("keeps seat order in append mode, and the next song's owner is up", () => {
    const rows = whosHere({
      roster: [...roster].reverse(),
      current: null,
      upcoming: [item("11", 3), item("12", 1), item("13", 3)],
      turn: turn(),
      presence: {},
    });
    expect(rows.map((r) => [r.name, r.status, r.queuedCount])).toEqual([
      ["Ana", "queued", 1],
      ["Ben", "no_song", 0],
      ["Cy", "up_next", 2],
    ]);
  });

  it("puts someone the circle hasn't caught up with after it", () => {
    const rows = whosHere({
      roster,
      current: null,
      upcoming: [],
      turn: turn({
        kind: "empty_seat",
        performerId: 3,
        circle: [
          { id: 3, name: "Cy" },
          { id: 1, name: "Ana" },
        ],
      }),
      presence: {},
    });
    expect(rows.map((r) => r.name)).toEqual(["Cy", "Ana", "Ben"]);
    expect(statusLabel(rows[0])).toBe("Up next - needs to pick a song");
  });

  it("leaves out anyone removed from the rotation", () => {
    const rows = whosHere({
      roster: [...roster, performer(4, "Dee", 3, false)],
      current: null,
      upcoming: [item("11", 4)],
      turn: turn(),
      presence: {},
    });
    expect(rows.map((r) => r.name)).toEqual(["Ana", "Ben", "Cy"]);
  });

  it("says whose phone is open, closed, or not linked", () => {
    const rows = whosHere({
      roster,
      current: null,
      upcoming: [],
      turn: turn(),
      presence: {
        1: {
          performerId: 1,
          connected: true,
          visible: true,
          onControls: false,
        },
        2: {
          performerId: 2,
          connected: true,
          visible: false,
          onControls: false,
        },
      },
    });
    expect(rows.map((r) => r.phone)).toEqual(["open", "closed", null]);
  });
});

describe("statusLabel", () => {
  it("counts waiting songs", () => {
    const base = { id: 1, name: "Ana", phone: null } as const;
    expect(statusLabel({ ...base, status: "queued", queuedCount: 1 })).toBe(
      "1 song waiting",
    );
    expect(statusLabel({ ...base, status: "queued", queuedCount: 3 })).toBe(
      "3 songs waiting",
    );
  });
});
