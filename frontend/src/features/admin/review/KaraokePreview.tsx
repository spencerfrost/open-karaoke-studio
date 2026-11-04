import React, { useRef, useState } from "react";
import { ThrottledLyricsDisplay } from "@/features/lyrics";
import type { SongAudioPreviewHandle } from "@/features/songs/components/song-card/SongAudioPreview";
import { LyricsPreview } from "./LyricsPreview";
import { StemPreview } from "./StemPreview";

/**
 * The song playing with its lyrics drawn the way the stage draws them: same
 * renderer, word timings and instrumental breaks, so whether the timing is
 * right can be seen and heard. No lyrics offset: these are the timings as
 * stored. Click a line to play from it.
 *
 * Without timed lyrics there is nothing to play along, so the words are just
 * listed under the player.
 */
export const KaraokePreview: React.FC<{
  songId: string;
  syncedLyrics?: string;
  plainLyrics?: string;
}> = ({ songId, syncedLyrics, plainLyrics }) => {
  const [currentTime, setCurrentTime] = useState(0);
  const playerRef = useRef<SongAudioPreviewHandle>(null);

  return (
    <div className="space-y-3">
      <StemPreview
        songId={songId}
        onTimeChange={setCurrentTime}
        playerRef={playerRef}
      />
      {syncedLyrics ? (
        <div className="h-96 overflow-hidden rounded-md border border-border/60 bg-background">
          <ThrottledLyricsDisplay
            lyrics={syncedLyrics}
            isSync
            currentTime={currentTime}
            lyricsSize="small"
            lyricsOffset={0}
            songId={songId}
            onSeek={(seconds) => playerRef.current?.playFrom(seconds)}
            showProgressBar
            aria-label="Lyrics as they play on stage"
          />
        </div>
      ) : (
        <LyricsPreview plainLyrics={plainLyrics} />
      )}
    </div>
  );
};
