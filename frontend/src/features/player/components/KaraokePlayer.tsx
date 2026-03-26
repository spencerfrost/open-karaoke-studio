/**
 * KaraokePlayer - Main unified karaoke player component
 * YouTube-like API: <KaraokePlayer songId="123" />
 */

import React from "react";
import { useNavigate } from "react-router-dom";
import { useKaraokePlayer, usePlayerUI } from "../hooks";
import {
  FullscreenContainer,
  PlayerErrorBoundary,
  SongEnded,
  QueueEnded,
  BottomControlsArea,
  ChordCarousel,
} from "./subcomponents";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:karaoke-player");
import { LyricsDisplayWithCountIn } from "@/features/lyrics";
import type { KaraokePlayerProps } from "../types/KaraokePlayer.types";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import { Maximize, Play, Library } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTapTempo } from "@/hooks/useTapTempo";
import { useSongs } from "@/hooks/api/useSongs";

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
  className = "",
}) => {
  // Initialize player and UI hooks
  const player = useKaraokePlayer(songId, { autoPlay });
  const ui = usePlayerUI();
  const navigate = useNavigate();

  // Song API hooks
  const { useUpdateSong, useSongChords } = useSongs();
  const updateSongMutation = useUpdateSong();
  const { data: songChords = [] } = useSongChords(songId, {
    enabled: !!songId,
  });

  // Hover state for overlay controls
  const [isHovering, setIsHovering] = React.useState(false);

  // Track mouse movement for showing controls
  const [mouseRecentlyMoved, setMouseRecentlyMoved] = React.useState(false);
  const mouseTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  // Tap tempo hook with minimum 3 taps before setting BPM
  const MIN_TAPS = 3;
  const tapTempo = useTapTempo({
    minTaps: MIN_TAPS,
  });

  // Get effective BPM (from tap tempo if active, otherwise from song)
  const effectiveBpm = tapTempo.bpm ?? player.song?.bpm ?? null;

  // Save BPM to database
  const handleSaveBpm = React.useCallback(() => {
    if (songId && tapTempo.bpm && tapTempo.bpm >= 30 && tapTempo.bpm <= 300) {
      updateSongMutation.mutate(
        { id: songId, bpm: tapTempo.bpm },
        {
          onSuccess: () => {
            // Reset the tap tempo after successful save
            tapTempo.reset();
          },
          onError: (error) => {
            logger.error("Failed to update BPM:", error);
          },
        },
      );
    }
  }, [songId, tapTempo, updateSongMutation]);

  // Reset mouse movement timer on mouse move while hovering
  const handleMouseMove = React.useCallback(() => {
    setMouseRecentlyMoved(true);
    if (mouseTimeoutRef.current) {
      clearTimeout(mouseTimeoutRef.current);
    }
    mouseTimeoutRef.current = setTimeout(() => {
      setMouseRecentlyMoved(false);
    }, 30000);
  }, []);

  // Clear timeout on unmount
  React.useEffect(() => {
    return () => {
      if (mouseTimeoutRef.current) {
        clearTimeout(mouseTimeoutRef.current);
      }
    };
  }, []);

  // Global keyboard shortcuts for the player
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!(e.target instanceof HTMLElement)) return;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
      if (!player.song || !player.isReady) return;

      if (e.code === "Space") {
        e.preventDefault(); // prevent page scroll
        player.togglePlay();
      } else if (e.code === "KeyT") {
        tapTempo.handleTap();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [player.song, player.isReady, player.togglePlay, tapTempo]);

  // Show control overlays when hovering and mouse recently moved
  const showControlOverlays = isHovering && mouseRecentlyMoved;

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

  // Volume control handlers
  const handleVolumeToggle = () => {
    if (player.vocalVolume === 0) {
      player.setVocalVolume(1);
    } else {
      player.setVocalVolume(0);
    }
  };

  // Hover overlay handlers
  const handleFullscreenOnly = () => {
    ui.toggleFullscreen();
  };

  const handleFullscreenAndPlay = () => {
    ui.toggleFullscreen();
    if (!player.isPlaying && player.song && player.isReady) {
      player.togglePlay();
    }
  };

  // No-op handlers for disabled controls
  const noop = () => {};
  const noopVolume = (/*volume: number*/) => {};

  // Error state
  if (player.error) {
    return (
      <div
        className={`aspect-video flex flex-col items-center justify-center bg-black/80 rounded-xl text-center p-8 ${className}`}
      >
        <div className="text-red-500 text-lg font-semibold mb-4">
          {player.error.message}
        </div>
        <button
          onClick={() => player.reload()}
          className="text-orange-peel hover:text-orange-peel/80 underline"
        >
          Try Again
        </button>
      </div>
    );
  }

  const playerContent = (
    <FullscreenContainer
      isFullscreen={ui.isFullscreen}
      containerRef={ui.containerRef}
      fsError={ui.fsError}
      className={`bg-black/80 rounded-xl overflow-hidden relative ${className}`}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => {
        setIsHovering(false);
        setMouseRecentlyMoved(false);
        if (mouseTimeoutRef.current) {
          clearTimeout(mouseTimeoutRef.current);
        }
      }}
      onMouseMove={handleMouseMove}
    >
      {/* Hover Buttons - Show on hover when paused (but not when song ended) */}
      {!player.isPlaying && !player.songEnded && player.song && isHovering && (
        <div
          className={`absolute top-0 left-0 right-0 bottom-24 z-40 flex items-center justify-center gap-12 pointer-events-none transition-opacity duration-300 ${
            showControlOverlays ? "opacity-100" : "opacity-0"
          }`}
        >
          {ui.isFullscreen ? (
            /* In fullscreen: single Play button */
            <Button
              variant="outline"
              className="p-0 rounded-full bg-black/70 hover:bg-black/90 border-2 border-orange-peel/50 hover:border-orange-peel transition-all pointer-events-auto disabled:opacity-50 disabled:pointer-events-none"
              style={{ height: "12rem", width: "12rem" }}
              onClick={() => player.isReady && player.togglePlay()}
              disabled={!player.isReady}
              aria-label="Play"
            >
              <Play
                style={{ height: "6rem", width: "6rem" }}
                className="text-orange-peel"
                fill="currentColor"
                strokeWidth={1.5}
              />
            </Button>
          ) : (
            /* Not fullscreen: Fullscreen and Fullscreen+Play buttons */
            <>
              <Button
                variant="outline"
                className="p-0 rounded-full bg-black/70 hover:bg-black/90 border-2 border-orange-peel/50 hover:border-orange-peel transition-all pointer-events-auto"
                style={{ height: "12rem", width: "12rem" }}
                onClick={handleFullscreenOnly}
                aria-label="Fullscreen"
              >
                <Maximize
                  style={{ height: "6rem", width: "6rem" }}
                  className="text-orange-peel"
                  strokeWidth={1.5}
                />
              </Button>
              <Button
                variant="outline"
                className="p-0 rounded-full bg-black/70 hover:bg-black/90 border-2 border-orange-peel/50 hover:border-orange-peel transition-all pointer-events-auto disabled:opacity-50 disabled:pointer-events-none"
                style={{ height: "12rem", width: "12rem" }}
                onClick={handleFullscreenAndPlay}
                disabled={!player.isReady}
                aria-label="Fullscreen and Play"
              >
                <div className="relative flex items-center justify-center">
                  <Maximize
                    style={{ height: "6rem", width: "6rem" }}
                    className="text-orange-peel"
                    strokeWidth={1.5}
                  />
                  <Play
                    style={{ height: "3rem", width: "3rem" }}
                    className="text-orange-peel absolute"
                    fill="currentColor"
                    strokeWidth={1.5}
                  />
                </div>
              </Button>
            </>
          )}
        </div>
      )}
      {/* Song Info Header */}
      {player.song && (
        <div className="absolute top-2 left-3 z-30 text-background/50">
          <h1 className="font-bold text-xl">{player.song.title}</h1>
          <h2
            className="text-base cursor-pointer hover:text-orange-peel transition-colors"
            onClick={() =>
              navigate(
                `/library?expandArtist=${encodeURIComponent(player.song.artist)}`,
              )
            }
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                navigate(
                  `/library?expandArtist=${encodeURIComponent(player.song.artist)}`,
                );
              }
            }}
          >
            {player.song.artist}
          </h2>
        </div>
      )}

      {/* Session QR Code - scan to join */}
      <SessionInfoDisplay
        variant="qr"
        trigger="hover"
        visibility="host-only"
        className="absolute top-2 right-3 z-30"
        qrSize={180}
      />

      {/* Main Lyrics Display or End States - positioned above controls */}
      <div className={`absolute top-0 left-0 right-0 bottom-0`}>
        {player.song && player.songEnded ? (
          // Determine if queue has more songs (position 0 is current, position > 0 are remaining)
          queueItems && queueItems.length > 1 ? (
            <SongEnded
              currentSong={player.song}
              nextQueueItem={queueItems.find((item) => item.position === 1)}
              onPlayNext={
                onPlayNext
                  ? () => {
                      const nextItem = queueItems.find(
                        (item) => item.position === 1,
                      );
                      if (nextItem) onPlayNext(String(nextItem.id));
                    }
                  : undefined
              }
            />
          ) : (
            <QueueEnded currentSong={player.song} />
          )
        ) : player.song ? (
          <>
            {player.showChords && <ChordCarousel chords={songChords} currentTime={player.currentTime} />}
            <LyricsDisplayWithCountIn
              lyrics={player.lyrics}
              isSync={player.isLyricsSync}
              currentTime={player.currentTime}
              lyricsSize={player.lyricsSize}
              lyricsOffset={player.lyricsOffset}
              onSeek={player.seek}
              songId={songId}
              songTitle={player.song?.title}
              songArtist={player.song?.artist}
              songAlbum={player.song?.album}
              songDuration={player.song?.duration}
              bpm={player.song?.bpm}
              // Count-in props (hardcoded for initial testing)
              showCountdownNumbers={false}
              showCountdownIcons={false}
              showProgressBar={true}
              showLeadInHighlight={false}
            />
          </>
        ) : (
          <div className="flex flex-col items-center justify-center w-full h-full gap-4">
            <div className="text-background/60 text-xl font-semibold">
              No songs in the queue
            </div>
            <Button
              variant="outline"
              size="lg"
              onClick={() => navigate("/library")}
              className="bg-black/60 hover:bg-black/80 border-white/20 hover:border-white/40 text-white gap-2"
            >
              <Library className="w-5 h-5" />
              Browse Library
            </Button>
          </div>
        )}
      </div>

      {/* Bottom Controls Area */}
      <BottomControlsArea
        song={player.song}
        isLoading={player.isLoading}
        isReady={player.isReady}
        isPlaying={player.isPlaying}
        songEnded={player.songEnded}
        currentTime={player.currentTime}
        duration={player.duration}
        vocalVolume={player.vocalVolume}
        isFullscreen={ui.isFullscreen}
        tapTempoBpm={effectiveBpm}
        tapTempoSongBpm={player.song?.bpm ?? null}
        tapTempoIsActive={tapTempo.isActive}
        tapTempoTapCount={tapTempo.tapCount}
        tapTempoMinTaps={MIN_TAPS}
        tapTempoHasUnsavedChanges={tapTempo.hasUnsavedChanges}
        tapTempoIsSaving={updateSongMutation.isPending}
        mouseRecentlyMoved={mouseRecentlyMoved}
        hasNextSong={
          !!(
            player.songEnded &&
            onPlayNext &&
            queueItems &&
            queueItems.length > 1
          )
        }
        onPlayPause={
          player.song
            ? player.songEnded
              ? onPlayNext && queueItems && queueItems.length > 1
                ? () => {
                    const nextItem = queueItems.find(
                      (item) => item.position === 1,
                    );
                    if (nextItem) onPlayNext(String(nextItem.id));
                  }
                : player.replay
              : player.togglePlay
            : noop
        }
        onSeek={player.seek}
        onVolumeChange={player.song ? player.setVocalVolume : noopVolume}
        onVolumeToggle={player.song ? handleVolumeToggle : noop}
        onFullscreenToggle={ui.toggleFullscreen}
        onTapTempoTap={tapTempo.handleTap}
        onTapTempoSave={handleSaveBpm}
        onTapTempoReset={tapTempo.reset}
      />
    </FullscreenContainer>
  );

  return (
    <PlayerErrorBoundary onError={undefined}>
      <div className="h-[70vh] max-w-full aspect-video mx-auto">
        {playerContent}
      </div>
    </PlayerErrorBoundary>
  );
};

export default KaraokePlayer;
