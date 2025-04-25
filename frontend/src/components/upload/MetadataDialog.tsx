import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface MetadataDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (metadata: { artist: string; title: string }) => void;
  initialMetadata?: { artist: string; title: string };
  videoTitle?: string;
  isSubmitting?: boolean;
}

export function MetadataDialog({
  isOpen,
  onClose,
  onSubmit,
  initialMetadata = { artist: "Unknown Artist", title: "" },
  videoTitle = "",
  isSubmitting = false,
}: MetadataDialogProps) {
  const [artist, setArtist] = useState(initialMetadata.artist);
  const [title, setTitle] = useState(initialMetadata.title);

  // Update state when initialMetadata changes
  useEffect(() => {
    if (initialMetadata) {
      setArtist(initialMetadata.artist);
      setTitle(initialMetadata.title);
    }
  }, [initialMetadata]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ artist: artist.trim(), title: title.trim() });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Song Information</DialogTitle>
          <DialogDescription>
            {videoTitle ? (
              <>Verify or edit song information from: <strong>{videoTitle}</strong></>
            ) : (
              <>Enter song information</>
            )}
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="title" className="text-right">
              Title
            </Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="col-span-3"
              placeholder="Song title"
              required
              autoFocus
            />
          </div>
          
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="artist" className="text-right">
              Artist
            </Label>
            <Input
              id="artist"
              value={artist}
              onChange={(e) => setArtist(e.target.value)}
              className="col-span-3"
              placeholder="Artist name"
              required
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !title.trim() || !artist.trim()}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                "Add to Library"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}