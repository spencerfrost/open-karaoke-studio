import React, { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Pencil, UserCircle } from "lucide-react";
import { toast } from "sonner";
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
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApiMutation } from "@/hooks/api/useApi";
import { createLogger } from "@/lib/logger";
import { Artist } from "@/hooks/api/useArtists";
import ArtistImageSearch from "./ArtistImageSearch";

const logger = createLogger("component:EditArtistDialog");

interface UpdateArtistResponse {
  id: number;
  name: string;
  display_name: string;
}

interface DeleteArtistResponse {
  deleted_songs: number;
  unlinked_songs: number;
}

interface EditArtistDialogProps {
  artist: Artist;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const ArtistImagePreview: React.FC<{ imageUrl: string; artistName: string }> = ({
  imageUrl,
  artistName,
}) => {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setHasError(false);
  }, [imageUrl]);

  return hasError ? (
    <div className="w-full h-full flex items-center justify-center">
      <UserCircle className="h-10 w-10 text-muted-foreground" />
    </div>
  ) : (
    <img
      src={imageUrl}
      alt={artistName}
      className="w-full h-full object-cover"
      onError={() => setHasError(true)}
    />
  );
};

const EditArtistDialog: React.FC<EditArtistDialogProps> = ({
  artist,
  open,
  onOpenChange,
}) => {
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(artist.name);
  const [mode, setMode] = useState<"edit" | "image-search">("edit");
  const [imageVersion, setImageVersion] = useState(0);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setDisplayName(artist.name);
      setMode("edit");
    }
  }, [open, artist.name]);

  const updateMutation = useApiMutation<
    UpdateArtistResponse,
    { display_name: string }
  >(`artists/${artist.id}`, "patch", {
    onSuccess: (data) => {
      logger.info("Artist updated", { id: data.id, display_name: data.display_name });
      queryClient.invalidateQueries({ queryKey: ["artists"] });
      toast.success(`Artist renamed to "${data.display_name}"`);
      onOpenChange(false);
    },
    onError: (err) => {
      logger.error("Failed to update artist", { error: err.message });
      toast.error(`Failed to update artist: ${err.message}`);
    },
  });

  const deleteMutation = useApiMutation<DeleteArtistResponse, void>(
    `artists/${artist.id}`,
    "delete",
    {
      onSuccess: (data) => {
        logger.info("Artist deleted", data);
        queryClient.invalidateQueries({ queryKey: ["artists"] });
        queryClient.invalidateQueries({ queryKey: ["songs"] });
        const msg =
          data.deleted_songs > 0
            ? `Artist deleted. ${data.deleted_songs} exclusive song${data.deleted_songs !== 1 ? "s" : ""} also removed.`
            : "Artist deleted.";
        toast.success(msg);
        onOpenChange(false);
      },
      onError: (err) => {
        logger.error("Failed to delete artist", { error: err.message });
        toast.error(`Failed to delete artist: ${err.message}`);
      },
    },
  );

  const setImageMutation = useApiMutation<{ success: boolean }, { url: string }>(
    `artists/${artist.id}/image`,
    "post",
    {
      onSuccess: () => {
        logger.info("Artist image updated", { id: artist.id });
        setImageVersion((v) => v + 1);
        setMode("edit");
        toast.success("Artist image updated");
      },
      onError: (err) => {
        logger.error("Failed to set artist image", { error: err.message });
        toast.error(`Failed to set image: ${err.message}`);
      },
    },
  );

  const handleSave = () => {
    const trimmed = displayName.trim();
    if (!trimmed) return;
    updateMutation.mutate({ display_name: trimmed });
  };

  const handleImageSelect = (url: string) => {
    setImageMutation.mutate({ url });
  };

  const isBusy =
    updateMutation.isPending ||
    deleteMutation.isPending ||
    setImageMutation.isPending;

  const imageUrl = `/api/artists/image?name=${encodeURIComponent(artist.name)}&v=${imageVersion}`;

  return (
    <Dialog open={open} onOpenChange={(o) => !isBusy && onOpenChange(o)}>
      <DialogContent
        className={
          mode === "image-search" ? "sm:max-w-[600px]" : "sm:max-w-[400px]"
        }
      >
        <DialogHeader>
          <DialogTitle>
            {mode === "image-search" ? "Search Artist Image" : "Edit Artist"}
          </DialogTitle>
        </DialogHeader>

        {mode === "edit" ? (
          <>
            <div className="space-y-4 py-2">
              {/* Artist image preview with pencil overlay */}
              <div className="flex justify-center">
                <button
                  type="button"
                  className="relative group w-24 h-24 rounded-lg overflow-hidden border border-border bg-muted hover:ring-2 hover:ring-primary transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={() => setMode("image-search")}
                  disabled={isBusy}
                  aria-label="Edit artist image"
                >
                  <ArtistImagePreview imageUrl={imageUrl} artistName={artist.name} />
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <Pencil className="h-5 w-5 text-white" />
                  </div>
                </button>
              </div>

              <div className="space-y-2">
                <Label htmlFor="artist-display-name">Display Name</Label>
                <Input
                  id="artist-display-name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSave()}
                  disabled={isBusy}
                  autoFocus
                />
              </div>
            </div>

            <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-between">
              {/* Delete on the left */}
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" disabled={isBusy}>
                    Delete Artist
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete &quot;{artist.name}&quot;?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently delete this artist.
                      {artist.songCount > 0 && (
                        <>
                          {" "}
                          {artist.songCount} song
                          {artist.songCount !== 1 ? "s" : ""} exclusively linked to
                          this artist will also be removed. Songs credited to
                          multiple artists will be kept.
                        </>
                      )}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => deleteMutation.mutate(undefined as void)}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      Delete
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>

              {/* Save / Cancel on the right */}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={isBusy}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={isBusy || !displayName.trim()}
                >
                  {updateMutation.isPending ? "Saving…" : "Save"}
                </Button>
              </div>
            </DialogFooter>
          </>
        ) : (
          <>
            <ArtistImageSearch
              artistId={artist.id}
              initialQuery={artist.name}
              onSelect={handleImageSelect}
              isApplying={setImageMutation.isPending}
            />
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setMode("edit")}
                disabled={setImageMutation.isPending}
              >
                ← Back
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default EditArtistDialog;
