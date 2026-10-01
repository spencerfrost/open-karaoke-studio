/**
 * StageAmbientBar - the bottom-of-screen strip shown while the stage rails
 * are collapsed (playing, mouse idle). The transport's buttons hide
 * themselves in this state, so this is what tells the room the song is still
 * moving: a waveform sitting right above a thin progress rail pinned to the
 * very bottom edge of the viewport.
 */

import React from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { cn } from "@/lib/utils";
import AudioVisualizer from "../subcomponents/AudioVisualizer";
import ProgressBar from "../subcomponents/ProgressBar";

const VISUALIZER_HEIGHT = 56;
// gap-2 between the visualizer and the progress rail, then the rail's own h-2.
// px, not rem: the strip is pinned to the viewport and does not scale.
export const STAGE_AMBIENT_BAR_HEIGHT = `${VISUALIZER_HEIGHT + 8 + 8}px`;

interface StageAmbientBarProps {
  visible: boolean;
}

const StageAmbientBar: React.FC<StageAmbientBarProps> = ({ visible }) => {
  const { currentTime, duration, seek } = useKaraokePlayerStore();

  return (
    <div
      className={cn(
        "pointer-events-none fixed inset-x-0 bottom-0 z-30 flex flex-col gap-2 transition-opacity duration-500",
        visible ? "opacity-100" : "opacity-0",
      )}
    >
      <AudioVisualizer height={VISUALIZER_HEIGHT} />
      <div className={cn(visible && "pointer-events-auto")}>
        <ProgressBar
          currentTime={currentTime}
          duration={duration}
          onSeek={seek}
        />
      </div>
    </div>
  );
};

export default StageAmbientBar;
