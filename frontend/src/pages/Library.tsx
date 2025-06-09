import React, { useState } from "react";
import { Grid, List, Music, Search, Filter } from "lucide-react";
import SongCard from "../components/songs/SongCard";
import AppLayout from "../components/layout/AppLayout";
import { Song } from "@/types/Song";
import { useNavigate } from "react-router-dom";
import vintageTheme from "@/utils/theme";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useSongs } from "@/hooks/useSongs";

type SortOption = "title" | "artist" | "album" | "dateAdded" | "duration" | "metadataQuality" | "year";
type FilterSource = "all" | "itunes" | "youtube" | "both";

const LibraryPage: React.FC = () => {
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [filterTerm, setFilterTerm] = useState("");
  const [filterFavorites, setFilterFavorites] = useState(false);
  const [filterGenre, setFilterGenre] = useState<string>("all");
  const [filterYear, setFilterYear] = useState<string>("all");
  const [filterSource, setFilterSource] = useState<FilterSource>("all");
  const [sortBy, setSortBy] = useState<SortOption>("dateAdded");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  
  const navigate = useNavigate();
  const colors = vintageTheme.colors;

  // Use our hook
  const { useAllSongs, useToggleFavorite, getMetadataQuality } = useSongs();
  
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

  // Get unique genres and years for filters
  const availableGenres = [...new Set(songs.map(song => song.genre).filter(Boolean))].sort();
  const availableYears = [...new Set(songs.map(song => song.year).filter(Boolean))].sort();

  // Filter and sort songs
  const filteredAndSortedSongs = React.useMemo(() => {
    const filtered = songs.filter(song => {
      const matchesSearch = !filterTerm || 
        song.title.toLowerCase().includes(filterTerm.toLowerCase()) ||
        song.artist.toLowerCase().includes(filterTerm.toLowerCase()) ||
        song.album?.toLowerCase().includes(filterTerm.toLowerCase());
      
      const matchesFavorites = !filterFavorites || song.favorite;
      
      const matchesGenre = filterGenre === "all" || song.genre === filterGenre;
      
      const matchesYear = filterYear === "all" || song.year === filterYear;
      
      const matchesSource = filterSource === "all" || 
        (filterSource === "itunes" && song.itunesTrackId) ||
        (filterSource === "youtube" && song.videoId) ||
        (filterSource === "both" && song.itunesTrackId && song.videoId);
      
      return matchesSearch && matchesFavorites && matchesGenre && matchesYear && matchesSource;
    });

    // Sort the filtered results
    filtered.sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case "title":
          comparison = a.title.localeCompare(b.title);
          break;
        case "artist":
          comparison = a.artist.localeCompare(b.artist);
          break;
        case "album":
          comparison = (a.album || "").localeCompare(b.album || "");
          break;
        case "dateAdded":
          comparison = new Date(a.dateAdded).getTime() - new Date(b.dateAdded).getTime();
          break;
        case "duration":
          comparison = a.duration - b.duration;
          break;
        case "metadataQuality":
          comparison = getMetadataQuality(a).percentage - getMetadataQuality(b).percentage;
          break;
        case "year": {
          const yearA = parseInt(a.year || "0");
          const yearB = parseInt(b.year || "0");
          comparison = yearA - yearB;
          break;
        }
      }
      
      return sortDirection === "asc" ? comparison : -comparison;
    });

    return filtered;
  }, [songs, filterTerm, filterFavorites, filterGenre, filterYear, filterSource, sortBy, sortDirection, getMetadataQuality]);

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
        favorite: newFavoriteStatus 
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

        {/* Advanced filters */}
        <div className="mb-4">
          <Button onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}>
            <Filter size={16} className="mr-2" />
            Advanced Filters
          </Button>
        </div>

        {showAdvancedFilters && (
          <div className="mb-4 p-4 border rounded-lg" style={{ borderColor: colors.orangePeel }}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="genre" className="block mb-2" style={{ color: colors.lemonChiffon }}>
                  Genre
                </label>
                <Select value={filterGenre} onValueChange={setFilterGenre}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select genre" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    {availableGenres.map(genre => (
                      <SelectItem key={genre} value={genre!}>{genre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label htmlFor="year" className="block mb-2" style={{ color: colors.lemonChiffon }}>
                  Year
                </label>
                <Select value={filterYear} onValueChange={setFilterYear}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select year" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    {availableYears.map(year => (
                      <SelectItem key={year} value={year!}>{year}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label htmlFor="source" className="block mb-2" style={{ color: colors.lemonChiffon }}>
                  Source
                </label>
                <Select value={filterSource} onValueChange={(value) => setFilterSource(value as FilterSource)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select source" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="itunes">iTunes</SelectItem>
                    <SelectItem value="youtube">YouTube</SelectItem>
                    <SelectItem value="both">Both</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label htmlFor="sortBy" className="block mb-2" style={{ color: colors.lemonChiffon }}>
                  Sort By
                </label>
                <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortOption)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select sort option" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="title">Title</SelectItem>
                    <SelectItem value="artist">Artist</SelectItem>
                    <SelectItem value="album">Album</SelectItem>
                    <SelectItem value="dateAdded">Date Added</SelectItem>
                    <SelectItem value="duration">Duration</SelectItem>
                    <SelectItem value="metadataQuality">Metadata Quality</SelectItem>
                    <SelectItem value="year">Year</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label htmlFor="sortDirection" className="block mb-2" style={{ color: colors.lemonChiffon }}>
                  Sort Direction
                </label>
                <Select value={sortDirection} onValueChange={(value) => setSortDirection(value as "asc" | "desc")}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select sort direction" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="asc">Ascending</SelectItem>
                    <SelectItem value="desc">Descending</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <>
            {viewMode === "grid" ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {Array.from({ length: 8 }).map((_, index) => (
                  <div key={index} className="rounded-lg overflow-hidden shadow-md" style={{
                    backgroundColor: colors.lemonChiffon,
                    boxShadow: `0 4px 6px rgba(0, 0, 0, 0.2), inset 0 0 0 1px ${colors.orangePeel}`,
                  }}>
                    {/* Image skeleton */}
                    <Skeleton className="aspect-video w-full" style={{ backgroundColor: `${colors.orangePeel}20` }} />
                    
                    {/* Content skeleton */}
                    <div className="p-3">
                      <div className="flex justify-between items-start mb-2">
                        <Skeleton className="h-5 w-3/4" style={{ backgroundColor: `${colors.russet}30` }} />
                        <Skeleton className="h-6 w-6 rounded-full" style={{ backgroundColor: `${colors.russet}30` }} />
                      </div>
                      <Skeleton className="h-4 w-1/2 mb-2" style={{ backgroundColor: `${colors.russet}20` }} />
                      <div className="flex justify-between items-center">
                        <Skeleton className="h-4 w-8" style={{ backgroundColor: `${colors.russet}20` }} />
                        <Skeleton className="h-3 w-12" style={{ backgroundColor: `${colors.russet}20` }} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div key={index} className="rounded-lg p-3 flex items-center" style={{
                    backgroundColor: colors.lemonChiffon,
                    boxShadow: `0 4px 6px rgba(0, 0, 0, 0.2), inset 0 0 0 1px ${colors.orangePeel}`,
                  }}>
                    {/* Image skeleton */}
                    <Skeleton className="h-12 w-12 rounded-md mr-3" style={{ backgroundColor: `${colors.orangePeel}20` }} />
                    
                    {/* Content skeleton */}
                    <div className="flex-1">
                      <Skeleton className="h-5 w-3/4 mb-1" style={{ backgroundColor: `${colors.russet}30` }} />
                      <Skeleton className="h-4 w-1/2" style={{ backgroundColor: `${colors.russet}20` }} />
                    </div>
                    
                    {/* Right side skeleton */}
                    <div className="text-right mr-3">
                      <Skeleton className="h-4 w-12 mb-1" style={{ backgroundColor: `${colors.russet}20` }} />
                      <Skeleton className="h-6 w-16" style={{ backgroundColor: `${colors.darkCyan}40` }} />
                    </div>
                    
                    {/* Action buttons skeleton */}
                    <div className="flex flex-col items-center gap-1">
                      <Skeleton className="h-8 w-8 rounded-full" style={{ backgroundColor: `${colors.russet}30` }} />
                      <Skeleton className="h-6 w-6 rounded" style={{ backgroundColor: `${colors.russet}30` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
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
            {filteredAndSortedSongs.length === 0 && (
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
            {filteredAndSortedSongs.length > 0 &&
              (viewMode === "grid" ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {filteredAndSortedSongs.map((song) => (
                    <SongCard
                      key={song.id}
                      song={song}
                      onAddToQueue={handleAddToQueue}
                      onToggleFavorite={handleToggleFavorite}
                      onSongUpdated={handleSongUpdated}
                    />
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredAndSortedSongs.map((song) => (
                    <SongCard
                      key={song.id}
                      song={song}
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
