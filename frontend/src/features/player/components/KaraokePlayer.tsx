/**
 * KaraokePlayer - Main unified karaoke player component
 * YouTube-like API: <KaraokePlayer songId="123" />
 */

import React from "react";
import { useNavigate } from "react-router-dom";
import { useKaraokePlayer, usePlayerUI } from "../hooks";
import {
  PlayerControls,
  FullscreenContainer,
  PlayerErrorBoundary,
  PlayerSidebar,
  PlayerSidebarTrigger,
  SongEndedOverlay,
  TapTempoButton,
} from "./subcomponents";
import { LyricsDisplayWithCountIn } from "@/features/lyrics";
import AudioVisualizer from "./subcomponents/AudioVisualizer";
import ProgressBar from "./subcomponents/ProgressBar";
import { formatTime } from "@/utils/formatters";
import type { KaraokePlayerProps } from "../types/KaraokePlayer.types";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import { Settings2, Maximize, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { IndeterminateProgress } from "@/components/ui/indeterminate-progress";
import { useTapTempo } from "@/hooks/useTapTempo";

const KaraokePlayer: React.FC<KaraokePlayerProps> = ({
  songId,
  autoPlay = false,
  size = "full",
  controls = true,
  showInfo = true,
  showVisualizer = true,
  sidebarMode = "floating",
  showSidebarTrigger = true,
  onPlay,
  onPause,
  onEnd,
  onTimeUpdate,
  onError,
  className = "",
}) => {
  // Navigation for song selection
  const navigate = useNavigate();

  // Initialize player and UI hooks
  const player = useKaraokePlayer(songId, { autoPlay });
  const ui = usePlayerUI();

  // Hover state for overlay controls
  const [isHovering, setIsHovering] = React.useState(false);

  // Sidebar state
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(false);

  // Sidebar edge hover state
  const [isSidebarEdgeHovering, setIsSidebarEdgeHovering] =
    React.useState(false);

  // Track mouse movement for showing sidebar trigger
  const [mouseRecentlyMoved, setMouseRecentlyMoved] = React.useState(false);
  const mouseTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  // Tap tempo hook with minimum 3 taps before setting BPM
  const MIN_TAPS = 3;
  const tapTempo = useTapTempo({
    minTaps: MIN_TAPS,
  });

  // Track saving state
  const [isSavingBpm, setIsSavingBpm] = React.useState(false);

  // Get effective BPM (from tap tempo if active, otherwise from song)
  const effectiveBpm = tapTempo.bpm ?? player.song?.bpm ?? null;

  // Save BPM to database
  const handleSaveBpm = React.useCallback(async () => {
    if (songId && tapTempo.bpm && tapTempo.bpm >= 30 && tapTempo.bpm <= 300) {
      setIsSavingBpm(true);
      try {
        const response = await fetch(`/api/songs/${songId}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({ bpm: tapTempo.bpm }),
        });

        if (!response.ok) {
          throw new Error(`Failed to update BPM: ${response.status}`);
        }

        // Reset the tap tempo after successful save
        tapTempo.reset();
      } catch (error) {
        console.error("Failed to update BPM:", error);
      } finally {
        setIsSavingBpm(false);
      }
    }
  }, [songId, tapTempo]);

  // Reset mouse movement timer on mouse move while hovering
  const handleMouseMove = React.useCallback(() => {
    setMouseRecentlyMoved(true);
    if (mouseTimeoutRef.current) {
      clearTimeout(mouseTimeoutRef.current);
    }
    mouseTimeoutRef.current = setTimeout(() => {
      setMouseRecentlyMoved(false);
    }, 3000);
  }, []);

  // Clear timeout on unmount
  React.useEffect(() => {
    return () => {
      if (mouseTimeoutRef.current) {
        clearTimeout(mouseTimeoutRef.current);
      }
    };
  }, []);

  // Global spacebar handler for tap tempo
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle spacebar if not focused on an input element
      if (
        e.code === "Space" &&
        e.target instanceof HTMLElement &&
        !["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)
      ) {
        // Don't prevent default if the player isn't loaded or ready
        if (!player.song || !player.isReady) {
          return;
        }

        // Prevent default space behavior (scrolling) when tapping tempo
        e.preventDefault();
        tapTempo.handleTap();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [player.song, player.isReady, tapTempo]);

  // Show sidebar trigger when hovering and mouse recently moved
  const showSidebarTriggerIcon = isHovering && mouseRecentlyMoved;

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

  // Size-based styling
  const sizeClasses = {
    compact: "max-h-80",
    full: "aspect-video",
    stage: "min-h-screen",
  };

  // Bottom offset for lyrics container to avoid overlapping controls
  const lyricsBottomOffset = {
    compact: "bottom-14",
    full: "bottom-16",
    stage: "bottom-20",
  };

  // Show controls based on configuration
  const showControls = controls;
  const showPlay = showControls;
  const showVolume = showControls;
  const showProgress = showControls;
  const showFullscreen = showControls;

  // Error state
  if (player.error) {
    return (
      <div
        className={`${sizeClasses[size]} ${className} flex flex-col items-center justify-center bg-black/80 rounded-xl text-center p-8`}
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

  // Show player UI even if no song is loaded
  // For push mode, we need a flex container wrapper
  const playerContent = (
    <FullscreenContainer
      isFullscreen={ui.isFullscreen}
      containerRef={ui.containerRef}
      fsError={ui.fsError}
      className={`${sizeClasses[size]} ${className} bg-black/80 rounded-xl overflow-hidden relative flex-1`}
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
      {/* Song Ended Overlay - Shows suggestions when song finishes */}
      {player.songEnded && player.song && (
        <SongEndedOverlay
          currentSong={player.song}
          onReplay={player.replay}
          onSelectSong={(song) => navigate(`/player/${song.id}`)}
        />
      )}

      {/* Hover Buttons - Show on hover when paused (but not when song ended) */}
      {!player.isPlaying && !player.songEnded && player.song && isHovering && (
        <div
          className={`absolute top-0 left-0 right-0 bottom-24 z-40 flex items-center justify-center gap-12 pointer-events-none transition-opacity duration-300 ${
            showSidebarTriggerIcon ? "opacity-100" : "opacity-0"
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
      {showInfo && player.song && (
        <div className="absolute top-2 left-3 z-30 text-background/50">
          <h1
            className={`font-bold ${size === "stage" ? "text-2xl" : "text-xl"}`}
          >
            {player.song.title}
          </h1>
          <h2 className={`${size === "stage" ? "text-lg" : "text-base"}`}>
            {player.song.artist}
          </h2>
        </div>
      )}

      {/* Session Code Display */}
      <SessionInfoDisplay
        variant="code"
        colorScheme="player"
        trigger="hover"
        visibility="host-only"
        className="absolute top-2 right-3 z-30"
      />

      {/* Main Lyrics Display or No Song Message - positioned above controls */}
      <div
        className={`absolute top-0 left-0 right-0 ${lyricsBottomOffset[size]}`}
      >
        {player.song ? (
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
            showCountdownNumbers={true}
            showCountdownIcons={false}
            showProgressBar={true}
            showLeadInHighlight={false}
          />
        ) : (
          <div className="flex flex-col items-center justify-center w-full h-full">
            <div className="text-background/60 text-xl font-semibold py-12">
              No songs in the queue
            </div>
          </div>
        )}
      </div>

      {/* Tap Tempo Button - Bottom Left Corner */}
      {player.song && (
        <div className="absolute bottom-20 left-3 z-30">
          <TapTempoButton
            bpm={effectiveBpm}
            songBpm={player.song.bpm ?? null}
            isPlaying={player.isPlaying}
            isActive={tapTempo.isActive}
            tapCount={tapTempo.tapCount}
            minTaps={MIN_TAPS}
            hasUnsavedChanges={tapTempo.hasUnsavedChanges}
            onTap={tapTempo.handleTap}
            onSave={handleSaveBpm}
            onReset={tapTempo.reset}
            isSaving={isSavingBpm}
          />
        </div>
      )}

      {/* Bottom Controls Area */}
      <div className="w-full absolute bottom-0 left-0 right-0 z-20">
        {/* Audio Visualizer */}
        {showVisualizer && <AudioVisualizer className="w-full" />}

        {/* Progress Bar - show indeterminate when loading */}
        {player.song &&
          showProgress &&
          (player.isLoading ? (
            <IndeterminateProgress className="w-full" size="sm" />
          ) : (
            <ProgressBar
              currentTime={player.currentTime}
              duration={player.duration}
              onSeek={player.seek}
            />
          ))}

        {/* Player Controls (always rendered, disabled if no song) */}
        <div className="flex items-center">
          {/* Main Controls (Play/Pause, Volume) */}
          <PlayerControls
            isPlaying={player.isPlaying}
            isReady={!!player.song && player.isReady}
            vocalVolume={player.vocalVolume}
            songEnded={player.songEnded}
            isFullscreen={ui.isFullscreen}
            showVolumeSlider={ui.showVolumeSlider}
            controls={
              [showPlay && "play", showVolume && "volume"].filter(
                Boolean,
              ) as Array<"play" | "volume">
            }
            onPlayPause={
              player.song
                ? player.songEnded
                  ? player.replay
                  : player.togglePlay
                : noop
            }
            onVolumeChange={player.song ? player.setVocalVolume : noopVolume}
            onVolumeToggle={player.song ? handleVolumeToggle : noop}
            onFullscreenToggle={ui.toggleFullscreen}
            onVolumeSliderShow={ui.setShowVolumeSlider}
          />

          {/* Time Display */}
          {player.song && showProgress && (
            <div
              className={`flex-1 text-sm text-background/50 ${size === "compact" ? "text-xs" : "text-sm"}`}
            >
              {formatTime(player.currentTime)} / {formatTime(player.duration)}
            </div>
          )}

          {/* Spacer to push controls to far right */}
          <div className="flex-1" />

          {/* Sidebar Trigger */}
          {showSidebarTrigger && (
            <PlayerSidebarTrigger
              onClick={() => setIsSidebarOpen(true)}
              className="mr-1"
            />
          )}

          {/* Fullscreen Control (always rendered, disabled if no song) */}
          {showFullscreen && (
            <PlayerControls
              isPlaying={player.isPlaying}
              isReady={!!player.song && player.isReady}
              vocalVolume={player.vocalVolume}
              isFullscreen={ui.isFullscreen}
              showVolumeSlider={ui.showVolumeSlider}
              controls={["fullscreen"]}
              onPlayPause={player.song ? player.togglePlay : noop}
              onVolumeChange={player.song ? player.setVocalVolume : noopVolume}
              onVolumeToggle={player.song ? handleVolumeToggle : noop}
              onFullscreenToggle={ui.toggleFullscreen}
              onVolumeSliderShow={ui.setShowVolumeSlider}
            />
          )}
        </div>
      </div>

      {/* Right Edge Hover Zone - Opens sidebar on click */}
      {!isSidebarOpen && (
        <div
          className="absolute top-0 right-0 bottom-24 w-12 z-35 cursor-pointer group"
          onMouseEnter={() => setIsSidebarEdgeHovering(true)}
          onMouseLeave={() => setIsSidebarEdgeHovering(false)}
          onClick={() => setIsSidebarOpen(true)}
          aria-label="Open controls"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              setIsSidebarOpen(true);
            }
          }}
        >
          {/* Hover indicator - shows when hovering over player and mouse recently moved */}
          <div
            className={`absolute inset-0 flex items-center justify-center transition-all duration-200 ${
              isSidebarEdgeHovering || showSidebarTriggerIcon
                ? "bg-gradient-to-l from-black/60 to-transparent opacity-100"
                : "opacity-0"
            }`}
          >
            <div
              className={`flex flex-col items-center gap-1 transition-all duration-200 ${
                isSidebarEdgeHovering || showSidebarTriggerIcon
                  ? "opacity-100 translate-x-0"
                  : "opacity-0 translate-x-2"
              }`}
            >
              <Settings2 className="w-7 h-7 text-background/80" />
            </div>
          </div>
        </div>
      )}

      {/* Player Sidebar (floating mode - inside container) */}
      {sidebarMode === "floating" && (
        <PlayerSidebar
          isOpen={isSidebarOpen}
          onOpenChange={setIsSidebarOpen}
          mode="floating"
        />
      )}
    </FullscreenContainer>
  );

  return (
    <PlayerErrorBoundary onError={undefined}>
      {sidebarMode === "push" ? (
        // Push mode: flex container with sidebar alongside player
        <div className="flex w-full h-full">
          {playerContent}
          <PlayerSidebar
            isOpen={isSidebarOpen}
            onOpenChange={setIsSidebarOpen}
            mode="push"
          />
        </div>
      ) : (
        // Floating mode: just the player content
        playerContent
      )}
    </PlayerErrorBoundary>
  );
};

export default KaraokePlayer;
