import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { LyricsResults } from "@/components/forms";
import { useSongCreation } from "@/hooks/useSongCreation";
import { useAddSongDialog } from "@/hooks/useAddSongDialog";

interface AddSongDialogContainerProps {
  songCreation: ReturnType<typeof useSongCreation>;
  dialog: ReturnType<typeof useAddSongDialog>;
}

export const AddSongDialog: React.FC<AddSongDialogContainerProps> = ({
  songCreation,
  dialog,
}) => {
  const { currentSong, createdSong, lyricsOptions, isLoadingLyrics } = songCreation;
  const { isOpen, selectedLyrics, closeDialog, selectLyrics } = dialog;

  const handleConfirm = async () => {
    if (selectedLyrics) {
      try {
        await songCreation.saveLyrics(selectedLyrics);
      } catch (error) {
        console.error("Failed to save lyrics:", error);
      }
    }
    closeDialog();
    songCreation.resetState();
  };

  const handleClose = () => {
    closeDialog();
    songCreation.resetState();
  };

  if (!currentSong || !createdSong) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[700px] max-h-[90dvh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>Add Song to Library</DialogTitle>
          <DialogDescription>
            Adding: <strong>{currentSong.title}</strong>
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex-1 overflow-y-auto">
          <LyricsResults
            isLoading={isLoadingLyrics}
            options={lyricsOptions || []}
            selectedOption={selectedLyrics}
            onSelectionChange={selectLyrics}
            youtubeMusicDurationSeconds={currentSong.duration}
          />
        </div>
        
        <div className="flex justify-end pt-4">
          <Button
            onClick={handleConfirm}
            disabled={!selectedLyrics}
          >
            Confirm
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};