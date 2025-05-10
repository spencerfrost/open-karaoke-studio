import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import React from "react";

interface LyricsDisplayProps {
  className?: string;
  lyrics: string;
  progress: number;
  currentTime?: number;
}

const LyricsDisplay: React.FC<LyricsDisplayProps> = ({
  className = "",
  lyrics,
}) => {
  const { lyricsSize } = useKaraokePlayerStore();
  const lyricsSizeClass =
    lyricsSize === "small"
      ? "text-base"
      : lyricsSize === "large"
        ? "text-3xl"
        : "text-xl";

  return (
    <div
      className={`flex flex-col items-center justify-center text-center w-full h-full ${className}`}
    >
      <div
        className="w-full h-full overflow-y-auto scrollbar-hide"
        style={{ maxHeight: "100%" }}
      >
        {lyrics ? (
          <div
            className={`text-2xl font-semibold text-background whitespace-pre-line ${lyricsSizeClass}`}
          >
            {lyrics}
          </div>
        ) : (
          <div className="text-gray-400">No lyrics available</div>
        )}
      </div>
    </div>
  );
};

export default LyricsDisplay;
