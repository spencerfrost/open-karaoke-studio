/**
 * OpenYourPhonePrompt - asks the singer to take their phone out.
 *
 * Shown over the performance screen while the singer's phone is closed, locked
 * or in the background. Nothing to tap: once the phone is back on the page it
 * sees its song has started and opens the controls itself, and this goes away.
 * A singer with no phone linked (a walk-up the host typed in) never sees it.
 *
 * Kept short, because plenty of singers never want the controls and a phone
 * set down mid-song locks itself:
 * - only during the intro, up to the first sung line (see `phonePromptEnd`);
 * - only once per singer per session, and never for a singer whose phone has
 *   already been on the controls (see `isPromptSong`).
 */

import React, { useEffect, useMemo } from "react";
import { Smartphone } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useSongPosition } from "@/features/player/hooks";
import { useSongs } from "@/hooks/api/useSongs";
import {
  isPromptSong,
  needsPhoneOpened,
  usePresenceStore,
} from "@/stores/presenceStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";
import { phonePromptEnd } from "./phonePromptWindow";

interface OpenYourPhonePromptProps {
  current?: KaraokeQueueItemWithSong | null;
}

const OpenYourPhonePrompt: React.FC<OpenYourPhonePromptProps> = ({
  current,
}) => {
  const performerId = current?.performerId ?? null;
  const itemId = current ? String(current.id) : null;
  const presence = usePresenceStore((s) =>
    performerId === null ? undefined : s.performers[performerId],
  );
  const promptSong = usePresenceStore(
    (s) =>
      performerId !== null &&
      itemId !== null &&
      isPromptSong({
        performerId,
        itemId,
        promptedFor: s.promptedFor,
        usedControls: s.usedControls,
      }),
  );
  const markPrompted = usePresenceStore((s) => s.markPrompted);

  // The same song query the player reads, so this shares its cache.
  const { useSong } = useSongs();
  const { data: song } = useSong(current?.song.id ?? "");
  const lyricsOffset = useKaraokePlayerStore((s) => s.lyricsOffset);
  const promptEnd = useMemo(
    () => phonePromptEnd(song?.syncedLyrics, lyricsOffset),
    [song?.syncedLyrics, lyricsOffset],
  );
  // Half-second steps: the prompt only needs to notice the intro ending.
  const position = useSongPosition(0.5);

  const show =
    Boolean(current) &&
    promptSong &&
    needsPhoneOpened(presence) &&
    position < promptEnd;

  // Showing it is what counts as asking: a singer whose phone was already open
  // through the intro hasn't been asked, and can be on a later song.
  useEffect(() => {
    if (show && performerId !== null && itemId !== null) {
      markPrompted(performerId, itemId);
    }
  }, [show, performerId, itemId, markPrompted]);

  if (!show || !current) return null;

  return (
    <div className="pointer-events-none absolute inset-x-0 top-6 z-30 flex justify-center px-6">
      <Alert
        data-tour="open-your-phone"
        className="pointer-events-auto w-auto max-w-xl border-primary/60 px-6 py-4 shadow-lg [&>svg]:size-6"
      >
        <Smartphone className="text-primary" />
        <AlertTitle className="text-xl">
          {current.singer}, open your phone
        </AlertTitle>
        <AlertDescription className="text-base">
          Go back to the karaoke page on your phone to turn your voice up or
          down while you sing.
        </AlertDescription>
      </Alert>
    </div>
  );
};

export default OpenYourPhonePrompt;
