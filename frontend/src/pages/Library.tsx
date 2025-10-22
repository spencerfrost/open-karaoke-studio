import React, { useState } from "react";
import { useArtists } from "@/hooks/api/useArtists";
import AppLayout from "@/components/layout/AppLayout";
import { LibrarySearchInput, SongResultsSection, ArtistResultsSection, RecentlyAddedSongs } from "@/features/library";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";

const LibraryPage: React.FC = () => {
  // State
  const [searchTerm, setSearchTerm] = useState("");

  // Song search (paginated, not infinite)
  const { useSongs } = useSongsHook();

  // Use appropriate parameters based on whether we're searching or browsing
  const songsParams = searchTerm.trim()
    ? {
        // Search parameters - the backend should handle this in useSongs
        q: searchTerm,
        limit: 24,
        offset: 0,
        sort: "relevance",
        direction: "desc",
      }
    : {
        limit: 24,
        offset: 0,
        sort_by: "date_added",
        direction: "desc",
      };

  const songsQuery = useSongs(songsParams);

  // Artist search (fetch all matching artists, up to 200)
  const { artists, isLoading: artistsLoading } = useArtists({
    search: searchTerm,
    limit: 200,
  });


  // hasSearch logic
  const hasSearch = searchTerm && searchTerm.trim().length > 0;

  return (
    <AppLayout>
      <div className="mb-6">
        {/* Search Input */}
        <div className="mb-6">
          <LibrarySearchInput
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            isLoading={songsQuery.isLoading || artistsLoading}
            placeholder="Search songs and artists..."
            className="w-full max-w-xl mx-auto"
          />
        </div>

        <div className="space-y-8">
          {!hasSearch ? (
            <RecentlyAddedSongs
              songsPerPage={12}
              maxSongs={48}
              animated={true}
            />
          ) : (
            <SongResultsSection
              songs={songsQuery.data || []}
              hasNextPage={false} // Pagination can be added later
              isFetchingNextPage={false}
              fetchNextPage={() => {}}
              searchTerm={searchTerm}
            />
          )}
          {/* Artist Results Section - Always visible for browsing */}
          <ArtistResultsSection
            artists={artists}
            searchTerm={searchTerm}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default LibraryPage;
