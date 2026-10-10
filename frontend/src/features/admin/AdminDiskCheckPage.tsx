import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  FolderX,
  HardDrive,
  RefreshCw,
  Trash2,
} from "lucide-react";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { apiSend, useApiMutation } from "@/hooks/api/useApi";
import { createLogger } from "@/lib/logger";
import { useSongRecovery } from "@/features/songs/hooks/useSongRecovery";
import {
  countAuditIssues,
  LIBRARY_AUDIT_KEY,
  useLibraryAudit,
  type AuditResult,
  type GhostRecord,
  type IncompleteSong,
  type OrphanedDir,
} from "./hooks/useAdminQueries";
import {
  FilterChips,
  ReviewEmpty,
  ReviewLayout,
  type ReviewSelection,
} from "./review/ReviewLayout";
import { SongPanel } from "./review/SongPanel";
import { DeleteSongButton } from "./review/SongActions";

const logger = createLogger("component:AdminDiskCheckPage");

type DiskItem =
  | { kind: "orphan"; id: string; dir: OrphanedDir }
  | { kind: "ghost"; id: string; record: GhostRecord }
  | { kind: "incomplete"; id: string; song: IncompleteSong };

type Kind = DiskItem["kind"];
type KindFilter = "all" | Kind;

const KIND_LABEL: Record<Kind, string> = {
  orphan: "Folders with no song",
  ghost: "Songs with no files",
  incomplete: "Songs missing files",
};

const KIND_HELP: Record<Kind, string> = {
  orphan: "Files on disk that no song in the database points to.",
  ghost: "A song in the database whose folder is gone.",
  incomplete: "The folder is there, but some audio files are missing.",
};

// Songs a person can do something about first; leftover folders last.
function toItems(result: AuditResult | undefined): DiskItem[] | undefined {
  if (!result) return undefined;
  return [
    ...result.incomplete_songs.map(
      (song): DiskItem => ({ kind: "incomplete", id: song.id, song }),
    ),
    ...result.ghost_records.map(
      (record): DiskItem => ({ kind: "ghost", id: record.id, record }),
    ),
    ...result.orphaned_directories.map(
      (dir): DiskItem => ({ kind: "orphan", id: dir.dir_name, dir }),
    ),
  ];
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** The scan result with these orphan folders and songs gone. */
function withoutItems(
  prev: AuditResult | undefined,
  dirs: Set<string>,
  songIds: Set<string>,
): AuditResult | undefined {
  if (!prev) return prev;
  const orphaned_directories = prev.orphaned_directories.filter(
    (d) => !dirs.has(d.dir_name),
  );
  const ghost_records = prev.ghost_records.filter((r) => !songIds.has(r.id));
  const incomplete_songs = prev.incomplete_songs.filter(
    (s) => !songIds.has(s.id),
  );
  return {
    orphaned_directories,
    ghost_records,
    incomplete_songs,
    summary: {
      ...prev.summary,
      orphaned_count: orphaned_directories.length,
      ghost_count: ghost_records.length,
      incomplete_count: incomplete_songs.length,
    },
  };
}

function useDropFromAudit() {
  const queryClient = useQueryClient();
  return (dirs: Iterable<string>, songIds: Iterable<string>) =>
    queryClient.setQueryData<AuditResult>(LIBRARY_AUDIT_KEY, (prev) =>
      withoutItems(prev, new Set(dirs), new Set(songIds)),
    );
}

const OrphanDetail: React.FC<{
  dir: OrphanedDir;
  selection: ReviewSelection;
}> = ({ dir, selection }) => {
  const drop = useDropFromAudit();
  const remove = useApiMutation<unknown, void>(
    `songs/orphan/${dir.dir_name}`,
    "delete",
    {
      onSuccess: () => {
        toast.success("Folder deleted");
        selection.done();
        drop([dir.dir_name], []);
      },
      onError: (error) => toast.error(error.message),
    },
  );

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <FolderX className="mt-0.5 h-6 w-6 shrink-0 text-muted-foreground" />
        <div className="min-w-0">
          <p className="break-all font-mono text-sm">{dir.dir_name}</p>
          <p className="text-sm text-muted-foreground">{KIND_HELP.orphan}</p>
        </div>
      </div>
      <div className="rounded-md border border-border/60 bg-muted/30 p-3">
        <p className="mb-2 text-xs text-muted-foreground">
          {dir.files.length} file{dir.files.length === 1 ? "" : "s"} ·{" "}
          {formatBytes(dir.total_size_bytes)}
        </p>
        <ul className="space-y-0.5 font-mono text-xs">
          {dir.files.map((file) => (
            <li key={file} className="break-all">
              {file}
            </li>
          ))}
        </ul>
      </div>
      <Button
        size="sm"
        variant="destructive"
        disabled={remove.isPending}
        onClick={() => remove.mutate()}
      >
        <Trash2 className="mr-1.5 h-3.5 w-3.5" />
        {remove.isPending ? "Deleting…" : "Delete folder"}
      </Button>
    </div>
  );
};

