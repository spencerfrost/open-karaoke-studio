import React from "react";
import { Song } from "@/types/Song";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ReprocessSection } from "../ReprocessSection";
import { SongPreviewPlayer } from "../SongPreviewPlayer";
import { Music2, Headphones } from "lucide-react";

interface AudioTabProps {
  song: Song;
}

export const AudioTab: React.FC<AudioTabProps> = ({ song }) => {
  return (
    <div className="space-y-6">
      {/* iTunes Preview Player */}
      {song.itunesPreviewUrl && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Headphones size={18} className="text-muted-foreground" />
              <CardTitle className="text-base">iTunes Preview</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <SongPreviewPlayer
              previewUrl={song.itunesPreviewUrl}
              title={song.title}
              artist={song.artist}
            />
            <p className="text-xs text-muted-foreground mt-3">
              30-second preview from iTunes to help verify this is the correct
              song
            </p>
          </CardContent>
        </Card>
      )}

      {/* Audio Processing */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Music2 size={18} className="text-muted-foreground" />
            <CardTitle className="text-base">Audio Processing</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <ReprocessSection song={song} />
        </CardContent>
      </Card>

      {/* Processing Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">About Audio Processing</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Songs are processed using AI models to separate vocals from
            instrumental tracks, allowing for karaoke playback with adjustable
            vocals.
          </p>
          <div className="space-y-2">
            <p className="font-medium text-foreground">Available Engines:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>
                <span className="font-medium">Demucs:</span> Standard quality,
                fastest processing
              </li>
              <li>
                <span className="font-medium">Roformer:</span> High quality,
                fast processing
              </li>
              <li>
                <span className="font-medium">Hybrid:</span> Best quality,
                slower processing
              </li>
              <li>
                <span className="font-medium">Clean Backing:</span> Cleanest
                backing vocals
              </li>
            </ul>
          </div>
          <p className="text-xs">
            You can reprocess a song with a different engine if you're not
            satisfied with the audio quality. Processing happens in the
            background and may take a few minutes depending on song length.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};
