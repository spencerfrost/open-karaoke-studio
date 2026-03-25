import React from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Volume2, VolumeX } from "lucide-react";

interface VolumeChannelProps {
  label: string;
  icon: React.ReactNode;
  volume: number;
  onVolumeChange: (volume: number) => void;
  onToggleMute: () => void;
  className?: string;
}

const VolumeChannel: React.FC<VolumeChannelProps> = ({
  label,
  icon,
  volume,
  onVolumeChange,
  onToggleMute,
  className,
}) => {
  return (
    <div className={`flex flex-col items-center gap-2 ${className ?? ""}`}>
      <div className="flex items-center gap-2">
        <span className="text-primary shrink-0">
          {React.cloneElement(icon as React.ReactElement, { size: 18 })}
        </span>
        <span className="text-sm font-semibold text-lemon-chiffon">
          {label} {Math.round(volume * 100)}%
        </span>
      </div>

      <div className="flex-1 min-h-0 w-full flex flex-col items-center gap-2">
        <Slider
          value={[volume]}
          min={0}
          max={1}
          step={0.05}
          variant="performance"
          orientation="vertical"
          onValueChange={([v]) => onVolumeChange(v)}
          className="flex-1 min-h-0"
        />
        <Button
          variant="outline"
          size="sm"
          onClick={onToggleMute}
          className="w-full"
        >
          {volume === 0 ? (
            <>
              <VolumeX size={18} className="mr-1" />
              Unmute
            </>
          ) : (
            <>
              <Volume2 size={18} className="mr-1" />
              Mute
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

export default VolumeChannel;
