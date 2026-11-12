import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useApiMutation } from "@/hooks/api/useApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import type { ReplacePanelProps } from "./types";

export const EditMetadataPanel: React.FC<ReplacePanelProps> = ({
  song,
  onDone,
}) => {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(song.title ?? "");
  const [artist, setArtist] = useState(song.artist ?? "");
  const [album, setAlbum] = useState(song.album ?? "");

  const saveMutation = useApiMutation<unknown, Record<string, string>>(
    `songs/${song.id}`,
    "patch",
    {
      onSuccess: () => {
        toast.success("Metadata saved");
        queryClient.invalidateQueries({ queryKey: ["songs"] });
        onDone();
      },
      onError: (e: Error) => toast.error(e.message),
    },
  );

  const save = () => {
    const body: Record<string, string> = {};
    if (title.trim()) body.title = title.trim();
    if (artist.trim()) body.artist = artist.trim();
    body.album = album.trim(); // allow clearing album
    saveMutation.mutate(body);
  };

  return (
    <div className="space-y-3 pt-1">
      <div className="space-y-2">
        <div>
          <label className="text-xs font-medium text-muted-foreground">
            Title
          </label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Song title"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground">
            Artist
          </label>
          <Input
            value={artist}
            onChange={(e) => setArtist(e.target.value)}
            placeholder="Artist name"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground">
            Album
          </label>
          <Input
            value={album}
            onChange={(e) => setAlbum(e.target.value)}
            placeholder="Album name (optional)"
          />
        </div>
      </div>
      <Button
        size="sm"
        onClick={save}
        disabled={saveMutation.isPending || !title.trim() || !artist.trim()}
      >
        {saveMutation.isPending ? "Saving..." : "Save Changes"}
      </Button>
    </div>
  );
};
