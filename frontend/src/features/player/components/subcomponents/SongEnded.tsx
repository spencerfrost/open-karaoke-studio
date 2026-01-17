/**
 * SongEnded - Content displayed when a song finishes playing and queue has more songs
 * 
 * Shows the completed song title/artist and the next song from the queue.
 * Replaces the lyrics display when the song ends and queue continues.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Music, Library } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSongs } from '@/hooks/api/useSongs';
import type { Song } from '@/types/Song';
import type { KaraokeQueueItemWithSong } from '@/types/KaraokeQueue';

interface SongEndedProps {
  /** The song that just finished */
  currentSong: Song;
  /** The next song in the queue */
  nextQueueItem?: KaraokeQueueItemWithSong;
  /** Optional class name */
  className?: string;
}

export const SongEnded: React.FC<SongEndedProps> = ({
  currentSong,
  nextQueueItem,
  className = '',
}) => {
  const navigate = useNavigate();
  const { getArtworkUrl } = useSongs();
  
  const nextSong = nextQueueItem?.song;
  const nextArtworkUrl = nextSong ? getArtworkUrl(nextSong, 'medium') : null;

  return (
    <div className={`flex items-center justify-center w-full h-full ${className}`}>
      <div className="flex flex-col items-center gap-8 p-6 max-w-2xl w-full">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white mb-2">
            Song Complete! 🎤
          </h2>
          <p className="text-white/60">
            Good job!
          </p>
        </div>

        {/* Last song section */}
        <div className="w-full border-t border-white/10 pt-6">
          <p className="text-sm text-white/60 mb-3">
            Just finished singing:
          </p>
          <div className="flex gap-4 items-start">
            {/* Artwork */}
            <div className="flex-shrink-0 w-20 h-20 rounded-lg bg-black/60 flex items-center justify-center overflow-hidden">
              {currentSong.coverArt ? (
                <img
                  src={getArtworkUrl(currentSong, 'small') || undefined}
                  alt={currentSong.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <Music size={32} className="text-cyan-700" />
              )}
            </div>
            
            {/* Song info */}
            <div className="flex-1 min-w-0">
              <h3 className="text-white font-semibold truncate">
                {currentSong.title}
              </h3>
              <p className="text-white/60 text-sm truncate">
                {currentSong.artist}
              </p>
            </div>
          </div>
        </div>

        {/* Next song section */}
        {nextSong && (
          <div className="w-full border-t border-white/10 pt-6">
            <p className="text-sm text-white/60 mb-3">
              Up next:
            </p>
            <div className="flex gap-4 items-start">
              {/* Artwork */}
              <div className="flex-shrink-0 w-20 h-20 rounded-lg bg-black/60 flex items-center justify-center overflow-hidden">
                {nextArtworkUrl ? (
                  <img
                    src={nextArtworkUrl}
                    alt={nextSong.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <Music size={32} className="text-cyan-700" />
                )}
              </div>
              
              {/* Song info */}
              <div className="flex-1 min-w-0">
                <h3 className="text-white font-semibold truncate">
                  {nextSong.title}
                </h3>
                <p className="text-white/60 text-sm truncate">
                  {nextSong.artist}
                </p>
                {nextQueueItem?.singer && (
                  <p className="text-white/40 text-xs mt-1">
                    Singing: {nextQueueItem.singer}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Browse Library Button */}
        <div className="flex items-center gap-4 mt-4 w-full justify-center">
          <Button
            variant="outline"
            size="lg"
            onClick={() => navigate('/library')}
            className="bg-black/50 hover:bg-black/70 border-white/30 hover:border-white/50 text-white gap-2"
          >
            <Library className="w-5 h-5" />
            Browse Library
          </Button>
        </div>
      </div>
    </div>
  );
};

export default SongEnded;
