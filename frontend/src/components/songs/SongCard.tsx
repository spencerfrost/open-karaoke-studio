import React from 'react';
import { Music, Heart, Play } from 'lucide-react';
import { Song } from '../../types/Song';
import { formatTime } from '../../utils/formatters';
import vintageTheme from '../../utils/theme';

interface SongCardProps {
  song: Song;
  onPlay: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  onToggleFavorite: (song: Song) => void;
  compact?: boolean; // For list view
}

const SongCard: React.FC<SongCardProps> = ({
  song,
  onPlay,
  onAddToQueue,
  onToggleFavorite,
  compact = false,
}) => {
  const colors = vintageTheme.colors;
  
  // Vintage card style
  const cardStyle = {
    backgroundColor: colors.lemonChiffon,
    color: colors.russet,
    boxShadow: `0 4px 6px rgba(0, 0, 0, 0.2), inset 0 0 0 1px ${colors.orangePeel}`,
    position: 'relative' as const,
    overflow: 'hidden' as const,
  };
  
  // Button style
  const primaryButtonStyle = {
    backgroundColor: colors.darkCyan,
    color: colors.lemonChiffon,
    border: `1px solid ${colors.lemonChiffon}`,
    transition: 'all 0.2s ease',
  };
  
  // Render different layouts based on compact prop
  if (compact) {
    // List view (compact)
    return (
      <div
        className="rounded-lg p-3 flex items-center"
        style={cardStyle}
      >
        <div
          className="h-12 w-12 rounded-md flex items-center justify-center mr-3"
          style={{ backgroundColor: `${colors.orangePeel}20` }}
        >
          {song.coverArt ? (
            <img
              src={song.coverArt}
              alt={song.title}
              className="h-full w-full object-cover rounded-md"
            />
          ) : (
            <Music size={24} style={{ color: colors.darkCyan }} />
          )}
        </div>
        
        <div className="flex-1">
          <h3 className="font-medium">{song.title}</h3>
          <p className="text-sm opacity-75">{song.artist}</p>
        </div>
        
        <div className="text-right">
          <div className="text-sm opacity-60">
            {formatTime(song.duration)}
          </div>
          <div className="mt-1">
            {song.status === 'processing' && (
              <span style={{ color: colors.rust }} className="text-xs">
                Processing...
              </span>
            )}
            {song.status === 'queued' && (
              <span style={{ color: colors.orangePeel }} className="text-xs">
                Queued
              </span>
            )}
            {song.status === 'processed' && (
              <button
                className="px-2 py-1 rounded text-xs"
                style={primaryButtonStyle}
                onClick={() => onAddToQueue(song)}
              >
                Sing
              </button>
            )}
          </div>
        </div>
        
        <button
          className="ml-2"
          onClick={() => onToggleFavorite(song)}
          aria-label={song.favorite ? 'Remove from favorites' : 'Add to favorites'}
        >
          <Heart
            fill={song.favorite ? colors.orangePeel : 'none'}
            style={{ color: colors.orangePeel }}
            className="h-5 w-5"
          />
        </button>
      </div>
    );
  }
  
  // Grid view (default)
  return (
    <div className="rounded-lg overflow-hidden shadow-md" style={cardStyle}>
      <div
        className="h-40 flex items-center justify-center relative"
        style={{ backgroundColor: `${colors.orangePeel}20` }}
      >
        {song.coverArt ? (
          <img
            src={song.coverArt}
            alt={song.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <Music size={64} style={{ color: colors.darkCyan }} />
        )}
        
        {/* Play button overlay */}
        {song.status === 'processed' && (
          <button
            className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30 opacity-0 hover:opacity-100 transition-opacity"
            onClick={() => onPlay(song)}
            aria-label="Play song"
          >
            <div
              className="h-12 w-12 rounded-full flex items-center justify-center"
              style={{ backgroundColor: colors.darkCyan }}
            >
              <Play
                size={24}
                className="text-white"
                style={{ marginLeft: '2px' }}
              />
            </div>
          </button>
        )}
      </div>
      
      <div className="p-3">
        <div className="flex justify-between items-start">
          <h3 className="font-medium truncate">{song.title}</h3>
          <button
            onClick={() => onToggleFavorite(song)}
            aria-label={song.favorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Heart
              fill={song.favorite ? colors.orangePeel : 'none'}
              style={{ color: colors.orangePeel }}
              className="h-5 w-5 flex-shrink-0"
            />
          </button>
        </div>
        
        <p className="text-sm opacity-75">{song.artist}</p>
        
        <div className="flex justify-between items-center mt-2 text-xs">
          <span className="opacity-60">{formatTime(song.duration)}</span>
          
          {song.status === 'processing' && (
            <span style={{ color: colors.rust }}>Processing...</span>
          )}
          {song.status === 'queued' && (
            <span style={{ color: colors.orangePeel }}>Queued</span>
          )}
          {song.status === 'processed' && (
            <button
              className="px-2 py-1 rounded text-xs"
              style={primaryButtonStyle}
              onClick={() => onAddToQueue(song)}
            >
              Sing
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SongCard;
