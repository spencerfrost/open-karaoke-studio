import React from "react";
import { Song } from "../../types/Song";
import { SourceBadges } from "./song-details/SourceBadges";
import { MetadataQualityIndicator } from "./song-details/MetadataQualityIndicator";
import { SongPreviewPlayer } from "./song-details/SongPreviewPlayer";
import { formatTimeMs } from "../../utils/formatters";
import { Badge } from "@/components/ui/badge";
import { Music, Calendar, Clock, Tag } from "lucide-react";
import { cn } from "@/lib/utils";

interface PrimarySongDetailsProps {
  song: Song;
  className?: string;
}

export const PrimarySongDetails: React.FC<PrimarySongDetailsProps> = ({
  song,
  className = "",
}) => {
  const missingFields = [];
  if (!song.title) missingFields.push("title");
  if (!song.artist) missingFields.push("artist");
  if (!song.album) missingFields.push("album");
  if (!song.genre) missingFields.push("genre");
  if (!song.lyrics && !song.syncedLyrics) missingFields.push("lyrics");

  return (
    <div className={cn("space-y-4", className)}>
      {/* Song Title - Large and prominent */}
      <div>
        <h1 className="text-3xl font-bold leading-tight">{song.title}</h1>
        <p className="text-xl text-muted-foreground mt-1">{song.artist}</p>
      </div>

      {/* Primary metadata grid */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        {/* Album */}
        <div className="flex items-center gap-2">
          <Music size={16} className="text-muted-foreground flex-shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">Album</p>
            <p className="font-medium">{song.album}</p>
          </div>
        </div>

        {/* Duration */}
        <div className="flex items-center gap-2">
          <Clock size={16} className="text-muted-foreground flex-shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">Duration</p>
            <p className="font-medium">{formatTimeMs(song.durationMs ?? 0)}</p>
          </div>
        </div>

        {/* Genre */}
        {song.genre && (
          <div className="flex items-center gap-2">
            <Tag size={16} className="text-muted-foreground flex-shrink-0" />
            <div>
              <p className="text-xs text-muted-foreground">Genre</p>
              <p className="font-medium">{song.genre}</p>
            </div>
          </div>
        )}

        {/* Year */}
        {song.year && (
          <div className="flex items-center gap-2">
            <Calendar
              size={16}
              className="text-muted-foreground flex-shrink-0"
            />
            <div>
              <p className="text-xs text-muted-foreground">Year</p>
              <p className="font-medium">{song.year}</p>
            </div>
          </div>
        )}
      </div>

      {/* Source indicators and quality */}
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Sources</p>
          <SourceBadges song={song} size="medium" />
        </div>
      </div>

      {/* Special features badges */}
      <div className="flex flex-wrap gap-2">
        {song.syncedLyrics && (
          <Badge variant="secondary" className="bg-green-100 text-green-800">
            Synced Lyrics
          </Badge>
        )}
        {song.itunesExplicit && (
          <Badge variant="secondary" className="bg-red-100 text-red-800">
            Explicit
          </Badge>
        )}
      </div>

      {/* iTunes Preview Player */}
      {song.itunesPreviewUrl && (
        <div>
          <SongPreviewPlayer
            previewUrl={song.itunesPreviewUrl}
            title={song.title}
            artist={song.artist}
          />
        </div>
      )}
    </div>
  );
};
