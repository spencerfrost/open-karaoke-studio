import React from "react";
import { Song } from "@/types/Song";
import { ITunesSearchResult } from "@/hooks/useItunesSearch";

interface MetadataComparisonViewProps {
  currentSong: Song;
  selectedResult: ITunesSearchResult;
}

export const MetadataComparisonView: React.FC<MetadataComparisonViewProps> = ({
  currentSong,
  selectedResult,
}) => {
  const changes = [
    {
      field: "Title",
      current: currentSong.title,
      new: selectedResult.trackName,
      changed: currentSong.title !== selectedResult.trackName,
    },
    {
      field: "Artist",
      current: currentSong.artist,
      new: selectedResult.artistName,
      changed: currentSong.artist !== selectedResult.artistName,
    },
    {
      field: "Album",
      current: currentSong.album,
      new: selectedResult.collectionName,
      changed: currentSong.album !== selectedResult.collectionName,
    },
    {
      field: "Genre",
      current: currentSong.genre || "Not set",
      new: selectedResult.primaryGenreName || "Not set",
      changed:
        (currentSong.genre || "") !== (selectedResult.primaryGenreName || ""),
    },
    {
      field: "Year",
      current: currentSong.year?.toString() || "Not set",
      new: selectedResult.releaseYear?.toString() || "Not set",
      changed:
        (currentSong.year?.toString() || "") !== (selectedResult.releaseYear?.toString() || ""),
    },
    {
      field: "Track Number",
      current: "Not set",
      new: selectedResult.trackNumber
        ? `${selectedResult.trackNumber}${selectedResult.trackCount ? ` of ${selectedResult.trackCount}` : ""}`
        : "Not set",
      changed: !!selectedResult.trackNumber,
    },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2 text-sm font-medium">
        <div>Field</div>
        <div>Current</div>
        <div>New</div>
      </div>

      {changes.map((change) => (
        <div
          key={change.field}
          className={`grid grid-cols-3 gap-2 text-sm p-2 rounded ${
            change.changed ? "bg-yellow-50 border border-yellow-200" : ""
          }`}
        >
          <div className="font-medium">{change.field}</div>
          <div className="truncate text-muted-foreground">{change.current}</div>
          <div
            className={`truncate ${change.changed ? "font-medium text-foreground" : "text-muted-foreground"}`}
          >
            {change.new}
          </div>
        </div>
      ))}

      <div className="pt-2 text-xs text-muted-foreground space-y-1">
        <p>
          <strong>Additional metadata:</strong>
        </p>
        <ul className="list-disc list-inside space-y-1">
          <li>
            iTunes IDs: Track {selectedResult.trackId}, Artist{" "}
            {selectedResult.artistId}, Collection {selectedResult.collectionId}
          </li>
          {selectedResult.artworkUrl600 && (
            <li>High-resolution artwork (600x600px) will be saved</li>
          )}
          {selectedResult.trackTimeMillis && (
            <li>
              iTunes duration: {Math.floor(selectedResult.trackTimeMillis / 60000)}:
              {String(Math.floor((selectedResult.trackTimeMillis % 60000) / 1000)).padStart(2, "0")}
            </li>
          )}
          {selectedResult.previewUrl && (
            <li>30-second preview URL will be saved</li>
          )}
          {selectedResult.trackExplicitness && (
            <li>
              Content advisory: {selectedResult.trackExplicitness === "explicit" ? "Explicit" : "Clean"}
            </li>
          )}
        </ul>
        <p className="pt-2">
          <strong>Note:</strong> Your original audio file duration will be preserved.
        </p>
      </div>
    </div>
  );
};
