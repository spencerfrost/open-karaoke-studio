/**
 * useDefaultSinger - who a "who's singing?" picker starts on.
 *
 * Whoever's turn it is, not whoever sits first on the roster. A walk-up at the
 * TV is almost always the person the handoff screen just called, and starting
 * on seat one (usually the host) filed their song under the wrong name.
 */

import { useState } from "react";
import type { SessionPerformer } from "@/types/SessionPerformer";
import type { SessionTurn } from "@/types/KaraokeQueue";

type TurnPerformer = Pick<SessionTurn, "performerId" | "performerName">;

/**
 * The turn's performer when the picker offers them, else the first seat.
 *
 * The roster only lists active performers, and a queued turn's name can come
 * from a deactivated performer or a legacy row's free-text `singer_name`, so
 * the turn is matched against the roster rather than trusted: the picker must
 * never start on a name it has no button for.
 */
export function pickDefaultSinger(
  roster: SessionPerformer[],
  turn: TurnPerformer | null | undefined,
): string {
  const match =
    turn?.performerId != null
      ? roster.find((p) => p.id === turn.performerId)
      : roster.find((p) => p.name === turn?.performerName);
  return (match ?? roster[0])?.name ?? "";
}

/**
 * The picker's singer, as `useState` would hand it back.
 *
 * Until someone picks, the value is derived on every render, so a roster or
 * turn that arrives after mount still moves the default. The first pick -
 * including "" from "Someone else…" - is stored and wins from then on.
 */
export function useDefaultSinger(
  roster: SessionPerformer[],
  turn: TurnPerformer | null | undefined,
) {
  const [picked, setPicked] = useState<string | null>(null);
  const singer = picked ?? pickDefaultSinger(roster, turn);
  return [singer, setPicked] as const;
}
