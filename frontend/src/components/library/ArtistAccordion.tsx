import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Music, Users } from 'lucide-react';
import { Song } from '@/types/Song';
import { useLibraryBrowsing } from '@/hooks/useLibraryBrowsing';
import SongCard from '@/components/songs/SongCard';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

interface ArtistAccordionProps {
  searchTerm?: string;
  onSongSelect?: (song: Song) => void;
  onToggleFavorite?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
  className?: string;
}

interface ArtistSectionProps {
  artistName: string;
  songCount: number;
  isExpanded: boolean;
  onToggle: () => void;
  onSongSelect?: (song: Song) => void;
  onToggleFavorite?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
}

const ArtistSection: React.FC<ArtistSectionProps> = ({
  artistName,
  songCount,
  isExpanded,
  onToggle,
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
}) => {
  const [songsPage, setSongsPage] = useState(0);
  const PAGE_SIZE = 10;

  const { useArtistSongs } = useLibraryBrowsing();
  
  const {
    data: songsData,
    isLoading: songsLoading,
    error: songsError,
  } = useArtistSongs(artistName, {
    limit: PAGE_SIZE,
    offset: songsPage * PAGE_SIZE,
    sort: 'title',
    direction: 'asc',
  });

  const handleLoadMore = () => {
    setSongsPage(prev => prev + 1);
  };

  const handleSongUpdated = () => {
    // Song was updated, could refresh the data
    // For now, React Query should handle this automatically
  };

  return (
    <div className="border border-orange-peel rounded-lg overflow-hidden">
      {/* Artist Header */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between text-left bg-lemon-chiffon/10 text-lemon-chiffon hover:bg-opacity-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown size={20} className="text-orange-peel" />
          ) : (
            <ChevronRight size={20} className="text-orange-peel" />
          )}
          <Users size={18} className="text-orange-peel" />
          <div>
            <h3 className="font-semibold text-lg">{artistName}</h3>
            <p className="text-sm opacity-75">
              {songCount} {songCount === 1 ? 'song' : 'songs'}
            </p>
          </div>
        </div>
        <div className="px-3 py-1 rounded-full text-sm font-medium bg-orange-peel text-dark-cyan">
          {songCount}
        </div>
      </button>

      {/* Expanded Songs List */}
      {isExpanded && (
        <div className="border-t border-orange-peel">
          {songsLoading && songsPage === 0 ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : songsError ? (
            <div className="p-4 text-center text-red-500">
              Error loading songs: {songsError instanceof Error ? songsError.message : 'Unknown error'}
            </div>
          ) : (
            <div className="p-2">
              {songsData?.songs.map((song) => (
                <div key={song.id} className="mb-2">
                  <SongCard
                    song={song}
                    compact={true}
                    onToggleFavorite={onToggleFavorite}
                    onAddToQueue={onAddToQueue}
                    onSongUpdated={handleSongUpdated}
                    onClick={() => onSongSelect?.(song)}
                  />
                </div>
              ))}

              {/* Load More Button */}
              {songsData?.pagination.hasMore && (
                <div className="mt-4 text-center">
                  <Button
                    variant="outline"
                    onClick={handleLoadMore}
                    disabled={songsLoading}
                    className="border-orange-peel text-orange-peel"
                  >
                    {songsLoading ? 'Loading...' : `Load More (${songsData.pagination.total - songsData.songs.length} remaining)`}
                  </Button>
                </div>
              )}

              {/* Songs count summary */}
              {songsData && !songsLoading && (
                <div className="mt-3 pt-3 border-t border-orange-peel text-center text-sm opacity-60">
                  Showing {songsData.songs.length} of {songsData.pagination.total} songs
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ArtistAccordion: React.FC<ArtistAccordionProps> = ({
  searchTerm = '',
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
  className = '',
}) => {
  const [expandedArtists, setExpandedArtists] = useState<Set<string>>(new Set());
  const [artistsPage, setArtistsPage] = useState(0);
  const ARTISTS_PAGE_SIZE = 20;

  const { useArtists } = useLibraryBrowsing();

  const {
    data: artistsData,
    isLoading: artistsLoading,
    error: artistsError,
  } = useArtists({
    search: searchTerm,
    limit: ARTISTS_PAGE_SIZE,
    offset: artistsPage * ARTISTS_PAGE_SIZE,
  });

  const toggleArtist = (artistName: string) => {
    setExpandedArtists(prev => {
      const newSet = new Set(prev);
      if (newSet.has(artistName)) {
        newSet.delete(artistName);
      } else {
        newSet.add(artistName);
      }
      return newSet;
    });
  };

  const handleLoadMoreArtists = () => {
    setArtistsPage(prev => prev + 1);
  };

  // Group artists by first letter for better navigation
  const groupedArtists = React.useMemo(() => {
    if (!artistsData?.artists) return {};
    
    return artistsData.artists.reduce((groups, artist) => {
      const letter = artist.firstLetter;
      if (!groups[letter]) {
        groups[letter] = [];
      }
      groups[letter].push(artist);
      return groups;
    }, {} as Record<string, typeof artistsData.artists>);
  }, [artistsData]);

  if (artistsError) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <div className="text-red-500 mb-2">Error loading artists</div>
        <div className="text-sm opacity-60">
          {artistsError instanceof Error ? artistsError.message : 'Unknown error'}
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Loading State */}
      {artistsLoading && artistsPage === 0 ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : (
        <>
          {/* Artists List */}
          {Object.keys(groupedArtists).length === 0 ? (
            <div className="text-center py-12 rounded-lg bg-lemon-chiffon/10 text-lemon-chiffon">
              <Music size={48} className="mx-auto mb-4 text-orange-peel" />
              <p>
                {searchTerm 
                  ? `No artists found matching "${searchTerm}"`
                  : 'No artists found in your library'
                }
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Alphabetical sections */}
              {Object.entries(groupedArtists).map(([letter, artists]) => (
                <div key={letter}>
                  {/* Letter Header */}
                  <div className="sticky top-0 px-3 py-2 mb-3 font-bold text-lg border-b bg-dark-cyan text-orange-peel border-orange-peel z-10">
                    {letter}
                  </div>
                  
                  {/* Artists in this letter group */}
                  <div className="space-y-2">
                    {artists.map((artist) => (
                      <ArtistSection
                        key={artist.name}
                        artistName={artist.name}
                        songCount={artist.songCount}
                        isExpanded={expandedArtists.has(artist.name)}
                        onToggle={() => toggleArtist(artist.name)}
                        onSongSelect={onSongSelect}
                        onToggleFavorite={onToggleFavorite}
                        onAddToQueue={onAddToQueue}
                      />
                    ))}
                  </div>
                </div>
              ))}

              {/* Load More Artists Button */}
              {artistsData?.pagination.hasMore && (
                <div className="text-center mt-6">
                  <Button
                    variant="outline"
                    onClick={handleLoadMoreArtists}
                    disabled={artistsLoading}
                    className="px-6 py-3 border-orange-peel text-orange-peel"
                  >
                    {artistsLoading ? 'Loading...' : 'Load More Artists'}
                  </Button>
                </div>
              )}

              {/* Summary */}
              {artistsData && !artistsLoading && (
                <div className="mt-6 text-center text-sm opacity-60">
                  Showing {artistsData.artists.length} of {artistsData.pagination.total} artists
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ArtistAccordion;
