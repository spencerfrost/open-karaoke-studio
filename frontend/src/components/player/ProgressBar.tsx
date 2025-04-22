import React from 'react';
import { usePlayer } from '../../context/PlayerContext';
import { formatTime } from '../../utils/formatters';
import vintageTheme from '../../utils/theme';

interface ProgressBarProps {
  onChange?: (value: number) => void;
  className?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  onChange,
  className = '',
}) => {
  const { state: playerState, dispatch } = usePlayer();
  const colors = vintageTheme.colors;
  
  // Calculate progress percentage
  const progressPercentage = playerState.duration 
    ? (playerState.currentTime / playerState.duration) * 100
    : 0;
  
  // Handle user seeking
  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const seekTime = Number(e.target.value);
    
    // Update progress locally
    dispatch({ type: 'SET_CURRENT_TIME', payload: seekTime });
    
    // Notify parent component
    if (onChange) {
      onChange(seekTime);
    }
  };
  
  return (
    <div className={`w-full ${className}`}>
      <div className="flex justify-between text-xs mb-1">
        <span style={{ color: `${colors.lemonChiffon}80` }}>
          {formatTime(playerState.currentTime)}
        </span>
        <span style={{ color: `${colors.lemonChiffon}80` }}>
          {formatTime(playerState.duration)}
        </span>
      </div>
      
      <div className="relative h-2">
        {/* Progress bar track */}
        <div 
          className="absolute inset-0 rounded-full overflow-hidden"
          style={{ backgroundColor: 'rgba(0,0,0,0.3)' }}
        >
          {/* Progress bar fill */}
          <div 
            className="h-full rounded-full"
            style={{ 
              width: `${progressPercentage}%`,
              background: `linear-gradient(90deg, ${colors.darkCyan} 0%, ${colors.orangePeel} 100%)`
            }}
          />
        </div>
        
        {/* Slider input (visually hidden but functional) */}
        <input
          type="range"
          min={0}
          max={playerState.duration || 100}
          value={playerState.currentTime}
          onChange={handleSeek}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          aria-label="Seek"
        />
      </div>
    </div>
  );
};

export default ProgressBar;
