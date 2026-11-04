import React, { useState } from "react";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  SongAudioPreview,
  type PreviewTrack,
  type SongAudioPreviewHandle,
} from "@/features/songs/components/song-card/SongAudioPreview";

const TRACKS: { value: PreviewTrack; label: string }[] = [
  { value: "original", label: "Original" },
  { value: "vocals", label: "Vocals" },
  { value: "instrumental", label: "Instrumental" },
  { value: "backing-vocals", label: "Backing" },
];

/**
 * Play the song, switching between the original and its stems. "Backing" is
 * the backing vocals alone; a song separated without them can't play it.
 */
export const StemPreview: React.FC<{
  songId: string;
  onTimeChange?: (seconds: number) => void;
  playerRef?: React.Ref<SongAudioPreviewHandle>;
}> = ({ songId, onTimeChange, playerRef }) => {
  const [track, setTrack] = useState<PreviewTrack>("original");
  return (
    <div className="space-y-2">
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        value={track}
        onValueChange={(value) => value && setTrack(value as PreviewTrack)}
        aria-label="Which audio to play"
      >
        {TRACKS.map(({ value, label }) => (
          <ToggleGroupItem key={value} value={value}>
            {label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <SongAudioPreview
        songId={songId}
        track={track}
        onTimeChange={onTimeChange}
        ref={playerRef}
      />
    </div>
  );
};
