import { useApiQuery } from "@/hooks/api/useApi";
import type { Song } from "@/types/Song";
import type { BatchRun, JobKind } from "./useBatchJobs";

/*
 * Server state the admin sections and the sidebar share. A section and the
 * sidebar call the same hook, so they read one cache entry.
 *
 * The three scans (disk check, metadata, duplicates) are expensive, so they
 * only run when someone presses the button: `enabled: false` plus a manual
 * `refetch()`. Their results never go stale or get collected, so leaving a
 * section and coming back shows the last result instead of an empty page.
 */

const KEEP_UNTIL_RESCAN = {
  enabled: false,
  staleTime: Infinity,
  gcTime: Infinity,
} as const;

// --- AcoustID review lists ---

export type FingerprintStatus =
  | "suggested"
  | "ambiguous"
  | "no_match"
  | "failed";

export const ACOUSTID_SONGS_KEY = "admin-acoustid-songs";

export function useSongsByFingerprintStatus(status: FingerprintStatus) {
  return useApiQuery<Song[], readonly [string, FingerprintStatus]>(
    [ACOUSTID_SONGS_KEY, status] as const,
    `songs/by-fingerprint-status?status=${status}&limit=500`,
  );
}

// --- Disk check (library audit) ---

export interface OrphanedDir {
  dir_name: string;
  files: string[];
  total_size_bytes: number;
}

export interface GhostRecord {
  id: string;
  title: string;
  artist: string;
  date_added: string | null;
}

export interface IncompleteSong {
  id: string;
  title: string;
  artist: string;
  missing_files: string[];
  has_original: boolean;
  video_id: string | null;
}

export interface AuditSummary {
  total_directories: number;
  total_db_songs: number;
  orphaned_count: number;
  ghost_count: number;
  incomplete_count: number;
}

export interface AuditResult {
  orphaned_directories: OrphanedDir[];
  ghost_records: GhostRecord[];
  incomplete_songs: IncompleteSong[];
  summary: AuditSummary;
}

export const LIBRARY_AUDIT_KEY = ["admin-scan", "library-audit"] as const;

export function useLibraryAudit() {
  return useApiQuery<AuditResult, typeof LIBRARY_AUDIT_KEY>(
    LIBRARY_AUDIT_KEY,
    "songs/library-audit",
    KEEP_UNTIL_RESCAN,
  );
}

export function countAuditIssues(summary: AuditSummary): number {
  return (
    summary.orphaned_count + summary.ghost_count + summary.incomplete_count
  );
}

// --- Metadata scan ---

export type Severity = "error" | "warning" | "info";

export interface MetadataIssue {
  type: string;
  label: string;
  severity: Severity;
}

export interface FlaggedSong {
  id: string;
  title: string;
  artist: string;
  date_added: string | null;
  source: string | null;
  status: string;
  issues: MetadataIssue[];
}

export interface MetadataAuditResult {
  flagged_songs: FlaggedSong[];
  summary: Record<string, number>;
  total_songs_scanned: number;
  total_flagged: number;
}

export const METADATA_AUDIT_KEY = ["admin-scan", "metadata-audit"] as const;

export function useMetadataAudit() {
  return useApiQuery<MetadataAuditResult, typeof METADATA_AUDIT_KEY>(
    METADATA_AUDIT_KEY,
    "songs/metadata-audit",
    KEEP_UNTIL_RESCAN,
  );
}

// --- Duplicates scan ---

export interface DuplicateSong {
  id: string;
  title: string;
  artist: string;
  date_added: string | null;
  source: string | null;
}

export interface DuplicatesResult {
  clusters: DuplicateSong[][];
  total_clusters: number;
  total_duplicates: number;
}

export const DUPLICATES_KEY = ["admin-scan", "duplicates"] as const;

export function useDuplicatesScan() {
  return useApiQuery<DuplicatesResult, typeof DUPLICATES_KEY>(
    DUPLICATES_KEY,
    "songs/duplicates",
    KEEP_UNTIL_RESCAN,
  );
}

// --- Failed songs ---

export const FAILED_SONGS_KEY = ["admin-failed-songs"] as const;

/** Songs whose download or processing failed; the songbook hides them. */
export function useFailedSongs() {
  return useApiQuery<Song[], typeof FAILED_SONGS_KEY>(
    FAILED_SONGS_KEY,
    "admin/songs/failed",
  );
}

// --- Overview ---

export type ScanKind = "disk_check" | "metadata_scan" | "duplicates";

/** A finished hand-run scan, recorded the way batch runs are. */
export type ScanRun = Omit<BatchRun, "kind"> & { kind: ScanKind };

export interface AdminOverview {
  /** Songs guests can see: everything but failed ones. */
  librarySize: number;
  needsYou: {
    lyricsReports: number;
    acoustid: {
      suggested: number;
      ambiguous: number;
      noMatch: number;
      failed: number;
    };
    failedSongs: number;
    alignmentRepair: number;
  };
  jobs: {
    kind: JobKind;
    coverage: { have: number; of: number };
    activeRun: BatchRun | null;
  }[];
  songsAdded: {
    /** 12 weeks, oldest first; the last is the past seven days. */
    weeks: { start: string; count: number }[];
    recent: {
      id: string;
      title: string;
      artist: string;
      status: string;
      dateAdded: string;
    }[];
  };
  /** Each scan's last finished run; null if it has never run. */
  scans: Record<ScanKind, ScanRun | null>;
}

export const OVERVIEW_KEY = ["admin-overview"] as const;

// Quick while a batch run moves, so its bar does too.
const OVERVIEW_ACTIVE_POLL_MS = 3000;
const OVERVIEW_IDLE_POLL_MS = 30000;

/** Counts for the admin landing page. Refetches whenever the page mounts,
 * so a scan run in its section shows up on the way back. */
export function useAdminOverview() {
  return useApiQuery<AdminOverview, typeof OVERVIEW_KEY>(
    OVERVIEW_KEY,
    "admin/overview",
    {
      refetchInterval: (query) =>
        query.state.data?.jobs.some((job) => job.activeRun)
          ? OVERVIEW_ACTIVE_POLL_MS
          : OVERVIEW_IDLE_POLL_MS,
    },
  );
}
