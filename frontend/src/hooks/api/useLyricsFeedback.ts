import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiSend, useApiMutation, useApiQuery } from "@/hooks/api/useApi";

/** An answer to "How were the lyrics?" after a song. */
export type LyricsRating = "spot_on" | "a_bit_off" | "way_off";

/** Every answer about one song, for the admin list. */
export interface SongLyricsFeedback {
  songId: string;
  title: string | null;
  artist: string | null;
  /** Answers about the lyrics and word timings the song shows now. */
  spotOn: number;
  aBitOff: number;
  wayOff: number;
  /** Answers about lyrics or timings that have since been replaced. */
  earlier: number;
  plays: number;
  lastAnsweredAt: string | null;
  /** Where the word timings on screen came from ("lrclib:1", "asr:whisperx"). */
  lyricsSource: string | null;
  lyricsHandPicked: boolean;
}

const FEEDBACK_KEY = ["lyrics", "feedback"] as const;

/** Where the answer for one queue item is kept, so it survives a remount. */
const answerKey = (queueItemId: number) =>
  [...FEEDBACK_KEY, "answer", queueItemId] as const;

/** The answer already given for a queue item on this device, if any. */
export function useLyricsFeedbackAnswer(queueItemId: number | null) {
  return useQuery<LyricsRating | null>({
    queryKey: answerKey(queueItemId ?? -1),
    // Only ever filled by the answer mutation; there's nothing to fetch.
    queryFn: () => null,
    enabled: false,
    staleTime: Infinity,
    gcTime: Infinity,
  }).data;
}

/** Say how the lyrics went for the song that just finished. */
export function useAnswerLyricsFeedback() {
  const queryClient = useQueryClient();
  return useApiMutation<
    { queueItemId: number; rating: LyricsRating },
    { queueItemId: number; rating: LyricsRating }
  >("lyrics/feedback", "post", {
    mutationFn: ({ queueItemId, rating }) =>
      apiSend<
        { queueItemId: number; rating: LyricsRating },
        { queue_item_id: number; rating: LyricsRating }
      >("lyrics/feedback", "post", { queue_item_id: queueItemId, rating }),
    onSuccess: ({ queueItemId, rating }) => {
      queryClient.setQueryData(answerKey(queueItemId), rating);
    },
  });
}

/** Every song with answers, worst first. Admins only. */
export function useLyricsFeedback() {
  return useApiQuery<SongLyricsFeedback[], typeof FEEDBACK_KEY>(
    FEEDBACK_KEY,
    "lyrics/feedback",
  );
}
