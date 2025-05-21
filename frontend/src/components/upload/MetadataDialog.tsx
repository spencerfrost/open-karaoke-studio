import React, { useState, useEffect, useRef } from "react";
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
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly onSubmit: (metadata: {
    artist: string;
    title: string;
    album: string;
  }) => void;
  readonly initialMetadata?: { artist: string; title: string; album?: string };
  readonly videoTitle?: string;
  readonly isSubmitting?: boolean;
}

export function MetadataDialog({
  isOpen,
  onClose,
  onSubmit,
  initialMetadata = { artist: "", title: "", album: "" },
  videoTitle = "",
  isSubmitting = false,
}: MetadataDialogProps) {
  const [artist, setArtist] = useState("");
  const [title, setTitle] = useState("");
  const [album, setAlbum] = useState("");
  const initialized = useRef(false);

  // Initialize form values when dialog opens
  useEffect(() => {
    if (isOpen && !initialized.current) {
      setArtist(initialMetadata.artist);
      setTitle(initialMetadata.title);
      setAlbum(initialMetadata.album ?? "");
      initialized.current = true;
    }
  }, [isOpen, initialMetadata]);

  // Reset initialization flag when dialog closes
  useEffect(() => {
    if (!isOpen) {
      initialized.current = false;
    }
  }, [isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      artist: artist.trim(),
      title: title.trim(),
      album: album.trim(),
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Song Information</DialogTitle>
          <DialogDescription>
            {videoTitle ? (
              <div className="space-y-1">
                <p>
                  Verify or edit song information from:{" "}
                  <strong>{videoTitle}</strong>
                </p>
                <p className="text-xs text-muted-foreground">
                  After this step, we'll find matching lyrics and additional metadata for verification.
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                <p>Enter song information</p>
                <p className="text-xs text-muted-foreground">
                  Provide accurate artist and title information to help find the best matches.
                </p>
              </div>
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

          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="album" className="text-right">
              Album
            </Label>
            <Input
              id="album"
              value={album}
              onChange={(e) => setAlbum(e.target.value)}
              className="col-span-3"
              placeholder="Album name (optional)"
            />
          </div>

          <DialogFooter>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting || !title.trim() || !artist.trim()}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                "Continue to Verification"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
