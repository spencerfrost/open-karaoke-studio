import React from "react";
import { Song } from "@/types/Song";
import { SongDetailsDialog } from "../song-details/SongDetailsDialog";
import { SingerNameDialog } from "../SingerNameDialog";
import { useSongDialogs } from "@/hooks/useSongDialogs";
import { useSongActions } from "@/hooks/useSongActions";
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

interface SongDialogsProps {
  song: Song;
  dialogs: ReturnType<typeof useSongDialogs>;
  songActions: ReturnType<typeof useSongActions>;
}

export const SongDialogs: React.FC<SongDialogsProps> = ({
  song,
  dialogs,
  songActions,
}) => {
  const handleDelete = () => {
    songActions.handleDelete();
    dialogs.closeDialog();
  };

  return (
    <>
      <SongDetailsDialog
        song={song}
        isOpen={dialogs.isDialogOpen("details")}
        onClose={dialogs.closeDialog}
      />

      <SingerNameDialog
        isOpen={dialogs.isDialogOpen("singer")}
        onClose={dialogs.closeDialog}
        onConfirm={songActions.handleAddToQueue}
        songTitle={song.title}
      />

      <AlertDialog
        open={dialogs.isDialogOpen("delete")}
        onOpenChange={(open) => !open && dialogs.closeDialog()}
      >
        <AlertDialogTrigger asChild>
          <div style={{ display: 'none' }} />
        </AlertDialogTrigger>
        <AlertDialogContent
          onKeyDown={(e) => {
            if (e.key === "Enter" && !songActions.isDeleting) {
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
            <AlertDialogCancel disabled={songActions.isDeleting}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={songActions.isDeleting}
              autoFocus
            >
              {songActions.isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
          {songActions.deleteError && (
            <div className="text-destructive text-xs mt-2">
              Error deleting song. Please try again.
            </div>
          )}
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};