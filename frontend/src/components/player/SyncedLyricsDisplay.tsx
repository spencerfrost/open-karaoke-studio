import React from "react";
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

  // TO DO: Use the size from the performance controls store
  // const { lyricsSize } = usePerformanceControlsStore();

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
                ? "text-background text-2xl font-bold"
                : "text-background/50 text-xl opacity-70"
            }`}
          >
            {line.content}
          </div>
        )}
        className="h-full w-full overflow-y-scroll scrollbar-hide pb-20 mask-image-fade-bottom"
      />
      <AudioVisualizer className="absolute bottom-0 left-0 right-0" />
    </div>
  );
};

export default SyncedLyricsDisplay;
