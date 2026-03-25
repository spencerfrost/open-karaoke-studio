import React from "react";
import { Song } from "@/types/Song";
import { ArtworkDisplay } from "../ArtworkDisplay";
import { PrimaryActionsSection } from "../PrimaryActionsSection";
import { Badge } from "@/components/ui/badge";
import { formatTime } from "@/utils/formatters";
import { getSongDuration } from "@/utils/songUtils";
import { Music, Clock, Calendar, Tag } from "lucide-react";

interface OverviewTabProps {
  song: Song;
  onClose: () => void;
  onSongDeleted?: () => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  song,
  onClose,
  onSongDeleted,
}) => {
  return (
    <div className="space-y-6">
      {/* Artwork and Essential Info */}
      <div className="grid grid-cols-1 lg:grid-cols-[250px_1fr] gap-6">
        {/* Left: Artwork */}
        <div className="flex justify-center lg:justify-start">
          <ArtworkDisplay
            song={song}
            size="large"
            className="w-full max-w-[250px]"
            showFallback={true}
          />
        </div>

        {/* Right: Essential Info */}
        <div className="space-y-4">
          {/* Title and Artist */}
          <div>
            <h1 className="text-3xl font-bold leading-tight">{song.title}</h1>
            <p className="text-xl text-muted-foreground mt-1">{song.artist}</p>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            {/* Duration */}
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Duration</p>
                <p className="font-medium">
                  {formatTime(getSongDuration(song))}
                </p>
              </div>
            </div>

            {/* Album */}
            {song.album && song.album !== "Unknown Album" && (
              <div className="flex items-center gap-2">
                <Music size={16} className="text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Album</p>
                  <p className="font-medium truncate">{song.album}</p>
                </div>
              </div>
            )}

            {/* Genre */}
            {song.primaryGenre && (
              <div className="flex items-center gap-2">
                <Tag size={16} className="text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Genre</p>
                  <p className="font-medium">{song.primaryGenre}</p>
                </div>
              </div>
            )}

            {/* Year */}
            {song.year && (
              <div className="flex items-center gap-2">
                <Calendar size={16} className="text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Year</p>
                  <p className="font-medium">{song.year}</p>
                </div>
              </div>
            )}
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-2">
            {song.syncedLyrics && (
              <Badge
                variant="secondary"
                className="bg-green-100 text-green-800"
              >
                Synced Lyrics
              </Badge>
            )}
            {song.itunesExplicit && (
              <Badge variant="secondary" className="bg-red-100 text-red-800">
                Explicit
              </Badge>
            )}
            {song.status === "processed" && (
              <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                Ready to Play
              </Badge>
            )}
            {song.status === "processing" && (
              <Badge
                variant="secondary"
                className="bg-yellow-100 text-yellow-800"
              >
                Processing...
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Primary Actions */}
      <PrimaryActionsSection
        song={song}
        onClose={onClose}
        onSongDeleted={onSongDeleted}
      />

      {/* Processing Status Notice */}
      {song.status !== "processed" && (
        <div className="bg-muted/30 border rounded-lg p-4">
          <p className="text-sm text-muted-foreground text-center">
            This song is currently being processed and will be available for
            playback soon. You can view details and edit metadata while
            processing continues.
          </p>
        </div>
      )}
    </div>
  );
};
