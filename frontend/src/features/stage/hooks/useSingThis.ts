/**
 * useSingThis - the processing list's "Sing this": queue a finished song and
 * start it, under whoever's turn it is.
 *
 * The same queue-and-play path as the confirm screen's "Sing it now"
 * (useSongActions.handlePlayAs), and the same default singer the confirm
 * screen's picker starts on (pickDefaultSinger), so a song started from the
 * list is filed under the person the rotation says is up.
 *
 * This is the one place a "Sing this" start happens. It only makes the song
 * current; the player's countdown runs for any song that becomes current.
 */

import { useSongActions } from "@/features/songs/hooks/useSongActions";
import { useRoster } from "@/hooks/api/useRoster";
import { useSessionStore } from "@/stores/sessionStore";
import type { Song } from "@/types/Song";
import { useStageQueue } from "../StageShellContext";
import { pickDefaultSinger } from "./useDefaultSinger";

export function useSingThis(song: Song) {
  const { handlePlayAs } = useSongActions(song);
  const queue = useStageQueue();
  const displayCode = useSessionStore((s) => s.displayCode);
  const { data: roster = [] } = useRoster(displayCode || undefined);

  /** Resolves true once the song is playing. */
  const start = async (): Promise<boolean> => {
    const singer = pickDefaultSinger(roster, queue?.turn);
    return handlePlayAs(singer || undefined);
  };

  return start;
}
