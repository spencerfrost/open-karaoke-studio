import React, { useState } from "react";
import { ChevronDown, ChevronRight, Disc, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

import { useYoutubeMusicAlbumTracks } from "@/hooks/api/useYoutubeMusic";
import { YoutubeMusicAlbum, YoutubeMusicSearchResult } from "@/types/Youtube";

interface AlbumTracksExpanderProps {
  album: YoutubeMusicAlbum;
  onSelectTrack: (track: YoutubeMusicSearchResult) => void;
  loadingStates: Record<string, boolean>;
}

export const AlbumTracksExpander: React.FC<AlbumTracksExpanderProps> = ({
  album,
  onSelectTrack,
  loadingStates,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  // Only fetch when expanded
  const { data, isLoading, error } = useYoutubeMusicAlbumTracks(
    album.browseId,
    isOpen,
  );

  const tracks = data?.data?.tracks || [];
  const thumbnail = album.thumbnails?.[0]?.url || "";

  const handleToggle = () => {
    setIsOpen(!isOpen);
  };

  return (
    <Card className="overflow-hidden py-0 gap-0">
      {/* Album header - clickable to expand/collapse */}
      <button className="w-full text-left" onClick={handleToggle}>
        <CardContent className="p-3 hover:bg-muted/50 transition-colors cursor-pointer">
          <div className="flex items-center gap-3">
            {/* Album artwork */}
            <div className="w-12 h-12 rounded overflow-hidden flex-shrink-0 bg-muted">
              {thumbnail ? (
                <img
                  src={thumbnail}
                  alt={album.title}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Disc className="w-6 h-6 text-muted-foreground" />
                </div>
              )}
            </div>

            {/* Album info */}
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm line-clamp-1">
                {album.title}
              </h4>
              <p className="text-xs text-muted-foreground">
                {album.year && `${album.year} • `}
                {album.type === "single" ? "Single" : "Album"}
              </p>
            </div>

            {/* Expand/collapse icon */}
            <div className="flex-shrink-0">
              {isOpen ? (
                <ChevronDown className="w-5 h-5 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-5 h-5 text-muted-foreground" />
              )}
            </div>
          </div>
        </CardContent>
      </button>

      {/* Expandable tracks section */}
      {isOpen && (
        <div className="border-t bg-muted/30">
          {isLoading && (
            <div className="p-4 flex items-center justify-center">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">
                Loading tracks...
              </span>
            </div>
          )}

          {error && (
            <div className="p-4 text-center text-sm text-destructive">
              Failed to load tracks. Please try again.
            </div>
          )}

          {!isLoading && !error && tracks.length === 0 && (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No tracks found for this album.
            </div>
          )}

          {!isLoading && !error && tracks.length > 0 && (
            <div className="divide-y">
              {tracks.map((track, index) => (
                <TrackRow
                  key={track.videoId || index}
                  track={track}
                  trackNumber={track.trackNumber || index + 1}
                  isLoading={loadingStates[track.videoId] || false}
                  onSelect={() => onSelectTrack(track)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

interface TrackRowProps {
  track: YoutubeMusicSearchResult;
  trackNumber: number;
  isLoading: boolean;
  onSelect: () => void;
}

const TrackRow: React.FC<TrackRowProps> = ({
  track,
  trackNumber,
  isLoading,
  onSelect,
}) => {
  const isDisabled = !track.videoId || track.existsInLibrary;

  return (
    <div className="flex items-center gap-3 px-4 py-2 hover:bg-muted/50">
      {/* Track number */}
      <span className="w-6 text-xs text-muted-foreground text-right flex-shrink-0">
        {trackNumber}
      </span>

      {/* Track info */}
      <div className="flex-1 min-w-0">
        <p
          className={`text-sm line-clamp-1 ${!track.videoId ? "text-muted-foreground" : ""}`}
        >
          {track.title}
          {track.isExplicit && (
            <span className="ml-1 text-xs text-muted-foreground">(E)</span>
          )}
        </p>
        {track.duration && (
          <p className="text-xs text-muted-foreground">{track.duration}</p>
        )}
      </div>

      {/* Add button */}
      <Button
        size="sm"
        onClick={onSelect}
        disabled={isDisabled || isLoading}
        className="flex-shrink-0"
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : !track.videoId ? (
          "Unavailable"
        ) : track.existsInLibrary ? (
          "Added"
        ) : (
          "Add"
        )}
      </Button>
    </div>
  );
};
