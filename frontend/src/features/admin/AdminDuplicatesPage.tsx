import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useSongs } from "@/hooks/api/useSongs";
import { createLogger } from "@/lib/logger";
import { SongAudioPreview } from "@/features/songs/components/song-card/SongAudioPreview";
import {
  DUPLICATES_KEY,
  useDuplicatesScan,
  type DuplicateSong,
  type DuplicatesResult,
} from "./hooks/useAdminQueries";
import {
  ReviewEmpty,
  ReviewLayout,
  type ReviewSelection,
} from "./review/ReviewLayout";
import { SongSummary } from "./review/SongPanel";
import { DeleteSongButton } from "./review/SongActions";

const logger = createLogger("component:AdminDuplicatesPage");

type Cluster = DuplicateSong[];

const clusterId = (cluster: Cluster) => cluster[0].id;

/** The scan result with these songs gone, and clusters of one dropped. */
function withoutSongs(
  result: DuplicatesResult | undefined,
  ids: Set<string>,
): DuplicatesResult | undefined {
  if (!result) return result;
  const clusters = result.clusters
    .map((cluster) => cluster.filter((song) => !ids.has(song.id)))
    .filter((cluster) => cluster.length > 1);
  return {
    clusters,
    total_clusters: clusters.length,
    total_duplicates: clusters.reduce((sum, c) => sum + c.length, 0),
  };
}

const ClusterDetail: React.FC<{
  cluster: Cluster;
  selection: ReviewSelection;
}> = ({ cluster, selection }) => {
  const queryClient = useQueryClient();
  const { useDeleteSong } = useSongs();
  const deleteSong = useDeleteSong();
  const [keepingId, setKeepingId] = useState<string | null>(null);

  const removeFromList = (ids: Set<string>) => {
    const remaining = cluster.filter((song) => !ids.has(song.id));
    if (remaining.length < 2) selection.done();
    else if (ids.has(clusterId(cluster))) selection.select(remaining[0].id);
    queryClient.setQueryData<DuplicatesResult>(DUPLICATES_KEY, (prev) =>
      withoutSongs(prev, ids),
    );
  };

  const keep = async (kept: DuplicateSong) => {
    const others = cluster.filter((song) => song.id !== kept.id);
    setKeepingId(kept.id);
    const deleted = new Set<string>();
    try {
      for (const song of others) {
        await deleteSong.mutateAsync({ id: song.id });
        deleted.add(song.id);
      }
      toast.success(
        `Kept one, deleted ${deleted.size} other cop${deleted.size === 1 ? "y" : "ies"}`,
      );
    } catch (error) {
      logger.error("Failed to delete a duplicate", { error });
      toast.error(
        error instanceof Error ? error.message : "Couldn't delete a copy",
      );
    } finally {
      setKeepingId(null);
      if (deleted.size) removeFromList(deleted);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {cluster.length} songs share this title and artist. Listen, then keep
        the best copy; the others are deleted.
      </p>
      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {cluster.map((song) => (
          <div
            key={song.id}
            className="flex flex-col gap-4 rounded-lg border border-border/60 p-4"
          >
            <SongSummary basics={song} size="sm" />
            <SongAudioPreview songId={song.id} />
            <div className="mt-auto flex flex-wrap gap-2">
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button size="sm" disabled={keepingId !== null}>
                    <Check className="mr-1.5 h-3.5 w-3.5" />
                    {keepingId === song.id
                      ? "Deleting the others…"
                      : "Keep this one"}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Keep this copy?</AlertDialogTitle>
                    <AlertDialogDescription>
                      The other {cluster.length - 1} cop
                      {cluster.length === 2 ? "y" : "ies"} of &ldquo;
                      {song.title}&rdquo; and their audio files go for good.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      onClick={() => keep(song)}
                    >
                      Delete the others
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
              <DeleteSongButton
                song={song}
                label="Delete"
                onDeleted={() => removeFromList(new Set([song.id]))}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

/** Songs added more than once, from a scan run by hand. */
const AdminDuplicatesPage: React.FC = () => {
  const scanQuery = useDuplicatesScan();
  const result = scanQuery.data;

  const runScan = async () => {
    const { data, isError } = await scanQuery.refetch();
    if (isError || !data) {
      toast.error("Couldn't scan for duplicates");
      return;
    }
    logger.info("Duplicate scan complete", {
      clusters: data.total_clusters,
      duplicates: data.total_duplicates,
    });
  };

  return (
    <ReviewLayout
      label="Duplicated songs"
      items={result?.clusters}
      getId={clusterId}
      isLoading={scanQuery.isFetching && !result}
      toolbar={
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            {result
              ? `${result.total_clusters} song${result.total_clusters === 1 ? " is" : "s are"} in the library more than once (${result.total_duplicates} copies).`
              : "Find songs that are in the library more than once, by title and artist."}
          </p>
          <Button onClick={runScan} disabled={scanQuery.isFetching}>
            <Copy className="mr-2 h-4 w-4" />
            {scanQuery.isFetching
              ? "Scanning…"
              : result
                ? "Scan again"
                : "Find duplicates"}
          </Button>
        </div>
      }
      empty={
        result ? (
          <ReviewEmpty icon={Copy} title="No duplicates">
            Every song in the library is there once.
          </ReviewEmpty>
        ) : (
          <ReviewEmpty icon={Copy}>
            Run a scan to find songs that were added more than once.
          </ReviewEmpty>
        )
      }
      renderRow={(cluster) => (
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{cluster[0].title}</p>
            <p className="truncate text-xs text-muted-foreground">
              {cluster[0].artist}
            </p>
          </div>
          <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
            {cluster.length} copies
          </span>
        </div>
      )}
      renderDetail={(cluster, selection) => (
        <ClusterDetail cluster={cluster} selection={selection} />
      )}
    />
  );
};

export default AdminDuplicatesPage;
