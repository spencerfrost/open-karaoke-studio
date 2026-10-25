/**
 * jobTimeline - one timeline per song, built from the jobs feed.
 *
 * `/ws/jobs` sends in-flight jobs only: a job is deleted when it finishes, so
 * "done" shows up as the song's jobs leaving the feed. A song can have two jobs
 * at once, because lyrics alignment runs as its own job (`step: "align"`) and
 * starts while separation is still going. Both are folded into one entry here.
 *
 * Ownership comes from `owner_tag`, an opaque per-session tag (the feed never
 * carries the join code). The alignment job has no tag of its own, so an entry
 * keeps the tag it first saw from the song's main job.
 *
 * Pure functions, so the store and the tests share them.
 */

import {
  JOB_STEPS,
  type JobStep,
  type SongProcessingStatus,
} from "@/types/Song";

export interface TrackedSong {
  songId: string;
  title?: string;
  artist?: string;
  /** The song's in-flight jobs. Empty once it has finished. */
  jobs: SongProcessingStatus[];
  /** The session that added it, sticky across the song's jobs. */
  ownerTag: string | null;
  /** When it joined the job queue, for queue order. */
  queuedAt: number;
  /** When its last job left the feed; null while it's still in the pipeline. */
  finishedAt: number | null;
}

export type TrackedSongs = Record<string, TrackedSong>;

/** How long a finished song of ours keeps its row if nobody acts on it. */
export const FINISHED_TTL_MS = 60 * 60 * 1000;

const isInFlight = (job: SongProcessingStatus) =>
  job.status === "queued" || job.status === "processing";

const stepIndex = (job: SongProcessingStatus) =>
  job.step ? JOB_STEPS.indexOf(job.step) : JOB_STEPS.length;

const parseTime = (iso: string | undefined) => {
  const t = iso ? Date.parse(iso) : NaN;
  return Number.isNaN(t) ? null : t;
};

/** Fold the latest jobs feed into the tracked songs. */
export function mergeJobs(
  prev: TrackedSongs,
  jobs: SongProcessingStatus[],
  now: number,
): TrackedSongs {
  const groups = new Map<string, SongProcessingStatus[]>();
  for (const job of jobs) {
    if (!job.song_id || !isInFlight(job)) continue;
    const group = groups.get(job.song_id);
    if (group) group.push(job);
    else groups.set(job.song_id, [job]);
  }

  const next: TrackedSongs = {};
  for (const [songId, group] of groups) {
    const before = prev[songId];
    group.sort((a, b) => stepIndex(a) - stepIndex(b));
    const created = group
      .map((j) => parseTime(j.createdAt))
      .filter((t): t is number => t !== null);
    const stillQueued = before && before.finishedAt === null;
    next[songId] = {
      songId,
      title: group.find((j) => j.title)?.title ?? before?.title,
      artist: group.find((j) => j.artist)?.artist ?? before?.artist,
      jobs: group,
      ownerTag:
        group.find((j) => j.ownerTag)?.ownerTag ?? before?.ownerTag ?? null,
      queuedAt: stillQueued
        ? before.queuedAt
        : created.length
          ? Math.min(...created)
          : now,
      finishedAt: null,
    };
  }

  for (const [songId, before] of Object.entries(prev)) {
    if (next[songId]) continue;
    // Nobody can claim an untagged song, so it has no finished row to show.
    if (!before.ownerTag) continue;
    const finishedAt = before.finishedAt ?? now;
    if (now - finishedAt > FINISHED_TTL_MS) continue;
    next[songId] =
      before.finishedAt === null ? { ...before, jobs: [], finishedAt } : before;
  }

  return next;
}

export type TrackerPhase = "waiting" | "working" | "finished";

export interface TrackerRow {
  songId: string;
  title?: string;
  artist?: string;
  /** Added by this device's session. */
  isMine: boolean;
  phase: TrackerPhase;
  /** The step it's on; null when the server didn't say. */
  step: JobStep | null;
  /** 1-based position of `step` in the pipeline. */
  stepNumber: number | null;
  stepCount: number;
  /** Progress of the current job, 0-100. */
  progress: number;
  /** The pipeline's own detail line ("Separating: Model 1/2"). */
  detail?: string;
  /** Songs ahead of this one in the job queue. */
  ahead: number;
}

/**
 * The rows to show for one session: every song still in the pipeline, plus
 * this session's own finished songs. Other sessions' songs drop out when done.
 * Finished rows come first, so "Sing this" is never below the fold; the rest
 * are in queue order.
 */
export function buildTrackerRows(
  songs: TrackedSongs,
  myOwnerTag: string | null | undefined,
): TrackerRow[] {
  const isMine = (s: TrackedSong) =>
    Boolean(myOwnerTag) && s.ownerTag === myOwnerTag;

  const inPipeline = Object.values(songs)
    .filter((s) => s.finishedAt === null)
    .sort((a, b) => a.queuedAt - b.queuedAt);
  const finished = Object.values(songs)
    .filter((s) => s.finishedAt !== null && isMine(s))
    .sort((a, b) => (a.finishedAt ?? 0) - (b.finishedAt ?? 0));

  const finishedRows: TrackerRow[] = finished.map((s) => ({
    songId: s.songId,
    title: s.title,
    artist: s.artist,
    isMine: true,
    phase: "finished",
    step: null,
    stepNumber: null,
    stepCount: JOB_STEPS.length,
    progress: 100,
    ahead: 0,
  }));

  const pipelineRows: TrackerRow[] = inPipeline.map((s, index) => {
    const running = s.jobs.filter((j) => j.status === "processing");
    // The earliest step that's running; if nothing is, the earliest queued.
    const current = (running.length ? running : s.jobs)[0];
    const step = current?.step ?? null;
    return {
      songId: s.songId,
      title: s.title,
      artist: s.artist,
      isMine: isMine(s),
      phase: running.length ? "working" : "waiting",
      step,
      stepNumber: step ? JOB_STEPS.indexOf(step) + 1 : null,
      stepCount: JOB_STEPS.length,
      progress: current?.progress ?? 0,
      detail: current?.message,
      ahead: index,
    };
  });

  return [...finishedRows, ...pipelineRows];
}

/** The job a song's library card should reflect: separation over alignment. */
export function primaryJob(
  jobs: SongProcessingStatus[],
): SongProcessingStatus | undefined {
  return [...jobs].sort((a, b) => stepIndex(a) - stepIndex(b))[0];
}
