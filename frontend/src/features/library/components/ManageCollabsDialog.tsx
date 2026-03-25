import React, { useEffect, useState } from "react";
import { X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
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
import { useApiMutation } from "@/hooks/api/useApi";
import { Artist } from "@/hooks/api/useArtists";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:ManageCollabsDialog");

interface ManageCollabsDialogProps {
  artist: Artist;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface SplitArtistCreditsRequest {
  credits: { name: string; role: "primary" | "featured" }[];
}

interface SplitArtistCreditsResponse {
  updated: number;
}

const ManageCollabsDialog: React.FC<ManageCollabsDialogProps> = ({
  artist,
  open,
  onOpenChange,
}) => {
  const queryClient = useQueryClient();
  const [primaryArtist, setPrimaryArtist] = useState(artist.name);
  const [collabArtists, setCollabArtists] = useState<string[]>([""]);

  useEffect(() => {
    if (open) {
      setPrimaryArtist(artist.name);
      setCollabArtists([""]);
    }
  }, [open, artist.name]);

  const splitMutation = useApiMutation<
    SplitArtistCreditsResponse,
    SplitArtistCreditsRequest
  >(`artists/${artist.id}/split-credits`, "post", {
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["artists"] });
      toast.success(`Credits updated for ${data.updated} song(s)`);
      onOpenChange(false);
    },
    onError: (err) => {
      logger.error("Failed to split artist credits", { error: err.message });
      toast.error(`Failed to update credits: ${err.message}`);
    },
  });

  const handleSave = () => {
    const credits: SplitArtistCreditsRequest["credits"] = [
      { name: primaryArtist.trim(), role: "primary" },
      ...collabArtists
        .filter((n) => n.trim())
        .map((n) => ({ name: n.trim(), role: "featured" as const })),
    ];
    splitMutation.mutate({ credits });
  };

  const updateCollab = (index: number, value: string) => {
    setCollabArtists((prev) => prev.map((n, i) => (i === index ? value : n)));
  };

  const removeCollab = (index: number) => {
    setCollabArtists((prev) => prev.filter((_, i) => i !== index));
  };

  const addCollab = () => {
    setCollabArtists((prev) => [...prev, ""]);
  };

  const isBusy = splitMutation.isPending;
  const canSave = primaryArtist.trim().length > 0 && !isBusy;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Manage Collabs — {artist.name}</DialogTitle>
          <DialogDescription>
            Split artist credits. Changes apply to all songs by this artist.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label>Primary Artist</Label>
            <Input
              value={primaryArtist}
              onChange={(e) => setPrimaryArtist(e.target.value)}
              placeholder="Primary artist name"
            />
          </div>

          <div className="space-y-2">
            <Label>Collab Artists</Label>
            {collabArtists.map((name, i) => (
              <div key={i} className="flex gap-2">
                <Input
                  value={name}
                  onChange={(e) => updateCollab(i, e.target.value)}
                  placeholder="Collab artist name"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeCollab(i)}
                  aria-label="Remove collab artist"
                >
                  <X size={16} />
                </Button>
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={addCollab}>
              + Add Artist
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!canSave}>
            {isBusy ? "Saving..." : "Apply to All Songs"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ManageCollabsDialog;
