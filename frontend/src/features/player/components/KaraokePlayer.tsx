/**
 * KaraokePlayer - the stage's centre column.
 *
 * Since the page itself is now the player, this is only the song title, the
 * lyrics and the error state. All chrome — transport,
 * settings popovers, hover overlays, the mouse-idle timer — lives in the
 * stage layout and the shared controls strip instead.
 */

import React from "react";
import { useKaraokePlayer } from "../hooks";
import { PlayerErrorBoundary } from "./subcomponents";
import { ThrottledLyricsDisplay } from "@/features/lyrics";
import type { KaraokePlayerProps } from "../types/KaraokePlayer.types";
import { BookOpen, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useOpenSongSelect } from "@/hooks/useOpenSongSelect";
import { cn } from "@/lib/utils";

const KaraokePlayer: React.FC<KaraokePlayerProps> = ({
  songId,
  autoPlay = false,
  onPlay,
  onPause,
  onEnd,
  onTimeUpdate,
  onError,
  chromeCollapsed = false,
  className = "",
}) => {
  const player = useKaraokePlayer(songId, { autoPlay });
  const openSongSelect = useOpenSongSelect();

  // Handle play/pause callbacks
  React.useEffect(() => {
    if (player.isPlaying && onPlay) {
      onPlay();
    } else if (!player.isPlaying && onPause) {
      onPause();
    }
  }, [player.isPlaying, onPlay, onPause]);

  // Handle error callback
  React.useEffect(() => {
    if (player.error && onError) {
      // Adapt PlayerError to Error for callback
      const err: Error = {
        name: player.error.code || "PlayerError",
        message: player.error.message,
        stack: undefined,
      };
      onError(err);
    }
  }, [player.error, onError]);

  // Handle time update callback
  React.useEffect(() => {
    if (onTimeUpdate) {
      onTimeUpdate(player.currentTime, player.duration);
    }
  }, [player.currentTime, player.duration, onTimeUpdate]);

  // Handle song end callback
  React.useEffect(() => {
    if (onEnd && player.duration > 0 && player.currentTime >= player.duration) {
      onEnd();
    }
  }, [player.currentTime, player.duration, onEnd]);

  // Hoisted so the header's event handlers close over a narrowed value —
  // TypeScript cannot keep `player.song` narrowed inside a callback.
  const song = player.song;

  // The way to the songbook mid-song, top left where an app's back button
  // would be. A word, not an icon: someone who wants the songbook looks for
  // the word. Not a call to action - singing is the point of this screen - so
  // it stays quiet and comes and goes with the rest of the chrome.
  //
  // Only with a song loaded. With none, the empty state below has its own
  // "Open the Songbook" button, and two would be one too many.
  const songbookButton = (
    <Button
      variant="ghost"
      size="lg"
      onClick={() => openSongSelect()}
      className={cn(
        "absolute left-0 top-0 z-10 gap-2 text-lg text-foreground-dim transition-opacity duration-500 hover:text-foreground",
        chromeCollapsed && "pointer-events-none opacity-0",
      )}
    >
      <BookOpen className="size-5" />
      Songbook
    </Button>
  );

  if (player.error) {
    return (
      <div
        className={cn(
          "relative flex min-h-0 w-full flex-1 flex-col items-center justify-center gap-4 text-center",
          className,
        )}
      >
        {songbookButton}
        <div className="text-lg font-semibold text-destructive">
          {player.error.message}
        </div>
        <Button variant="outline" onClick={() => player.reload()}>
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <PlayerErrorBoundary onError={undefined}>
      <div
        className={cn(
          "relative flex min-h-0 w-full flex-1 flex-col items-center",
          className,
        )}
      >
        {song && songbookButton}

        {/* Song header */}
        {song && (
          <div
            className={cn(
              // Side padding keeps a long title wrapping clear of the
              // Songbook button in the top-left corner.
              "shrink-0 px-44 pb-4 pt-1 text-center transition-opacity duration-500",
              chromeCollapsed && "opacity-35",
            )}
          >
            <h1 className="font-display text-3xl leading-tight text-foreground">
              {song.title}
            </h1>
            <h2
              className="cursor-pointer pt-1 text-lg text-foreground-dim transition-colors hover:text-primary"
              onClick={() => openSongSelect({ expandArtist: song.artist })}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  openSongSelect({ expandArtist: song.artist });
                }
              }}
            >
              {song.artist}
            </h2>
          </div>
        )}

        {/* Lyrics. What happens when a song ends belongs to the stage shell's
            handoff screen - it is a whole screen about a person, not a branch
            inside the lyrics column. */}
        <div className="relative flex min-h-0 w-full flex-1 flex-col">
          {song && !player.isReady ? (
            // Until the stems are decoded there is nothing to sing along to,
            // and with autoplay on the song starts by itself once they are.
            <div className="flex h-full w-full items-center justify-center gap-3 text-xl text-foreground-dim">
              <Loader2 className="size-6 animate-spin" />
              Getting the song ready…
            </div>
          ) : song ? (
            <>
              <div className="min-h-0 w-full flex-1">
                <ThrottledLyricsDisplay
                  lyrics={player.lyrics}
                  isSync={player.isLyricsSync}
                  currentTime={player.currentTime}
                  lyricsSize={player.lyricsSize}
                  lyricsOffset={player.lyricsOffset}
                  onSeek={player.seek}
                  songId={songId}
                  songTitle={song.title}
                  songArtist={song.artist}
                  songAlbum={song.album}
                  songDuration={song.duration}
                  showProgressBar={true}
                  showLeadInHighlight={false}
                />
              </div>
            </>
          ) : (
            <div className="flex h-full w-full flex-col items-center justify-center gap-4">
              <div className="text-xl font-semibold text-foreground-dim">
                No songs in the queue
              </div>
              <Button
                variant="outline"
                size="lg"
                onClick={() => openSongSelect()}
                className="gap-2"
              >
                <BookOpen className="size-5" />
                Open the Songbook
              </Button>
            </div>
          )}
        </div>
      </div>
    </PlayerErrorBoundary>
  );
};

export default KaraokePlayer;
