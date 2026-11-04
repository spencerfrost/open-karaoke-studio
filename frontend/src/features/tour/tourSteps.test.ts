import { describe, expect, it } from "vitest";
import type { TrackerRow } from "@/features/songs/processing/jobTimeline";
import {
  afterSoundOn,
  BUSY_AHEAD,
  docsLink,
  fallbackReason,
  nextStep,
  pickFallbackSong,
  progressSignature,
  STALL_MS,
  type FallbackInputs,
  type TourSignals,
} from "./tourSteps";

const idle: TourSignals = {
  phoneJoined: false,
  hasMyJob: false,
  myReadySong: false,
  countingDown: false,
  isPlaying: false,
  singerOnControls: null,
  mixChanged: false,
  songEnded: false,
};

const row = (overrides: Partial<TrackerRow> = {}): TrackerRow => ({
  songId: "s1",
  isMine: true,
  phase: "working",
  step: "separate",
  stepNumber: 2,
  stepCount: 3,
  progress: 40,
  ahead: 0,
  ...overrides,
});

describe("nextStep", () => {
  it("never leaves the sound prompt by itself", () => {
    expect(nextStep("sound", { ...idle, hasMyJob: true })).toBe("sound");
  });

  it("waits on the scan step until a phone joins", () => {
    expect(nextStep("scan", idle)).toBe("scan");
    expect(nextStep("scan", { ...idle, phoneJoined: true })).toBe("add");
  });

  it("waits on the add step until a job of ours shows up", () => {
    const joined = { ...idle, phoneJoined: true };
    expect(nextStep("add", joined)).toBe("add");
    expect(nextStep("add", { ...joined, hasMyJob: true })).toBe("wheel");
    // A song added from the stage itself skips the phone entirely.
    expect(nextStep("scan", { ...idle, hasMyJob: true })).toBe("wheel");
  });

  it("stays on add if the phone drops off", () => {
    expect(nextStep("add", idle)).toBe("add");
  });

  it("moves to ready once our song comes out playable", () => {
    expect(nextStep("wheel", { ...idle, hasMyJob: true })).toBe("wheel");
    expect(
      nextStep("wheel", { ...idle, hasMyJob: true, myReadySong: true }),
    ).toBe("ready");
  });

  it("follows the count, then the song playing", () => {
    expect(nextStep("ready", { ...idle, countingDown: true })).toBe(
      "countdown",
    );
    expect(
      nextStep("countdown", {
        ...idle,
        isPlaying: true,
        singerOnControls: false,
      }),
    ).toBe("controls");
  });

  it("goes to the mix step when the phone opens its controls", () => {
    const playing = { ...idle, isPlaying: true };
    expect(nextStep("controls", { ...playing, singerOnControls: false })).toBe(
      "controls",
    );
    expect(nextStep("controls", { ...playing, singerOnControls: true })).toBe(
      "mix",
    );
  });

  it("skips waiting for a phone when the singer has none", () => {
    expect(
      nextStep("countdown", {
        ...idle,
        isPlaying: true,
        singerOnControls: null,
      }),
    ).toBe("mix");
  });

  it("ends once the mix moves, or the song ends untouched", () => {
    const playing = { ...idle, isPlaying: true, singerOnControls: true };
    expect(nextStep("mix", playing)).toBe("mix");
    expect(nextStep("mix", { ...playing, mixChanged: true })).toBe("end");
    expect(
      nextStep("controls", {
        ...idle,
        singerOnControls: false,
        songEnded: true,
      }),
    ).toBe("end");
  });

  it("jumps ahead when the visitor picks a song off the wheel", () => {
    expect(nextStep("scan", { ...idle, countingDown: true })).toBe("countdown");
    expect(nextStep("wheel", { ...idle, isPlaying: true })).toBe("mix");
  });

  it("never goes back", () => {
    // Paused mid-song: not playing, not counting, but the tour stays put.
    expect(nextStep("mix", idle)).toBe("mix");
    expect(nextStep("countdown", { ...idle, hasMyJob: true })).toBe(
      "countdown",
    );
    // A second song of ours finishing doesn't drag the tour back to ready.
    expect(
      nextStep("controls", {
        ...idle,
        myReadySong: true,
        singerOnControls: false,
      }),
    ).toBe("controls");
  });

  it("holds the end card and done", () => {
    expect(nextStep("end", { ...idle, isPlaying: true })).toBe("end");
    expect(nextStep("done", { ...idle, hasMyJob: true })).toBe("done");
  });
});

describe("afterSoundOn", () => {
  it("starts at scan on a fresh session", () => {
    expect(afterSoundOn(idle)).toBe("scan");
  });

  it("picks up wherever the app already is", () => {
    expect(afterSoundOn({ ...idle, phoneJoined: true })).toBe("add");
    expect(afterSoundOn({ ...idle, hasMyJob: true })).toBe("wheel");
  });
});

