import React from "react";
import { Song } from "@/types/Song";
import { SongPreviewPlayer } from "./SongPreviewPlayer";
import { BpmEditor } from "./BpmEditor";
import { formatTime } from "@/utils/formatters";
import { getSongDuration } from "@/utils/songUtils";
import { Badge } from "@/components/ui/badge";
import { Music, Calendar, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface PrimarySongDetailsProps {
  song: Song;
  className?: string;
}

export const PrimarySongDetails: React.FC<PrimarySongDetailsProps> = ({
  song,
  className = "",
}) => {
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
        {song.album && song.album !== "Unknown Album" && (
          <div className="flex items-center gap-2">
            <Music size={16} className="text-muted-foreground flex-shrink-0" />
            <div>
              <p className="text-xs text-muted-foreground">Album</p>
              <p className="font-medium">{song.album}</p>
            </div>
          </div>
        )}

        {/* Duration */}
        <div className="flex items-center gap-2">
          <Clock size={16} className="text-muted-foreground flex-shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">Duration</p>
            <p className="font-medium">{formatTime(getSongDuration(song))}</p>
          </div>
        </div>

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

      {/* BPM Editor */}
      <div className="border-t pt-4">
        <BpmEditor song={song} />
        <p className="text-xs text-muted-foreground mt-1">
          Used for count-in timing before lyrics
        </p>
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
