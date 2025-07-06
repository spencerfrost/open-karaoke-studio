import React from "react";

interface ProgressBarProps {
  currentTime: number;
  duration_ms: number;
  onSeek?: (value: number) => void;
  className?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  currentTime,
  duration_ms,
  onSeek,
  className = "",
}) => {
  const progressPercentage = duration_ms
    ? (currentTime / (duration_ms / 1000)) * 100
    : 0;

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const seekTime = Number(e.target.value);
    if (onSeek) {
      onSeek(seekTime);
    }
  };

  return (
    <div className={`w-full ${className}`}>
      <div className="relative h-2">
        <div className="absolute inset-0 overflow-hidden bg-black/30">
          <div
            className={`h-full rounded-full bg-gradient-to-r from-dark-cyan to-orange-peel px-1`}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        <input
          type="range"
          min={0}
          max={duration_ms || 100}
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
