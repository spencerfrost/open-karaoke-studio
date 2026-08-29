import { create } from "zustand";
import { createLogger } from "@/lib/logger";
import { getPreviewStartSeconds } from "@/utils/songUtils";
import { Song } from "@/types/Song";
import { useKaraokePlayerStore } from "./useKaraokePlayerStore";

const logger = createLogger("store:songPreview");

/** How long a hover preview plays before stopping itself. */
export const PREVIEW_WINDOW_SEC = 30;
/** How long the cursor must rest on a card before a preview starts. */
export const HOVER_INTENT_MS = 500;

const FADE_IN_MS = 300;
const FADE_OUT_MS = 250;
const BASE_VOLUME = 0.7;

type PreviewStatus = "idle" | "loading" | "playing";

interface SongPreviewState {
  previewSongId: string | null;
  status: PreviewStatus;
  /** 0–1 through the preview window (not through the song). */
  progress: number;

  start: (song: Song) => void;
  /** Stops the preview. Passing a songId makes it a no-op unless that song is the one playing. */
  stop: (songId?: string) => void;
  /** Cuts the preview dead with no fade, even one already fading out. */
  stopImmediate: () => void;
}

/**
 * A single shared <audio> element drives every song-card preview.
 *
 * One element rather than one per card: it makes "only one preview at a time"
 * structurally impossible to violate, and it survives the constant unmounting
 * of cards as the library grid re-renders on search and animates rows out.
 * The element is created lazily, so browsing costs nothing until the first
 * preview actually starts.
 */
let audio: HTMLAudioElement | null = null;
let rampFrame: number | null = null;
/** Monotonic; bumped on every start/stop so stale async work can detect it lost the race. */
let token = 0;
let pending: { token: number; song: Song } | null = null;
let previewStartedAt = 0;
let targetVolume = BASE_VOLUME;

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

/** Preview volume adjusted by the song's stored normalization gain, so the library plays back level. */
const volumeForSong = (song: Song): number => {
  const gainDb = song.gainDb ?? 0;
  return clamp(BASE_VOLUME * 10 ** (gainDb / 20), 0, 1);
};

const cancelRamp = () => {
  if (rampFrame !== null) {
    cancelAnimationFrame(rampFrame);
    rampFrame = null;
  }
};

const rampVolume = (to: number, durationMs: number, onDone?: () => void) => {
  if (!audio) return;
  cancelRamp();

  const from = audio.volume;
  const startedAt = performance.now();

  const step = () => {
    if (!audio) return;
    const elapsed = performance.now() - startedAt;
    const t = clamp(elapsed / durationMs, 0, 1);
    audio.volume = clamp(from + (to - from) * t, 0, 1);

    if (t < 1) {
      rampFrame = requestAnimationFrame(step);
    } else {
      rampFrame = null;
      onDone?.();
    }
  };

  rampFrame = requestAnimationFrame(step);
};

