/**
 * SpeedControl - Playback speed control with pitch preservation
 * Uses granular synthesis (Tone.js GrainPlayer) to maintain pitch
 */

import React, { memo } from "react";
import { Gauge } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Slider } from "@/components/ui/slider";

interface SpeedControlProps {
  speed: number;
  onSpeedChange: (speed: number) => void;
  className?: string;
}

const SPEED_PRESETS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

const SpeedControl: React.FC<SpeedControlProps> = memo(
  ({ speed, onSpeedChange, className = "" }) => {
    const displaySpeed = `${speed.toFixed(2)}x`;

    return (
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="pill"
            className={`gap-1 ${className}`}
            aria-label={`Playback speed: ${displaySpeed}`}
          >
            <Gauge size={20} aria-hidden="true" />
            <span className="text-sm font-mono">{displaySpeed}</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-4" align="end">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Playback Speed</span>
              <span className="text-sm text-muted-foreground">
                {displaySpeed}
              </span>
            </div>

            <Slider
              min={0.5}
              max={2.0}
              step={0.05}
              value={[speed]}
              onValueChange={([val]) => onSpeedChange(val)}
              aria-label="Playback speed"
              className="w-full"
            />

            <div className="flex flex-wrap gap-1">
              {SPEED_PRESETS.map((preset) => (
                <Button
                  key={preset}
                  variant={speed === preset ? "default" : "outline"}
                  size="sm"
                  onClick={() => onSpeedChange(preset)}
                  className="flex-1 min-w-[3rem]"
                >
                  {preset}x
                </Button>
              ))}
            </div>

            <p className="text-xs text-muted-foreground text-center">
              Pitch-preserving time-stretch with adaptive grain sizing
            </p>
          </div>
        </PopoverContent>
      </Popover>
    );
  },
);

SpeedControl.displayName = "SpeedControl";

export default SpeedControl;
