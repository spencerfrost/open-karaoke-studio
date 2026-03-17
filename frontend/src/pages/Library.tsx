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
        className="fixed top-2 right-3 z-30"
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

        <div className="space-y-8">
          {!hasSearch ? (
            <Tabs defaultValue="recently-added">
              <TabsList className="mb-4">
                <TabsTrigger value="recently-added">Recently Added</TabsTrigger>
                <TabsTrigger value="recently-sang">Recently Sang</TabsTrigger>
              </TabsList>
              <TabsContent value="recently-added">
                <RecentlyAddedSongs
                  songsPerPage={12}
                  maxSongs={48}
                  animated={true}
                />
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
              fetchNextPage={() => {}}
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
