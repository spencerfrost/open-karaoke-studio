import React, { useState } from "react";
import { useArtists } from "@/hooks/api/useArtists";
import { Filter, Music } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import LibrarySearchInput from "../components/library/LibrarySearchInput";
import SongResultsSection from "../components/library/SongResultsSection";
import ArtistResultsSection from "../components/library/ArtistResultsSection";
import RecentlyAddedSongs from "../components/library/RecentlyAddedSongs";
import { Song } from "@/types/Song";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";

const LibraryPage: React.FC = () => {
  const navigate = useNavigate();

  // State
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  // Song search (paginated, not infinite)
  const { useSongs } = useSongsHook();
  const songsQuery = useSongs(
    searchTerm.trim()
      ? {
          q: searchTerm,
          limit: 24,
          offset: 0,
          sort_by: "relevance",
          direction: "desc",
        }
      : { limit: 24, offset: 0, sort_by: "date_added", direction: "desc" }
  );

  // Artist search (fetch all matching artists, up to 200)
  const {
    artists,
    isLoading: artistsLoading,
  } = useArtists({ search: searchTerm, limit: 200 });

  // Handlers
  const handleSongSelect = (song: Song) => {
    navigate(`/player/${song.id}`);
  };

  const handleAddToQueue = (song: Song) => {
    navigate("/queue", { state: { songId: song.id } });
  };

  // hasSearch logic
  const hasSearch = searchTerm && searchTerm.trim().length > 0;

  return (
    <AppLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold mb-6 text-orange-peel">
          Song Library
        </h1>

        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Music size={20} className="text-orange-peel" />
              <span className="text-lemon-chiffon">
                {searchTerm ? "Search Results" : "Browse Library"}
              </span>
            </div>
          </div>

          <Button
            variant="outline"
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            className="border-orange-peel text-orange-peel"
          >
            <Filter size={16} className="mr-2" />
            Advanced Filters
          </Button>
        </div>

        {/* Search Input */}
        <div className="mb-6">
          <LibrarySearchInput
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            isLoading={songsQuery.isLoading || artistsLoading}
            placeholder="Search songs and artists..."
          />
        </div>

        {/* Advanced Filters Panel */}
        {showAdvancedFilters && (
          <div className="mb-6 p-4 border border-orange-peel rounded-lg">
            <div className="text-sm opacity-60 mb-2">
              Advanced filtering options coming soon...
            </div>
            {/* TODO: Add genre, year, source filters here */}
          </div>
        )}

        <div className="space-y-8">
          {!hasSearch ? (
            <RecentlyAddedSongs
              onSongSelect={handleSongSelect}
              onAddToQueue={handleAddToQueue}
            />
          ) : (
            <SongResultsSection
              songs={songsQuery.data || []}
              hasNextPage={false} // Pagination can be added later
              isFetchingNextPage={false}
              fetchNextPage={() => {}}
              onSongSelect={handleSongSelect}
              onAddToQueue={handleAddToQueue}
              searchTerm={searchTerm}
            />
          )}
          {/* Artist Results Section - Always visible for browsing */}
          <ArtistResultsSection
            artists={artists}
            onSongSelect={handleSongSelect}
            onAddToQueue={handleAddToQueue}
            searchTerm={searchTerm}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default LibraryPage;
