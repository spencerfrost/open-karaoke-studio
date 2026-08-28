import React, { useState } from "react";
import { AlertCircle, Music2, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Song } from "@/types/Song";
import { useSongs } from "@/hooks/api/useSongs";
import { useAuthStore } from "@/stores/authStore";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { createLogger } from "@/lib/logger";
import { useSongRecovery } from "../../hooks/useSongRecovery";
import { humanizeSongError } from "../../utils/errorMessage";

const logger = createLogger("component:SongManagementHeader");

interface SongManagementHeaderProps {
  song: Song;
  onDeleted: () => void;
}

const STATUS_CONFIG = {
  processing: {
    label: "Processing",
    className: "text-warning-strong border-warning/50",
  },
  queued: {
    label: "Queued",
    className: "text-warning-strong border-warning/50",
  },
  processed: {
    label: "Ready",
    className: "text-success-strong border-success/50",
  },
  error: {
    label: "Error",
    className: "text-destructive-strong border-destructive/50",
  },
} as const;

export const SongManagementHeader: React.FC<SongManagementHeaderProps> = ({
  song,
  onDeleted,
}) => {
  const { getArtworkUrl, useDeleteSong } = useSongs();
  const deleteSong = useDeleteSong();
  const [imageError, setImageError] = useState(false);
  const isAdmin = useAuthStore((s) => s.user?.isAdmin);
  const { recoverSong, isRecovering } = useSongRecovery();

  const artworkUrl = getArtworkUrl(song);
  const statusConfig = STATUS_CONFIG[song.status] ?? STATUS_CONFIG.error;
  const hasError = song.status === "error";
  const songError = humanizeSongError(song.errorMessage);

  const handleRetry = () => {
    recoverSong({
      id: song.id,
      title: song.title,
      artist: song.artist,
      videoId: song.videoId,
    });
  };

  const handleDelete = () => {
    deleteSong.mutate(
      { id: song.id },
      {
        onSuccess: () => {
          onDeleted();
        },
        onError: (err) => {
          logger.error("Failed to delete song", {
            id: song.id,
            error: err.message,
          });
          toast.error("Failed to delete song. Please try again.");
        },
      },
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4">
        <button
          type="button"
          className="relative group w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden border border-border bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => toast.info("Image replacement coming soon")}
          aria-label="Edit song artwork"
        >
          {artworkUrl && !imageError ? (
            <img
              src={artworkUrl}
              alt={`${song.title} artwork`}
              className="w-full h-full object-cover"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Music2 size={24} className="text-muted-foreground" />
            </div>
          )}
          <div className="absolute inset-0 bg-overlay/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <Pencil className="h-4 w-4 text-foreground" />
          </div>
        </button>

        <div className="flex-1 min-w-0">
          <p className="text-lg font-semibold truncate">{song.title}</p>
          <p className="text-sm text-muted-foreground truncate">
            {song.artist}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <Badge variant="outline" className={statusConfig.className}>
            {statusConfig.label}
          </Badge>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="destructive"
                size="sm"
                disabled={deleteSong.isPending}
              >
                <Trash2 size={14} />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this song?</AlertDialogTitle>
                <AlertDialogDescription>
                  This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  disabled={deleteSong.isPending}
                >
                  {deleteSong.isPending ? "Deleting…" : "Delete"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {hasError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>Processing failed</AlertTitle>
          <AlertDescription>
            {songError.hint && <p>{songError.hint}</p>}
            <p>{songError.detail}</p>
          </AlertDescription>
          {isAdmin && (
            <Button
              size="sm"
              variant="outline"
              className="col-start-2 mt-1 justify-self-start"
              disabled={isRecovering(song.id)}
              onClick={handleRetry}
            >
              {isRecovering(song.id) ? "Retrying…" : "Retry"}
            </Button>
          )}
        </Alert>
      )}
    </div>
  );
};
