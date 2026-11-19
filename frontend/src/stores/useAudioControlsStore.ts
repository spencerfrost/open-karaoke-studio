import { create } from "zustand";
import { normalizeVolume } from "./shared/audioHelpers";

export interface AudioControlsState {
  // Volume controls
  vocalVolume: number;
  backingVocalVolume: number;
  instrumentalVolume: number;
  /**
   * The lead vocal in the singer's headphones, separate from the room mix.
   * Kept across songs and resets: it suits the ears in the headphones, not
   * the song.
   */
  headphonesVolume: number;

  // Actions
  setVocalVolume: (volume: number) => void;
  setBackingVocalVolume: (volume: number) => void;
  setInstrumentalVolume: (volume: number) => void;
  setHeadphonesVolume: (volume: number) => void;
  resetAudioControls: () => void;

  // Internal methods for Web Audio API integration
  applyVolumeToGainNode: (node: GainNode | null, volume: number) => void;
}

export const useAudioControlsStore = create<AudioControlsState>((set) => ({
  // Default values
  vocalVolume: 0,
  backingVocalVolume: 1.0,
  instrumentalVolume: 1.0,
  headphonesVolume: 1.0,

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

  setHeadphonesVolume: (volume: number) => {
    set({ headphonesVolume: normalizeVolume(volume) });
  },

  resetAudioControls: () => {
    set({
      vocalVolume: 0,
      backingVocalVolume: 1.0,
      instrumentalVolume: 1.0,
    });
  },

  // Helper to apply volume to Web Audio gain node
  applyVolumeToGainNode: (node: GainNode | null, volume: number) => {
    if (node) {
      node.gain.value = volume;
    }
  },
}));
