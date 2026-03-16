import { create } from "zustand";
import * as Tone from "tone";
import {
  normalizeVolume,
  clampSpeed,
  getGrainParams,
} from "./shared/audioHelpers";
import { createLogger } from "@/lib/logger";

const logger = createLogger("store:audioControls");

export interface AudioControlsState {
  // Volume controls
  vocalVolume: number;
  backingVocalVolume: number;
  instrumentalVolume: number;
  playbackSpeed: number;

  // Actions
  setVocalVolume: (volume: number) => void;
  setBackingVocalVolume: (volume: number) => void;
  setInstrumentalVolume: (volume: number) => void;
  setPlaybackSpeed: (speed: number) => void;
  resetAudioControls: () => void;

  // Internal methods for Web Audio API integration
  applyVolumeToGainNode: (node: GainNode | null, volume: number) => void;
  applySpeedToGrainPlayers: (
    players: (Tone.GrainPlayer | null)[],
    speed: number,
  ) => void;
}

export const useAudioControlsStore = create<AudioControlsState>((set) => ({
  // Default values
  vocalVolume: 0,
  backingVocalVolume: 1.0,
  instrumentalVolume: 1.0,
  playbackSpeed: 1.0,

  setVocalVolume: (volume: number) => {
    const normalized = normalizeVolume(volume);
    set({ vocalVolume: normalized });
  },

  setBackingVocalVolume: (volume: number) => {
    const normalized = normalizeVolume(volume);
    set({ backingVocalVolume: normalized });
  },

  setInstrumentalVolume: (volume: number) => {
    const normalized = normalizeVolume(volume);
    set({ instrumentalVolume: normalized });
  },

  setPlaybackSpeed: (speed: number) => {
    const clamped = clampSpeed(speed);
    logger.debug("Setting playback speed:", clamped);
    set({ playbackSpeed: clamped });
  },

  resetAudioControls: () => {
    set({
      vocalVolume: 0,
      backingVocalVolume: 1.0,
      instrumentalVolume: 1.0,
      playbackSpeed: 1.0,
    });
  },

  // Helper to apply volume to Web Audio gain node
  applyVolumeToGainNode: (node: GainNode | null, volume: number) => {
    if (node) {
      node.gain.value = volume;
    }
  },

  // Helper to apply speed to Tone.js GrainPlayers
  applySpeedToGrainPlayers: (
    players: (Tone.GrainPlayer | null)[],
    speed: number,
  ) => {
    const clamped = clampSpeed(speed);
    const { grainSize, overlap } = getGrainParams(clamped);

    players.forEach((player) => {
      if (player) {
        player.playbackRate = clamped;
        player.grainSize = grainSize;
        player.overlap = overlap;
      }
    });
  },
}));
