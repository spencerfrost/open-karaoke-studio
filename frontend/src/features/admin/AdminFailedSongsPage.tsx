import React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { RefreshCw, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useApiMutation } from "@/hooks/api/useApi";
import type { Song } from "@/types/Song";
import { FAILED_SONGS_KEY, useFailedSongs } from "./hooks/useAdminQueries";
import {
  ReviewEmpty,
  ReviewLayout,
  type ReviewSelection,
} from "./review/ReviewLayout";
import { SongPanel } from "./review/SongPanel";
import { DeleteSongButton, FixPanels } from "./review/SongActions";

/** "Oct 8, 21:14"; stored as UTC without a zone marker. */
function describeWhen(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const when = new Date(
    iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`,
  );
  return when.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** The error's first line: enough to tell failures apart in the list. */
function firstLine(message: string | undefined): string {
  return message?.split("\n").find((line) => line.trim()) ?? "No reason given";
}

const FailedSongDetail: React.FC<{
  song: Song;
  selection: ReviewSelection;
}> = ({ song, selection }) => {
  const queryClient = useQueryClient();
  const failedAt = describeWhen(song.failedAt);

  const onDone = () => {
    selection.done();
    queryClient.invalidateQueries({ queryKey: FAILED_SONGS_KEY });
    queryClient.invalidateQueries({ queryKey: ["songs"] });
  };

  const retry = useApiMutation<unknown, void>(
    `songs/${song.id}/retry`,
    "post",
    {
      onSuccess: () => {
        toast.success(
          "Trying again. It's back in the songbook once it's ready",
        );
        onDone();
      },
      onError: (error) => toast.error(error.message),
    },
  );

  return (
    <SongPanel
      basics={song}
      // A failed song's files are cleared or never finished.
      hasAudio={false}
      details={
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            {failedAt
              ? `Failed ${failedAt}`
              : "Failed before failures were timed"}
          </p>
          <pre className="max-h-60 overflow-auto whitespace-pre-wrap break-words rounded-md border border-destructive/40 bg-destructive/10 p-3 font-mono text-xs text-destructive-strong">
            {song.errorMessage ?? "No reason was recorded."}
          </pre>
        </div>
      }
    >
      <FixPanels song={song} panels={["replace-yt"]} onDone={onDone}>
        <Button
          size="sm"
          disabled={!song.videoId || retry.isPending}
          onClick={() => retry.mutate()}
          title={
            song.videoId
              ? "Download it again from the same video and process it"
              : "This song has no YouTube video to download again"
          }
        >
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          {retry.isPending ? "Starting…" : "Try again"}
        </Button>
        <DeleteSongButton song={song} onDeleted={onDone} />
      </FixPanels>
    </SongPanel>
  );
};

/** Songs whose download or processing failed. The songbook hides them. */
const AdminFailedSongsPage: React.FC = () => {
  const { data: songs, isLoading, error } = useFailedSongs();

  return (
    <ReviewLayout
      label="Failed songs"
      items={songs}
      getId={(song) => song.id}
      isLoading={isLoading}
      error={error}
      toolbar={
        <p className="text-sm text-muted-foreground">
          Songs that didn&apos;t download or process. The songbook hides them.
          Try again from the same video, pick a different source, or delete
          them.
        </p>
      }
      empty={
        <ReviewEmpty icon={TriangleAlert} title="No failed songs">
          Every song finished downloading and processing.
        </ReviewEmpty>
      }
      renderRow={(song) => (
        <>
          <p className="truncate text-sm font-medium">{song.title}</p>
          <p className="truncate text-xs text-muted-foreground">
            {song.artist}
          </p>
          <p className="mt-1 truncate text-xs text-muted-foreground">
            {firstLine(song.errorMessage)}
          </p>
        </>
      )}
      renderDetail={(song, selection) => (
        <FailedSongDetail song={song} selection={selection} />
      )}
    />
  );
};

export default AdminFailedSongsPage;
