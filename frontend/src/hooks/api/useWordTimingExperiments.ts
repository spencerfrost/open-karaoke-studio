import { useQueryClient } from "@tanstack/react-query";

import { useApiMutation, useApiQuery } from "@/hooks/api/useApi";
import type { WordTimestamp } from "@/utils/lrcParser";

/** Which timing followed the singing, by ear. */
export type WordTimingAnswer =
  | "b_right"
  | "a_right"
  | "both_wrong"
  | "cant_tell";

/** One of an experiment's two timings. */
export interface TimingSide {
  /** The key its results are stored under. */
  key: string;
  label: string;
}

export interface WordTimingExperiment {
  id: string;
  name: string;
  description: string;
  a: TimingSide;
  b: TimingSide;
  /** Kinds of test song, in the order to check them. */
  groups: { key: string; label: string }[];
}

interface SideSummary {
  /** Lines bad by the sweep's rules (crammed or a held last word). */
  bad: number | null;
  lines: number | null;
  meanScore: number | null;
}

export interface WordTimingSongRow {
  songId: string;
  title: string;
  artist: string;
  group: string | null;
  a: SideSummary;
  b: SideSummary;
  /** Lines whose timing differs enough to hear. */
  moments: number;
  answered: number;
}

/** A line whose two timings differ, with both sets of words. */
export interface WordTimingMoment {
  key: string;
  lineIndex: number;
  start: number;
  end: number;
  /** Average distance between the two timings' word starts; null when the
   * two have different words. */
  meanShift: number | null;
  a: WordTimestamp[];
  b: WordTimestamp[];
  answer: WordTimingAnswer | null;
}

export interface WordTimingSong {
  songId: string;
  title: string;
  artist: string;
  group: string | null;
  moments: WordTimingMoment[];
}

const KEY = ["admin", "word-timing"] as const;

/** Experiments found on this machine; empty where none were run. */
export function useWordTimingExperiments() {
  return useApiQuery<{ experiments: WordTimingExperiment[] }, typeof KEY>(
    KEY,
    "admin/word-timing/experiments",
  );
}

/** One experiment's songs, still to check first, and its answers counted. */
export function useWordTimingSongs(experimentId: string | undefined) {
  return useApiQuery<
    {
      experiment: WordTimingExperiment;
      songs: WordTimingSongRow[];
      tally: Partial<Record<WordTimingAnswer, number>>;
    },
    readonly [...typeof KEY, string | undefined]
  >(
    [...KEY, experimentId],
    `admin/word-timing/experiments/${experimentId}/songs`,
    { enabled: !!experimentId },
  );
}

export function useWordTimingSong(experimentId: string, songId: string) {
  return useApiQuery<WordTimingSong, readonly [...typeof KEY, string, string]>(
    [...KEY, experimentId, songId],
    `admin/word-timing/experiments/${experimentId}/songs/${songId}`,
    { retry: false },
  );
}

/** Answer moments by ear; `answer: null` clears one. */
export function useSaveWordTimingAnswers(experimentId: string, songId: string) {
  const queryClient = useQueryClient();
  return useApiMutation<
    WordTimingSong,
    { answers: { key: string; answer: WordTimingAnswer | null }[] }
  >(
    `admin/word-timing/experiments/${experimentId}/songs/${songId}/answers`,
    "put",
    {
      onSuccess: (song) => {
        queryClient.setQueryData([...KEY, experimentId, songId], song);
        queryClient.invalidateQueries({
          queryKey: [...KEY, experimentId],
          exact: true,
        });
      },
    },
  );
}
