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
  variant?: "hero" | "secondary";
  className?: string;
}

const VolumeChannel: React.FC<VolumeChannelProps> = ({
  label,
  icon,
  volume,
  onVolumeChange,
  onToggleMute,
  variant = "secondary",
  className,
}) => {
  const isHero = variant === "hero";
  const sliderVariant = isHero ? "performance-hero" : "performance";
  const iconSize = isHero ? 18 : 14;
  const labelClass = isHero
    ? "text-sm font-semibold text-lemon-chiffon"
    : "text-xs text-lemon-chiffon/80";
  const sliderClass = isHero ? "flex-1 min-h-0" : "h-20";

  return (
    <div className={`flex flex-col items-center gap-2 ${className ?? ""}`}>
      <div className="flex items-center gap-2">
        <span className={`text-${isHero ? "primary" : "muted-foreground"} shrink-0`}>
          {React.cloneElement(icon as React.ReactElement, { size: iconSize })}
        </span>
        <span className={labelClass}>
          {label} {Math.round(volume * 100)}%
        </span>
      </div>

      <div className={`${isHero ? "flex-1 min-h-0" : ""} w-full flex flex-col items-center gap-2`}>
        <Slider
          value={[volume]}
          min={0}
          max={1}
          step={0.05}
          variant={sliderVariant}
          orientation="vertical"
          onValueChange={([v]) => onVolumeChange(v)}
          className={sliderClass}
        />
        <Button
          variant="outline"
          size="sm"
          onClick={onToggleMute}
          className={`w-full ${isHero ? "" : "text-xs"}`}
        >
          {volume === 0 ? (
            <>
              <VolumeX size={iconSize} className="mr-1" />
              Unmute
            </>
          ) : (
            <>
              <Volume2 size={iconSize} className="mr-1" />
              Mute
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

export default VolumeChannel;
