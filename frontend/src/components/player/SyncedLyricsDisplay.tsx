import React, { ref } from "react";
import { Lrc } from "react-lrc";
import AudioVisualizer from "@/components/player/AudioVisualizer";

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
  if (!syncedLyrics) {
    return null;
  }

  return (
    <div className={`h-full w-full ${className}`}>
      <Lrc
        lrc={syncedLyrics}
        currentMillisecond={currentTime}
        verticalSpace={true}
        lineRenderer={({ active, line }) => (
          <div
            className={`py-2 px-2 transition-all duration-500 ${
              active
                ? "text-background text-2xl font-bold"
                : "text-background/50 text-xl opacity-70"
            }`}
          >
            {line.content}
          </div>
        )}
        className="h-full w-full overflow-y-scroll scrollbar-hide"
      />
    </div>
  );
};

export default SyncedLyricsDisplay;