import React, { useState } from "react";
import SongCard from "@/components/songs/SongCard";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";
import { Song } from "@/types/Song";
import { Button } from "@/components/ui/button";
import { ChevronRight } from "lucide-react";

interface RecentlyAddedSongsProps {
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  limit?: number;
}

const RecentlyAddedSongs: React.FC<RecentlyAddedSongsProps> = ({
  onSongSelect,
  onAddToQueue,
  limit: songsPerPage = 6,
}) => {
  const [currentPage, setCurrentPage] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [displayPage, setDisplayPage] = useState(0); // What we actually show during animation
  
  // Fetch a larger number of songs to support pagination
  const totalSongsToFetch = Math.max(24, songsPerPage * 4);
  
  const { useSongs } = useSongsHook();
  const { data: allSongs, isLoading } = useSongs({
    limit: totalSongsToFetch,
    sort_by: "date_added",
    direction: "desc",
  });

  const songs = allSongs || [];
  
  // Calculate current page songs (use displayPage during animation)
  const startIndex = displayPage * songsPerPage;
  const currentPageSongs = songs.slice(startIndex, startIndex + songsPerPage);
  
  // Calculate next page songs for animation
  const nextStartIndex = (displayPage + 1) * songsPerPage;
  const nextPageSongs = songs.slice(nextStartIndex, nextStartIndex + songsPerPage);
  
  // Check if there are more pages available
  const hasNextPage = currentPage * songsPerPage + songsPerPage < songs.length;

  const handleNext = () => {
    if (hasNextPage && !isAnimating) {
      setIsAnimating(true);
      
      // After animation completes, update the actual page
      setTimeout(() => {
        setCurrentPage(prev => prev + 1);
        setDisplayPage(prev => prev + 1);
        setIsAnimating(false);
      }, 300);
    }
  };

  // TODO: Improve empty and loading states
  if (isLoading || !songs || songs.length === 0) return null;

  return (
    <div className="mb-8 w-full">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xl font-semibold text-orange-peel">
          Recently Added
        </span>
        {hasNextPage && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleNext}
            disabled={isAnimating}
            title="Show next 6 songs"
            className="text-orange-peel hover:bg-orange-peel/20 disabled:opacity-50"
          >
            <ChevronRight size={20} />
          </Button>
        )}
      </div>
      <div className="relative overflow-hidden">
        {/* Current page content - slides out to the left */}
        <div 
          className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 transition-all duration-300 ease-in-out ${
            isAnimating ? '-translate-x-full opacity-0' : 'translate-x-0 opacity-100'
          }`}
        >
          {currentPageSongs.map((song: Song) => (
            <SongCard
              key={`${song.id}-${displayPage}`}
              song={song}
              onSelect={onSongSelect}
              onAddToQueue={onAddToQueue}
            />
          ))}
        </div>
        
        {/* Next page content - slides in from the right during animation */}
        {isAnimating && nextPageSongs.length > 0 && (
          <div 
            className={`absolute top-0 left-0 w-full grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 transition-all duration-300 ease-in-out ${
              isAnimating ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
            }`}
          >
            {nextPageSongs.map((song: Song) => (
              <SongCard
                key={`${song.id}-${displayPage + 1}`}
                song={song}
                onSelect={onSongSelect}
                onAddToQueue={onAddToQueue}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RecentlyAddedSongs;
