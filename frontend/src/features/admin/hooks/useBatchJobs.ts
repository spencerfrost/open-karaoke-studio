import { useQueryClient } from "@tanstack/react-query";
import { apiSend, useApiMutation, useApiQuery } from "@/hooks/api/useApi";

export type JobKind =
  | "duration"
  | "loudness"
  | "vocal_range"
  | "song_albums"
  | "album_covers"
  | "fingerprint"
  | "artist_images"
  | "lyrics_alignment";

export type RunMode = "missing" | "repair" | "all";

export type RunStatus = "queued" | "running" | "done" | "failed" | "cancelled";

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
