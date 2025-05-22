import React, { useState } from "react";
import { Grid, List, Music, Search } from "lucide-react";
import SongCard from "../components/songs/SongCard";
import AppLayout from "../components/layout/AppLayout";
import { Song } from "../types/Song";
import { useNavigate } from "react-router-dom";
import vintageTheme from "../utils/theme";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group";
import { useSongs } from "../hooks/useSongs";

const LibraryPage: React.FC = () => {
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [filterTerm, setFilterTerm] = useState("");
  const [filterFavorites, setFilterFavorites] = useState(false);
  const navigate = useNavigate();
  const colors = vintageTheme.colors;

  // Use our new hook
  const { useAllSongs, useToggleFavorite } = useSongs();
  
  // Get all songs with React Query
  const { 
    data: songs = [], 
    isLoading, 
    isError, 
    error,
    refetch 
  } = useAllSongs();
  
  // Use the toggle favorite mutation
  const toggleFavorite = useToggleFavorite();

  // Filter songs based on search term and favorites filter
  const filteredSongs = songs.filter(song => {
    const matchesSearch = !filterTerm || 
      song.title.toLowerCase().includes(filterTerm.toLowerCase()) ||
      song.artist.toLowerCase().includes(filterTerm.toLowerCase());
    
    const matchesFavorites = !filterFavorites || song.favorite;
    
    return matchesSearch && matchesFavorites;
  });

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilterTerm(e.target.value);
  };

  const handleFavoritesFilter = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilterFavorites(e.target.checked);
  };

  const handleToggleFavorite = async (song: Song) => {
    const newFavoriteStatus = !song.favorite;

    // React Query will handle optimistic updates for us through the mutation
    try {
      await toggleFavorite.mutateAsync({ 
        id: song.id, 
        isFavorite: newFavoriteStatus 
      });
    } catch (error) {
      console.error("Failed to toggle favorite:", error);
    }
  };

  const handleSongUpdated = () => {
    // With React Query, we don't need to manually update the UI
    // It will be handled through cache invalidation
    // Just trigger a refetch to be sure
    refetch();
  };

  const handlePlaySong = (song: Song) => {
    navigate(`/player/${song.id}`);
  };

  const handleAddToQueue = (song: Song) => {
    navigate("/queue", { state: { songId: song.id } });
  };

  return (
    <AppLayout>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold mb-6"
          style={{ color: colors.orangePeel }}
        >
          Song Library
        </h1>

        {/* Search and filters */}
        <div className="mb-4">
          <div
            className="flex items-center border rounded-lg mb-4 relative overflow-hidden"
            style={{
              backgroundColor: `${colors.lemonChiffon}20`,
              borderColor: colors.orangePeel,
            }}
          >
            <Search
              size={20}
              className="absolute left-3"
              style={{ color: colors.orangePeel }}
            />
            <input
              type="text"
              placeholder="Search songs..."
              className="py-2 px-10 w-full bg-transparent focus:outline-none"
              style={{ color: colors.lemonChiffon }}
              value={filterTerm}
              onChange={handleSearch}
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="favorites"
                className="mr-2"
                checked={filterFavorites}
                onChange={handleFavoritesFilter}
              />
              <label htmlFor="favorites" style={{ color: colors.lemonChiffon }}>
                Favorites Only
              </label>
            </div>

            <div className="flex ml-auto gap-2">
              <ToggleGroup type="single" value={viewMode} onValueChange={(value) => value && setViewMode(value as "grid" | "list")}>
                <ToggleGroupItem value="grid" aria-label="Grid view">
                  <Grid size={20} />
                </ToggleGroupItem>
                <ToggleGroupItem value="list" aria-label="List view">
                  <List size={20} />
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
          </div>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div
            className="text-center py-8"
            style={{ color: colors.lemonChiffon }}
          >
            Loading songs...
          </div>
        )}

        {/* Error state */}
        {isError && (
          <div
            className="text-center py-8 text-red-500"
            role="alert"
          >
            Error loading songs: {error instanceof Error ? error.message : "Unknown error"}
          </div>
        )}

        {/* Success state */}
        {!isLoading && !isError && (
          <>
            {/* Empty state */}
            {filteredSongs.length === 0 && (
              <div
                className="text-center py-12 rounded-lg"
                style={{
                  backgroundColor: `${colors.lemonChiffon}10`,
                  color: colors.lemonChiffon,
                }}
              >
                <Music
                  size={48}
                  className="mx-auto mb-4"
                  style={{ color: colors.orangePeel }}
                />
                <p>No songs found. Try adjusting your search filters or upload some songs.</p>
              </div>
            )}

            {/* Songs grid/list */}
            {filteredSongs.length > 0 &&
              (viewMode === "grid" ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {filteredSongs.map((song) => (
                    <SongCard
                      key={song.id}
                      song={song}
                      onPlay={handlePlaySong}
                      onAddToQueue={handleAddToQueue}
                      onToggleFavorite={handleToggleFavorite}
                      onSongUpdated={handleSongUpdated}
                    />
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredSongs.map((song) => (
                    <SongCard
                      key={song.id}
                      song={song}
                      onPlay={handlePlaySong}
                      onAddToQueue={handleAddToQueue}
                      onToggleFavorite={handleToggleFavorite}
                      onSongUpdated={handleSongUpdated}
                      compact
                    />
                  ))}
                </div>
              ))}
          </>
        )}
      </div>
    </AppLayout>
  );
};

export default LibraryPage;
