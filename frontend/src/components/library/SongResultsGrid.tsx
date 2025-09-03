import React from "react";
import { Song } from "@/types/Song";
import { SongCard } from "@/components/songs/song-card";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface SongResultsGridProps {
  songs: Song[];
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  fetchNextPage?: () => void;
  onSongSelect?: (song: Song) => void;
}

const SongResultsGrid: React.FC<SongResultsGridProps> = ({ 
  songs,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  onSongSelect,
}) => {
  if (songs.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Song Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {songs.filter(Boolean).map((song) => (
          <SongCard 
            key={song.id} 
            song={song}
            onPlay={onSongSelect}
          />
        ))}
      </div>

      {/* Load More Button */}
      {hasNextPage && (
        <div className="flex justify-center mt-6">
          <Button
            onClick={fetchNextPage}
            disabled={isFetchingNextPage}
            variant="outline"
            className="px-8"
          >
            {isFetchingNextPage ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading...
              </>
            ) : (
              "Load More Songs"
            )}
          </Button>
        </div>
      )}
    </div>
  );
};

export default SongResultsGrid;
