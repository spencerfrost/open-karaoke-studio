import { useQueryClient } from "@tanstack/react-query";

import { useApiMutation, useApiQuery } from "@/hooks/api/useApi";

/** [start, end] in seconds. */
export type Span = [number, number];

/** One song in the Compare breaks list. */
export interface SingingMapSongRow {
  songId: string;
  title: string;
  artist: string;
  /** False until the singing map is measured (the page measures on open). */
  measured: boolean;
  hasWordTiming: boolean;
  /** Breaks the TV shows today, from gaps between aligned words. */
  wordGapBreaks: number;
  /** Breaks from the singing map; null until measured. */
  mapBreaks: number | null;
  /** Breaks the two methods don't agree on; null until measured. */
  disagreements: number | null;
  /** Moments still to listen to (breaks both agree on don't count). */
  toCheck: number;
  /** Answers given about the moments it shows now. */
  answers: BreakCheckAnswer[];
}

/** What can be said about a moment, by ear. */
export type BreakCheckAnswer =
  | "map_right"
  | "today_right"
  | "both_wrong"
  | "either_fine"
  | "bar_fine"
  | "no_bar"
  | "lyrics_match"
  | "lyrics_dont_match";

/** An instrumental break, in the shape the player reads. */
export interface BreakInterval {
  start: number;
  end: number;
  duration: number;
  lead_in_start: number;
  next_line_index: number;
  confidence: number;
  source: string;
}

interface MomentBase {
  /** Identifies the moment by its exact times; answers are saved by it. */
  key: string;
  answer: BreakCheckAnswer | null;
}

/** Something worth a listen, in song order. */
export type BreaksMoment = MomentBase &
  (
    | {
        kind: "break";
        start: number;
        end: number;
        /** Each method's version of the break; null when it found none here. */
        map: Span | null;
        wordGaps: Span | null;
        /** Both found it and their ends are within 1.5 s. */
        agree: boolean;
      }
    | {
        kind: "backing_only";
        start: number;
        end: number;
        /** A lyric line is on screen meanwhile, so this isn't a break. */
        onScreen: boolean;
        lineText: string | null;
      }
  );

export interface SingingMapLine {
  /** The line's index in the LRC, blank lines included. */
  index: number;
  start: number;
  end: number;
  text: string;
  /** Start and end come from word timing, not the LRC timestamps. */
  timed: boolean;
}

export interface SingingMapSong {
  songId: string;
  title: string;
  artist: string;
  duration: number | null;
  measured: boolean;
  measuredAt: string | null;
  params: Record<string, number> | null;
  hasWordTiming: boolean;
  lead: Span[];
  /** null: the song has no backing vocals track. */
  backing: Span[] | null;
  /** Backing singing while a line is on screen: counted as singing. */
  backingOnScreen: Span[];
  lines: SingingMapLine[];
  mapBreaks: BreakInterval[] | null;
  wordGapBreaks: BreakInterval[];
  moments: BreaksMoment[] | null;
}

const KEY = ["admin", "singing-map"] as const;

/** Songs with synced lyrics, most still to check first, and every answer
 * so far counted. Admins only. */
export function useSingingMapSongs() {
  return useApiQuery<
    {
      songs: SingingMapSongRow[];
      tally: Partial<Record<BreakCheckAnswer, number>>;
    },
    typeof KEY
  >(KEY, "admin/singing-map/songs");
}

/** One song's map, breaks and moments; measures it first if needed. */
export function useSingingMapSong(songId: string) {
  return useApiQuery<SingingMapSong, readonly [...typeof KEY, string]>(
    [...KEY, songId],
    `admin/singing-map/songs/${songId}`,
    { retry: false },
  );
}

/** Answer moments by ear; `answer: null` clears one. */
export function useSaveBreakChecks(songId: string) {
  const queryClient = useQueryClient();
  return useApiMutation<
    SingingMapSong,
    { answers: { key: string; answer: BreakCheckAnswer | null }[] }
  >(`admin/singing-map/songs/${songId}/checks`, "put", {
    onSuccess: (song) => {
      queryClient.setQueryData([...KEY, songId], song);
      queryClient.invalidateQueries({ queryKey: KEY, exact: true });
    },
  });
}
