/**
 * whosHere - the rows of the stage's "Who's here" panel, worked out in one
 * place so the rules can be tested without rendering the popover.
 *
 * One row per singer still in the rotation. Anyone removed from it for the
 * night is left out: they asked to stop, and listing them would read as
 * "still waiting for a turn".
 *
 * Order follows the turn: the circle starts with whoever is up next, so the
 * person singing now comes last, having just had their go. In append mode
 * there is no circle and the rows keep seat (join) order.
 */

import type {
  KaraokeQueueItemWithSong,
  SessionTurn,
} from "@/types/KaraokeQueue";
import type { PerformerPresence } from "@/types/Presence";
import type { SessionPerformer } from "@/types/SessionPerformer";

export type SingerStatus = "singing" | "up_next" | "queued" | "no_song";

export interface WhosHereRow {
  id: number;
  name: string;
  status: SingerStatus;
  /** Their songs waiting in the queue, not counting one playing now. */
  queuedCount: number;
  /**
   * Their phone: open on screen, or closed / locked / in the background.
   * Null when no phone is linked to them, e.g. a name the host typed in.
   */
  phone: "open" | "closed" | null;
}

interface WhosHereInput {
  roster: SessionPerformer[];
  current: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  turn: SessionTurn | null;
  presence: Record<number, PerformerPresence>;
}

export function whosHere({
  roster,
  current,
  upcoming,
  turn,
  presence,
}: WhosHereInput): WhosHereRow[] {
  const active = roster
    .filter((p) => p.is_active)
    .sort((a, b) => a.seat - b.seat);

  const circleOrder = new Map(
    (turn?.circle ?? []).map((p, index) => [p.id, index]),
  );
  // Anyone the circle hasn't caught up with yet (a join a moment ago) goes
  // after it, in seat order - the sort is stable.
  const ordered =
    circleOrder.size > 0
      ? [...active].sort(
          (a, b) =>
            (circleOrder.get(a.id) ?? Infinity) -
            (circleOrder.get(b.id) ?? Infinity),
        )
      : active;

  // Append mode names nobody in the turn, so whoever owns the next song is up.
  const upNextId =
    turn && turn.kind !== "open" && turn.performerId != null
      ? turn.performerId
      : (upcoming[0]?.performerId ?? null);
  const singingId = current?.performerId ?? null;

  const queued = new Map<number, number>();
  for (const item of upcoming) {
    if (item.performerId == null) continue;
    queued.set(item.performerId, (queued.get(item.performerId) ?? 0) + 1);
  }

  return ordered.map((performer) => {
    const queuedCount = queued.get(performer.id) ?? 0;
    const status: SingerStatus =
      performer.id === singingId
        ? "singing"
        : performer.id === upNextId
          ? "up_next"
          : queuedCount > 0
            ? "queued"
            : "no_song";
    const linked = presence[performer.id];
    return {
      id: performer.id,
      name: performer.name,
      status,
      queuedCount,
      phone: linked
        ? linked.connected && linked.visible
          ? "open"
          : "closed"
        : null,
    };
  });
}

/** What the row says about where they are in the night, in a guest's words. */
export function statusLabel(row: WhosHereRow): string {
  switch (row.status) {
    case "singing":
      return "Singing now";
    case "up_next":
      return row.queuedCount > 0 ? "Up next" : "Up next - needs to pick a song";
    case "queued":
      return row.queuedCount === 1
        ? "1 song waiting"
        : `${row.queuedCount} songs waiting`;
    case "no_song":
      return "Hasn't picked a song yet";
  }
}
