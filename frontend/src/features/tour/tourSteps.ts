/**
 * tourSteps - the guided demo's steps and what moves it from one to the next.
 *
 * The tour never moves on a "Next" click. Each step waits on something the app
 * does: a job from this session shows up, the song comes out ready, the count
 * starts, the song plays, the singer's phone opens its controls, the mix moves.
 * The one click it asks for is the first one, "Sound is on", because a browser
 * needs a click before it lets a page play sound.
 *
 * Steps only ever move forward. The visitor can take a shortcut (pick a song
 * off the wheel instead of waiting for theirs) and the tour jumps ahead to
 * match, but nothing the app does later sends it back.
 *
 * Pure functions, so the tests can drive the whole tour without a stage.
 */

import type { TrackerRow } from "@/features/songs/processing/jobTimeline";

export const TOUR_STEPS = [
  /** Turn the sound on. The click is the gesture that lets audio play. */
  "sound",
  /** Scan the QR code and add a song from the phone. */
  "scan",
  /** The song is processing; spin the wheel meanwhile. */
  "wheel",
  /** Their song is ready: Sing this. */
  "ready",
  /** The 3-2-1 before the song. */
  "countdown",
  /** The song plays; waiting for the singer's phone to open its controls. */
  "controls",
  /** The phone is on the controls: move the mix and hear it on the stage. */
  "mix",
  /** The stack, the repo, the docs, keep exploring. */
  "end",
  /** Finished or skipped. Nothing shows. */
  "done",
] as const;

export type TourStep = (typeof TOUR_STEPS)[number];

const order = (step: TourStep) => TOUR_STEPS.indexOf(step);

export const isTourStep = (value: unknown): value is TourStep =>
  typeof value === "string" &&
  (TOUR_STEPS as readonly string[]).includes(value);

/** What the app is doing right now, as far as the tour cares. */
export interface TourSignals {
  /** A song from this session is in the processing list. */
  hasMyJob: boolean;
  /** A song from this session finished and came out playable. */
  myReadySong: boolean;
  /** The stage is counting into a song. */
  countingDown: boolean;
  /** A song is playing on the stage. */
  isPlaying: boolean;
  /**
   * Whether the current singer's phone is showing the performance controls.
   * Null when the singer has no phone linked (a name typed in on the stage,
   * or a song started from the stage itself): there's no phone to wait for.
   */
  singerOnControls: boolean | null;
  /** A volume moved since the song started playing. */
  mixChanged: boolean;
  /** The song that was playing has ended. */
  songEnded: boolean;
}

/** The furthest step the app's state shows the visitor has reached. */
function reachedStep(signals: TourSignals): TourStep {
  if (signals.isPlaying) {
    return signals.singerOnControls === false ? "controls" : "mix";
  }
  if (signals.countingDown) return "countdown";
  if (signals.myReadySong) return "ready";
  if (signals.hasMyJob) return "wheel";
  return "scan";
}

/**
 * The step to show next, given the current one and what the app is doing.
 *
 * - `sound` only leaves on its own button (see `afterSoundOn`).
 * - `controls` and `mix` lead to the end card once the mix moves, or once the
 *   song ends without anyone touching it, so the tour still finishes.
 * - `end` only leaves on "Keep exploring"; `done` is final.
 */
export function nextStep(current: TourStep, signals: TourSignals): TourStep {
  if (current === "sound" || current === "end" || current === "done") {
    return current;
  }
  if (
    (current === "controls" || current === "mix") &&
    (signals.mixChanged || signals.songEnded)
  ) {
    return "end";
  }
  const reached = reachedStep(signals);
  return order(reached) > order(current) ? reached : current;
}

/** The step after the sound prompt: wherever the app already is. */
export function afterSoundOn(signals: TourSignals): TourStep {
  return nextStep("scan", signals);
}

/** Steps where the visitor is still waiting on a song of their own. */
export const isWaitingForSong = (step: TourStep) =>
  step === "scan" || step === "wheel";

// --- Fallback --------------------------------------------------------------

