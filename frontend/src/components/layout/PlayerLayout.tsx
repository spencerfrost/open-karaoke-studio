import React, { ReactNode, useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { useSettings } from '../../context/SettingsContext';
import { usePlayer } from '../../context/PlayerContext';
import vintageTheme from '../../utils/theme';

interface PlayerLayoutProps {
  children: ReactNode;
  showControls?: boolean;
}

const PlayerLayout: React.FC<PlayerLayoutProps> = ({ 
  children, 
  showControls = true 
}) => {
  const { settings } = useSettings();
  const { state: playerState } = usePlayer();
  const [showMenu, setShowMenu] = useState(false);
  
  // Styles for the full-screen player layout
  const layoutStyles = {
    background: vintageTheme.background,
    color: vintageTheme.text.primary,
    height: '100vh',
    width: '100vw',
    overflow: 'hidden',
    position: 'relative' as const,
  };
  
  return (
    <div style={layoutStyles}>
      {/* Texture overlay for vintage feel */}
      <div style={vintageTheme.getTextureOverlay()} />
      
      {/* Sunburst pattern - only shown in certain views if desired */}
      {settings.theme.themeName === 'vintage' && (
        <div style={vintageTheme.getSunburstPattern()} />
      )}
      
      {/* Top controls bar - only visible if showControls is true */}
      {showControls && playerState.currentSong && (
        <div 
          className="absolute top-0 left-0 right-0 p-4 flex justify-between items-center z-20"
          style={{
            backgroundImage: 'linear-gradient(to bottom, rgba(0,0,0,0.7), transparent)',
          }}
        >
          <div className="flex items-center">
            {/* Song info */}
            <div>
              <h2 className="font-semibold">
                {playerState.currentSong.song.title}
              </h2>
              <p 
                className="text-sm"
                style={{ color: vintageTheme.text.secondary }}
              >
                {playerState.currentSong.song.artist}
              </p>
            </div>
          </div>
          
          {/* Menu toggle button */}
          <button 
            className="p-2 rounded-lg"
            style={{
              backgroundColor: vintageTheme.colors.darkCyan,
              color: vintageTheme.text.primary,
            }}
            onClick={() => setShowMenu(!showMenu)}
          >
            {showMenu ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </button>
        </div>
      )}
      
      {/* Main content area */}
      <div className="relative z-10 h-full">
        {children}
      </div>
    </div>
  );
};

export default PlayerLayout;
