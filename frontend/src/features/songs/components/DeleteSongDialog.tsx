import React from "react";
import { Song } from "@/types/Song";
import { toast } from "sonner";
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

interface DeleteSongDialogProps {
  song: Song;
  onConfirm: () => void | Promise<void>;
  isDeleting: boolean;
  deleteError?: boolean;
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSuccess?: () => void;
  trigger?: React.ReactNode;
}

export const DeleteSongDialog: React.FC<DeleteSongDialogProps> = ({
  song,
  onConfirm,
  isDeleting,
  deleteError,
  isOpen,
  onOpenChange,
  onSuccess,
  trigger,
}) => {
  const handleConfirm = async () => {
    try {
      await Promise.resolve(onConfirm());
      onSuccess?.();
      toast.success(`"${song.title}" has been deleted from your library`);
      onOpenChange?.(false);
    } catch (error) {
      console.error("Failed to delete song:", error);
      toast.error("Failed to delete song. Please try again.");
      // Don't close the dialog on error
    }
  };

  const alertDialog = (
    <AlertDialog open={isOpen} onOpenChange={onOpenChange}>
      {trigger && (
        <AlertDialogTrigger asChild>
          {trigger}
        </AlertDialogTrigger>
      )}
      <AlertDialogContent
        onKeyDown={(e) => {
          if (e.key === "Enter" && !isDeleting) {
            e.preventDefault();
            handleConfirm();
          }
        }}
      >
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this song?</AlertDialogTitle>
          <AlertDialogDescription>
            This action cannot be undone. This will permanently delete{" "}
            <span className="font-semibold">"{song.title}"</span> and all its data.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isDeleting}
            autoFocus
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
        {deleteError && (
          <div className="text-destructive text-xs mt-2">
            Error deleting song. Please try again.
          </div>
        )}
      </AlertDialogContent>
    </AlertDialog>
  );

  return alertDialog;
};