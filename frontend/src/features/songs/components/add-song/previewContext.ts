/**
 * The add flow's one preview player: what's previewing, and how to start or
 * pause it. PreviewProvider (PreviewPlayer.tsx) owns the <audio> behind it.
 */

import { createContext, useContext } from "react";

export interface PreviewTrack {
  videoId: string;
  title: string;
  artist: string;
}

export type PreviewStatus = "loading" | "playing" | "paused" | "error";

export interface PreviewState {
  track: PreviewTrack | null;
  status: PreviewStatus;
  currentTime: number;
  duration: number;
}

export interface PreviewApi {
  /** Play this track; the one playing already pauses or resumes instead. */
  toggle: (track: PreviewTrack) => void;
  stop: () => void;
}

export const PreviewStateContext = createContext<PreviewState | null>(null);
export const PreviewApiContext = createContext<PreviewApi | null>(null);

export const usePreviewApi = () => {
  const api = useContext(PreviewApiContext);
  if (!api) throw new Error("usePreviewApi needs a PreviewProvider");
  return api;
};

export const usePreviewState = () => {
  const state = useContext(PreviewStateContext);
  if (!state) throw new Error("usePreviewState needs a PreviewProvider");
  return state;
};

/** Whether this track is the one previewing, and a toggle for it. */
export const usePreview = (track: PreviewTrack | null) => {
  const { toggle } = usePreviewApi();
  const state = usePreviewState();
  const isCurrent = !!track && state.track?.videoId === track.videoId;
  return {
    status: isCurrent ? state.status : null,
    toggle: () => track && toggle(track),
  };
};
