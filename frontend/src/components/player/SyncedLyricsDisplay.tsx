import React, { useEffect } from "react";
import { Play, Pause, Minimize, Maximize } from "lucide-react";
import { Lrc } from "react-lrc";

import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import AudioVisualizer from "@/components/player/AudioVisualizer";
import { Button } from "../ui/button";

interface SyncedLyricsDisplayProps {
  className?: string;
  syncedLyrics: string;
  currentTime: number;
}

const SyncedLyricsDisplay: React.FC<SyncedLyricsDisplayProps> = ({
  className = "",
  syncedLyrics,
  currentTime,
}) => {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const [fsError, setFsError] = React.useState<string | null>(null);
  const { lyricsSize, lyricsOffset, isReady, isPlaying, userPlay, userPause } =
    useKaraokePlayerStore();

  useEffect(() => {
    const handleFullscreenChange = () => {
      const fsElement =
        document.fullscreenElement || (document as any).webkitFullscreenElement;
      setIsFullscreen(!!fsElement && fsElement === containerRef.current);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener(
        "webkitfullscreenchange",
        handleFullscreenChange
      );
    };
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullscreen) {
        exitFullscreen();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isFullscreen]);

  const enterFullscreen = async () => {
    setFsError(null);
    try {
      if (containerRef.current) {
        if (containerRef.current.requestFullscreen) {
          await containerRef.current.requestFullscreen();
        } else if ("webkitRequestFullscreen" in containerRef.current!) {
          (
            containerRef.current! as HTMLElement & {
              webkitRequestFullscreen?: () => void;
            }
          ).webkitRequestFullscreen?.();
        } else {
          setFsError("Fullscreen not supported in this browser.");
        }
      }
    } catch {
      setFsError("Failed to enter fullscreen.");
    }
  };

  const exitFullscreen = async () => {
    setFsError(null);
    try {
      if (document.exitFullscreen) {
        await document.exitFullscreen();
      } else if (
        (document as Document & { webkitExitFullscreen?: () => void })
          .webkitExitFullscreen
      ) {
        // Safari
        (
          document as Document & { webkitExitFullscreen?: () => void }
        ).webkitExitFullscreen?.();
      }
    } catch {
      setFsError("Failed to exit fullscreen.");
    }
  };

  const handlePlayPause = () => {
    if (!isReady) return;
    if (isPlaying) {
      userPause();
    } else {
      userPlay();
    }
  };

  if (!syncedLyrics) {
    return null;
  }

  // Remove duplicate playback controls and handler
  const lyricsSizeClass =
    lyricsSize === "small"
      ? "text-base"
      : lyricsSize === "large"
        ? "text-3xl"
        : "text-xl";

  const activeLyricsSizeClass =
    lyricsSize === "small"
      ? "text-lg"
      : lyricsSize === "large"
        ? "text-4xl"
        : "text-2xl";

  return (
    <div
      ref={containerRef}
      className={`h-full w-full ${className} relative`}
      tabIndex={-1}
      style={{ outline: isFullscreen ? "none" : undefined }}
    >
      <Button
        type="button"
        aria-label={isPlaying ? "Pause" : "Play"}
        onClick={handlePlayPause}
        disabled={!isReady}
        className="absolute left-6 bottom-8 z-30 p-4 rounded-full"
      >
        {isPlaying ? <Pause size={48} /> : <Play size={48} />}
      </Button>
      <Button
        type="button"
        size="icon"
        aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
        onClick={isFullscreen ? exitFullscreen : enterFullscreen}
        className="absolute top-2 right-2 z-20 p-2 rounded-full"
      >
        {isFullscreen ? <Minimize /> : <Maximize />}
      </Button>
      {/* Error message */}
      {fsError && (
        <div className="absolute top-12 right-2 z-30 bg-red-500 text-white text-xs px-2 py-1 rounded shadow">
          {fsError}
        </div>
      )}
      <Lrc
        lrc={syncedLyrics}
        currentMillisecond={currentTime + lyricsOffset}
        verticalSpace={true}
        lineRenderer={({ active, line }) => (
          <div
            className={`py-2 px-2 transition-all duration-500 text-center ${
              active
                ? `text-background font-bold ${activeLyricsSizeClass} text-shadow`
                : `text-background/50 opacity-70 ${lyricsSizeClass}`
            }`}
          >
            {line.content}
          </div>
        )}
        className="lrc h-full w-full overflow-y-scroll scrollbar-hide pb-20 mask-image-fade-bottom"
      />
      <AudioVisualizer className="absolute bottom-0 left-0 right-0" />
    </div>
  );
};

export default SyncedLyricsDisplay;
