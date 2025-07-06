import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Music, Play, Heart, Plus, MoreVertical } from "lucide-react";
import { SongDetailsDialog } from "./song-details/SongDetailsDialog";
import { Song } from "@/types/Song";
import { formatTimeMs } from "@/utils/formatters";
import { useSongs } from "@/hooks/useSongs";
import { Button } from "@/components/ui/button";

interface HorizontalSongCardProps {
  song: Song;
  onSongSelect?: (song: Song) => void;
  onToggleFavorite?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
}

const HorizontalSongCard: React.FC<HorizontalSongCardProps> = ({
  song,
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
}) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { getArtworkUrl } = useSongs();

  const artworkUrl = getArtworkUrl(song, "small");

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
  };

  const handlePlayClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSongSelect?.(song);
  };

  const handleFavoriteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleFavorite?.(song);
  };

  const handleQueueClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onAddToQueue?.(song);
  };

  const handleDetailsClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDialogOpen(true);
  };

  return (
    <>
      <Card
        className="overflow-hidden hover:shadow-md transition-all duration-200 cursor-pointer group border-orange-peel/25 bg-lemon-chiffon/5"
        onClick={() => onSongSelect?.(song)}
      >
        <CardContent className="p-3">
          <div className="flex items-center gap-3">
            {/* Album Artwork */}
            <div className="relative flex-shrink-0 rounded overflow-hidden w-[60px] h-[60px]">
              {song.syncedLyrics && (
                <Badge
                  className="absolute -top-1 -right-1 z-10 text-xs px-1 py-0 bg-orange-peel text-dark-cyan text-[0.6rem]"
                  variant="accent"
                >
                  ♪
                </Badge>
              )}

              {artworkUrl ? (
                <img
                  src={artworkUrl}
                  alt={song.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-orange-peel/20">
                  <Music size={24} className="text-orange-peel" />
                </div>
              )}
            </div>

            {/* Song Info */}
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-start mb-1">
                <h4 className="font-medium truncate text-sm text-lemon-chiffon">
                  {song.title}
                </h4>
                <span className="text-xs ml-2 flex-shrink-0 text-lemon-chiffon/80">
                  {formatTimeMs(song.duration)}
                </span>
              </div>

              <p className="text-xs truncate mb-1 text-lemon-chiffon/90">
                {song.artist}
              </p>

              {song.album && (
                <p className="text-xs truncate text-lemon-chiffon/60">
                  {song.album}
                </p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-orange-peel bg-transparent"
                onClick={handlePlayClick}
              >
                <Play size={14} />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                className={`h-8 w-8 p-0 bg-transparent ${
                  song.favorite ? "text-orange-peel" : "text-lemon-chiffon/60"
                }`}
                onClick={handleFavoriteClick}
              >
                <Heart
                  size={14}
                  fill={song.favorite ? "currentColor" : "none"}
                />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-lemon-chiffon/80 bg-transparent"
                onClick={handleQueueClick}
              >
                <Plus size={14} />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-lemon-chiffon/60 bg-transparent"
                onClick={handleDetailsClick}
              >
                <MoreVertical size={14} />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Song Details Dialog */}
      <SongDetailsDialog
        song={song}
        isOpen={isDialogOpen}
        onClose={handleCloseDialog}
      />
    </>
  );
};

export default HorizontalSongCard;
