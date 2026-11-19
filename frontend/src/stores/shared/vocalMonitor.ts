/**
 * The singer's headphones: the lead vocal alone, on a second audio output,
 * playing in step with the room mix.
 *
 * A Web Audio context plays to one output, so this runs its own context and
 * points it at the chosen device with AudioContext.setSinkId (Chromium only).
 * The two contexts have separate clocks, so every start is lined up against the
 * room context at that moment: each side's reported output latency, plus a
 * delay the host sets for the speakers' own lag (a TV's sound processing is
 * not reported to the browser).
 *
 * Nothing plays until the browser has confirmed the chosen device. A context
 * starts on the default output, which is the room, and the vocal must never
 * reach the room by accident.
 */

import { createLogger } from "@/lib/logger";

const logger = createLogger("store:vocalMonitor");

// AudioContext.setSinkId is not in TypeScript's DOM types yet.
type SinkableAudioContext = AudioContext & {
  setSinkId: (sinkId: string) => Promise<void>;
};

/** Seconds between scheduling a start and the start, so it is never missed. */
const LEAD_SECONDS = 0.05;

/** True when this browser can send a Web Audio context to a chosen output. */
export function canChooseAudioOutput(): boolean {
  return (
    typeof window !== "undefined" &&
    window.isSecureContext &&
    typeof window.AudioContext !== "undefined" &&
    "setSinkId" in window.AudioContext.prototype
  );
}

function totalLatency(ctx: AudioContext): number {
  return (ctx.baseLatency || 0) + (ctx.outputLatency || 0);
}

/** Where the room mix is, so the headphones can be lined up against it. */
export interface RoomClock {
  ctx: AudioContext;
  /** Room context time the stems start (or started) at. */
  startAt: number;
  /** Seconds into the song at startAt. */
  offset: number;
}

export interface VocalMonitor {
  /** Send the vocal to this output, or turn the headphones off with null. */
  setDevice: (deviceId: string | null) => void;
  /** Linear volume, normalization included. */
  setLevel: (level: number) => void;
  /** Extra seconds the headphones wait, to match the speakers' own lag. */
  setDelay: (seconds: number) => void;
  /** Line up again after the room's output changed under it. */
  resync: () => void;
  /**
   * Open the output ahead of a play, so the play starts on time. Until the
   * first call nothing is opened: only the device playing songs needs it.
   * From then on it stays open across songs, and a call retries an output
   * that was unplugged.
   */
  prepare: () => void;
  start: (buffer: AudioBuffer, room: RoomClock) => void;
  stop: () => void;
  /** Same curve and length as the room's fade. */
  fadeOut: (curve: Float32Array, seconds: number) => void;
  cancelFade: () => void;
}

/**
 * @param onReadyChange called with true once the chosen output is confirmed,
 *   and with false when it is turned off or lost.
 */