describe("fallbackReason", () => {
  const base: FallbackInputs = {
    step: "wheel",
    myRows: [],
    myFinishedOutcome: null,
    quota: { sessionRemaining: 3, dailyRemaining: 20 },
    lastProgressAt: null,
    now: 1_000_000,
  };

  it("offers nothing while things are moving", () => {
    expect(
      fallbackReason({ ...base, myRows: [row()], lastProgressAt: 999_000 }),
    ).toBeNull();
  });

  it("reports the quota when no new song can be added", () => {
    expect(
      fallbackReason({
        ...base,
        step: "scan",
        quota: { sessionRemaining: 3, dailyRemaining: 0 },
      }),
    ).toBe("quota");
    expect(
      fallbackReason({
        ...base,
        step: "scan",
        quota: { sessionRemaining: 0, dailyRemaining: 5 },
      }),
    ).toBe("quota");
  });

  it("ignores the quota while a song of ours is on the way", () => {
    expect(
      fallbackReason({
        ...base,
        myRows: [row()],
        quota: { sessionRemaining: 0, dailyRemaining: 0 },
      }),
    ).toBeNull();
  });

  it("reports a failed song", () => {
    expect(
      fallbackReason({
        ...base,
        myRows: [row({ phase: "finished" })],
        myFinishedOutcome: "failed",
      }),
    ).toBe("failed");
  });

  it("waits while the library hasn't said how a song ended", () => {
    expect(
      fallbackReason({
        ...base,
        myRows: [row({ phase: "finished" })],
        myFinishedOutcome: "pending",
      }),
    ).toBeNull();
  });

  it("calls it busy with several songs ahead", () => {
    expect(
      fallbackReason({
        ...base,
        myRows: [row({ phase: "waiting", ahead: BUSY_AHEAD - 1 })],
      }),
    ).toBeNull();
    expect(
      fallbackReason({
        ...base,
        myRows: [row({ phase: "waiting", ahead: BUSY_AHEAD })],
      }),
    ).toBe("busy");
  });

  it("calls it busy once our song goes quiet", () => {
    const quietSince = base.now - STALL_MS;
    expect(
      fallbackReason({
        ...base,
        myRows: [row()],
        lastProgressAt: quietSince + 1,
      }),
    ).toBeNull();
    expect(
      fallbackReason({ ...base, myRows: [row()], lastProgressAt: quietSince }),
    ).toBe("busy");
  });

  it("only applies while waiting on a song", () => {
    expect(
      fallbackReason({
        ...base,
        step: "countdown",
        quota: { sessionRemaining: 0, dailyRemaining: 0 },
      }),
    ).toBeNull();
    expect(
      fallbackReason({
        ...base,
        myRows: [row({ phase: "finished" })],
        myFinishedOutcome: "ready",
      }),
    ).toBeNull();
  });
});

describe("progressSignature", () => {
  it("changes when anything on the row changes", () => {
    expect(progressSignature(row())).not.toBe(
      progressSignature(row({ progress: 41 })),
    );
    expect(progressSignature(row({ phase: "waiting", ahead: 2 }))).not.toBe(
      progressSignature(row({ phase: "waiting", ahead: 1 })),
    );
    expect(progressSignature(undefined)).toBeNull();
  });
});

describe("pickFallbackSong", () => {
  const songs = [
    { id: "a", status: "processed" },
    { id: "b", status: "processed", syncedLyrics: "[00:01.00] hi" },
    { id: "c", status: "error", syncedLyrics: "[00:01.00] hi" },
    { id: "d", status: "processed", syncedLyrics: "[00:01.00] hey" },
  ];

  it("prefers playable songs with timed lyrics", () => {
    const pick = pickFallbackSong(songs, "ABCD");
    expect(["b", "d"]).toContain(pick?.id);
  });

  it("is stable for a seed", () => {
    expect(pickFallbackSong(songs, "WXYZ")).toBe(
      pickFallbackSong(songs, "WXYZ"),
    );
  });

  it("skips excluded songs and falls back to any playable one", () => {
    expect(pickFallbackSong(songs, "ABCD", ["b", "d"])?.id).toBe("a");
    expect(pickFallbackSong([{ id: "c", status: "error" }], "ABCD")).toBeNull();
  });
});

describe("docsLink", () => {
  it("joins the base and page", () => {
    expect(docsLink("https://x.dev/docs", "architecture.html")).toBe(
      "https://x.dev/docs/architecture.html",
    );
    expect(docsLink("https://x.dev/docs/", "")).toBe("https://x.dev/docs/");
  });

  it("is hidden without a docs URL", () => {
    expect(docsLink(undefined, "architecture.html")).toBeNull();
    expect(docsLink("", "architecture.html")).toBeNull();
  });
});
