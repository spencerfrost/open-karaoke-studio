/**
 * LyricsDisplay - Pure component for rendering synced/unsynced lyrics
 * Handles scrolling, highlighting, and different sizes
 * Optimized for performance with smooth scrolling and proper accessibility
 */

import React, { memo, useState } from 'react';
import { Lrc } from 'react-lrc';
import { Button } from '@/components/ui/button';
import { Search } from 'lucide-react';
import LyricsFetchDialog from '@/components/LyricsFetchDialog';
import { useSongs } from '@/hooks/api/useSongs';
import { toast } from 'sonner';
import type { LyricsResult } from '@/components/LyricsFetchDialog';
import type { Song } from '@/types/Song';

interface LyricsDisplayProps {
  lyrics: string;
  isSync: boolean;
  currentTime: number;        // in seconds
  lyricsSize: 'small' | 'medium' | 'large';
  lyricsOffset: number;       // in milliseconds
  className?: string;
  'aria-label'?: string;
  // Optional song data for lyrics search
  songId?: string;
  songTitle?: string;
  songArtist?: string;
  songAlbum?: string;
  songDuration?: number;      // in seconds
}

const LyricsDisplay: React.FC<LyricsDisplayProps> = memo(({
  lyrics,
  isSync,
  currentTime,
  lyricsSize,
  lyricsOffset,
  className = "",
  'aria-label': ariaLabel = "Song lyrics",
  songId,
  songTitle,
  songArtist,
  songAlbum,
  songDuration,
}) => {
  const [isLyricsDialogOpen, setIsLyricsDialogOpen] = useState(false);
  const { useUpdateSong } = useSongs();
  const updateSongMutation = useUpdateSong();

  const handleLyricsSearch = () => {
    if (!songId || !songTitle || !songArtist) {
      toast.error("Missing song information for lyrics search");
      return;
    }
    setIsLyricsDialogOpen(true);
  };

  const handleLyricsSelected = (lyricsResult: LyricsResult) => {
    if (!songId) {
      toast.error("Cannot update song: missing song ID");
      return;
    }

    updateSongMutation.mutate({
      id: songId,
      plainLyrics: lyricsResult.plainLyrics,
      syncedLyrics: lyricsResult.syncedLyrics,
    }, {
      onSuccess: () => {
        toast.success("Lyrics updated successfully!");
        setIsLyricsDialogOpen(false);
      },
      onError: (error) => {
        toast.error(`Failed to update lyrics: ${error.message}`);
      }
    });
  };
  const lyricsSizeClass =
    lyricsSize === "small"
      ? "text-base"
      : lyricsSize === "large"
        ? "text-3xl"
        : "text-xl";

  const activeLyricsSizeClass =
    lyricsSize === "small"
      ? "text-lg"
      : lyricsSize === "large"
        ? "text-4xl"
        : "text-2xl";

  if (isSync) {
    return (
      <Lrc
        lrc={lyrics}
        currentMillisecond={(currentTime * 1000) + lyricsOffset}
        verticalSpace={true}
        lineRenderer={({ active, line }) => (
          <div
            className={`py-2 px-2 transition-all duration-500 text-center ${
              active
                ? `text-background font-bold ${activeLyricsSizeClass} text-shadow`
                : `text-background/50 opacity-70 ${lyricsSizeClass}`
            }`}
            role={active ? "status" : undefined}
            aria-live={active ? "polite" : undefined}
          >
            {line.content}
          </div>
        )}
        className={`lrc h-full w-full overflow-y-scroll scrollbar-hide pb-20 mask-image-fade-bottom ${className}`}
        role="region"
        aria-label={ariaLabel}
      />
    );
  }

  return (
    <div 
      className={`w-full h-full overflow-y-auto scrollbar-hide ${className}`}
      role="region"
      aria-label={ariaLabel}
    >
      {lyrics ? (
        <div
          className={`text-2xl font-semibold text-background whitespace-pre-line text-center ${lyricsSizeClass}`}
          role="document"
        >
          {lyrics}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-full text-center p-8" role="status">
          <div className="text-gray-400 text-lg mb-2">
            🎵 No lyrics available
          </div>
          <div className="text-gray-500 text-sm mb-4">
            Enjoy the music and sing along if you know the words!
          </div>
          {songId && songTitle && songArtist && (
            <Button
              onClick={handleLyricsSearch}
              variant="outline"
              size="sm"
              className="mt-2"
            >
              <Search className="w-4 h-4 mr-2" />
              Search for Lyrics
            </Button>
          )}
        </div>
      )}

      {/* Lyrics Search Dialog */}
      {songId && songTitle && songArtist && (
        <LyricsFetchDialog
          isOpen={isLyricsDialogOpen}
          onClose={() => setIsLyricsDialogOpen(false)}
          song={{
            id: songId,
            title: songTitle,
            artist: songArtist,
            album: songAlbum || '',
            duration: songDuration,
          } as Song}
          onLyricsSelected={handleLyricsSelected}
        />
      )}
    </div>
  );
});

LyricsDisplay.displayName = 'LyricsDisplay';

export default LyricsDisplay;