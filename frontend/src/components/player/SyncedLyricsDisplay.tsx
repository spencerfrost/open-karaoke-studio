import React from "react";
import { Play, Pause } from "lucide-react";
import { useWebAudioKaraokeStore } from "@/stores/useWebAudioKaraokeStore";
import { Lrc } from "react-lrc";
import AudioVisualizer from "@/components/player/AudioVisualizer";
import { usePerformanceControlsStore } from "@/stores/usePerformanceControlsStore";
import { Button } from "../ui/button";

// Simple fullscreen icon (SVG)
const FullscreenIcon = () => (
  <svg
    width="24"
    height="24"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    className="w-6 h-6"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M4 8V6a2 2 0 012-2h2m8 0h2a2 2 0 012 2v2m0 8v2a2 2 0 01-2 2h-2m-8 0H6a2 2 0 01-2-2v-2"
    />
  </svg>
);

const ExitFullscreenIcon = () => (
  <svg
    width="24"
    height="24"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    className="w-6 h-6"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M10 14H6a2 2 0 01-2-2v-4m0 0V6a2 2 0 012-2h4m4 0h4a2 2 0 012 2v4m0 4v4a2 2 0 01-2 2h-4"
    />
  </svg>
);

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
  // All hooks must be called unconditionally at the top
  const { lyricsSize } = usePerformanceControlsStore();
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const [fsError, setFsError] = React.useState<string | null>(null);
  // Playback controls from global store
  const isPlaying = useWebAudioKaraokeStore((s) => s.isPlaying);
  const isReady = useWebAudioKaraokeStore((s) => s.isReady);
  const play = useWebAudioKaraokeStore((s) => s.play);
  const pause = useWebAudioKaraokeStore((s) => s.pause);

  React.useEffect(() => {
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

  React.useEffect(() => {
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
        } else if ((containerRef.current as any).webkitRequestFullscreen) {
          // Safari
          (containerRef.current as any).webkitRequestFullscreen();
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
      } else if ((document as any).webkitExitFullscreen) {
        // Safari
        (document as any).webkitExitFullscreen();
      }
    } catch {
      setFsError("Failed to exit fullscreen.");
    }
  };

  const handlePlayPause = () => {
    if (!isReady) return;
    if (isPlaying) {
      pause();
    } else {
      play();
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
      {/* Play/Pause button in fullscreen */}
      {isFullscreen && (
        <Button
          type="button"
          aria-label={isPlaying ? "Pause" : "Play"}
          onClick={handlePlayPause}
          disabled={!isReady}
          className="absolute left-16 bottom-24 z-30 p-4 rounded-full"
        >
          {isPlaying ? <Pause size={48} /> : <Play size={48} />}
        </Button>
      )}
      {/* Fullscreen button */}
      <button
        type="button"
        aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
        onClick={isFullscreen ? exitFullscreen : enterFullscreen}
        className="absolute top-2 right-2 z-20 p-2 rounded-full bg-background/80 hover:bg-background/90 border border-border shadow transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
      >
        {isFullscreen ? <ExitFullscreenIcon /> : <FullscreenIcon />}
      </button>
      {/* Error message */}
      {fsError && (
        <div className="absolute top-12 right-2 z-30 bg-red-500 text-white text-xs px-2 py-1 rounded shadow">
          {fsError}
        </div>
      )}
      <Lrc
        lrc={syncedLyrics}
        currentMillisecond={currentTime}
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
