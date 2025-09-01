import React from "react";
import { SongResultItem } from "./SongResultItem";
import { SearchResultsProps } from "./YouTubeMusicSearch.types";

export const SearchResults: React.FC<SearchResultsProps> = ({
  results,
  isLoading,
  error,
  query,
  onAddToLibrary,
  addingStates,
}) => {
  if (isLoading) {
    return <div className="text-center py-4">Loading...</div>;
  }

  if (error) {
    return <div className="text-destructive py-2">{error.message}</div>;
  }

  if (results.length === 0 && query) {
    return (
      <div className="text-center text-muted-foreground py-4">
        No official audio found.
      </div>
    );
  }

  if (results.length === 0) {
    return null;
  }

  return (
    <ul className="divide-y divide-border">
      {results.map((song) => (
        <SongResultItem
          key={song.videoId}
          song={song}
          isAdding={addingStates[song.videoId] || false}
          onAddToLibrary={onAddToLibrary}
        />
      ))}
    </ul>
  );
};