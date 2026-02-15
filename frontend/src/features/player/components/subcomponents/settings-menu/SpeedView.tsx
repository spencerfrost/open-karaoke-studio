/**
 * SpeedView - Playback speed control with pitch preservation
 * Moved from standalone SpeedControl into the settings menu
 */

import React from "react";
import { ChevronLeft } from "lucide-react";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { useAudioControlsStore } from "@/stores/useAudioControlsStore";

interface SpeedViewProps {
  onBack: () => void;
}

const SPEED_PRESETS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

const SpeedView: React.FC<SpeedViewProps> = ({ onBack }) => {
  const playbackSpeed = useAudioControlsStore((state) => state.playbackSpeed);
  const setPlaybackSpeed = useAudioControlsStore(
    (state) => state.setPlaybackSpeed,
  );

  const displaySpeed = `${playbackSpeed.toFixed(2)}x`;

  return (
    <div className="py-2">
      {/* Header with back button */}
      <div className="px-4 py-3 border-b border-white/10">
        <button
          onClick={onBack}
          className="flex items-center gap-2 hover:text-orange-peel transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Speed</h2>
        </button>
      </div>

      {/* Content */}
      <div className="px-4 py-4 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Playback Speed</span>
          <span className="text-sm text-background/60">{displaySpeed}</span>
        </div>

        <Slider
          min={0.5}
          max={2.0}
          step={0.05}
          value={[playbackSpeed]}
          onValueChange={([val]) => setPlaybackSpeed(val)}
          aria-label="Playback speed"
          className="w-full"
        />

        <div className="flex flex-wrap gap-1">
          {SPEED_PRESETS.map((preset) => (
            <Button
              key={preset}
              variant={playbackSpeed === preset ? "default" : "outline"}
              size="sm"
              onClick={() => setPlaybackSpeed(preset)}
              className="flex-1 min-w-[3rem]"
            >
              {preset}x
            </Button>
          ))}
        </div>

        <p className="text-xs text-background/40 text-center">
          Pitch-preserving time-stretch
        </p>
      </div>
    </div>
  );
};

export default SpeedView;
