import React from 'react';
import { ChevronDown, ChevronRight, Users } from 'lucide-react';
import { Song } from '@/types/Song';
import { useInfiniteArtistSongs } from '@/hooks/useInfiniteLibraryBrowsing';
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll';
import HorizontalSongCard from '@/components/songs/HorizontalSongCard';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { Skeleton } from '@/components/ui/skeleton';

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
  const {
    songs,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    isLoading,
    error,
  } = useInfiniteArtistSongs(artistName);

  // Infinite scroll hook for songs within this artist
  const sentinelRef = useInfiniteScroll({
    loading: isFetchingNextPage,
    hasMore: hasNextPage,
    onLoadMore: fetchNextPage,
    threshold: 0.1,
    rootMargin: '100px',
  });

  return (
    <div className="border border-orange-peel rounded-lg overflow-hidden">
      {/* Artist Header */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-opacity-50 transition-colors bg-lemon-chiffon/10 text-lemon-chiffon"
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
          {isLoading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : error ? (
            <div className="p-4 text-center text-red-500">
              Error loading songs: {error.message}
            </div>
          ) : (
            <div className="p-2 max-h-80 overflow-y-auto">
              {songs.map((song) => (
                <div key={song.id} className="mb-2">
                  <HorizontalSongCard
                    song={song}
                    onSongSelect={onSongSelect}
                    onToggleFavorite={onToggleFavorite}
                    onAddToQueue={onAddToQueue}
                  />
                </div>
              ))}

              {/* Intersection Observer Sentinel */}
              <div ref={sentinelRef} className="h-4">
                {isFetchingNextPage && (
                  <div className="flex justify-center items-center py-2">
                    <LoadingSpinner size={16} />
                    <span className="ml-2 text-sm opacity-60">Loading more songs...</span>
                  </div>
                )}
              </div>

              {/* End of results indicator */}
              {!hasNextPage && songs.length > 0 && (
                <div className="text-center py-2 text-sm opacity-60">
                  All songs loaded ({songs.length} total)
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ArtistSection;
