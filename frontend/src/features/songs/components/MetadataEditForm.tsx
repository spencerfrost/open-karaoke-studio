import React, { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface MetadataFormData {
  title: string;
  artist: string;
  album?: string;
}

interface MetadataEditFormProps {
  initialTitle: string;
  initialArtist: string;
  initialAlbum?: string;
  onChange: (metadata: MetadataFormData) => void;
  className?: string;
}

export const MetadataEditForm: React.FC<MetadataEditFormProps> = ({
  initialTitle,
  initialArtist,
  initialAlbum = "",
  onChange,
  className = "",
}) => {
  const [title, setTitle] = useState(initialTitle);
  const [artist, setArtist] = useState(initialArtist);
  const [album, setAlbum] = useState(initialAlbum);

  // Update parent on any change
  useEffect(() => {
    onChange({
      title: title.trim(),
      artist: artist.trim(),
      album: album.trim() || undefined,
    });
  }, [title, artist, album, onChange]);

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="metadata-title">
            Title <span className="text-destructive">*</span>
          </Label>
          <Input
            id="metadata-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter song title"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="metadata-artist">
            Artist <span className="text-destructive">*</span>
          </Label>
          <Input
            id="metadata-artist"
            value={artist}
            onChange={(e) => setArtist(e.target.value)}
            placeholder="Enter artist name"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="metadata-album">Album</Label>
          <Input
            id="metadata-album"
            value={album}
            onChange={(e) => setAlbum(e.target.value)}
            placeholder="Enter album name (optional)"
          />
        </div>

      </div>
    </div>
  );
};
