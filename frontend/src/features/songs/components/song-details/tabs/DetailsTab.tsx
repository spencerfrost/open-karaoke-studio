import React, { useState } from "react";
import { Song, SongArtist } from "@/types/Song";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSongs } from "@/hooks/api/useSongs";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import { ArtistManager } from "../components/ArtistManager";

const logger = createLogger("component:DetailsTab");

interface DetailsTabProps {
  song: Song;
}

export const DetailsTab: React.FC<DetailsTabProps> = ({ song }) => {
  const { useUpdateSong } = useSongs();
  const updateSongMutation = useUpdateSong();

  const [title, setTitle] = useState(song.title);
  const [album, setAlbum] = useState(song.album ?? "");
  const [year, setYear] = useState(song.year?.toString() ?? "");
  const [primaryArtist, setPrimaryArtist] = useState(song.artist);
  const [featuredArtists, setFeaturedArtists] = useState<SongArtist[]>(
    song.artists?.filter((a) => a.role === "featured") ?? [],
  );

  const handleSave = () => {
    const artistString =
      featuredArtists.length > 0
        ? `${primaryArtist} feat. ${featuredArtists.map((a) => a.name).join(", ")}`
        : primaryArtist;

    logger.debug("Saving song metadata", { id: song.id, title, artistString });

    updateSongMutation.mutate(
      {
        id: song.id,
        title,
        album: album || undefined,
        year: year ? parseInt(year) : undefined,
        artist: artistString,
      },
      {
        onSuccess: () => toast.success("Saved"),
        onError: () => toast.error("Failed to save"),
      },
    );
  };

  const capitalize = (value: string) =>
    value.charAt(0).toUpperCase() + value.slice(1);

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="song-title">Title</Label>
          <Input
            id="song-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="song-album">Album</Label>
          <Input
            id="song-album"
            value={album}
            onChange={(e) => setAlbum(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="song-year">Year</Label>
          <Input
            id="song-year"
            type="number"
            min="1800"
            max="2100"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          />
        </div>

        <ArtistManager
          primaryArtist={primaryArtist}
          featuredArtists={featuredArtists}
          onPrimaryChange={setPrimaryArtist}
          onFeaturedChange={setFeaturedArtists}
        />

        <Button
          className="w-full"
          onClick={handleSave}
          disabled={updateSongMutation.isPending}
        >
          {updateSongMutation.isPending ? "Saving…" : "Save"}
        </Button>
      </div>

      <div>
        <p className="text-sm font-medium text-muted-foreground mb-2">
          Song Identity
        </p>
        <div>
          {song.acoustidFingerprintStatus && (
            <div className="flex justify-between text-sm py-1 border-b">
              <span className="text-muted-foreground">Fingerprint</span>
              <span>
                {capitalize(song.acoustidFingerprintStatus)}
                {song.acoustidScore != null &&
                  ` (${Math.round(song.acoustidScore * 100)}%)`}
              </span>
            </div>
          )}

          <div className="flex justify-between text-sm py-1 border-b">
            <span className="text-muted-foreground">MusicBrainz</span>
            <span>{song.musicbrainzRecordingId ?? "Not identified"}</span>
          </div>

          {song.engineType && (
            <div className="flex justify-between text-sm py-1 border-b">
              <span className="text-muted-foreground">Engine</span>
              <span>{capitalize(song.engineType)}</span>
            </div>
          )}

          {song.loudnessDbfs != null && (
            <div className="flex justify-between text-sm py-1 border-b">
              <span className="text-muted-foreground">Loudness</span>
              <span>
                {song.loudnessDbfs.toFixed(1)} dBFS
                {song.gainDb != null &&
                  ` (+${song.gainDb.toFixed(1)} dB gain)`}
              </span>
            </div>
          )}

          {song.source && (
            <div className="flex justify-between text-sm py-1 border-b">
              <span className="text-muted-foreground">Source</span>
              <span>{capitalize(song.source)}</span>
            </div>
          )}

          {song.videoId && (
            <div className="flex justify-between text-sm py-1 last:border-b-0">
              <span className="text-muted-foreground">Video ID</span>
              <span className="font-mono text-xs">{song.videoId}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