export function createVocalMonitor(
  onReadyChange: (ready: boolean) => void,
): VocalMonitor {
  let deviceId: string | null = null;
  let level = 1;
  let delaySeconds = 0;
  let prepared = false;

  let ctx: SinkableAudioContext | null = null;
  // Set once setSinkId has resolved for the current context; until then the
  // context is on the room output and must stay silent.
  let routed = false;
  let opening: Promise<boolean> | null = null;

  let source: AudioBufferSourceNode | null = null;
  let levelGain: GainNode | null = null;
  let fadeGain: GainNode | null = null;
  let limiter: DynamicsCompressorNode | null = null;

  // What is meant to be playing, kept so the headphones can be restarted in
  // place when the device or delay changes, or once a late open finishes.
  let playing: { buffer: AudioBuffer; room: RoomClock } | null = null;

  function stopSource() {
    if (!source) return;
    try {
      source.stop();
    } catch {
      // Already stopped
    }
    source.disconnect();
    source = null;
  }

  function closeContext() {
    stopSource();
    if (ctx) void ctx.close();
    const wasRouted = routed;
    ctx = null;
    routed = false;
    opening = null;
    levelGain = null;
    fadeGain = null;
    limiter = null;
    if (wasRouted) onReadyChange(false);
  }

  /** Resolves true once a context is playing to the chosen device. */
  function open(): Promise<boolean> {
    if (!deviceId || !canChooseAudioOutput()) return Promise.resolve(false);
    if (ctx && routed) return Promise.resolve(true);
    if (opening) return opening;

    const target = deviceId;
    const context = new window.AudioContext({
      latencyHint: "interactive",
    }) as SinkableAudioContext;
    ctx = context;
    opening = context
      .setSinkId(target)
      .then(() => {
        // The device changed or the monitor closed while this was pending.
        if (ctx !== context) return false;
        routed = true;
        opening = null;
        levelGain = context.createGain();
        levelGain.gain.value = level;
        fadeGain = context.createGain();
        limiter = context.createDynamicsCompressor();
        limiter.threshold.value = -1;
        limiter.knee.value = 0;
        limiter.ratio.value = 20;
        limiter.attack.value = 0.003;
        limiter.release.value = 0.1;
        levelGain.connect(fadeGain);
        fadeGain.connect(limiter);
        limiter.connect(context.destination);
        logger.info("Headphones output ready");
        onReadyChange(true);
        return true;
      })
      .catch((error: unknown) => {
        // Unplugged, or an id this browser no longer knows.
        logger.warn("Headphones output unavailable:", error);
        if (ctx === context) closeContext();
        return false;
      });
    return opening;
  }

  /** Start the vocal where the room is now, lined up with what it plays. */
  function startNow() {
    if (!playing || !ctx || !routed || !levelGain) return;
    const { buffer, room } = playing;
    stopSource();
    void ctx.resume();

    // When the room's sample at room.startAt comes out of its output,
    // measured in seconds from now.
    const roomHeardIn =
      room.startAt - room.ctx.currentTime + totalLatency(room.ctx);
    // Start so the headphones put that sample out at the same moment.
    let startAt =
      ctx.currentTime + roomHeardIn - totalLatency(ctx) + delaySeconds;
    let offset = room.offset;
    const earliest = ctx.currentTime + LEAD_SECONDS;
    if (startAt < earliest) {
      // Too late to catch that moment (a late open, a slower output):
      // start a little further into the song instead.
      offset += earliest - startAt;
      startAt = earliest;
    }
    if (offset >= buffer.duration) return;

    if (fadeGain) {
      fadeGain.gain.cancelScheduledValues(0);
      fadeGain.gain.value = 1;
    }
    source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(levelGain);
    source.start(startAt, offset);
  }

  return {
    setDevice: (next) => {
      if (next === deviceId) return;
      deviceId = next;
      closeContext();
      if (!deviceId || !prepared) return;
      // Opened now, not on the next play, so phones learn straight away
      // whether there are headphones to control.
      void open().then((ready) => {
        if (ready && playing) startNow();
      });
    },

    setLevel: (next) => {
      level = next;
      if (levelGain) levelGain.gain.value = next;
    },

    setDelay: (seconds) => {
      if (seconds === delaySeconds) return;
      delaySeconds = seconds;
      if (playing && source) startNow();
    },

    resync: () => {
      if (playing && source) startNow();
    },

    prepare: () => {
      prepared = true;
      void open();
    },

    start: (buffer, room) => {
      playing = { buffer, room };
      if (!deviceId) return;
      if (ctx && routed) {
        startNow();
        return;
      }
      const intended = playing;
      void open().then((ready) => {
        // Only if nothing was paused, sought or replaced meanwhile.
        if (ready && playing === intended) startNow();
      });
    },

    stop: () => {
      playing = null;
      stopSource();
    },

    fadeOut: (curve, seconds) => {
      if (!ctx || !fadeGain) return;
      const gain = fadeGain.gain;
      gain.cancelScheduledValues(ctx.currentTime);
      gain.setValueCurveAtTime(curve, ctx.currentTime, seconds);
    },

    cancelFade: () => {
      if (!fadeGain) return;
      fadeGain.gain.cancelScheduledValues(0);
      fadeGain.gain.value = 1;
    },
  };
}
