import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useShallow } from "zustand/react/shallow";
import {
  getLyricsSizeValue,
  parseLyricsSize,
  toggleVolume,
  type LyricsSize,
} from "@/utils/performanceControls";

/**
 * Hook for performance controls logic
 * Handles volume toggles and lyrics size conversions
 */
export const usePerformanceControlsLogic = () => {
  const {
    vocalVolume,
    backingVocalVolume,
    instrumentalVolume,
    lyricsSize,
    setVocalVolume,
    setBackingVocalVolume,
    setInstrumentalVolume,
    setLyricsSize,
  } = useKaraokePlayerStore(
    useShallow((s) => ({
      vocalVolume: s.vocalVolume,
      backingVocalVolume: s.backingVocalVolume,
      instrumentalVolume: s.instrumentalVolume,
      lyricsSize: s.lyricsSize,
      setVocalVolume: s.setVocalVolume,
      setBackingVocalVolume: s.setBackingVocalVolume,
      setInstrumentalVolume: s.setInstrumentalVolume,
      setLyricsSize: s.setLyricsSize,
    })),
  );

  const toggleVocalsVolume = () => {
    const newVolume = toggleVolume(vocalVolume, 1); // Max volume is 1 (100%)
    setVocalVolume(newVolume);
  };

  const toggleBackingVocalsVolume = () => {
    const newVolume = toggleVolume(backingVocalVolume, 1);
    setBackingVocalVolume(newVolume);
  };

  const toggleInstrumentalVolume = () => {
    const newVolume = toggleVolume(instrumentalVolume, 1); // Max volume is 1 (100%)
    setInstrumentalVolume(newVolume);
  };

  const handleLyricsSizeChange = (value: number) => {
    const newSize = parseLyricsSize(value);
    setLyricsSize(newSize);
  };

  const getLyricsSizeNumericValue = (size: LyricsSize) => {
    return getLyricsSizeValue(size);
  };

  return {
    // State
    vocalVolume,
    backingVocalVolume,
    instrumentalVolume,
    lyricsSize,

    // Actions
    toggleVocalsVolume,
    toggleBackingVocalsVolume,
    toggleInstrumentalVolume,
    handleLyricsSizeChange,
    getLyricsSizeNumericValue,

    // Setters (for direct access if needed)
    setVocalVolume,
    setBackingVocalVolume,
    setInstrumentalVolume,
    setLyricsSize,
  };
};
