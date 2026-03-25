import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Music, Save, Upload } from "lucide-react";
import { Song } from "@/types/Song";

interface MetadataEditorTabProps {
  song: Song;
  onSave: (metadata: Partial<Song>) => void;
}

const MetadataEditorTab: React.FC<MetadataEditorTabProps> = ({
  song,
  onSave,
}) => {
  const [metadata, setMetadata] = useState<Partial<Song>>({
    title: song.title,
    artist: song.artist,
    album: song.album ?? "",
    year: song.year ?? "",
  });

  const artworkUrl = song.albumCoverUrl ?? (song.thumbnail ? `/api/songs/${song.id}/thumbnail` : null);

  const handleChange = (field: keyof Song, value: string) => {
    setMetadata((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave(metadata);
  };

  return (
    <div className="p-2">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Cover Art Column */}
        <div className="flex flex-col items-center gap-4">
          <div className="w-full aspect-square rounded-md flex items-center justify-center relative overflow-hidden bg-accent/20">
            {artworkUrl ? (
              <img
                src={artworkUrl}
                alt={metadata.title}
                className="h-full w-full object-cover"
              />
            ) : (
              <Music size={64} className="text-accent" />
            )}
          </div>

          <Button
            variant="ghost"
            className="w-full flex items-center justify-center gap-2"
          >
            <Upload size={18} />
            Change Image
          </Button>
        </div>

        {/* Form Fields Column */}
        <div className="md:col-span-2 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              placeholder="Enter song title"
              value={metadata.title}
              onChange={(e) => handleChange("title", e.target.value)}
              className="w-full"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="artist">Artist</Label>
            <Input
              id="artist"
              value={metadata.artist}
              onChange={(e) => handleChange("artist", e.target.value)}
              className="w-full"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="album">Album</Label>
              <Input
                id="album"
                value={metadata.album}
                onChange={(e) => handleChange("album", e.target.value)}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="year">Year</Label>
              <Input
                id="year"
                value={metadata.year}
                onChange={(e) => handleChange("year", e.target.value)}
                className="w-full"
              />
            </div>
          </div>

        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <Button
          className="flex items-center gap-2 bg-accent"
          onClick={handleSave}
        >
          <Save size={18} />
          Save Changes
        </Button>
      </div>
    </div>
  );
};

export default MetadataEditorTab;
