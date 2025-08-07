import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Music, Play, ListPlus, Plus, MoreVertical, Trash } from "lucide-react";
import { SongDetailsDialog } from "./song-details/SongDetailsDialog";
import { SingerNameDialog } from "./SingerNameDialog";
import { Song } from "@/types/Song";
import { formatTimeMs } from "@/utils/formatters";
import { useSongs } from "@/hooks/api/useSongs";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { useAddToKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
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

interface SongCardProps {
  song: Song;
  onSelect?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
  variant?: "grid" | "horizontal";
  onSongSelect?: (song: Song) => void; // For backward compatibility with HorizontalSongCard usage
}

// Reusable Components
const SyncedLyricsBadge: React.FC = () => (
  <Badge
    className="absolute top-2 right-2 z-10"
    variant="accent"
  >
    Synced
  </Badge>
);

const ArtworkDisplay: React.FC<{
  artworkUrl: string | null;
  song: Song;
  variant: "grid" | "horizontal";
}> = ({ artworkUrl, song, variant }) => {
  const isHorizontal = variant === "horizontal";
  
  return (
    <div className={`
      relative overflow-hidden
      ${isHorizontal 
        ? "flex-shrink-0 rounded w-[60px] h-[60px]" 
        : "flex items-center justify-center bg-primary/20"
      }
    `}>
      {!isHorizontal && song.syncedLyrics && <SyncedLyricsBadge />}
      
      <div className={isHorizontal ? "w-full h-full" : "aspect-video w-full"}>
        {song.syncedLyrics && isHorizontal && <SyncedLyricsBadge />}
        {artworkUrl ? (
          <img 
            src={artworkUrl} 
            alt={song.title} 
            className={`
              object-cover
              ${isHorizontal 
                ? "w-full h-full" 
                : `h-full w-full ${song.itunesArtworkUrls ? "aspect-square" : "aspect-video"}`
              }
            `}
          />
        ) : (
          <div className={`
            flex items-center justify-center
            ${isHorizontal 
              ? "w-full h-full bg-orange-peel/20" 
              : "w-full h-full aspect-video"
            }
          `}>
            <Music 
              size={isHorizontal ? 24 : 64} 
              className={isHorizontal ? "text-orange-peel" : "text-cyan-900"} 
            />
          </div>
        )}
      </div>
    </div>
  );
};

const SongInfo: React.FC<{
  song: Song;
  variant: "grid" | "horizontal";
}> = ({ song, variant }) => {
  const isHorizontal = variant === "horizontal";
  
  if (isHorizontal) {
    return (
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-start mb-1">
          <h4 className="font-medium truncate text-sm">
            {song.title}
          </h4>
          <span className="text-xs ml-2 flex-shrink-0">
            {formatTimeMs(song.durationMs ?? 0)}
          </span>
        </div>
        <p className="text-xs truncate mb-1">
          {song.artist}
        </p>
        {song.album && (
          <p className="text-xs truncate">
            {song.album}
          </p>
        )}
      </div>
    );
  }

  return (
    <CardContent className="p-3">
      <div className="flex justify-between items-start">
        <h3 className="font-medium truncate">{song.title}</h3>
        <span className="text-xs opacity-60">
          {formatTimeMs(song.durationMs || 0)}
        </span>
      </div>
      <p className="text-sm opacity-75">{song.artist}</p>
      <div className="flex gap-2 justify-between items-center mt-1">
        <p className="text-xs text-secondary">{song.album}</p>
        {song.genre && <p className="text-xs text-secondary">{song.genre}</p>}
      </div>
    </CardContent>
  );
};

const ActionButtons: React.FC<{
  onPlay: (e?: React.MouseEvent) => void;
  onQueue: (e: React.MouseEvent) => void;
  onDetails?: (e: React.MouseEvent) => void;
  onDelete?: (e: React.MouseEvent) => void;
}> = ({ onPlay, onQueue, onDetails, onDelete }) => {
  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon"
        className="text-accent"
        aria-label="Play song"
        onClick={onPlay}
      >
        <Play className="w-5 h-5" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="text-secondary"
        aria-label="Add to karaoke queue"
        onClick={onQueue}
      >
        <ListPlus className="w-5 h-5" />
      </Button>
      {onDelete && (
        <Button
          variant="ghost"
          size="icon"
          className="text-destructive"
          aria-label="Delete song"
          onClick={onDelete}
        >
          <Trash className="w-5 h-5" />
        </Button>
      )}
      {onDetails && (
        <Button
          variant="ghost"
          onClick={onDetails}
        >
          <MoreVertical size={14} />
        </Button>
      )}
    </div>
  );
};