export const useSongPreviewStore = create<SongPreviewState>((set, get) => {
  /**
   * Tears the element all the way down. `pause()` alone leaves the browser
   * downloading the rest of the mp3 — clearing src and calling load() is what
   * actually aborts the request.
   */
  const hardStop = () => {
    cancelRamp();
    pending = null;
    if (audio) {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    }
    set({ previewSongId: null, status: "idle", progress: 0 });
  };

  const getAudio = (): HTMLAudioElement => {
    if (audio) return audio;

    audio = new Audio();
    audio.preload = "auto";

    audio.addEventListener("loadedmetadata", () => {
      if (!audio || !pending || pending.token !== token) return;
      const { song } = pending;

      // currentTime can only be set once metadata has arrived — before that
      // the assignment is silently dropped.
      const duration = song.duration ?? audio.duration;
      previewStartedAt = getPreviewStartSeconds(duration, PREVIEW_WINDOW_SEC);
      audio.currentTime = previewStartedAt;
      audio.volume = 0;

      const startedToken = token;
      audio
        .play()
        .then(() => {
          if (startedToken !== token) return;
          set({ status: "playing" });
          rampVolume(targetVolume, FADE_IN_MS);
        })
        .catch((error) => {
          if (startedToken !== token) return;
          logger.warn("Preview playback rejected", error);
          hardStop();
        });
    });

    audio.addEventListener("timeupdate", () => {
      if (!audio || get().previewSongId === null) return;

      const elapsed = audio.currentTime - previewStartedAt;
      if (elapsed >= PREVIEW_WINDOW_SEC) {
        get().stop();
        return;
      }

      // timeupdate fires ~4x/sec and every visible card subscribes, so only
      // publish when the rendered value would actually change.
      const next = clamp(elapsed / PREVIEW_WINDOW_SEC, 0, 1);
      if (Math.round(next * 100) !== Math.round(get().progress * 100)) {
        set({ progress: next });
      }
    });

    audio.addEventListener("ended", () => {
      get().stop();
    });

    audio.addEventListener("error", () => {
      // Clearing src to abort a preview fires an error event; that is expected,
      // not a failure worth reporting.
      if (get().previewSongId === null) return;
      logger.warn("Preview failed to load", audio?.error?.message);
      hardStop();
    });

    return audio;
  };

  return {
    previewSongId: null,
    status: "idle",
    progress: 0,

    start: (song) => {
      // A performance always wins. Checked here rather than only at the call
      // site because the hover-intent timer arms 500ms before it fires, so
      // playback can begin in between.
      if (useKaraokePlayerStore.getState().isPlaying) return;

      // Already previewing this song — but if it is mid-fade-out, re-hovering
      // should restart it rather than let it die.
      if (get().previewSongId === song.id && get().status !== "idle") return;

      // Cut the outgoing song rather than crossfading — overlapping fades read
      // as a glitch instead of a transition.
      hardStop();

      // One bump invalidates any in-flight callback from the preview we just
      // tore down, and stamps the one replacing it.
      token += 1;
      pending = { token, song };
      targetVolume = volumeForSong(song);
      previewStartedAt = 0;

      const el = getAudio();
      el.volume = 0;
      el.src = `/api/songs/${song.id}/download/original`;
      el.load();

      logger.debug("Preview starting", song.id);
      set({ previewSongId: song.id, status: "loading", progress: 0 });
    },

    stop: (songId) => {
      const current = get().previewSongId;
      if (current === null) return;
      // Guards against a card that is unmounting late stopping a newer preview.
      if (songId !== undefined && songId !== current) return;
      // Already fading out — let the in-flight ramp finish.
      if (get().status === "idle") return;

      token += 1;
      pending = null;
      logger.debug("Preview stopping", current);

      if (!audio || audio.paused) {
        hardStop();
        return;
      }

      const stoppingToken = token;
      rampVolume(0, FADE_OUT_MS, () => {
        if (stoppingToken !== token) return;
        hardStop();
      });
      set({ status: "idle" });
    },

    stopImmediate: () => {
      // Deliberately does not consult `status`: a preview mid-fade-out already
      // reads as "idle" while its audio is still audible, which is exactly the
      // case a hard cut has to catch.
      if (get().previewSongId === null) return;

      token += 1;
      logger.debug("Preview cut", get().previewSongId);
      hardStop();
    },
  };
});

// The main karaoke player always wins: a preview can never talk over a
// performance, however that performance was started (queue auto-advance, the
// mini-player, or a remote play over the session websocket).
useKaraokePlayerStore.subscribe((state, previous) => {
  if (state.isPlaying && !previous.isPlaying) {
    // Hard cut, not a fade: there is no transition to smooth over here, and a
    // fade would let the preview overlap the performance for its duration.
    useSongPreviewStore.getState().stopImmediate();
  }
});

if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      // Also a hard cut: the fade rides on requestAnimationFrame, which a
      // hidden tab stops firing, so a faded stop would never reach hardStop
      // and the preview would keep playing in the background.
      useSongPreviewStore.getState().stopImmediate();
    }
  });
}
