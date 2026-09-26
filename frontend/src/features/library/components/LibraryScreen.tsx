/**
 * LibraryScreen - browse and search the library, with no opinion on chrome.
 *
 * Extracted from the Library page so the stage can render the same thing as a
 * screen inside its shell. Everything that used to come from the URL arrives as
 * a prop; `pages/Library.tsx` is now just the router adapter that reads it.
 */

import React, { useState } from "react";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import LibrarySearchInput from "./LibrarySearchInput";
import SongResultsSection from "./SongResultsSection";
import ArtistResultsSection from "./ArtistResultsSection";
import RecentlyAddedSongs from "./RecentlyAddedSongs/RecentlyAddedSongs";
import RecentlySang from "./RecentlySang/RecentlySang";

interface LibraryScreenProps {
  /** Artist to auto-expand on arrival, from a deep link or the stage's player. */
  expandArtist?: string | null;
  /** Search field placeholder — the TV asks a different question than the phone. */
  searchPlaceholder?: string;
}

const LibraryScreen: React.FC<LibraryScreenProps> = ({
  expandArtist = null,
  searchPlaceholder = "Search songs and artists...",
}) => {
  const [searchTerm, setSearchTerm] = useState("");

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
    <div className="mb-6">
      {/* Search Input */}
      <div className="my-4 sm:my-12">
        <LibrarySearchInput
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          isLoading={songsQuery.isLoading}
          placeholder={searchPlaceholder}
          className="w-full max-w-xl mx-auto"
        />
      </div>

      <div>
        {!hasSearch ? (
          <Tabs defaultValue="recently-added">
            <TabsList className="mb-4" variant="line">
              <TabsTrigger
                className="text-xl font-semibold text-primary/80 hover:text-primary"
                value="recently-added"
              >
                Recently Added
              </TabsTrigger>
              <TabsTrigger
                className="text-xl font-semibold text-primary/80 hover:text-primary"
                value="recently-sang"
              >
                Recently Sang
              </TabsTrigger>
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
  );
};

export default LibraryScreen;
