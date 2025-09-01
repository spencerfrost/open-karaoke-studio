import React, { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { useYouTubeMusicSearch } from "@/hooks/api/useYouTubeMusic";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useSongCreation } from "@/hooks/useSongCreation";
import { useAddSongDialog } from "@/hooks/useAddSongDialog";
import { SearchInput } from "./SearchInput";
import { SearchResults } from "./SearchResults";
import { AddSongDialog } from "./AddSongDialog";
import { YouTubeMusicSong } from "@/types/YouTubeMusic";
import { YouTubeMusicSearchProps } from "./YouTubeMusicSearch.types";

export const YouTubeMusicSearch: React.FC<YouTubeMusicSearchProps> = ({
  className = "",
}) => {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 1000);
  
  // API hook for search
  const { data, isLoading, error } = useYouTubeMusicSearch(
    debouncedQuery,
    !!debouncedQuery
  );
  
  // Custom hooks for business logic
  const songCreation = useSongCreation();
  const dialog = useAddSongDialog();
  
  // Track which songs are currently being added
  const addingStates = songCreation.currentSong 
    ? { [songCreation.currentSong.videoId]: songCreation.isAdding }
    : {};

  const handleAddToLibrary = async (song: YouTubeMusicSong) => {
    try {
      await songCreation.createSong(song);
      dialog.openDialog();
    } catch (error) {
      // Error is already handled in the hook
      console.error("Failed to create song:", error);
    }
  };

  const results = data?.results || [];

  return (
    <>
      <Card className={`overflow-hidden bg-card/80 pb-0 gap-4 ${className}`}>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">
            YouTube Music Search
          </CardTitle>
          <CardDescription className="text-sm text-muted-foreground">
            Search for official audio tracks on YouTube Music.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <SearchInput query={query} onQueryChange={setQuery} />
          
          <SearchResults
            results={results}
            isLoading={isLoading}
            error={error}
            query={query}
            onAddToLibrary={handleAddToLibrary}
            addingStates={addingStates}
          />
        </CardContent>
      </Card>

      <AddSongDialog songCreation={songCreation} dialog={dialog} />
    </>
  );
};