import React from "react";
import { Song } from "@/types/Song";
import { useSongs } from "@/hooks/useSongs";
import { SongPreviewPlayer } from "./SongPreviewPlayer";
import { formatTime } from "@/utils/formatters";
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
  const { getAlbumName } = useSongs();
  
  const albumName = getAlbumName(song);
  
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
        {albumName && albumName !== 'Unknown Album' && (
          <div className="flex items-center gap-2">
            <Music size={16} className="text-muted-foreground flex-shrink-0" />
            <div>
              <p className="text-xs text-muted-foreground">Album</p>
              <p className="font-medium">{albumName}</p>
            </div>
          </div>
        )}

        {/* Duration */}
        <div className="flex items-center gap-2">
          <Clock size={16} className="text-muted-foreground flex-shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">Duration</p>
            <p className="font-medium">{formatTime(song.duration)}</p>
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
            <Calendar size={16} className="text-muted-foreground flex-shrink-0" />
            <div>
              <p className="text-xs text-muted-foreground">Year</p>
              <p className="font-medium">{song.year}</p>
            </div>
          </div>
        )}
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
        {song.favorite && (
          <Badge variant="secondary" className="bg-pink-100 text-pink-800">
            Favorite
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
