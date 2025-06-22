import React from "react";
import { Song } from "@/types/Song";
import { FuzzySearchResult } from "@/hooks/useInfiniteFuzzySearch";
import SongResultsSection from "./SongResultsSection";
import ArtistResultsSection from "./ArtistResultsSection";
import RecentlyAddedRow from "./RecentlyAddedRow";
import { useSongs as useSongsHook } from "@/hooks/useSongs";
import { useEffect, useState } from "react";

interface LibraryContentProps {
  searchResults: FuzzySearchResult;
  onSongSelect: (song: Song) => void;
  onToggleFavorite: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  searchTerm: string;
}

const RECENT_LIMIT = 12;

const LibraryContent: React.FC<LibraryContentProps> = ({
  searchResults,
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
  searchTerm,
}) => {
  const { songs, artists, songsPagination, artistsPagination } = searchResults;
  const { useSongs } = useSongsHook();
  const [recentSongs, setRecentSongs] = useState<Song[]>([]);

  // Fetch recent songs (sorted by date_added desc, limit RECENT_LIMIT)
  const { data: allSongs, isLoading: loadingRecent } = useSongs({
    select: (data: Song[]) =>
      [...data]
        .sort(
          (a, b) =>
            new Date(b.dateAdded).getTime() - new Date(a.dateAdded).getTime()
        )
        .slice(0, RECENT_LIMIT),
  });

  useEffect(() => {
    if (allSongs) setRecentSongs(allSongs);
  }, [allSongs]);

  return (
    <div className="space-y-8">
      {/* Recently Added Row - Always visible */}
      <RecentlyAddedRow
        songs={recentSongs}
        onSongSelect={onSongSelect}
        onToggleFavorite={onToggleFavorite}
        onAddToQueue={onAddToQueue}
      />

      {/* Song Results Section - Shows prominently when searching */}
      <SongResultsSection
        songs={songs}
        hasNextPage={songsPagination.hasNextPage}
        isFetchingNextPage={songsPagination.isFetchingNextPage}
        fetchNextPage={songsPagination.fetchNextPage}
        onSongSelect={onSongSelect}
        onToggleFavorite={onToggleFavorite}
        onAddToQueue={onAddToQueue}
        searchTerm={searchTerm}
      />

      {/* Artist Results Section - Always visible for browsing */}
      <ArtistResultsSection
        artists={artists}
        hasNextPage={artistsPagination.hasNextPage}
        isFetchingNextPage={artistsPagination.isFetchingNextPage}
        fetchNextPage={artistsPagination.fetchNextPage}
        onSongSelect={onSongSelect}
        onToggleFavorite={onToggleFavorite}
        onAddToQueue={onAddToQueue}
        searchTerm={searchTerm}
      />
    </div>
  );
};

export default LibraryContent;
