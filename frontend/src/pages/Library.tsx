import React, { useEffect, useState } from "react";
import { Grid, List, Music, Search } from "lucide-react";
import { useSongs } from "../context/SongsContext";
import SongCard from "../components/songs/SongCard";
import AppLayout from "../components/layout/AppLayout";
import { toggleFavorite } from "../services/songService";
import { useApiQuery } from "../hooks/useApi";
import { Song } from "../types/Song";
import { useNavigate } from "react-router-dom";
import vintageTheme from "../utils/theme";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"

const LibraryPage: React.FC = () => {
  const { state, dispatch } = useSongs();
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const navigate = useNavigate();
  const colors = vintageTheme.colors;

  const songsQuery = useApiQuery<Song[], ["songs", "list"]>(
    ["songs", "list"],
    "/songs",
    {}
  );

  useEffect(() => {
    if (songsQuery.isSuccess && songsQuery.data) {
      dispatch({ type: "SET_SONGS", payload: songsQuery.data });
    }
  }, [songsQuery.isSuccess, songsQuery.data, dispatch]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch({ type: "SET_FILTER_TERM", payload: e.target.value });
  };

  const handleFavoritesFilter = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch({
      type: "SET_FILTER_FAVORITES",
      payload: e.target.checked,
    });
  };

  const handleToggleFavorite = async (song: Song) => {
    const newFavoriteStatus = !song.favorite;

    // Optimistic update
    dispatch({
      type: "UPDATE_SONG",
      payload: {
        id: song.id,
        updates: { favorite: newFavoriteStatus },
      },
    });

    try {
      await toggleFavorite(song.id, newFavoriteStatus);
    } catch (error) {
      console.error("Failed to toggle favorite:", error);
      // Revert on error
      dispatch({
        type: "UPDATE_SONG",
        payload: {
          id: song.id,
          updates: { favorite: song.favorite }, // Revert to original status
        },
      });
    }
  };

  const handleSongUpdated = (updatedSong: Song) => {
    dispatch({
      type: "UPDATE_SONG",
      payload: {
        id: updatedSong.id,
        updates: updatedSong,
      },
    });

    // Invalidate the songs query to refresh data
    songsQuery.refetch();
  };

  const handlePlaySong = (song: Song) => {
    // Use the Song type
    navigate(`/player/${song.id}`);
  };

  const handleAddToQueue = (song: Song) => {
    // Use the Song type
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

        {/* Search and filters (no changes needed) */}
        <div className="mb-4">
          {/* ... existing search and filter JSX ... */}
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
              value={state.filterTerm}
              onChange={handleSearch}
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="favorites"
                className="mr-2"
                checked={state.filterFavorites}
                onChange={handleFavoritesFilter}
              />
              <label htmlFor="favorites" style={{ color: colors.lemonChiffon }}>
                Favorites Only
              </label>
            </div>

            <div className="flex ml-auto gap-2">
              <ToggleGroup
                type="single"
                defaultValue="grid"
                aria-label="View Mode"
                value={viewMode}
                onValueChange={(value) => {
                  if (value === "grid" || value === "list") {
                    setViewMode(value);
                  }
                }}
              >
                <ToggleGroupItem
                  value="grid"
                  className={
                    viewMode === "grid" ? "hover:none" : "bg-accent/70"
                  }
                >
                  <Grid size={20} />
                </ToggleGroupItem>
                <ToggleGroupItem
                  value="list"
                  className={
                    viewMode === "list" ? "hover:none" : "bg-accent/70"
                  }
                >
                  <List size={20} />
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
          </div>
        </div>

        {/* --- Use query states for Loading, Error, Empty --- */}

        {/* Loading state */}
        {songsQuery.isLoading && (
          <div
            className="text-center py-8"
            style={{ color: colors.lemonChiffon }}
          >
            Loading songs...
          </div>
        )}

        {/* Error state */}
        {songsQuery.isError && (
          <div
            className="text-center py-8 text-red-500" // Use error color
            role="alert"
          >
            Error loading songs:{" "}
            {songsQuery.error instanceof Error
              ? songsQuery.error.message
              : "Unknown error"}
          </div>
        )}

        {/* Success state */}
        {songsQuery.isSuccess && (
          <>
            {/* Empty state (uses context state which is updated by the effect) */}
            {state.filteredSongs.length === 0 && (
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
                <h3 className="text-xl font-semibold mb-2">No songs found</h3>
                <p className="opacity-80">
                  {state.filterTerm ||
                  state.filterStatus !== "all" ||
                  state.filterFavorites
                    ? "Try adjusting your filters"
                    : "Add some songs to get started"}
                </p>
              </div>
            )}

            {/* Songs grid/list (uses context state) */}
            {state.filteredSongs.length > 0 &&
              (viewMode === "grid" ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {state.filteredSongs.map((song) => (
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
                  {state.filteredSongs.map((song) => (
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
