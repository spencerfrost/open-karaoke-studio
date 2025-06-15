import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Music, Play } from "lucide-react";
import { SongDetailsDialog } from "./song-details/SongDetailsDialog";
import { Song } from "@/types/Song";
import { formatTime } from "@/utils/formatters";
import { useSongs } from "@/hooks/useSongs";
import { Button } from "@/components/ui/button";
import { Pencil } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface SongCardProps {
  song: Song;
}

const SongCard: React.FC<SongCardProps> = ({ song }) => {
  // Local state for dialog
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { getArtworkUrl } = useSongs();
  const navigate = useNavigate();

  const artworkUrl = getArtworkUrl(song, "medium");

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
  };

  // Grid view (default)
  return (
    <Card className="overflow-hidden relative py-0 gap-0">
      {song.syncedLyrics && (
        <Badge className="absolute top-2 right-2 z-10" variant="accent">
          Synced
        </Badge>
      )}

      <div className="flex items-center justify-center relative bg-primary/20">
        <div className="aspect-video w-full">
          {artworkUrl ? (
            <img
              src={artworkUrl}
              alt={song.title}
              className={
                "h-full w-full object-cover " +
                (song.itunesArtworkUrls ? "aspect-square" : "aspect-video")
              }
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center aspect-video">
              <Music size={64} className="text-cyan-900" />
            </div>
          )}
        </div>
      </div>

      <CardContent className="p-3">
        <div className="flex justify-between items-start">
          <h3 className="font-medium truncate">{song.title}</h3>
          <span className="text-xs opacity-60">
            {formatTime(song.duration)}
          </span>
        </div>

        <p className="text-sm opacity-75">{song.artist}</p>

        <div className="flex gap-2 justify-between items-center mt-1">
          {/* Show album with enhanced metadata */}
          <p className="text-xs text-secondary">{song.album}</p>

          {/* Show genre if available */}
          {song.genre && (
            <p className="text-xs text-secondary">{song.genre}</p>
          )}
        </div>
      </CardContent>

      <div className="flex justify-around items-center px-4 pb-2">
        <Button
          variant="ghost"
          size="icon"
          className="text-accent"
          aria-label="Play song"
          onClick={() => navigate(`/player/${song.id}`)}
        >
          <Play className="w-5 h-5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="text-secondary"
          aria-label="Edit song details"
          onClick={() => setIsDialogOpen(true)}
        >
          <Pencil className="w-5 h-5" />
        </Button>
      </div>

      {/* Song Details Dialog */}
      <SongDetailsDialog
        song={song}
        isOpen={isDialogOpen}
        onClose={handleCloseDialog}
      />
    </Card>
  );
};

export default SongCard;
