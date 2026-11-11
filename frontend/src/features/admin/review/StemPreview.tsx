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
  /** The audio it starts on; the original song unless a page needs a stem. */
  initialTrack?: PreviewTrack;
  /** Set both to choose the track from outside, e.g. per-moment play buttons. */
  track?: PreviewTrack;
  onTrackChange?: (track: PreviewTrack) => void;
}> = ({
  songId,
  onTimeChange,
  playerRef,
  initialTrack = "original",
  track: controlledTrack,
  onTrackChange,
}) => {
  const [ownTrack, setOwnTrack] = useState<PreviewTrack>(initialTrack);
  const track = controlledTrack ?? ownTrack;
  const setTrack = onTrackChange ?? setOwnTrack;
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
