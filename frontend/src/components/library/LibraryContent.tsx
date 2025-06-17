import React from 'react';
import { Song } from '@/types/Song';
import { FuzzySearchResult } from '@/hooks/useInfiniteFuzzySearch';
import SongResultsSection from './SongResultsSection';
import ArtistResultsSection from './ArtistResultsSection';

interface LibraryContentProps {
  searchResults: FuzzySearchResult;
  onSongSelect: (song: Song) => void;
  onToggleFavorite: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  searchTerm: string;
}

const LibraryContent: React.FC<LibraryContentProps> = ({
  searchResults,
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
  searchTerm,
}) => {
  const { songs, artists, songsPagination, artistsPagination } = searchResults;

  return (
    <div className="space-y-8">
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
