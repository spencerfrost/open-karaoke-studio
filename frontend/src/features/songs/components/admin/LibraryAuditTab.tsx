import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
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
import { createLogger } from "@/lib/logger";
import { toast } from "sonner";
import { AlertCircle, HardDrive, RefreshCw, Trash2 } from "lucide-react";

const logger = createLogger("component:LibraryAuditTab");

interface OrphanedDir {
  dir_name: string;
  files: string[];
  total_size_bytes: number;
}

interface GhostRecord {
  id: string;
  title: string;
  artist: string;
  date_added: string | null;
}

interface IncompleteSong {
  id: string;
  title: string;
  artist: string;
  missing_files: string[];
  has_original: boolean;
  video_id: string | null;
}

interface AuditSummary {
  total_directories: number;
  total_db_songs: number;
  orphaned_count: number;
  ghost_count: number;
  incomplete_count: number;
}

interface AuditResult {
  orphaned_directories: OrphanedDir[];
  ghost_records: GhostRecord[];
  incomplete_songs: IncompleteSong[];
  summary: AuditSummary;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const LibraryAuditTab: React.FC = () => {
  const { token } = useAuthStore();
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const [reprocessingIds, setReprocessingIds] = useState<Set<string>>(new Set());
  const [selectedOrphans, setSelectedOrphans] = useState<Set<string>>(new Set());
  const [selectedGhosts, setSelectedGhosts] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  const auditMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/songs/library-audit", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Audit failed");
      return res.json() as Promise<AuditResult>;
    },
    onSuccess: (data) => {
      setAuditResult(data);
      setSelectedOrphans(new Set());
      setSelectedGhosts(new Set());
      logger.info("Library audit complete", data.summary);
      const total =
        data.summary.orphaned_count +
        data.summary.ghost_count +
        data.summary.incomplete_count;
      if (total === 0) {
        toast.success("Library is clean — no issues found!");
      } else {
        toast.warning(`Found ${total} issue${total !== 1 ? "s" : ""}`);
      }
    },
    onError: () => toast.error("Failed to run library audit"),
  });

  const deleteOrphan = async (dirName: string) => {
    setDeletingIds((prev) => new Set(prev).add(dirName));
    try {
      const res = await fetch(`/api/songs/orphan/${dirName}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Delete failed");
      toast.success(`Deleted orphaned directory: ${dirName}`);
      setAuditResult((prev) =>
        prev
          ? {
            ...prev,
            orphaned_directories: prev.orphaned_directories.filter(
              (d) => d.dir_name !== dirName,
            ),
            summary: {
              ...prev.summary,
              orphaned_count: prev.summary.orphaned_count - 1,
            },
          }
          : null,
      );
    } catch {
      toast.error(`Failed to delete directory: ${dirName}`);
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(dirName);
        return next;
      });
    }
  };

  const deleteGhost = async (songId: string) => {
    setDeletingIds((prev) => new Set(prev).add(songId));
    try {
      const res = await fetch(`/api/songs/${songId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Delete failed");
      toast.success("Ghost record deleted");
      setAuditResult((prev) =>
        prev
          ? {
            ...prev,
            ghost_records: prev.ghost_records.filter((r) => r.id !== songId),
            summary: {
              ...prev.summary,
              ghost_count: prev.summary.ghost_count - 1,
            },
          }
          : null,
      );
    } catch {
      toast.error("Failed to delete ghost record");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(songId);
        return next;
      });
    }
  };

  const recoverSong = async (song: IncompleteSong) => {
    setReprocessingIds((prev) => new Set(prev).add(song.id));
    try {
      let res: Response;
      if (song.video_id) {
        // Re-download from YouTube and reprocess
        res = await fetch(`/api/songs/${song.id}/replace-youtube`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            video_id: song.video_id,
            title: song.title,
            artist: song.artist,
            engine_type: "demucs",
          }),
        });
        if (!res.ok) throw new Error("Re-download failed");
        toast.success("Re-download & reprocess job dispatched");
      } else {
        // original.mp3 exists, just reprocess
        res = await fetch(`/api/songs/${song.id}/reprocess`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ engine_type: "demucs" }),
        });
        if (!res.ok) throw new Error("Reprocess failed");
        toast.success("Reprocess job dispatched");
      }
      setAuditResult((prev) =>
        prev
          ? {
            ...prev,
            incomplete_songs: prev.incomplete_songs.filter((s) => s.id !== song.id),
            summary: {
              ...prev.summary,
              incomplete_count: prev.summary.incomplete_count - 1,
            },
          }
          : null,
      );
    } catch {
      toast.error("Failed to dispatch recovery job");
    } finally {
      setReprocessingIds((prev) => {
        const next = new Set(prev);
        next.delete(song.id);
        return next;
      });
    }
  };

  const bulkDeleteOrphans = async () => {
    const dirs = [...selectedOrphans];
    setIsBulkDeleting(true);
    try {
      const res = await fetch("/api/songs/orphan-bulk", {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ dir_names: dirs }),
      });
      if (!res.ok) throw new Error("Bulk delete failed");
      const { deleted, skipped } = (await res.json()) as {
        deleted: number;
        skipped: number;
      };
      toast.success(
        `Deleted ${deleted} orphaned director${deleted !== 1 ? "ies" : "y"}${skipped > 0 ? ` (${skipped} skipped)` : ""}`,
      );
      setAuditResult((prev) =>
        prev
          ? {
            ...prev,
            orphaned_directories: prev.orphaned_directories.filter(
              (d) => !selectedOrphans.has(d.dir_name),
            ),
            summary: {
              ...prev.summary,
              orphaned_count: prev.summary.orphaned_count - deleted,
            },
          }
          : null,
      );
      setSelectedOrphans(new Set());
    } catch {
      toast.error("Failed to bulk delete orphaned directories");
    } finally {
      setIsBulkDeleting(false);
    }
  };

  const bulkDeleteGhosts = async () => {
    const ids = [...selectedGhosts];
    setIsBulkDeleting(true);
    try {
      const res = await fetch("/api/songs/ghost-bulk", {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ song_ids: ids }),
      });
      if (!res.ok) throw new Error("Bulk delete failed");
      const { deleted, skipped } = (await res.json()) as {
        deleted: number;
        skipped: number;
      };
      toast.success(
        `Deleted ${deleted} ghost record${deleted !== 1 ? "s" : ""}${skipped > 0 ? ` (${skipped} skipped)` : ""}`,
      );
      setAuditResult((prev) =>
        prev
          ? {
            ...prev,
            ghost_records: prev.ghost_records.filter(
              (r) => !selectedGhosts.has(r.id),
            ),
            summary: {
              ...prev.summary,
              ghost_count: prev.summary.ghost_count - deleted,
            },
          }
          : null,
      );
      setSelectedGhosts(new Set());
    } catch {
      toast.error("Failed to bulk delete ghost records");
    } finally {
      setIsBulkDeleting(false);
    }
  };

  const { orphaned_directories, ghost_records, incomplete_songs, summary } =
    auditResult ?? {
      orphaned_directories: [],
      ghost_records: [],
      incomplete_songs: [],
      summary: null,
    };

  const isClean =
    auditResult &&
    summary &&
    summary.orphaned_count === 0 &&
    summary.ghost_count === 0 &&
    summary.incomplete_count === 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Library Audit</h2>
          <p className="text-sm text-muted-foreground">
            Cross-reference files on disk with database records to find
            discrepancies.
          </p>
        </div>
        <Button
          onClick={() => auditMutation.mutate()}
          disabled={auditMutation.isPending}
        >
          <HardDrive className="mr-2 h-4 w-4" />
          {auditMutation.isPending ? "Scanning..." : "Run Audit"}
        </Button>
      </div>

      {/* Summary bar */}
      {summary && (
        <div className="flex flex-wrap gap-3 rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
          <span>{summary.total_directories} directories on disk</span>
          <span>·</span>
          <span>{summary.total_db_songs} records in database</span>
          <span>·</span>
          <span
            className={
              summary.orphaned_count > 0 ? "font-medium text-orange-500" : ""
            }
          >
            {summary.orphaned_count} orphaned
          </span>
          <span>·</span>
          <span
            className={summary.ghost_count > 0 ? "font-medium text-red-500" : ""}
          >
            {summary.ghost_count} ghost records
          </span>
          <span>·</span>
          <span
            className={
              summary.incomplete_count > 0 ? "font-medium text-yellow-500" : ""
            }
          >
            {summary.incomplete_count} incomplete
          </span>
        </div>
      )}

      {/* Orphaned directories */}
      {orphaned_directories.length > 0 && (
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 font-medium">
              <Checkbox
                checked={
                  selectedOrphans.size === orphaned_directories.length
                    ? true
                    : selectedOrphans.size > 0
                      ? "indeterminate"
                      : false
                }
                onCheckedChange={(checked) => {
                  if (checked) {
                    setSelectedOrphans(
                      new Set(orphaned_directories.map((d) => d.dir_name)),
                    );
                  } else {
                    setSelectedOrphans(new Set());
                  }
                }}
                aria-label="Select all orphaned directories"
              />
              <Badge variant="outline" className="border-orange-500 text-orange-500">
                {orphaned_directories.length}
              </Badge>
              Orphaned Directories
              <span className="text-xs font-normal text-muted-foreground">
                — files on disk with no database record
              </span>
            </h3>
            {selectedOrphans.size > 0 && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={isBulkDeleting}
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    {isBulkDeleting
                      ? "Deleting..."
                      : `Delete Selected (${selectedOrphans.size})`}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete {selectedOrphans.size} orphaned director{selectedOrphans.size !== 1 ? "ies" : "y"}?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently delete {selectedOrphans.size} director{selectedOrphans.size !== 1 ? "ies" : "y"} and all their files from disk. This action cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      onClick={bulkDeleteOrphans}
                    >
                      Delete All Selected
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
          <div className="divide-y rounded-lg border">
            {orphaned_directories.map((dir) => (
              <div
                key={dir.dir_name}
                className="flex items-center justify-between px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <Checkbox
                    checked={selectedOrphans.has(dir.dir_name)}
                    onCheckedChange={(checked) => {
                      setSelectedOrphans((prev) => {
                        const next = new Set(prev);
                        if (checked) next.add(dir.dir_name);
                        else next.delete(dir.dir_name);
                        return next;
                      });
                    }}
                    aria-label={`Select ${dir.dir_name}`}
                  />
                  <div>
                    <p className="font-mono text-sm">{dir.dir_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {dir.files.length} file{dir.files.length !== 1 ? "s" : ""} ·{" "}
                      {formatBytes(dir.total_size_bytes)}
                    </p>
                  </div>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={deletingIds.has(dir.dir_name) || isBulkDeleting}
                  onClick={() => deleteOrphan(dir.dir_name)}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  {deletingIds.has(dir.dir_name) ? "Deleting..." : "Delete"}
                </Button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Ghost records */}
      {ghost_records.length > 0 && (
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 font-medium">
              <Checkbox
                checked={
                  selectedGhosts.size === ghost_records.length
                    ? true
                    : selectedGhosts.size > 0
                      ? "indeterminate"
                      : false
                }
                onCheckedChange={(checked) => {
                  if (checked) {
                    setSelectedGhosts(new Set(ghost_records.map((r) => r.id)));
                  } else {
                    setSelectedGhosts(new Set());
                  }
                }}
                aria-label="Select all ghost records"
              />
              <Badge variant="outline" className="border-red-500 text-red-500">
                {ghost_records.length}
              </Badge>
              Ghost Records
              <span className="text-xs font-normal text-muted-foreground">
                — database records with no files on disk
              </span>
            </h3>
            {selectedGhosts.size > 0 && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={isBulkDeleting}
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    {isBulkDeleting
                      ? "Deleting..."
                      : `Delete Selected (${selectedGhosts.size})`}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete {selectedGhosts.size} ghost record{selectedGhosts.size !== 1 ? "s" : ""}?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently remove {selectedGhosts.size} database record{selectedGhosts.size !== 1 ? "s" : ""} with no files on disk. This action cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      onClick={bulkDeleteGhosts}
                    >
                      Delete All Selected
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
          <div className="divide-y rounded-lg border">
            {ghost_records.map((record) => (
              <div
                key={record.id}
                className="flex items-center justify-between px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <Checkbox
                    checked={selectedGhosts.has(record.id)}
                    onCheckedChange={(checked) => {
                      setSelectedGhosts((prev) => {
                        const next = new Set(prev);
                        if (checked) next.add(record.id);
                        else next.delete(record.id);
                        return next;
                      });
                    }}
                    aria-label={`Select ${record.title}`}
                  />
                  <div>
                    <p className="text-sm font-medium">{record.title}</p>
                    <p className="text-xs text-muted-foreground">{record.artist}</p>
                  </div>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={deletingIds.has(record.id) || isBulkDeleting}
                  onClick={() => deleteGhost(record.id)}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  {deletingIds.has(record.id) ? "Deleting..." : "Delete"}
                </Button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Incomplete songs */}
      {incomplete_songs.length > 0 && (
        <section className="space-y-2">
          <h3 className="flex items-center gap-2 font-medium">
            <Badge variant="outline" className="border-yellow-500 text-yellow-500">
              {incomplete_songs.length}
            </Badge>
            Incomplete Songs
            <span className="text-xs font-normal text-muted-foreground">
              — missing one or more audio files
            </span>
          </h3>
          <div className="divide-y rounded-lg border">
            {incomplete_songs.map((song) => (
              <div
                key={song.id}
                className="flex items-center justify-between px-4 py-3"
              >
                <div className="space-y-1">
                  <p className="text-sm font-medium">{song.title}</p>
                  <p className="text-xs text-muted-foreground">{song.artist}</p>
                  <div className="flex flex-wrap gap-1">
                    {song.missing_files.map((f) => (
                      <Badge
                        key={f}
                        variant="outline"
                        className="text-xs text-muted-foreground"
                      >
                        missing: {f}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {song.has_original || song.video_id ? (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={reprocessingIds.has(song.id)}
                      onClick={() => recoverSong(song)}
                    >
                      <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                      {reprocessingIds.has(song.id)
                        ? "Dispatching..."
                        : song.video_id && !song.has_original
                          ? "Re-download & Reprocess"
                          : "Reprocess"}
                    </Button>
                  ) : (
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <AlertCircle className="h-3.5 w-3.5" />
                      Unrecoverable
                    </div>
                  )}
                  {/* Delete Button */}
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={deletingIds.has(song.id)}
                    onClick={() => deleteGhost(song.id)}
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    {deletingIds.has(song.id) ? "Deleting..." : "Delete"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Clean state */}
      {isClean && (
        <div className="py-12 text-center text-muted-foreground">
          <HardDrive className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="font-medium">Library is clean</p>
          <p className="text-sm">All files and database records are in sync.</p>
        </div>
      )}

      {/* Empty state (before first run) */}
      {!auditResult && !auditMutation.isPending && (
        <div className="py-12 text-center text-muted-foreground">
          <HardDrive className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">
            Run an audit to check for library inconsistencies.
          </p>
        </div>
      )}
    </div>
  );
};
