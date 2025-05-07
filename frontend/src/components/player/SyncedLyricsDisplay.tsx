import React from "react";
import { Lrc } from "react-lrc";
import AudioVisualizer from "@/components/player/AudioVisualizer";
import { usePerformanceControlsStore } from "@/stores/usePerformanceControlsStore";

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
  const { lyricsSize } = usePerformanceControlsStore();

  if (!syncedLyrics) {
    return null;
  }

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
    <div className={`h-full w-full ${className} relative`}>
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
