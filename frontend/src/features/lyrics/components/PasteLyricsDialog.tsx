import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export interface PasteLyricsDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Function to close the dialog */
  onClose: () => void;
  /** Callback when lyrics are confirmed */
  onLyricsConfirmed: (lyrics: string) => void;
}

export const PasteLyricsDialog: React.FC<PasteLyricsDialogProps> = ({
  isOpen,
  onClose,
  onLyricsConfirmed,
}) => {
  const [lyrics, setLyrics] = useState("");

  // Reset state when dialog opens
  useEffect(() => {
    if (isOpen) {
      setLyrics("");
    }
  }, [isOpen]);

  const handleClose = () => {
    onClose();
    setLyrics("");
  };

  const handleConfirm = () => {
    if (lyrics.trim()) {
      onLyricsConfirmed(lyrics.trim());
      handleClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Paste Lyrics</DialogTitle>
          <DialogDescription>
            Paste plain text lyrics for this song. These will be saved as
            unsynced lyrics.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="lyrics-textarea">Lyrics</Label>
            <Textarea
              id="lyrics-textarea"
              placeholder="Paste lyrics here..."
              value={lyrics}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                setLyrics(e.target.value)
              }
              className="min-h-[300px] font-mono"
              autoFocus
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Tip: For synced lyrics, use the "Search for Lyrics" feature instead.
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={!lyrics.trim()}>
            Save Lyrics
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default PasteLyricsDialog;
