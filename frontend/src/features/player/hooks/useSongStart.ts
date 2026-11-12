/**
 * useSongStart - how a new song starts on the stage: a 3-2-1, then play.
 *
 * This is the one place that happens. "Sing it now", the handoff screen, the
 * queue rail, Next and anything else that starts a song only change which
 * song the stage is on; the count follows from that. Restarting the same song
 * doesn't change it, so it never counts.
 *
 * In order:
 * 1. The stage is asked for a song it hasn't started: the count waits.
 * 2. The player store switches to it. A playing song fades out first (the
 *    store's song-change fade), so the count always runs over silence.
 * 3. With the player on screen, 3, 2, 1, one step a second. The audio loads
 *    underneath, so the count covers "Getting the song ready".
 * 4. On 1 it holds until the audio is ready, then the song plays from 0:00.
 *
 * Pressing play during the count just starts the song and ends the count.
 */

import { useEffect, useRef } from "react";
import {
  COUNTDOWN_STEP_MS,
  isReadyToStart,
  useSongCountdownStore,
} from "@/stores/useSongCountdownStore";

interface SongStartOptions {
  /** Off for players that never start songs by themselves. */
  enabled: boolean;
  /**
   * False while another screen covers the player. A count nobody can see is
   * no use to the singer, so it waits for the player to be shown.
   */
  visible: boolean;
  /** The song the stage is asked to play. */
  songId: string | undefined;
  /** The song the player store has switched to (after any fade-out). */
  loadedSongId: string | null;
  /** The loaded song's audio is decoded and can play. */
  isReady: boolean;
  isPlaying: boolean;
  /** Loading failed: no count, so the error shows instead. */
  failed: boolean;
  play: () => void;
}

/**
 * Whether audio may start without a click first. A song that loads before
 * anyone has touched the page is a reload, and an AudioContext started then
 * stays silent, so counting into it would be a false start.
 */
function hasUserActivation(): boolean {
  return !navigator.userActivation || navigator.userActivation.hasBeenActive;
}

export function useSongStart({
  enabled,
  visible,
  songId,
  loadedSongId,
  isReady,
  isPlaying,
  failed,
  play,
}: SongStartOptions): void {
  const countdown = useSongCountdownStore((s) => s.countdown);
  const { request, begin, suspend, tick, clear } =
    useSongCountdownStore.getState();

  // Once per song. The song already loaded when this mounted is skipped: that
  // is the stage resuming the night, not someone asking to sing.
  const startedFor = useRef<string | null>(loadedSongId);

  // 1. A new song was asked for (or the one asked for went away).
  useEffect(() => {
    if (!enabled) return;
    if (!songId) {
      clear();
      return;
    }
    if (failed || startedFor.current === songId) return;
    if (!hasUserActivation()) {
      startedFor.current = songId;
      return;
    }
    request(songId);
  }, [enabled, songId, failed, request, clear]);

  // Loading failed: drop the count so the error and its Try Again show. A
  // retry that succeeds is asked for again by step 1 and counts again.
  useEffect(() => {
    if (failed && countdown.phase !== "idle") clear();
  }, [failed, countdown.phase, clear]);

  // 2-3. Start counting once the player is on this song and on screen;
  // covered mid-count, wait and count again from the top.
  useEffect(() => {
    if (countdown.phase === "waiting") {
      if (visible && loadedSongId === countdown.songId) {
        begin(countdown.songId);
      }
    } else if (countdown.phase === "counting" && !visible) {
      suspend();
    }
  }, [countdown, visible, loadedSongId, begin, suspend]);

  // The count itself.
  useEffect(() => {
    if (countdown.phase !== "counting" || countdown.holding) return;
    const timer = setTimeout(tick, COUNTDOWN_STEP_MS);
    return () => clearTimeout(timer);
  }, [countdown, tick]);

  // 4. Done counting and the audio is ready: play.
  useEffect(() => {
    if (countdown.phase !== "counting") return;
    if (isReadyToStart(countdown, loadedSongId, isReady)) {
      startedFor.current = countdown.songId;
      clear();
      if (!isPlaying) play();
    } else if (isPlaying && loadedSongId === countdown.songId) {
      // Someone pressed play mid-count (here or on a phone): it has started.
      startedFor.current = countdown.songId;
      clear();
    }
  }, [countdown, loadedSongId, isReady, isPlaying, play, clear]);

  // A count belongs to the player showing it.
  useEffect(() => clear, [clear]);
}
