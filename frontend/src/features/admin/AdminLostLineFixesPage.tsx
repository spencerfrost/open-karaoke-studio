import React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { TextCursorInput } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  useLostLineFixes,
  type LostLyricsLineFix,
} from "@/hooks/api/useLyricsLineFixes";
import { LineFixesList } from "@/features/lyrics/components/LineFixesList";
import { ReviewEmpty, ReviewLayout } from "./review/ReviewLayout";
import { SongPanel } from "./review/SongPanel";
import { LyricsFixButtons } from "./review/SongActions";
import { describeWhen } from "./review/describeWhen";
import { useReviewSong } from "./review/useReviewSong";

const LostFixDetail: React.FC<{ fix: LostLyricsLineFix }> = ({ fix }) => {
  const queryClient = useQueryClient();
  const basics = {
    id: fix.songId,
    title: fix.songTitle ?? fix.songId,
    artist: fix.songArtist ?? "",
  };
  const song = useReviewSong(basics);

  return (
    <SongPanel
      basics={basics}
      lyrics={{
        syncedLyrics: song.syncedLyrics,
        plainLyrics: song.plainLyrics,
      }}
      details={
        <div className="space-y-3 text-sm">
          <p>
            {fix.fixedBy ?? "Someone"} fixed a line{" "}
            {describeWhen(fix.updatedAt)}, and the lyrics no longer have it.
          </p>
          <p className="text-muted-foreground">
            Find the line in the lyrics below. If it's there with other words,
            fix it on the stage again or edit the lyrics here; then undo this
            fix to forget it.
          </p>
          <LineFixesList songId={fix.songId} />
        </div>
      }
    >
      <div className="flex flex-wrap gap-2">
        <LyricsFixButtons
          song={song}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ["songs"] });
            queryClient.invalidateQueries({ queryKey: ["lyrics"] });
          }}
        />
      </div>
    </SongPanel>
  );
};

/**
 * Lines someone fixed on the stage that the lyrics no longer show: new
 * lyrics left them no line to go on, or someone changed the line since.
 * Every lyrics job keeps fixes, so these only come from lyrics that changed
 * around them.
 */
const AdminLostLineFixesPage: React.FC = () => {
  const { data: fixes, isLoading, error } = useLostLineFixes();

  return (
    <ReviewLayout
      label="Lost line fixes"
      items={fixes}
      getId={(fix) => String(fix.id)}
      isLoading={isLoading}
      error={error}
      toolbar={
        <p className="text-sm text-muted-foreground">
          Fixes made on the stage whose line isn't in the lyrics any more.
        </p>
      }
      empty={
        <ReviewEmpty icon={TextCursorInput} title="No lost line fixes">
          Every line fixed on the stage is still showing.
        </ReviewEmpty>
      }
      renderRow={(fix) => (
        <>
          <p className="truncate text-sm font-medium">
            {fix.songTitle ?? fix.songId}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {fix.songArtist}
          </p>
          <p className="mt-1 truncate text-xs">
            <Badge variant="outline" className="mr-1">
              Fixed
            </Badge>
            {fix.newText}
          </p>
        </>
      )}
      renderDetail={(fix) => <LostFixDetail fix={fix} />}
    />
  );
};

export default AdminLostLineFixesPage;
