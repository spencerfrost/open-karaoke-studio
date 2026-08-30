/**
 * useRecentSingers - the names already singing tonight, newest first.
 *
 * The stage's confirm screen needs to ask "who is singing?" without making
 * anyone type on a TV, and the queue already holds every name used so far.
 * This is a stand-in for the session roster (unit 3), which will replace it
 * with real performer entries rather than deduplicated strings.
 */

import { useMemo } from "react";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

const MAX_RECENT_SINGERS = 6;

export const useRecentSingers = (
  items?: KaraokeQueueItemWithSong[],
): string[] =>
  useMemo(() => {
    if (!items?.length) return [];

    const seen = new Set<string>();
    const names: string[] = [];

    // Newest first: the person who just queued something is the likeliest
    // next answer, and the oldest names fall off the end of the chip row.
    for (let i = items.length - 1; i >= 0; i--) {
      const name = items[i].singer?.trim();
      if (!name) continue;

      const key = name.toLowerCase();
      if (seen.has(key)) continue;

      seen.add(key);
      names.push(name);
      if (names.length >= MAX_RECENT_SINGERS) break;
    }

    return names;
  }, [items]);
