import React from "react";
import { formatTime } from "../../utils/formatters";

interface ProgressBarProps {
  currentTime: number;
  duration: number;
  onSeek?: (value: number) => void;
  className?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  currentTime,
  duration,
  onSeek,
  className = "",
}) => {
  const progressPercentage = duration ? (currentTime / duration) * 100 : 0;

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const seekTime = Number(e.target.value);
    if (onSeek) {
      onSeek(seekTime);
    }
  };

  return (
    <div className={`w-full ${className}`}>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-background">{formatTime(currentTime)}</span>
        <span className="text-background">{formatTime(duration)}</span>
      </div>
      <div className="relative h-2">
        <div
          className="absolute inset-0 rounded-full overflow-hidden"
          style={{ backgroundColor: "rgba(0,0,0,0.3)" }}
        >
          <div
            className={`h-full rounded-full bg-gradient-to-r from-dark-cyan to-orange-peel w-${progressPercentage}%`}
            style={{
              width: `${progressPercentage}%`,
            }}
          />
        </div>
        <input
          type="range"
          min={0}
          max={duration || 100}
          value={currentTime}
          onChange={handleSeek}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          aria-label="Seek"
        />
      </div>
    </div>
  );
};

export default ProgressBar;
