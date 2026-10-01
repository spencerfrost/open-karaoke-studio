import { useQueryClient } from "@tanstack/react-query";

import { apiSend, useApiMutation, useApiQuery } from "@/hooks/api/useApi";

/** "words": the text is wrong. "timing": the words are right but out of sync. */
export type LyricsReportKind = "words" | "timing";

/** What the app's automatic fix did about a report. */
export type LyricsReportOutcome =
  | "replaced"
  | "retimed"
  | "transcribed"
  | "unchanged";

export interface LyricsReport {
  id: number;
  songId: string;
  title: string | null;
  artist: string | null;
  kind: LyricsReportKind;
  reportCount: number;
  reporterName: string | null;
  createdAt: string | null;
  lastReportedAt: string | null;
  /** null while the fix is still running. */
  outcome: LyricsReportOutcome | null;
  resolved: boolean;
  /** Where the word timings on screen came from ("lrclib:1", "asr:whisperx"). */
  lyricsSource: string | null;
  lyricsHandPicked: boolean;
}

const REPORTS_KEY = ["lyrics", "reports"] as const;

/** Say the lyrics on screen have the wrong words or are out of sync. */
export function useReportLyrics() {
  const queryClient = useQueryClient();
  return useApiMutation<
    { report: LyricsReport },
    { songId: string; kind: LyricsReportKind }
  >("lyrics/songs/:id/reports", "post", {
    mutationFn: ({ songId, kind }) =>
      apiSend<{ report: LyricsReport }, { kind: LyricsReportKind }>(
        `lyrics/songs/${songId}/reports`,
        "post",
        { kind },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REPORTS_KEY });
    },
  });
}

/** Open lyrics reports, for hosts and admins. */
export function useLyricsReports() {
  return useApiQuery<LyricsReport[], typeof REPORTS_KEY>(
    REPORTS_KEY,
    "lyrics/reports",
    // Outcomes arrive when the fix finishes, a minute or so after a report.
    { refetchInterval: 15_000 },
  );
}

/** Mark a report as dealt with. */
export function useResolveLyricsReport() {
  const queryClient = useQueryClient();
  return useApiMutation<LyricsReport, number>(
    "lyrics/reports/:id/resolve",
    "post",
    {
      mutationFn: (reportId) =>
        apiSend<LyricsReport, null>(
          `lyrics/reports/${reportId}/resolve`,
          "post",
        ),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: REPORTS_KEY });
      },
    },
  );
}
