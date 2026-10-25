/**
 * useTourSignals - reads what the app is doing for the tour.
 *
 * Every signal comes from state the stage already has: the jobs feed, the
 * countdown, the player, presence and the mix. Job and presence updates reach
 * the stage over the server, so the tour advances the same whether the
 * visitor used a real phone or the stage's phone-view window.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useApiQuery } from "@/hooks/api/useApi";
import { useSongs } from "@/hooks/api/useSongs";
import { useJobTracker } from "@/features/songs/processing/useJobTracker";
import { useStageQueue } from "@/features/stage/StageShellContext";
import { useAudioControlsStore } from "@/stores/useAudioControlsStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { usePlaybackStateStore } from "@/stores/usePlaybackStateStore";
import { usePresenceStore } from "@/stores/presenceStore";
import { useSongCountdownStore } from "@/stores/useSongCountdownStore";
import {
  fallbackReason,
  isWaitingForSong,
  progressSignature,
  type FallbackReason,
  type TourSignals,
  type TourStep,
} from "./tourSteps";

/** How often the busy rule is checked while the visitor waits. */
const CLOCK_TICK_MS = 5000;
/** How often the demo's remaining downloads are asked while they wait. */
const QUOTA_POLL_MS = 15000;
/** A slider moved at least this far counts as the visitor changing the mix. */
const MIX_EPSILON = 0.02;

interface DemoQuotaResponse {
  session_remaining: number;
  daily_remaining: number;
}

export interface TourReadings {
  signals: TourSignals;
  fallback: FallbackReason | null;
  /** Songs of ours that came out broken, so the fallback never offers them. */
  failedSongIds: string[];
}

export function useTourSignals(
  sessionId: string,
  step: TourStep,
): TourReadings {
  const waiting = isWaitingForSong(step);

  // --- Jobs: ours, and how the newest finished one came out.
  const rows = useJobTracker();
  const myRows = useMemo(() => rows.filter((r) => r.isMine), [rows]);
  const finished = myRows.filter((r) => r.phase === "finished");
  const newestFinished = finished[finished.length - 1];
  const { useSong } = useSongs();
  const { data: finishedSong } = useSong(newestFinished?.songId ?? "");
  let myFinishedOutcome: "ready" | "failed" | "pending" | null = null;
  if (newestFinished) {
    if (finishedSong?.status === "processed") myFinishedOutcome = "ready";
    else if (finishedSong?.status === "error") myFinishedOutcome = "failed";
    else myFinishedOutcome = "pending";
  }

  // --- The stall clock: when our in-flight song last showed anything new.
  const inFlight = myRows.find((r) => r.phase !== "finished");
  const signature = progressSignature(inFlight);
  const lastChange = useRef<{ signature: string | null; at: number | null }>({
    signature: null,
    at: null,
  });
  const [lastProgressAt, setLastProgressAt] = useState<number | null>(null);
  useEffect(() => {
    if (signature === lastChange.current.signature) return;
    const at = signature === null ? null : Date.now();
    lastChange.current = { signature, at };
    setLastProgressAt(at);
  }, [signature]);

  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(() => setNow(Date.now()), CLOCK_TICK_MS);
    return () => clearInterval(timer);
  }, [waiting]);

  // --- Quota, only while it could matter.
  const quotaQuery = useApiQuery<DemoQuotaResponse>(
    ["demo", "quota", sessionId],
    "demo/quota",
    {
      enabled: waiting,
      refetchInterval: waiting ? QUOTA_POLL_MS : false,
      retry: false,
    },
  );
  const quota = quotaQuery.data
    ? {
        sessionRemaining: quotaQuery.data.session_remaining,
        dailyRemaining: quotaQuery.data.daily_remaining,
      }
    : null;

  // --- The stage: count, playback, the end of the song.
  const countingDown = useSongCountdownStore(
    (s) => s.countdown.phase === "counting",
  );
  const isPlaying = useKaraokePlayerStore((s) => s.isPlaying);
  const songEnded = usePlaybackStateStore((s) => s.songEnded);

  // --- The singer's phone.
  const queue = useStageQueue();
  const performerId = queue?.current?.performerId ?? null;
  const presence = usePresenceStore((s) =>
    performerId === null ? undefined : s.performers[performerId],
  );
  const singerOnControls = presence ? presence.onControls : null;

  // --- The mix, against where it was when the song started.
  const vocal = useAudioControlsStore((s) => s.vocalVolume);
  const backing = useAudioControlsStore((s) => s.backingVocalVolume);
  const instrumental = useAudioControlsStore((s) => s.instrumentalVolume);
  const inMixSteps = step === "controls" || step === "mix";
  const [baseline, setBaseline] = useState<number[] | null>(null);
  if (inMixSteps && baseline === null) {
    setBaseline([vocal, backing, instrumental]);
  }
  const mixChanged =
    inMixSteps &&
    baseline !== null &&
    [vocal, backing, instrumental].some(
      (value, i) => Math.abs(value - baseline[i]) >= MIX_EPSILON,
    );

  const signals: TourSignals = {
    hasMyJob: myRows.length > 0,
    myReadySong: myFinishedOutcome === "ready",
    countingDown,
    isPlaying,
    singerOnControls,
    mixChanged,
    songEnded,
  };

  const fallback = fallbackReason({
    step,
    myRows,
    myFinishedOutcome,
    quota,
    lastProgressAt,
    now,
  });

  const failedSongIds =
    myFinishedOutcome === "failed" && newestFinished
      ? [newestFinished.songId]
      : [];

  return { signals, fallback, failedSongIds };
}
