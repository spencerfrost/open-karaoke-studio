import React, { useState } from 'react';
import { useInfiniteArtists } from '@/hooks/useInfiniteLibraryBrowsing';
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll';
import ArtistSection from './ArtistSection';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { Skeleton } from '@/components/ui/skeleton';
import { Song } from '@/types/Song';
import vintageTheme from '@/utils/theme';

interface InfiniteArtistAccordionProps {
  searchTerm?: string;
  onSongSelect?: (song: Song) => void;
  onToggleFavorite?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
  className?: string;
}

const InfiniteArtistAccordion: React.FC<InfiniteArtistAccordionProps> = ({
  searchTerm = '',
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
  className = '',
}) => {
  const colors = vintageTheme.colors;
  const [expandedArtists, setExpandedArtists] = useState<Set<string>>(new Set());

  const {
    artists,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    isLoading,
    error,
  } = useInfiniteArtists(searchTerm);

  // Infinite scroll hook for artists
  const sentinelRef = useInfiniteScroll({
    loading: isFetchingNextPage,
    hasMore: hasNextPage,
    onLoadMore: fetchNextPage,
    threshold: 0.1,
    rootMargin: '200px', // Start loading when 200px away
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

  // Group artists alphabetically
  const groupedArtists = React.useMemo(() => {
    return artists.reduce((groups, artist) => {
      const letter = artist.firstLetter;
      if (!groups[letter]) {
        groups[letter] = [];
      }
      groups[letter].push(artist);
      return groups;
    }, {} as Record<string, typeof artists>);
  }, [artists]);

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-500">Error loading artists</div>
        <div className="text-sm opacity-60">{error.message}</div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded" />
          ))}
        </div>
      ) : (
        <>
          {/* Alphabetical artist sections */}
          {Object.entries(groupedArtists).map(([letter, letterArtists]) => (
            <div key={letter}>
              <div
                className="sticky top-0 px-3 py-2 mb-3 font-bold text-lg border-b"
                style={{
                  backgroundColor: colors.darkCyan,
                  color: colors.orangePeel,
                  borderColor: colors.orangePeel,
                  zIndex: 10
                }}
              >
                {letter}
              </div>

              <div className="space-y-2">
                {letterArtists.map((artist) => (
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

          {/* Intersection Observer Sentinel */}
          <div ref={sentinelRef} className="h-4">
            {isFetchingNextPage && (
              <div className="flex justify-center items-center py-4">
                <LoadingSpinner />
                <span className="ml-2 text-sm opacity-60">Loading more artists...</span>
              </div>
            )}
          </div>

          {/* End of results indicator */}
          {!hasNextPage && artists.length > 0 && (
            <div className="text-center py-4 text-sm opacity-60">
              All artists loaded ({artists.length} total)
            </div>
          )}

          {/* Empty state */}
          {!isLoading && artists.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              {searchTerm ? `No artists found for "${searchTerm}"` : 'No artists found'}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default InfiniteArtistAccordion;
