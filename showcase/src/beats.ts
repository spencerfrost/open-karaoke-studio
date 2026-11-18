import beatGrid from "./data/beats.json";

/** The soundtrack's beat times, in song seconds (librosa, from the instrumental). */
export const BEATS: number[] = beatGrid.beats;

/** Index of the beat nearest a song time. */
export const nearestBeat = (t: number) =>
  BEATS.reduce((best, b, i) => (Math.abs(b - t) < Math.abs(BEATS[best] - t) ? i : best), 0);

/**
 * A shot's beats as frames from the shot's start: `beats[0]` is 0, the shot
 * starting on a beat. Shots place their cuts, slams and landings on these.
 */
export type BeatFrames = number[];

/** Beats for a shot that starts on song beat `first`, at `fps`. */
export const beatFramesFrom = (first: number, startFrame: number, songStart: number, fps: number): BeatFrames =>
  BEATS.slice(first).map((b) => Math.round((b - songStart) * fps) - startFrame);

/** Evenly spaced beats at the song's tempo, for rendering a shot on its own. */
export const evenBeats = (fps = 30, count = 40): BeatFrames => {
  const period = 60 / beatGrid.tempo;
  return Array.from({ length: count }, (_, i) => Math.round(i * period * fps));
};
