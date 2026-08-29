/**
 * KaraokePlayer - the stage's centre column.
 *
 * Since the page itself is now the player, this is only the song title, the
 * lyrics (or the end states) and the error state. All chrome — transport,
 * settings popovers, hover overlays, the mouse-idle timer — lives in the
 * stage layout and the shared controls strip instead.
 */

import React from "react";
import { useNavigate } from "react-router-dom";
import { useKaraokePlayer } from "../hooks";
import {
  PlayerErrorBoundary,
  SongEnded,
  QueueEnded,
  ChordCarousel,
} from "./subcomponents";
import { LyricsDisplayWithCountIn } from "@/features/lyrics";
import type { KaraokePlayerProps } from "../types/KaraokePlayer.types";
import { Library } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSongs } from "@/hooks/api/useSongs";
import { cn } from "@/lib/utils";

const KaraokePlayer: React.FC<KaraokePlayerProps> = ({
  songId,
  queueItems,
  autoPlay = false,
  onPlay,
  onPause,
  onEnd,
  onPlayNext,
  onTimeUpdate,
  onError,
  dimHeader = false,
  className = "",
}) => {
  const player = useKaraokePlayer(songId, { autoPlay });
  const navigate = useNavigate();

  // Song API hooks
  const { useSongChords } = useSongs();
  const { data: songChords = [] } = useSongChords(songId, {
    enabled: !!songId,
  });

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

  const nextQueueItem = queueItems?.find((item) => item.position === 1);
  const hasNextSong = !!(onPlayNext && queueItems && queueItems.length > 1);

  if (player.error) {
    return (
      <div
        className={cn(
          "flex min-h-0 w-full flex-1 flex-col items-center justify-center gap-4 text-center",
          className,
        )}
      >
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
          "flex min-h-0 w-full flex-1 flex-col items-center",
          className,
        )}
      >
        {/* Song header */}
        {song && (
          <div
            className={cn(
              "shrink-0 pb-4 pt-1 text-center transition-opacity duration-500",
              dimHeader && "opacity-35",
            )}
          >
            <h1 className="font-display text-3xl leading-tight text-foreground">
              {song.title}
            </h1>
            <h2
              className="cursor-pointer pt-1 text-lg text-foreground/55 transition-colors hover:text-primary"
              onClick={() =>
                navigate(
                  `/library?expandArtist=${encodeURIComponent(song.artist)}`,
                )
              }
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  navigate(
                    `/library?expandArtist=${encodeURIComponent(song.artist)}`,
                  );
                }
              }}
            >
              {song.artist}
            </h2>
          </div>
        )}

        {/* Lyrics, or the end states */}
        <div className="relative flex min-h-0 w-full flex-1 flex-col">
          {song && player.songEnded ? (
            // Position 0 is the current song; anything beyond means more to come
            hasNextSong ? (
              <SongEnded
                currentSong={song}
                nextQueueItem={nextQueueItem}
                onPlayNext={
                  nextQueueItem && onPlayNext
                    ? () => onPlayNext(String(nextQueueItem.id))
                    : undefined
                }
              />
            ) : (
              <QueueEnded currentSong={song} />
            )
          ) : song ? (
            <>
              {player.showChords && (
                <div className="shrink-0">
                  <ChordCarousel
                    chords={songChords}
                    currentTime={player.currentTime}
                  />
                </div>
              )}
              {/* min-h-0 so the chord carousel takes its space out of the
                  lyrics rather than pushing them past the transport */}
              <div className="min-h-0 w-full flex-1">
                <LyricsDisplayWithCountIn
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
              <div className="text-xl font-semibold text-foreground/60">
                No songs in the queue
              </div>
              <Button
                variant="outline"
                size="lg"
                onClick={() => navigate("/library")}
                className="gap-2"
              >
                <Library className="size-5" />
                Browse Library
              </Button>
            </div>
          )}
        </div>
      </div>
    </PlayerErrorBoundary>
  );
};

export default KaraokePlayer;
