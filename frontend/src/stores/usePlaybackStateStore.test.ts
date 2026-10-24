import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { usePlaybackStateStore } from "./usePlaybackStateStore";

type MockSource = {
  buffer: unknown;
  connect: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
  start: ReturnType<typeof vi.fn>;
  stop: ReturnType<typeof vi.fn>;
  onended: (() => void) | null;
};

const VOLUMES = { vocal: 0.5, backing: 1, instrumental: 1 };

describe("usePlaybackStateStore - stem playback", () => {
  let sources: MockSource[] = [];
  let clock = { now: 0 };
  // Typed loosely: the setup mock is not a full AudioContext.
  const BaseAudioContext =
    globalThis.AudioContext as unknown as new () => object;

  const loadSong = async () => {
    const store = usePlaybackStateStore.getState();
    store.setSongId("song", 180);
    await store.load();
  };

  beforeEach(() => {
    sources = [];
    clock = { now: 10 };
    vi.stubGlobal("fetch", async () => ({
      ok: true,
      arrayBuffer: async () => new ArrayBuffer(8),
    }));
    vi.stubGlobal(
      "AudioContext",
      class extends BaseAudioContext {
        constructor() {
          super();
          // The base mock's currentTime is a plain field, which would hide a
          // getter declared here.
          Object.defineProperty(this, "currentTime", {
            get: () => clock.now,
          });
        }
        createGain = vi.fn(() => ({
          gain: {
            value: 1,
            cancelScheduledValues: vi.fn(),
            setValueCurveAtTime: vi.fn(),
          },
          connect: vi.fn(),
          disconnect: vi.fn(),
        }));
        createBufferSource = vi.fn(() => {
          const source: MockSource = {
            buffer: null,
            connect: vi.fn(),
            disconnect: vi.fn(),
            start: vi.fn(),
            stop: vi.fn(),
            onended: null,
          };
          sources.push(source);
          return source;
        });
      },
    );
  });

  afterEach(() => {
    usePlaybackStateStore.getState().cleanup();
    vi.unstubAllGlobals();
    // setup.ts stubs these for every test; put them back.
    vi.stubGlobal("AudioContext", BaseAudioContext);
  });

  it("starts every stem at the same instant and offset", async () => {
    await loadSong();
    usePlaybackStateStore.getState().play(VOLUMES);

    // Instrumental, vocals and backing vocals.
    expect(sources).toHaveLength(3);
    const [first] = sources[0].start.mock.calls;
    for (const source of sources) {
      expect(source.start).toHaveBeenCalledWith(first[0], 0);
    }
    expect(first[0]).toBeGreaterThan(clock.now);
  });

  it("restarts the stems from the new position on seek", async () => {
    await loadSong();
    const store = usePlaybackStateStore.getState();
    store.play(VOLUMES);
    const firstStems = [...sources];

    store.seek(42, VOLUMES);

    for (const source of firstStems) expect(source.stop).toHaveBeenCalled();
    const newStems = sources.slice(3);
    expect(newStems).toHaveLength(3);
    for (const source of newStems) {
      expect(source.start).toHaveBeenCalledWith(expect.any(Number), 42);
    }
    expect(usePlaybackStateStore.getState().currentTime).toBe(42);
  });

  it("keeps the position across pause and play", async () => {
    await loadSong();
    const store = usePlaybackStateStore.getState();
    store.play(VOLUMES);
    const startAt = sources[0].start.mock.calls[0][0] as number;

    clock.now = startAt + 30;
    store.pause();
    expect(usePlaybackStateStore.getState().currentTime).toBeCloseTo(30);

    store.play(VOLUMES);
    for (const source of sources.slice(3)) {
      expect(source.start.mock.calls[0][1]).toBeCloseTo(30);
    }
  });

  it("treats a pause as a pause, not the end of the song", async () => {
    await loadSong();
    const store = usePlaybackStateStore.getState();
    store.play(VOLUMES);
    const instrumental = sources[0];

    store.pause();
    // A stopped source fires onended in a real browser; the handler is
    // cleared before the stop, so nothing should be left to fire.
    instrumental.onended?.();

    expect(usePlaybackStateStore.getState().songEnded).toBe(false);
  });

  it("marks the song ended when the instrumental runs out", async () => {
    await loadSong();
    usePlaybackStateStore.getState().play(VOLUMES);

    sources[0].onended?.();

    const state = usePlaybackStateStore.getState();
    expect(state.songEnded).toBe(true);
    expect(state.isPlaying).toBe(false);
    expect(state.currentTime).toBe(180);
  });
});
