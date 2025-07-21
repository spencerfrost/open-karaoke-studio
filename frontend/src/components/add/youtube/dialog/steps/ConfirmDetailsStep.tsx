// frontend/src/components/upload/steps/ConfirmDetailsStep.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ConfirmDetailsStepProps {
  initialMetadata: {
    artist: string;
    title: string;
    album: string;
  };
  videoTitle: string;
  onContinue: (confirmedMetadata: {
    artist: string;
    title: string;
    album: string;
  }) => void;
}

export function ConfirmDetailsStep({
  initialMetadata,
  videoTitle,
  onContinue,
}: ConfirmDetailsStepProps) {
  const [artist, setArtist] = useState(initialMetadata.artist);
  const [title, setTitle] = useState(initialMetadata.title);
  const [album, setAlbum] = useState(initialMetadata.album);

  const handleContinue = () => {
    const confirmedMetadata = {
      artist: artist.trim(),
      title: title.trim(),
      album: album.trim(),
    };
    onContinue(confirmedMetadata);
  };

  const isValid = artist.trim() && title.trim();

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Confirm Song Details</CardTitle>
          <CardDescription>
            Verify the artist, title, and album information for:
            <strong> {videoTitle}</strong>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="artist">Artist *</Label>
            <Input
              id="artist"
              value={artist}
              onChange={(e) => setArtist(e.target.value)}
              placeholder="Enter artist name"
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="title">Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter song title"
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="album">Album</Label>
            <Input
              id="album"
              value={album}
              onChange={(e) => setAlbum(e.target.value)}
              placeholder="Enter album name (optional)"
              className="mt-1"
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleContinue} disabled={!isValid}>
          Continue
        </Button>
      </div>
    </div>
  );
}
