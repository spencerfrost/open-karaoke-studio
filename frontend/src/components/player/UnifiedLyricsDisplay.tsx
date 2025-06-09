import React, { useRef, useState, useEffect } from "react";
import {
  Play,
  Pause,
  Minimize,
  Maximize,
  Volume1,
  Volume2,
  VolumeX,
} from "lucide-react";
import { Lrc } from "react-lrc";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import AudioVisualizer from "@/components/player/AudioVisualizer";
import ProgressBar from "@/components/player/ProgressBar";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";

interface UnifiedLyricsDisplayProps {
  lyrics: string;
  isSynced: boolean;
  currentTime: number;
  duration: number;
  title: string;
  artist: string;
  onSeek: (val: number) => void;
  className?: string;
}

const UnifiedLyricsDisplay: React.FC<UnifiedLyricsDisplayProps> = ({
  lyrics,
  isSynced,
  currentTime,
  duration,
  title,
  artist,
  onSeek,
  className = "",
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [fsError, setFsError] = useState<string | null>(null);
  const {
    vocalVolume,
    setVocalVolume,
    lyricsSize,
    lyricsOffset,
    isReady,
    isPlaying,
    userPlay,
    userPause,
  } = useKaraokePlayerStore();

  // Fullscreen logic
  useEffect(() => {
    const handleFullscreenChange = () => {
      const fsElement =
        document.fullscreenElement ||
        (document as Document & { webkitFullscreenElement?: Element })
          .webkitFullscreenElement;
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
      {fsError && (
        <div className="absolute top-12 right-2 z-30 bg-red-500 text-white text-xs px-2 py-1 rounded shadow">
          {fsError}
        </div>
      )}
      <div className="absolute top-2 left-3 z-30 text-background/50">
        <h1 className="text-xl font-bold">{title}</h1>
        <h2 className="text-base">{artist}</h2>
      </div>
      {/* Lyrics display */}
      {isSynced ? (
        <Lrc
          lrc={lyrics}
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
      ) : (
        <div className="w-full h-full overflow-y-auto scrollbar-hide">
          {lyrics ? (
            <div
              className={`text-2xl font-semibold text-background whitespace-pre-line text-center ${lyricsSizeClass}`}
            >
              {lyrics}
            </div>
          ) : (
            <div className="text-gray-400">No lyrics available</div>
          )}
        </div>
      )}
      {/* Progress bar and visualizer */}
      <div className="w-full absolute bottom-0 left-0 right-0">
        <AudioVisualizer className="w-full" />

        <ProgressBar
          currentTime={currentTime / 1000}
          duration={duration}
          onSeek={onSeek}
        />
        <div className="flex items-center">
          <Button
            variant="ghost"
            aria-label={isPlaying ? "Pause" : "Play"}
            onClick={handlePlayPause}
            disabled={!isReady}
            className="px-4"
          >
            {isPlaying ? <Pause size={48} /> : <Play size={48} />}
          </Button>
          {/* Volume control */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  aria-label={
                    vocalVolume === 0 ? "Unmute vocals" : "Mute vocals"
                  }
                  className="px-4"
                  onClick={() =>
                    vocalVolume === 0 ? setVocalVolume(1) : setVocalVolume(0)
                  }
                >
                  {vocalVolume === 0 ? (
                    <VolumeX size={28} />
                  ) : vocalVolume < 0.5 ? (
                    <Volume1 size={28} />
                  ) : (
                    <Volume2 size={28} />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent
                side="top"
                align="center"
                className="flex flex-col items-center"
              >
                <Slider
                  orientation="vertical"
                  min={0}
                  max={1}
                  step={0.01}
                  value={[vocalVolume]}
                  onValueChange={([val]) => {
                    setVocalVolume(val);
                  }}
                  aria-label="Vocals volume"
                />
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <div className="flex-1 text-sm text-background/50">
            {new Date(currentTime).toISOString().substr(11, 8)} /{" "}
            {new Date(duration).toISOString().substr(11, 8)}
          </div>

          <Button
            variant="ghost"
            aria-label={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
            onClick={isFullscreen ? exitFullscreen : enterFullscreen}
            className="px-4"
          >
            {isFullscreen ? <Minimize size={24} /> : <Maximize size={24} />}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default UnifiedLyricsDisplay;
