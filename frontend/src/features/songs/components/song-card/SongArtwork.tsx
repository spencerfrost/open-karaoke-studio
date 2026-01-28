import React from "react";
import { Music, Play } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { SongArtworkProps } from "./SongCard.types";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";
import { ProcessingIndicator } from "./ProcessingIndicator";

const SyncedLyricsBadge: React.FC = () => (
  <Badge className="absolute top-2 right-2 z-10" variant="accent">
    Synced
  </Badge>
);

export const SongArtwork: React.FC<SongArtworkProps> = ({
  song,
  artworkUrl,
  showSyncedBadge = true,
  onPlay,
  showPlayButton = true,
}) => {
  const processingStatus = useProcessingIndicators((state) =>
    state.getStatus(song.id),
  );
  const isProcessing = !!processingStatus;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onPlay?.(e);
  };

  return (
    <div
      className="relative overflow-hidden flex items-center justify-center bg-primary/20 cursor-pointer"
      onClick={handleClick}
    >
      {showSyncedBadge && song.syncedLyrics && <SyncedLyricsBadge />}

      {/* Play button overlay - hide if processing or showPlayButton is false */}
      {showPlayButton && !isProcessing && (
        <div className="absolute inset-0 flex items-center justify-center z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-black/30">
          <div className="bg-white/20 backdrop-blur-sm rounded-full p-4">
            <Play className="w-12 h-12 text-white fill-white" />
          </div>
        </div>
      )}

      {/* Processing indicator overlay */}
      {processingStatus && (
        <ProcessingIndicator status={processingStatus} variant="overlay" />
      )}

      <div className="aspect-video w-full">
        {artworkUrl ? (
          <img
            src={artworkUrl}
            alt={song.title}
            className={`object-cover h-full w-full ${
              song.itunesArtworkUrls ? "aspect-square" : "aspect-video"
            }`}
          />
        ) : (
          <div className="flex items-center justify-center w-full h-full aspect-video">
            <Music size={64} className="text-cyan-900" />
          </div>
        )}
      </div>
    </div>
  );
};
