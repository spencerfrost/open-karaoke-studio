import React from "react";
import { Song } from "@/types/Song";
import { SongCard } from "@/components/songs/song-card";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";
import { usePagination } from "./usePagination";

interface RecentlyAddedSongsProps {
  songsPerPage?: number;
  maxSongs?: number;
  animated?: boolean; // Toggle between carousel animation and simple pagination
}

const RecentlyAddedSongs: React.FC<RecentlyAddedSongsProps> = ({
  songsPerPage = 12,
  maxSongs = 48,
  animated = true,
}) => {
  const { useSongs } = useSongsHook();
  const { 
    data: allSongs, 
    isLoading 
  } = useSongs({
    limit: maxSongs,
    sort_by: "date_added",
    direction: "desc",
  });

  const songs = allSongs || [];

  const { pagination, actions, currentPageItems } = usePagination({
    itemsPerPage: songsPerPage,
    totalItems: songs.length,
  });

  const currentPageSongs = currentPageItems(songs);

  // Don't render if loading or no songs
  if (isLoading || songs.length === 0) {
    return null;
  }

  return (
    <div className="mb-8 w-full">
      {/* Section Header with Pagination Controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-xl font-semibold text-orange-peel">
            Recently Added
          </span>
          <span className="text-sm text-lemon-chiffon/60">
            {songs.length} songs
          </span>
        </div>
        
        {/* Pagination Controls */}
        {pagination.totalPages > 1 && (
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={actions.previousPage}
              disabled={!pagination.hasPreviousPage}
              className="text-orange-peel hover:bg-orange-peel/20 disabled:opacity-30"
            >
              <ChevronLeft size={16} />
              Previous
            </Button>
            
            <span className="text-sm text-lemon-chiffon/80 px-2">
              {pagination.currentPage + 1} of {pagination.totalPages}
            </span>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={actions.nextPage}
              disabled={!pagination.hasNextPage}
              className="text-orange-peel hover:bg-orange-peel/20 disabled:opacity-30"
            >
              Next
              <ChevronRight size={16} />
            </Button>
          </div>
        )}
      </div>

      {/* Conditional Rendering: Animated Carousel vs Simple Grid */}
      {animated ? (
        /* Horizontal Sliding Carousel Container */
        <div className="relative overflow-hidden min-h-[400px]">
          <div 
            className="flex transition-transform duration-300 ease-in-out"
            style={{
              transform: `translateX(-${pagination.currentPage * (100 / pagination.totalPages)}%)`,
              width: `${pagination.totalPages * 100}%`
            }}
          >
            {Array.from({ length: pagination.totalPages }, (_, pageIndex) => {
              const pageStartIndex = pageIndex * songsPerPage;
              const pageSongs = songs.slice(pageStartIndex, pageStartIndex + songsPerPage);
              
              return (
                <div 
                  key={pageIndex}
                  className="w-full flex-shrink-0"
                  style={{ width: `${100 / pagination.totalPages}%` }}
                >
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    {pageSongs.map((song: Song) => (
                      <SongCard
                        key={`${song.id}-${pageIndex}`}
                        song={song}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* Simple Paginated Grid */
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {currentPageSongs.map((song: Song) => (
            <SongCard
              key={song.id}
              song={song}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default RecentlyAddedSongs;