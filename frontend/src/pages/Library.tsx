import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useInfiniteArtists } from "@/hooks/api/useInfiniteLibraryBrowsing";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";
import AppLayout from "@/components/layout/AppLayout";
import { LibrarySearchInput, SongResultsSection, ArtistResultsSection, RecentlyAddedSongs } from "@/features/library";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";

const LibraryPage: React.FC = () => {
  // State
  const [searchTerm, setSearchTerm] = useState("");
  const [searchParams] = useSearchParams();
  const expandArtist = searchParams.get("expandArtist");

  // Clear search term if we're expanding an artist (don't filter by search)
  const effectiveSearchTerm = expandArtist ? "" : searchTerm;

  // Song search (paginated, not infinite)
  const { useSongs } = useSongsHook();

  // Use appropriate parameters based on whether we're searching or browsing
  const songsParams = effectiveSearchTerm.trim()
    ? {
        // Search parameters - the backend should handle this in useSongs
        q: effectiveSearchTerm,
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

  // Artist search with infinite scrolling to fetch ALL artists
  const {
    artists,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    isLoading: artistsLoading,
  } = useInfiniteArtists(effectiveSearchTerm, 200);

  // Infinite scroll for artists
  const sentinelRef = useInfiniteScroll({
    loading: isFetchingNextPage,
    hasMore: hasNextPage,
    onLoadMore: fetchNextPage,
    threshold: 0.1,
    rootMargin: "100px",
  });

  // When expandArtist is set, trigger loading all artists until we find them
  React.useEffect(() => {
    if (expandArtist && !artists.find(a => a.name === expandArtist) && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [expandArtist, artists, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // hasSearch logic
  const hasSearch = effectiveSearchTerm && effectiveSearchTerm.trim().length > 0;

  return (
    <AppLayout>
      <SessionInfoDisplay variant="code" colorScheme="page" trigger="hover" visibility="host-only" className="absolute top-2 right-3 z-30" />
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
            hasNextPage={hasNextPage}
            isFetchingNextPage={isFetchingNextPage}
            fetchNextPage={fetchNextPage}
            sentinelRef={sentinelRef}
            expandArtist={expandArtist}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default LibraryPage;
