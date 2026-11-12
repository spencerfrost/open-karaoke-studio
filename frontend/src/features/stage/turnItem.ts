/**
 * turnItem - "does the next singer have a song?", asked in one place.
 *
 * The handoff screen asks it to decide what to show, and the shell asks it to
 * decide where Back goes after a song ends. Two copies of the check would let
 * the shell open the handoff screen for a song the screen itself can't find.
 */

import type {
  KaraokeQueueItemWithSong,
  SessionTurn,
} from "@/types/KaraokeQueue";

/**
 * The queued song whose turn it is, or null when the turn is an empty seat,
 * open, or points at an item the queue hasn't delivered yet.
 */
export function findTurnItem(
  turn: Pick<SessionTurn, "kind" | "itemId">,
  upcoming: KaraokeQueueItemWithSong[],
): KaraokeQueueItemWithSong | null {
  if (turn.kind !== "queued") return null;
  return upcoming.find((item) => Number(item.id) === turn.itemId) ?? null;
}
