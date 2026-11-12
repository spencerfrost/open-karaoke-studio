import { describe, expect, it } from "vitest";
import type { SongProcessingStatus } from "@/types/Song";
import {
  FINISHED_TTL_MS,
  buildTrackerRows,
  mergeJobs,
  pruneFinished,
  primaryJob,
  type TrackedSongs,
} from "./jobTimeline";

const MINE = "tag-mine";
const THEIRS = "tag-theirs";

function job(over: Partial<SongProcessingStatus>): SongProcessingStatus {
  return {
    id: "job",
    song_id: "song",
    progress: 0,
    status: "processing",
    rawStatus: "processing",
    step: "separate",
    ownerTag: MINE,
    ...over,
  };
}

describe("mergeJobs", () => {
  it("folds a song's separation and alignment jobs into one entry", () => {
    const songs = mergeJobs(
      {},
      [
        job({ id: "align", step: "align", ownerTag: null, status: "queued" }),
        job({ id: "main", step: "separate", progress: 40 }),
      ],
      1000,
    );
    expect(Object.keys(songs)).toEqual(["song"]);
    expect(songs.song.jobs.map((j) => j.id)).toEqual(["main", "align"]);
    expect(songs.song.ownerTag).toBe(MINE);
  });

  it("keeps the owner once only the untagged alignment job is left", () => {
    let songs = mergeJobs({}, [job({ id: "main" })], 1000);
    songs = mergeJobs(
      songs,
      [job({ id: "align", step: "align", ownerTag: null })],
      2000,
    );
    expect(songs.song.ownerTag).toBe(MINE);
    expect(songs.song.finishedAt).toBeNull();
  });

  it("marks a song finished when its jobs leave the feed", () => {
    let songs = mergeJobs({}, [job({})], 1000);
    songs = mergeJobs(songs, [], 2000);
    expect(songs.song.finishedAt).toBe(2000);
    expect(songs.song.jobs).toEqual([]);
  });

  it("ignores jobs that already finished and jobs without a song", () => {
    const songs = mergeJobs(
      {},
      [job({ status: "processed" }), job({ song_id: undefined })],
      1000,
    );
    expect(songs).toEqual({});
  });

  it("forgets untagged songs when done and stale finished songs", () => {
    let songs: TrackedSongs = mergeJobs(
      {},
      [
        job({ song_id: "a", ownerTag: null }),
        job({ song_id: "b", ownerTag: MINE }),
      ],
      0,
    );
    songs = mergeJobs(songs, [], 1);
    expect(Object.keys(songs)).toEqual(["b"]);
    songs = mergeJobs(songs, [], 2 + FINISHED_TTL_MS);
    expect(songs).toEqual({});
  });
});

describe("pruneFinished", () => {
  it("expires finished songs without waiting for the feed", () => {
    let songs: TrackedSongs = mergeJobs(
      {},
      [
        job({ song_id: "done", ownerTag: MINE }),
        job({ song_id: "busy", ownerTag: MINE }),
      ],
      0,
    );
    songs = mergeJobs(songs, [job({ song_id: "busy", ownerTag: MINE })], 1);
    expect(pruneFinished(songs, 1 + FINISHED_TTL_MS)).toBe(songs);
    expect(Object.keys(pruneFinished(songs, 2 + FINISHED_TTL_MS))).toEqual([
      "busy",
    ]);
  });
});

describe("buildTrackerRows", () => {
  it("shows everyone's songs in queue order, marking this session's", () => {
    const songs = mergeJobs(
      {},
      [
        job({
          song_id: "late",
          ownerTag: MINE,
          status: "queued",
          step: "download",
          createdAt: "2026-10-24T10:05:00Z",
        }),
        job({
          song_id: "early",
          ownerTag: THEIRS,
          step: "download",
          progress: 30,
          message: "Downloading video from YouTube",
          createdAt: "2026-10-24T10:00:00Z",
        }),
      ],
      0,
    );
    const rows = buildTrackerRows(songs, MINE);
    expect(rows.map((r) => [r.songId, r.isMine, r.phase, r.ahead])).toEqual([
      ["early", false, "working", 0],
      ["late", true, "waiting", 1],
    ]);
    expect(rows[0]).toMatchObject({
      step: "download",
      stepNumber: 1,
      stepCount: 3,
      progress: 30,
      detail: "Downloading video from YouTube",
    });
  });

  it("follows the running job when separation and alignment overlap", () => {
    const songs = mergeJobs(
      {},
      [
        job({ id: "main", step: "separate", status: "processing" }),
        job({ id: "align", step: "align", status: "queued" }),
      ],
      0,
    );
    expect(buildTrackerRows(songs, MINE)[0]).toMatchObject({
      step: "separate",
      stepNumber: 2,
    });
  });

  it("keeps this session's finished songs first and drops others'", () => {
    let songs = mergeJobs(
      {},
      [
        job({ song_id: "mine", ownerTag: MINE }),
        job({ song_id: "theirs", ownerTag: THEIRS }),
        job({ song_id: "busy", ownerTag: THEIRS }),
      ],
      0,
    );
    songs = mergeJobs(songs, [job({ song_id: "busy", ownerTag: THEIRS })], 1);
    const rows = buildTrackerRows(songs, MINE);
    expect(rows.map((r) => [r.songId, r.phase])).toEqual([
      ["mine", "finished"],
      ["busy", "working"],
    ]);
  });

  it("claims nothing without a session tag", () => {
    let songs = mergeJobs({}, [job({})], 0);
    songs = mergeJobs(songs, [], 1);
    expect(buildTrackerRows(songs, null)).toEqual([]);
  });
});

describe("primaryJob", () => {
  it("prefers the earlier step, so a card shows separation over alignment", () => {
    expect(
      primaryJob([
        job({ id: "align", step: "align" }),
        job({ id: "main", step: "separate" }),
      ])?.id,
    ).toBe("main");
  });
});
