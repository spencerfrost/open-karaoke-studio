import React, { useEffect, useRef } from "react";
import { Song } from "@/types/Song";
import SongCard from "@/components/songs/SongCard";

interface SongResultsGridProps {
  songs: Song[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
}

const SongResultsGrid: React.FC<SongResultsGridProps> = ({
  songs,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  onSongSelect,
  onAddToQueue,
}) => {
  const loadingRef = useRef<HTMLDivElement>(null);

  // Infinite scroll with intersection observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );

    const currentLoadingRef = loadingRef.current;
    if (currentLoadingRef) {
      observer.observe(currentLoadingRef);
    }

    return () => {
      if (currentLoadingRef) {
        observer.unobserve(currentLoadingRef);
      }
    };
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (songs.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Song Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {songs.filter(Boolean).map((song) => (
          <SongCard
            key={song.id}
            song={song}
            onSelect={onSongSelect}
            onAddToQueue={onAddToQueue}
          />
        ))}
      </div>

      {/* Loading indicator for infinite scroll */}
      {(hasNextPage || isFetchingNextPage) && (
        <div ref={loadingRef} className="flex justify-center py-4">
          {isFetchingNextPage ? (
            <div className="flex items-center gap-2 text-orange-peel">
              <div className="animate-spin h-4 w-4 border-2 border-orange-peel border-t-transparent rounded-full"></div>
              <span className="text-sm">Loading more songs...</span>
            </div>
          ) : (
            <div className="text-lemon-chiffon/60 text-sm">
              Scroll down for more songs
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SongResultsGrid;
