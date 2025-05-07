import { usePerformanceControlsStore } from "@/stores/usePerformanceControlsStore";
import React, { useEffect, useRef } from "react";

interface LyricsDisplayProps {
  className?: string;
  lyrics: string;
  progress: number;
  currentTime?: number;
}

const LyricsDisplay: React.FC<LyricsDisplayProps> = ({
  className = "",
  lyrics,
  // progress,
  // currentTime = 0,
}) => {
  const lyricsRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { lyricsSize } = usePerformanceControlsStore();
  const lyricsSizeClass =
    lyricsSize === "small"
      ? "text-base"
      : lyricsSize === "large"
        ? "text-3xl"
        : "text-xl";

  // useEffect(() => {
  //   if (lyricsRef.current && containerRef.current) {
  //     const updateScrollPosition = () => {
  //       const lyricsElement = lyricsRef.current;
  //       if (!lyricsElement) return;

  //       const totalScrollHeight =
  //         lyricsElement.scrollHeight - lyricsElement.clientHeight;
  //       const scrollPosition = Math.max(
  //         0,
  //         Math.min(totalScrollHeight, progress * totalScrollHeight),
  //       );

  //       lyricsElement.scrollTop = scrollPosition;
  //     };
  //     setTimeout(updateScrollPosition, 0);
  //   }
  // }, [progress, lyrics]);

  return (
    <div
      className={`flex flex-col items-center justify-center text-center w-full h-full ${className}`}
      ref={containerRef}
    >
      <div
        ref={lyricsRef}
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
