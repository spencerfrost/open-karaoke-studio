import { useQueryClient } from "@tanstack/react-query";

import { useApiMutation, useApiQuery } from "@/hooks/api/useApi";

/** Is this the note the lead sings here? */
export type MomentAnswer =
  | "right"
  /** The note shown is an octave above what's sung. */
  | "octave_high"
  /** The note shown is an octave below what's sung. */
  | "octave_low"
  | "wrong_note"
  /** Bleed, an effect, backing vocals or an instrument. */
  | "not_singer"
  /** The singer, but rapping or speaking: there's no note to judge. */
  | "no_note"
  /** The singer screaming or yelling: no clear note. */
  | "screamed"
  | "cant_tell";

export type SongKind = "sung" | "mixed" | "rapped" | "spoken" | "instrumental";

export interface RangeMethod {
  method: string;
  /** The pitch track it reads. */
  setting: string;
  description: string;
}

export interface RangeResult {
  low: string | null;
  high: string | null;
  /** Set instead of a range when the method says there's no sung range. */
  label: string | null;
}

export interface NoteRange {
  low: string;
  high: string;
}

export interface VocalRangeSongRow {
  songId: string;
  title: string;
  artist: string;
  group: string;
  /** What the app stores today. */
  stored: NoteRange | null;
  /** Each method's answer, by method name; null where it has no result. */
  results: Record<string, RangeResult | null>;
  /** Primary moments of the methods asked for, and how many are answered. */
  moments: number;
  answered: number;
  kind: SongKind | null;
  /** What kind of song the reference set says it is. */
  referenceKind: string | null;
}

export interface VocalRangeList {
  /** The methods asked for. */
  methods: RangeMethod[];
  /** Every method the benchmark has run. */
  allMethods: RangeMethod[];
  groups: { key: string; label: string }[];
  songs: VocalRangeSongRow[];
  /** Per method, how its ends were judged so far. */
  verdicts: Record<string, Partial<Record<MomentAnswer, number>>>;
  kinds: Partial<Record<SongKind, number>>;
}

/** A stretch of the lead a method says sets one end of the range. */
export interface RangeMoment {
  key: string;
  note: string;
  midi: number;
  start: number;
  duration: number;
  /** Which methods it sets an end for; rank 0 is that end's longest moment. */
  sets: { method: string; end: "low" | "high"; rank: number }[];
  /** Rank 0 for some method: it decides that end. The rest stand in when it
   * can't be told by ear. */
  primary: boolean;
  answer: MomentAnswer | null;
  /** The pitch track around it: [time, MIDI note, confident 0/1] per voiced frame. */
  contour: {
    start: number;
    end: number;
    points: [number, number, number][];
  } | null;
}

export interface SheetMusicReference {
  low?: string;
  high?: string;
  kind?: string;
  confidence?: string;
  source?: string;
  url?: string;
  notes?: string;
}

export interface VocalRangeSong {
  songId: string;
  title: string;
  artist: string;
  group: string;
  stored: NoteRange | null;
  reference: SheetMusicReference | null;
  kind: SongKind | null;
  methods: (RangeMethod & {
    result: RangeResult | null;
    verdicts: Record<"low" | "high", MomentAnswer | null>;
  })[];
  moments: RangeMoment[];
}

const KEY = ["admin", "vocal-range"] as const;

/** `?methods=a,b`, or nothing for every method. */
const methodsQuery = (methods: string[] | undefined) =>
  methods ? `?methods=${methods.map(encodeURIComponent).join(",")}` : "";

/** The benchmark's test songs; empty where it wasn't run. `methods`
 * narrows the moments counted to those methods. */
export function useVocalRangeSongs(methods: string[] | undefined) {
  return useApiQuery<
    VocalRangeList,
    readonly [...typeof KEY, "list", string[] | undefined]
  >(
    [...KEY, "list", methods],
    `admin/vocal-range/songs${methodsQuery(methods)}`,
  );
}

export function useVocalRangeSong(
  songId: string,
  methods: string[] | undefined,
) {
  return useApiQuery<
    VocalRangeSong,
    readonly [...typeof KEY, "song", string, string[] | undefined]
  >(
    [...KEY, "song", songId, methods],
    `admin/vocal-range/songs/${encodeURIComponent(songId)}${methodsQuery(methods)}`,
    { retry: false },
  );
}

/** Answer moments, or the song's kind (key "kind"); `answer: null` clears one. */
export function useSaveVocalRangeAnswers(
  songId: string,
  methods: string[] | undefined,
) {
  const queryClient = useQueryClient();
  return useApiMutation<
    VocalRangeSong,
    {
      answers: { key: string; answer: MomentAnswer | SongKind | null }[];
      methods?: string[];
    }
  >(`admin/vocal-range/songs/${encodeURIComponent(songId)}/answers`, "put", {
    onSuccess: (song) => {
      queryClient.setQueryData([...KEY, "song", songId, methods], song);
      queryClient.invalidateQueries({ queryKey: [...KEY, "list"] });
    },
  });
}
