import React from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { Button } from "@/components/ui/button";
import { Volume2, Play, Pause } from "lucide-react";
import PerformanceControlInput from "./PerformanceControlsInput";
import ProgressBar from "@/features/player/components/subcomponents/ProgressBar";
import { usePerformanceControlsLogic } from "../hooks/usePerformanceControlsLogic";
import { getLyricsSizeLabel } from "@/utils/performanceControls";
import LyricsTimingControls from "@/features/lyrics/components/LyricsTimingControls";

const PerformanceControlsPanel: React.FC = () => {
  const {
    isPlaying,
    currentTime,
    duration,
    userPlay,
    userPause,
    seek,
  } = useKaraokePlayerStore();

  const {
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    toggleVocalsVolume,
    toggleInstrumentalVolume,
    handleLyricsSizeChange,
    getLyricsSizeNumericValue,
  } = usePerformanceControlsLogic();

  return (
    <div className="flex-1 flex items-center justify-center flex-col">
      {/* Play/Pause and Progress */}
      <div className="flex items-center justify-center mb-4 w-full gap-4">
        <Button
          className="rounded-full"
          size="icon"
          onClick={isPlaying ? userPause : userPlay}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? <Pause size={24} /> : <Play size={24} />}
        </Button>
        <ProgressBar
          currentTime={currentTime}
          duration={duration}
          onSeek={seek}
          className="w-full"
        />
      </div>

      {/* Volume and Lyrics Controls */}
      <div className="flex-1 grid grid-cols-3 gap-4">
        {/* Vocal Volume Section */}
        <PerformanceControlInput
          icon="mic"
          label="Vocals"
          value={vocalVolume}
          valueDisplay={`${Math.round(vocalVolume * 100)}%`}
          min={0}
          max={1}
          step={0.05}
          onValueChange={(value) => useKaraokePlayerStore.getState().setVocalVolume(value)}
        >
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleVocalsVolume}
          >
            <Volume2 size={24} />
          </Button>
        </PerformanceControlInput>

        {/* Music Volume Section */}
        <PerformanceControlInput
          icon="music"
          label="Instrumental"
          value={instrumentalVolume}
          valueDisplay={`${Math.round(instrumentalVolume * 100)}%`}
          min={0}
          max={1}
          step={0.05}
          onValueChange={(value) => useKaraokePlayerStore.getState().setInstrumentalVolume(value)}
        >
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleInstrumentalVolume}
          >
            <Volume2 size={24} />
          </Button>
        </PerformanceControlInput>

        {/* Lyrics Size Section */}
        <PerformanceControlInput
          icon="maximize-2"
          label="Lyrics Size"
          value={getLyricsSizeNumericValue(lyricsSize)}
          valueDisplay={getLyricsSizeLabel(lyricsSize)}
          min={1}
          max={3}
          step={1}
          onValueChange={handleLyricsSizeChange}
        >
          <Button variant="ghost" size="icon">
            Aa
          </Button>
        </PerformanceControlInput>
      </div>

      {/* Lyrics Timing Controls */}
      <LyricsTimingControls />
    </div>
  );
};

export default PerformanceControlsPanel;