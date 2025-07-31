import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Music, Play, Trash } from "lucide-react";
import { SongDetailsDialog } from "./song-details/SongDetailsDialog";
import { Song } from "@/types/Song";
import { formatTimeMs } from "@/utils/formatters";
import { useSongs } from "@/hooks/api/useSongs";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from "@/components/ui/alert-dialog";
import { Pencil, ListPlus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAddToKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import { DEFAULT_SINGER } from "@/constants/singers";

interface SongCardProps {
  song: Song;
  onSelect?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
}

const SongCard: React.FC<SongCardProps> = ({ song, onSelect }) => {
  // Local state for dialogs
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const { getArtworkUrl, useDeleteSong } = useSongs();
  const navigate = useNavigate();
  const deleteSongMutation = useDeleteSong();
  const addToKaraokeQueue = useAddToKaraokeQueue();
  const artworkUrl = getArtworkUrl(song, "medium");

  const handlePlay = () => {
    if (onSelect) {
      onSelect(song);
    } else {
      navigate(`/player/${song.id}`);
    }
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
  };

  const handleDelete = () => {
    deleteSongMutation.mutate(
      { id: song.id },
      {
        onSuccess: () => {
          setIsDeleteDialogOpen(false);
        },
      }
    );
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
            {formatTimeMs(song.durationMs)}
          </span>
        </div>

        <p className="text-sm opacity-75">{song.artist}</p>

        <div className="flex gap-2 justify-between items-center mt-1">
          {/* Show album with enhanced metadata */}
          <p className="text-xs text-secondary">{song.album}</p>

          {/* Show genre if available */}
          {song.genre && <p className="text-xs text-secondary">{song.genre}</p>}
        </div>
      </CardContent>

      <div className="flex justify-around items-center px-4 pb-2">
        <Button
          variant="ghost"
          size="icon"
          className="text-accent"
          aria-label="Play song"
          onClick={handlePlay}
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
        <Button
          variant="ghost"
          size="icon"
          className="text-secondary"
          aria-label="Add to karaoke queue"
          onClick={() => {
            addToKaraokeQueue.mutate({ songId: song.id, singer: DEFAULT_SINGER });
          }}
        >
          <ListPlus className="w-5 h-5" />
        </Button>
        {/* Delete Song Button with AlertDialog */}
        <AlertDialog
          open={isDeleteDialogOpen}
          onOpenChange={setIsDeleteDialogOpen}
        >
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="text-destructive"
              aria-label="Delete song"
              onClick={() => setIsDeleteDialogOpen(true)}
            >
              <Trash className="w-5 h-5" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent
            onKeyDown={(e) => {
              if (e.key === "Enter" && !deleteSongMutation.isLoading) {
                e.preventDefault();
                handleDelete();
              }
            }}
          >
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this song?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. Are you sure you want to
                permanently delete{" "}
                <span className="font-semibold">{song.title}</span>?
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={deleteSongMutation.isLoading}>
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                disabled={deleteSongMutation.isLoading}
                autoFocus
              >
                {deleteSongMutation.isLoading ? "Deleting..." : "Delete"}
              </AlertDialogAction>
            </AlertDialogFooter>
            {deleteSongMutation.isError && (
              <div className="text-destructive text-xs mt-2">
                Error deleting song. Please try again.
              </div>
            )}
          </AlertDialogContent>
        </AlertDialog>
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