const SongIssueDetail: React.FC<{
  item: Extract<DiskItem, { kind: "ghost" | "incomplete" }>;
  selection: ReviewSelection;
}> = ({ item, selection }) => {
  const drop = useDropFromAudit();
  const basics = item.kind === "ghost" ? item.record : item.song;
  const { recoverSong, isRecovering } = useSongRecovery({
    engineType: "demucs",
  });

  const removeFromList = () => {
    selection.done();
    drop([], [basics.id]);
  };

  const recover = async (song: IncompleteSong) => {
    const dispatched = await recoverSong({
      id: song.id,
      title: song.title,
      artist: song.artist,
      videoId: song.video_id,
    });
    if (dispatched) removeFromList();
  };

  return (
    <SongPanel
      basics={basics}
      hasAudio={item.kind === "incomplete"}
      details={
        <div className="space-y-2 text-sm">
          <p className="text-muted-foreground">{KIND_HELP[item.kind]}</p>
          {item.kind === "incomplete" && (
            <div className="flex flex-wrap gap-1.5">
              {item.song.missing_files.map((file) => (
                <Badge
                  key={file}
                  variant="outline"
                  className="border-warning/50 text-warning-strong"
                >
                  Missing {file}
                </Badge>
              ))}
            </div>
          )}
        </div>
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        {item.kind === "incomplete" &&
          (item.song.has_original || item.song.video_id ? (
            <Button
              size="sm"
              disabled={isRecovering(item.song.id)}
              onClick={() => recover(item.song)}
            >
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              {isRecovering(item.song.id)
                ? "Starting…"
                : item.song.video_id && !item.song.has_original
                  ? "Download again and reprocess"
                  : "Reprocess"}
            </Button>
          ) : (
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <AlertCircle className="h-4 w-4" />
              No original or video to rebuild it from
            </span>
          ))}
        <DeleteSongButton
          song={basics}
          label={item.kind === "ghost" ? "Delete record" : "Delete song"}
          onDeleted={removeFromList}
        />
      </div>
    </SongPanel>
  );
};

/** Bulk delete for the ticked folders or records, after a confirm. */
const BulkDelete: React.FC<{
  kind: "orphan" | "ghost";
  ids: Set<string>;
  onDeleted: () => void;
}> = ({ kind, ids, onDeleted }) => {
  const drop = useDropFromAudit();
  const noun =
    kind === "orphan"
      ? `folder${ids.size === 1 ? "" : "s"}`
      : `record${ids.size === 1 ? "" : "s"}`;

  const remove = useApiMutation<{ deleted: number; skipped: number }, void>(
    kind === "orphan" ? "songs/orphan-bulk" : "songs/ghost-bulk",
    "delete",
    {
      mutationFn: () =>
        kind === "orphan"
          ? apiSend("songs/orphan-bulk", "delete", { dir_names: [...ids] })
          : apiSend("songs/ghost-bulk", "delete", { song_ids: [...ids] }),
      onSuccess: ({ deleted, skipped }) => {
        toast.success(
          `Deleted ${deleted} ${noun}${skipped > 0 ? ` (${skipped} skipped)` : ""}`,
        );
        onDeleted();
        if (kind === "orphan") drop(ids, []);
        else drop([], ids);
      },
      onError: (error) => {
        logger.error("Bulk delete failed", { kind, error });
        toast.error(error.message);
      },
    },
  );

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button size="sm" variant="destructive" disabled={remove.isPending}>
          <Trash2 className="mr-1.5 h-3.5 w-3.5" />
          {remove.isPending ? "Deleting…" : `Delete ${ids.size} ticked`}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            Delete {ids.size} {noun}?
          </AlertDialogTitle>
          <AlertDialogDescription>
            {kind === "orphan"
              ? "The folders and every file in them go for good."
              : "The database records go for good. They have no files on disk."}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            onClick={() => remove.mutate()}
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};

/**
 * Files on disk checked against the songs in the database, from a scan run
 * by hand.
 */
const AdminDiskCheckPage: React.FC = () => {
  const auditQuery = useLibraryAudit();
  const result = auditQuery.data;
  const items = toItems(result);
  const [kind, setKind] = useState<KindFilter>("all");
  const [ticked, setTicked] = useState<Set<string>>(new Set());

  const countOf = (k: Kind) => items?.filter((item) => item.kind === k).length;
  // The last of a kind dealt with: back to everything.
  const filter = kind !== "all" && !countOf(kind) ? "all" : kind;
  const shown =
    filter === "all" ? items : items?.filter((item) => item.kind === filter);

  // Ticking is for the bulk delete, so only folders and records can be.
  const bulkKind = filter === "orphan" || filter === "ghost" ? filter : null;
  const tickedShown = new Set(
    bulkKind
      ? (shown ?? []).filter((i) => ticked.has(i.id)).map((i) => i.id)
      : [],
  );
  const toggleTick = (id: string, on: boolean) =>
    setTicked((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  const runAudit = async () => {
    const { data, isError } = await auditQuery.refetch();
    if (isError || !data) {
      toast.error("Couldn't run the disk check");
      return;
    }
    setTicked(new Set());
    logger.info("Disk check complete", data.summary);
  };

  const summary = result?.summary;

  return (
    <ReviewLayout
      label="Disk check problems"
      items={shown}
      getId={(item) => item.id}
      isLoading={auditQuery.isFetching && !result}
      toolbar={
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            {summary
              ? `${summary.total_directories} folders on disk, ${summary.total_db_songs} songs in the database, ${countAuditIssues(summary)} problems.`
              : "Check the files on disk against the songs in the database."}
          </p>
          <Button onClick={runAudit} disabled={auditQuery.isFetching}>
            <HardDrive className="mr-2 h-4 w-4" />
            {auditQuery.isFetching
              ? "Checking…"
              : result
                ? "Check again"
                : "Run disk check"}
          </Button>
        </div>
      }
      filters={
        !!items?.length && (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <FilterChips
              label="Show problems"
              value={filter}
              onChange={(value) => setKind(value as KindFilter)}
              chips={[
                { value: "all", label: "All", count: items.length },
                ...(["incomplete", "ghost", "orphan"] as const)
                  .filter((k) => countOf(k))
                  .map((k) => ({
                    value: k,
                    label: KIND_LABEL[k],
                    count: countOf(k),
                  })),
              ]}
            />
            {bulkKind && shown && (
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={
                      tickedShown.size === shown.length
                        ? true
                        : tickedShown.size > 0
                          ? "indeterminate"
                          : false
                    }
                    onCheckedChange={(checked) =>
                      setTicked(
                        checked
                          ? new Set(shown.map((item) => item.id))
                          : new Set(),
                      )
                    }
                  />
                  Tick all
                </label>
                {tickedShown.size > 0 && (
                  <BulkDelete
                    kind={bulkKind}
                    ids={tickedShown}
                    onDeleted={() => setTicked(new Set())}
                  />
                )}
              </div>
            )}
          </div>
        )
      }
      empty={
        result ? (
          <ReviewEmpty icon={HardDrive} title="All in order">
            Every folder has a song, and every song has its files.
          </ReviewEmpty>
        ) : (
          <ReviewEmpty icon={HardDrive}>
            Run a disk check to find leftover folders and songs missing files.
          </ReviewEmpty>
        )
      }
      renderRowLead={
        bulkKind
          ? (item) => (
              <Checkbox
                checked={ticked.has(item.id)}
                onCheckedChange={(checked) => toggleTick(item.id, !!checked)}
                aria-label={`Tick ${item.id}`}
              />
            )
          : undefined
      }
      renderRow={(item) => (
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            {item.kind === "orphan" ? (
              <>
                <p className="truncate font-mono text-xs">
                  {item.dir.dir_name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {KIND_LABEL.orphan} · {formatBytes(item.dir.total_size_bytes)}
                </p>
              </>
            ) : (
              <>
                <p className="truncate text-sm font-medium">
                  {item.kind === "ghost" ? item.record.title : item.song.title}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {item.kind === "ghost"
                    ? item.record.artist
                    : item.song.artist}
                </p>
                <p className="text-xs text-muted-foreground">
                  {KIND_LABEL[item.kind]}
                </p>
              </>
            )}
          </div>
        </div>
      )}
      renderDetail={(item, selection) =>
        item.kind === "orphan" ? (
          <OrphanDetail dir={item.dir} selection={selection} />
        ) : (
          <SongIssueDetail item={item} selection={selection} />
        )
      }
    />
  );
};

export default AdminDiskCheckPage;
