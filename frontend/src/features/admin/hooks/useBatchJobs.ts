import { useQueryClient } from "@tanstack/react-query";
import { apiSend, useApiMutation, useApiQuery } from "@/hooks/api/useApi";

export type JobKind =
  | "duration"
  | "loudness"
  | "singing_map"
  | "vocal_range"
  | "song_albums"
  | "fingerprint"
  | "artist_images"
  | "lyrics_alignment"
  | "artist_credits";

export type RunMode =
  | "missing"
  | "repair"
  | "retry"
  | "all"
  | "preview"
  | "apply";

/**
 * "interrupted": the worker stopped mid-run; it carries on when the worker starts.
 * "pausing": Pause was pressed; it stops after the song it's on.
 * "paused": stopped by Pause, GPU memory given back; it waits for Resume.
 */
export type RunStatus =
  | "queued"
  | "running"
  | "interrupted"
  | "pausing"
  | "paused"
  | "done"
  | "failed"
  | "cancelled";

export type RepairReason =
  | "no_word_timing"
  | "plain_only"
  | "plain_timing"
  | "words_mismatch"
  | "reported";

export interface BatchRun {
  id: number;
  kind: JobKind;
  mode: RunMode;
  status: RunStatus;
  /** null until the task has looked at what it covers. */
  total: number | null;
  done: number;
  failed: number;
  error: string | null;
  /** Hand-run scans only: how many problems the scan found. */
  issues: number | null;
  /** A run that queued one job per song and waits on them (lyrics
   * alignment): how many haven't finished. null for any other run. */
  waiting: number | null;
  /** A finished run that saved a report (the artist credits rebuild). */
  hasReport: boolean;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface BatchJob {
  kind: JobKind;
  modes: RunMode[];
  coverage: { have: number; of: number };
  /** How many songs (or artists) a run in each mode would work through. */
  modeCounts: Partial<Record<RunMode, number>>;
  /** Lyrics alignment only. */
  repairReasons?: Record<RepairReason, number>;
  lastRun: BatchRun | null;
  activeRun: BatchRun | null;
}

export interface WorkerStatus {
  brokerReachable: boolean;
  workers: string[];
  queues: { queue: string; workers: string[] }[];
}

/** One song's credits, as the artist credits report lists them. */
export interface ReportCredit {
  name: string;
  role: "primary" | "featured";
}

export interface ReportSong {
  songId: string;
  title: string;
  artist: string;
  credits: ReportCredit[];
}

/** The numbers the artist credits rebuild counts, before and after. */
export interface LibraryNumbers {
  songs: number;
  songsWithRecording: number;
  artists: number;
  artistsLinked: number;
  artistsLinkedToNothing: number;
  featuredOnly: number;
  featuredOnlyOnOneSong: number;
  groupedGuestCredits: number;
  featInTitle: number;
  aliases: number;
  /** Missing from reports saved before shows were part of the run. */
  songsWithShow?: number;
}

/** What an artist credits run changed, or would change in a preview. */
export interface ArtistCreditsReport {
  mode: "preview" | "apply";
  before: LibraryNumbers;
  after: LibraryNumbers;
  songs: {
    counts: Partial<
      Record<
        "recording" | "parsed" | "kept" | "changed" | "lookup_failed",
        number
      >
    >;
    changed: {
      songId: string;
      title: string;
      artist: string;
      confirmed: boolean;
      source: "recording" | "parsed";
      before: ReportCredit[];
      after: ReportCredit[];
    }[];
  };
  merges: {
    from: string;
    into: string;
    reason: "musicbrainz" | "spelling";
    credits: number;
  }[];
  renames: { from: string; to: string }[];
  deleted: { count: number; names: string[] };
  unsure: { count: number; songs: ReportSong[] };
  disagree: { count: number; songs: ReportSong[] };
  /** Missing from reports saved before shows were part of the run. */
  shows?: {
    counts: Partial<Record<"changed" | "hand_set", number>>;
    changed: {
      songId: string;
      title: string;
      artist: string;
      before: string | null;
      after: string | null;
    }[];
  };
}

const JOBS_KEY = ["admin-jobs"] as const;
const RUNS_KEY = ["admin-jobs", "runs"] as const;
const WORKERS_KEY = ["admin-workers"] as const;

// Quick while something runs, so progress moves. Slow otherwise, which still
// picks up alignment finishing song by song after its run has queued them.
const ACTIVE_POLL_MS = 3000;
const IDLE_POLL_MS = 30000;
const RUNS_POLL_MS = 10000;

export function useBatchJobs() {
  return useApiQuery<{ jobs: BatchJob[] }, typeof JOBS_KEY>(
    JOBS_KEY,
    "admin/jobs",
    {
      refetchInterval: (query) =>
        query.state.data?.jobs.some((job) => job.activeRun)
          ? ACTIVE_POLL_MS
          : IDLE_POLL_MS,
    },
  );
}

export function useRecentRuns() {
  return useApiQuery<{ runs: BatchRun[] }, typeof RUNS_KEY>(
    RUNS_KEY,
    "admin/jobs/runs?limit=15",
    { refetchInterval: RUNS_POLL_MS },
  );
}

export function useWorkerStatus() {
  return useApiQuery<WorkerStatus, typeof WORKERS_KEY>(
    WORKERS_KEY,
    "admin/workers",
    { refetchInterval: IDLE_POLL_MS },
  );
}

export function useRunReport(runId: number | null) {
  return useApiQuery<
    { run: BatchRun; report: ArtistCreditsReport },
    readonly ["admin-jobs", "report", number | null]
  >(
    ["admin-jobs", "report", runId] as const,
    `admin/jobs/runs/${runId}/report`,
    {
      enabled: runId !== null,
      // A finished run's report never changes.
      staleTime: Infinity,
    },
  );
}

/** Invalidates the jobs list and recent runs (they share a key prefix). */
export function useRunJob() {
  const queryClient = useQueryClient();
  return useApiMutation<{ run: BatchRun }, { kind: JobKind; mode: RunMode }>(
    "admin/jobs/:kind/run",
    "post",
    {
      mutationFn: ({ kind, mode }) =>
        apiSend(`admin/jobs/${kind}/run?mode=${mode}`, "post"),
      onSettled: () => queryClient.invalidateQueries({ queryKey: JOBS_KEY }),
    },
  );
}

/** Pause or Resume a run; invalidates the jobs list and recent runs. */
function useRunAction(action: "pause" | "resume") {
  const queryClient = useQueryClient();
  return useApiMutation<{ run: BatchRun }, number>(
    `admin/jobs/runs/:id/${action}`,
    "post",
    {
      mutationFn: (runId) =>
        apiSend(`admin/jobs/runs/${runId}/${action}`, "post"),
      onSettled: () => queryClient.invalidateQueries({ queryKey: JOBS_KEY }),
    },
  );
}

export const usePauseRun = () => useRunAction("pause");
export const useResumeRun = () => useRunAction("resume");

export function useCancelRun() {
  const queryClient = useQueryClient();
  return useApiMutation<{ run: BatchRun }, number>(
    "admin/jobs/runs/:id/cancel",
    "post",
    {
      mutationFn: (runId) => apiSend(`admin/jobs/runs/${runId}/cancel`, "post"),
      onSettled: () => queryClient.invalidateQueries({ queryKey: JOBS_KEY }),
    },
  );
}
