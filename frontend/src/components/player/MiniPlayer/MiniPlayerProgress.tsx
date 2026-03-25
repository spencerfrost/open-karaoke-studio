/**
 * MiniPlayerProgress - Compact progress bar for mini-player
 */

import React from "react";

interface MiniPlayerProgressProps {
  currentTime: number; // seconds
  duration: number; // seconds
  className?: string;
}

const MiniPlayerProgress: React.FC<MiniPlayerProgressProps> = ({
  currentTime,
  duration,
  className = "",
}) => {
  const progressPercentage = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      className={`w-full h-1 bg-white/20 rounded-full overflow-hidden ${className}`}
    >
      <div
        className="h-full bg-gradient-to-r from-dark-cyan to-orange-peel transition-all duration-300"
        style={{ width: `${progressPercentage}%` }}
      />
    </div>
  );
};

export default MiniPlayerProgress;
