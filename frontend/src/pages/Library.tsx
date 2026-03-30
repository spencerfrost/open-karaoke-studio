import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import {
  LibrarySearchInput,
  SongResultsSection,
  ArtistResultsSection,
  RecentlyAddedSongs,
  RecentlySang,
} from "@/features/library";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

const LibraryPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [searchParams] = useSearchParams();
  const expandArtist = searchParams.get("expandArtist");

  // Clear search term if we're expanding an artist (don't filter by search)
  const effectiveSearchTerm = expandArtist ? "" : searchTerm;

  // Song search (paginated, not infinite)
  const { useSongs } = useSongsHook();

  const songsParams = effectiveSearchTerm.trim()
    ? {
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

  const hasSearch =
    effectiveSearchTerm && effectiveSearchTerm.trim().length > 0;

  return (
    <AppLayout>
      <SessionInfoDisplay
        variant="qr"
        colorScheme="page"
        trigger="hover"
        visibility="host-only"
        className="absolute top-2 right-3 z-30"
      />
      <div className="mb-6">
        {/* Search Input */}
        <div className="my-4 sm:my-12">
          <LibrarySearchInput
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            isLoading={songsQuery.isLoading}
            placeholder="Search songs and artists..."
            className="w-full max-w-xl mx-auto"
          />
        </div>

        <div>
          {!hasSearch ? (
            <Tabs defaultValue="recently-added">
              <TabsList className="mb-4" variant="line">
                <TabsTrigger className="text-xl font-semibold text-orange-peel/80 hover:text-orange-peel" value="recently-added">Recently Added</TabsTrigger>
                <TabsTrigger className="text-xl font-semibold text-orange-peel/80 hover:text-orange-peel" value="recently-sang">Recently Sang</TabsTrigger>
              </TabsList>
              <TabsContent value="recently-added">
                <RecentlyAddedSongs maxSongs={48} />
              </TabsContent>
              <TabsContent value="recently-sang">
                <RecentlySang />
              </TabsContent>
            </Tabs>
          ) : (
            <SongResultsSection
              songs={songsQuery.data || []}
              hasNextPage={false}
              isFetchingNextPage={false}
              fetchNextPage={() => { }}
              searchTerm={searchTerm}
            />
          )}
          {/* Artist Results Section - owns its own data fetching */}
          <ArtistResultsSection
            searchTerm={searchTerm}
            expandArtist={expandArtist}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default LibraryPage;