const SongCard: React.FC<SongCardProps> = ({ 
  song, 
  onSelect, 
  onAddToQueue, 
  variant = "grid",
  onSongSelect // For backward compatibility
}) => {
  // Local state for dialogs
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isSingerDialogOpen, setIsSingerDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const { getArtworkUrl, useDeleteSong } = useSongs();
  const navigate = useNavigate();
  const addToKaraokeQueue = useAddToKaraokeQueue();
  const deleteSongMutation = useDeleteSong();
  
  const isHorizontal = variant === "horizontal";
  
  // Use appropriate artwork size based on variant
  const artworkUrl = getArtworkUrl(song, isHorizontal ? "small" : "medium");

  // Unified handlers
  const handlePlay = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    
    if (onSongSelect) {
      onSongSelect(song);
    } else if (onSelect) {
      onSelect(song);
    } else {
      navigate(`/player/${song.id}`);
    }
  };

  const handleQueueClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isHorizontal && onAddToQueue) {
      onAddToQueue(song);
    } else {
      setIsSingerDialogOpen(true);
    }
  };

  const handleDetailsClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDialogOpen(true);
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDeleteDialogOpen(true);
  };

  const handleCardClick = () => {
    if (isHorizontal) {
      handlePlay();
    }
  };

  const handleCloseDialog = () => setIsDialogOpen(false);
  const handleAddToQueue = (singerName: string) => {
    addToKaraokeQueue.mutate({ songId: song.id, singer: singerName });
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

  return (
    <>
      <Card
        className={`overflow-hidden ${isHorizontal ? "" : "relative py-0 gap-0"}`}
        onClick={handleCardClick}
      >
        {!isHorizontal && song.syncedLyrics && <SyncedLyricsBadge />}
        
        <CardContent className={isHorizontal ? "p-3" : "p-0"}>
          <div className={`
            ${isHorizontal 
              ? "flex items-center gap-3" 
              : "flex flex-col"
            }
          `}>
            <ArtworkDisplay artworkUrl={artworkUrl} song={song} variant={variant} />
            <SongInfo song={song} variant={variant} />
            {isHorizontal && (
              <ActionButtons
                onPlay={handlePlay}
                onQueue={handleQueueClick}
                onDetails={handleDetailsClick}
                onDelete={handleDeleteClick}
              />
            )}
          </div>
        </CardContent>
        
        {!isHorizontal && (
          <ActionButtons
            onPlay={handlePlay}
            onQueue={handleQueueClick}
            onDelete={handleDeleteClick}
          />
        )}
      </Card>

      <SongDetailsDialog
        song={song}
        isOpen={isDialogOpen}
        onClose={handleCloseDialog}
      />

      <SingerNameDialog
        isOpen={isSingerDialogOpen}
        onClose={() => setIsSingerDialogOpen(false)}
        onConfirm={handleAddToQueue}
        songTitle={song.title}
      />

      <AlertDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
      >
        <AlertDialogTrigger asChild>
          <div style={{ display: 'none' }} />
        </AlertDialogTrigger>
        <AlertDialogContent
          onKeyDown={(e) => {
            if (e.key === "Enter" && !deleteSongMutation.isPending) {
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
            <AlertDialogCancel disabled={deleteSongMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteSongMutation.isPending}
              autoFocus
            >
              {deleteSongMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
          {deleteSongMutation.isError && (
            <div className="text-destructive text-xs mt-2">
              Error deleting song. Please try again.
            </div>
          )}
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default SongCard;
