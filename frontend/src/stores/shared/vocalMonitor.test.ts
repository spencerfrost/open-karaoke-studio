import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import type { Mock } from "vitest";
import { createVocalMonitor, type RoomClock } from "./vocalMonitor";

type MockSource = {
  buffer: unknown;
  connect: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
  start: ReturnType<typeof vi.fn>;
  stop: ReturnType<typeof vi.fn>;
};

const BUFFER = { duration: 180 } as AudioBuffer;

describe("vocalMonitor", () => {
  let sources: MockSource[];
  let sinkResult: Promise<void>;
  let contexts: object[];
  let setSinkId: Mock<(id: string) => Promise<void>>;
  // The headphones context's clock and latency.
  let monitorNow: number;
  const BaseAudioContext =
    globalThis.AudioContext as unknown as new () => object;

  const room = (startAt: number, offset: number, now: number): RoomClock => ({
    ctx: {
      currentTime: now,
      baseLatency: 0.01,
      outputLatency: 0.02,
    } as AudioContext,
    startAt,
    offset,
  });

  const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

  beforeEach(() => {
    sources = [];
    contexts = [];
    monitorNow = 3;
    sinkResult = Promise.resolve();
    setSinkId = vi.fn<(id: string) => Promise<void>>(() => sinkResult);
    vi.stubGlobal("isSecureContext", true);
    class MonitorContext extends BaseAudioContext {
      baseLatency = 0.005;
      outputLatency = 0.005;
      // On the prototype, where the browser support check looks.
      setSinkId(id: string) {
        return setSinkId(id);
      }
      constructor() {
        super();
        Object.defineProperty(this, "currentTime", { get: () => monitorNow });
        contexts.push(this);
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
        };
        sources.push(source);
        return source;
      });
    }
    vi.stubGlobal("AudioContext", MonitorContext);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.stubGlobal("AudioContext", BaseAudioContext);
  });

  it("plays nothing without a headphones output", async () => {
    const monitor = createVocalMonitor(vi.fn());
    monitor.prepare();
    monitor.start(BUFFER, room(10.05, 0, 10));
    await flush();

    expect(contexts).toHaveLength(0);
    expect(sources).toHaveLength(0);
  });

  it("opens nothing until the device that plays songs asks", async () => {
    const onReady = vi.fn();
    const monitor = createVocalMonitor(onReady);
    monitor.setDevice("headphones");
    await flush();

    expect(contexts).toHaveLength(0);
    monitor.prepare();
    await flush();
    expect(contexts).toHaveLength(1);
    expect(setSinkId).toHaveBeenCalledWith("headphones");
    expect(onReady).toHaveBeenCalledWith(true);
  });

  it("starts the vocal so both outputs put the same moment out together", async () => {
    const monitor = createVocalMonitor(vi.fn());
    monitor.setDevice("headphones");
    monitor.prepare();
    await flush();

    // Room: starts 0.05 s from now, 0.03 s of output latency.
    // Headphones: 0.01 s of output latency.
    monitor.start(BUFFER, room(10.05, 12, 10));

    expect(sources).toHaveLength(1);
    const [startAt, offset] = sources[0].start.mock.calls[0];
    expect(startAt).toBeCloseTo(3 + 0.05 + 0.03 - 0.01);
    expect(offset).toBe(12);
  });

  it("adds the host's delay for the speakers' own lag", async () => {
    const monitor = createVocalMonitor(vi.fn());
    monitor.setDevice("headphones");
    monitor.setDelay(0.1);
    monitor.prepare();
    await flush();

    monitor.start(BUFFER, room(10.05, 0, 10));

    expect(sources[0].start.mock.calls[0][0]).toBeCloseTo(3.07 + 0.1);
  });

  it("joins a song already playing at the room's position", async () => {
    const monitor = createVocalMonitor(vi.fn());
    monitor.setDevice("headphones");
    monitor.prepare();
    await flush();

    // The room started 20 s ago from 5 s in.
    monitor.start(BUFFER, room(10, 5, 30));

    const [startAt, offset] = sources[0].start.mock.calls[0];
    expect(startAt).toBeCloseTo(3.05);
    // 5 + 20 s elapsed + the lead-in, less the latency difference.
    expect(offset).toBeCloseTo(5 + 20 + 0.05 - 0.03 + 0.01);
  });

  it("never plays while the output is unconfirmed, and not at all if it fails", async () => {
    let fail!: (error: Error) => void;
    sinkResult = new Promise((_, reject) => {
      fail = reject;
    });
    const onReady = vi.fn();
    const monitor = createVocalMonitor(onReady);
    monitor.setDevice("unplugged");
    monitor.prepare();
    monitor.start(BUFFER, room(10.05, 0, 10));
    await flush();

    expect(sources).toHaveLength(0);
    fail(new Error("NotFoundError"));
    await flush();

    expect(sources).toHaveLength(0);
    expect(onReady).not.toHaveBeenCalledWith(true);
  });

  it("starts once a slow output is confirmed, unless paused meanwhile", async () => {
    let confirm!: () => void;
    sinkResult = new Promise((resolve) => {
      confirm = resolve;
    });
    const monitor = createVocalMonitor(vi.fn());
    monitor.setDevice("headphones");
    monitor.start(BUFFER, room(10.05, 0, 10));
    monitor.stop();
    monitor.prepare();
    confirm();
    await flush();

    expect(sources).toHaveLength(0);
  });

  it("restarts in place when the delay changes mid-song", async () => {
    const monitor = createVocalMonitor(vi.fn());
    monitor.setDevice("headphones");
    monitor.prepare();
    await flush();
    monitor.start(BUFFER, room(10.05, 0, 10));

    monitor.setDelay(0.05);

    expect(sources[0].stop).toHaveBeenCalled();
    expect(sources).toHaveLength(2);
  });

  it("reports the output lost when it is turned off", async () => {
    const onReady = vi.fn();
    const monitor = createVocalMonitor(onReady);
    monitor.setDevice("headphones");
    monitor.prepare();
    await flush();

    monitor.setDevice(null);

    expect(onReady).toHaveBeenLastCalledWith(false);
  });
});