/**
 * Several songs ahead of theirs in the job queue: each takes a GPU for about
 * half a minute to a minute, so three ahead is a few minutes of waiting.
 */
export const BUSY_AHEAD = 3;

/**
 * Their song has said nothing new (no step, progress or queue position change)
 * for this long. Separation reports progress every few seconds, so two minutes
 * of silence means the worker is stuck, retrying, or the GPU is taken.
 */
export const STALL_MS = 2 * 60 * 1000;

export type FallbackReason = "quota" | "busy" | "failed";

export interface FallbackInputs {
  step: TourStep;
  /** This session's rows from the processing list. */
  myRows: TrackerRow[];
  /** How the first finished row of ours came out, once the library says. */
  myFinishedOutcome: "ready" | "failed" | "pending" | null;
  /** New songs this demo can still add, or null while unknown. */
  quota: { sessionRemaining: number; dailyRemaining: number } | null;
  /** When our in-flight row last changed, ms since epoch. */
  lastProgressAt: number | null;
  now: number;
}

/**
 * Why the tour should offer a library song instead of waiting, or null to keep
 * waiting. Only while the visitor is waiting on a song of their own.
 *
 * - `quota`: the demo can't add any new song, and none of theirs is on the way.
 * - `failed`: their song didn't come out, and no other of theirs is on the way.
 * - `busy`: their song is still waiting with several ahead of it, or has gone
 *   quiet for `STALL_MS`. Their song keeps going; the tour only offers another.
 */
export function fallbackReason(inputs: FallbackInputs): FallbackReason | null {
  const { step, myRows, myFinishedOutcome, quota, lastProgressAt, now } =
    inputs;
  if (!isWaitingForSong(step)) return null;
  if (myFinishedOutcome === "ready") return null;

  const inFlight = myRows.filter((r) => r.phase !== "finished");

  if (inFlight.length === 0) {
    if (myFinishedOutcome === "failed") return "failed";
    if (myFinishedOutcome === "pending") return null;
    if (quota && (quota.sessionRemaining <= 0 || quota.dailyRemaining <= 0)) {
      return "quota";
    }
    return null;
  }

  const first = inFlight[0];
  if (first.phase === "waiting" && first.ahead >= BUSY_AHEAD) return "busy";
  if (lastProgressAt !== null && now - lastProgressAt >= STALL_MS) {
    return "busy";
  }
  return null;
}

/**
 * What counts as "said something new" for the stall rule. Anything that would
 * change the row on screen.
 */
export function progressSignature(row: TrackerRow | undefined): string | null {
  if (!row) return null;
  return [row.phase, row.step, row.progress, row.ahead].join("|");
}

// --- The library song it offers instead ------------------------------------

export interface FallbackCandidate {
  id: string;
  status?: string;
  syncedLyrics?: string;
}

/**
 * The library song to offer: a playable one, preferring songs with timed
 * lyrics so the stage looks like it should. Chosen by `seed` (the session), so
 * it stays the same song across re-renders and a reload, and two visitors at
 * once don't all get the same one.
 */
export function pickFallbackSong<T extends FallbackCandidate>(
  songs: T[],
  seed: string,
  excludeIds: string[] = [],
): T | null {
  const playable = songs.filter(
    (s) => s.status === "processed" && !excludeIds.includes(s.id),
  );
  const withLyrics = playable.filter((s) => Boolean(s.syncedLyrics));
  const pool = withLyrics.length ? withLyrics : playable;
  if (pool.length === 0) return null;
  let hash = 0;
  for (const ch of seed) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return pool[hash % pool.length];
}

// --- Docs links ------------------------------------------------------------

/**
 * A docs page on the published VitePress site, or null when this build has no
 * docs URL (`VITE_DOCS_URL`), in which case the links are hidden.
 */
export function docsLink(
  base: string | undefined,
  page: string | undefined,
): string | null {
  if (!base || page === undefined) return null;
  return `${base.endsWith("/") ? base : `${base}/`}${page}`;
}
